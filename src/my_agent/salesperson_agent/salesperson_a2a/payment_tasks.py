"""Helpers for building payment-related A2A tasks for the salesperson agent.

This module keeps the orchestration logic in one place so new developers can
read through the step-by-step flow:

1. Create a correlation ID that uniquely identifies the payment request.  The
   ID now comes from the MCP server so we can share the generator across
   multiple salesperson deployments.
2. Generate the return and cancel URLs bound to that correlation ID.
3. Use the shared :mod:`my_a2a_common` helpers to build the task payload that will be
   sent to the remote payment agent.

The high-level function :func:`build_salesperson_create_order_task` exposes an
easy-to-use wrapper around :func:`my_a2a_common.build_create_order_task` while still
following the protocol requirements from the payment team.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence, Tuple, List, Literal
from uuid import uuid4

from a2a.types import Task, TaskStatus, TaskState
from google.adk.tools import FunctionTool

from my_a2a_common.payment_schemas import *
from my_a2a_common.payment_schemas import PaymentRequest, QueryStatusRequest
from my_a2a_common.payment_schemas.payment_enums import PaymentChannel
from my_a2a_common.a2a_salesperson_payment.content import build_artifact, extract_payload_from_parts
from my_a2a_common.a2a_salesperson_payment.constants import PAYMENT_REQUEST_KIND, PAYMENT_STATUS_KIND

from my_agent.payment_agent.payment_a2a.payment_agent_skills import CREATE_ORDER_SKILL_ID, QUERY_STATUS_SKILL_ID
from my_agent.salesperson_agent.salesperson_mcp_client import (
    SalespersonMcpClient,
    get_salesperson_mcp_client, prepare_find_product_with_client, prepare_find_product_tool,
)


async def _default_correlation_id_factory(
    prefix: str, *, client: SalespersonMcpClient | None = None
) -> str:
    """Fetch a correlation ID by delegating to the MCP server."""
    client = client or get_salesperson_mcp_client()
    return await client.generate_correlation_id(prefix=prefix)


async def _default_url_factory(
    correlation_id: str, *, client: SalespersonMcpClient | None = None
) -> Tuple[str, str]:
    """Return the pair of return/cancel URLs used by the payment gateway."""
    client = client or get_salesperson_mcp_client()
    return (
        await client.generate_return_url(correlation_id),
        await client.generate_cancel_url(correlation_id),
    )


def _ensure_payment_item(item: Any) -> PaymentItem:
    if isinstance(item, PaymentItem):
        return item
    return PaymentItem.model_validate(item)


def _ensure_customer(customer: Any) -> CustomerInfo:
    if isinstance(customer, CustomerInfo):
        return customer
    return CustomerInfo.model_validate(customer)


def _base_task_metadata(skill_id: str, correlation_id: str) -> Dict[str, Any]:
    return {
        "skill_id": skill_id,
        "correlation_id": correlation_id,
    }


def extract_payment_request(task: Task) -> PaymentRequest:
    """Retrieve the ``PaymentRequest`` carried inside a task."""
    if not task.history:
        raise ValueError("Task contains no messages")

    payload = extract_payload_from_parts(
        task.history[-1].parts,
        expected_kind=PAYMENT_REQUEST_KIND,
    )
    return PaymentRequest.model_validate(payload)


def extract_status_request(task: Task) -> QueryStatusRequest:
    """Retrieve the status request payload from the task."""
    if not task.history:
        raise ValueError("Task contains no messages")

    payload = extract_payload_from_parts(
        task.history[-1].parts,
        expected_kind=PAYMENT_STATUS_KIND,
    )
    return QueryStatusRequest.model_validate(payload)


async def build_salesperson_create_order_task(
    items: Sequence[Any],
    customer: Any,
    channel: PaymentChannel,
    *,
    note: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None,
    mcp_client: SalespersonMcpClient | None = None,
) -> Task:
    """Create the payment order task with the required system fields injected to be sent to the payment agent.

    The helper ensures the salesperson injects the required system fields
    (correlation ID, return URL and cancel URL) before handing off the work to
    the remote agent.

    Parameters
    ----------
    items:
        Collection of items the customer wants to purchase. The helper accepts
        both raw dictionaries and :class:`~my_a2a_common.payment_schemas.PaymentItem`
        instances; the underlying :func:`build_create_order_task` takes care of
        normalising them.
    customer:
        Information about the customer. Either a dictionary or a
        :class:`~my_a2a_common.payment_schemas.CustomerInfo` instance.
    channel:
        Which payment channel to use (``REDIRECT`` or ``QR``).
    note, metadata:
        Optional fields that are passed straight through to the payment agent.
    mcp_client:
        Optional override used by tests to inject a fake MCP client. When not
        provided the module-level singleton is used.

    Returns
    -------
    Task
        A fully-prepared :class:`~a2a.types.Task` instance ready to be sent to
        the remote payment agent.
    """
    from my_a2a_common import build_create_order_message

    client = mcp_client or get_salesperson_mcp_client()
    correlation_id = await _default_correlation_id_factory("payment", client=client)
    return_url, cancel_url = await _default_url_factory(correlation_id, client=client)

    method = PaymentMethod(
        channel=channel,
        return_url=return_url,
        cancel_url=cancel_url,
    )

    payment_request = PaymentRequest(
        correlation_id=correlation_id,
        items=[_ensure_payment_item(item) for item in items],
        customer=_ensure_customer(customer),
        method=method,
        note=note,
        metadata=metadata,
    )

    message = build_create_order_message(payment_request)

    request_payload = payment_request.model_dump(mode="json")
    artifact = build_artifact(
        PAYMENT_REQUEST_KIND,
        request_payload,
        description="Structured payment order request sent by the salesperson agent.",
    )

    task_metadata = _base_task_metadata(CREATE_ORDER_SKILL_ID, correlation_id)
    if metadata:
        task_metadata["client_metadata"] = metadata

    return Task(
        id=str(uuid4()),
        context_id=correlation_id,
        history=[message],
        artifacts=[artifact],
        status=TaskStatus(state=TaskState.submitted),
        metadata=task_metadata,
    )


async def build_salesperson_query_status_task(correlation_id: str) -> Task:
    """Wrapper that exposes query-status functionality alongside create order."""
    from my_a2a_common import build_query_status_message

    status_request = QueryStatusRequest(correlation_id=correlation_id)
    message = build_query_status_message(status_request)

    artifact = build_artifact(
        PAYMENT_STATUS_KIND,
        status_request.model_dump(mode="json"),
        description="Status lookup request for an existing payment correlation.",
    )

    task_metadata = _base_task_metadata(QUERY_STATUS_SKILL_ID, correlation_id)

    return Task(
        id=str(uuid4()),
        context_id=correlation_id,
        history=[message],
        artifacts=[artifact],
        status=TaskStatus(state=TaskState.submitted),
        metadata=task_metadata,
    )


async def _resolve_items_via_product_tool(
    items: Sequence[Any],
    *,
    client: SalespersonMcpClient | None = None,
) -> List[PaymentItem]:
    """Normalise item payloads by looking up product metadata via the product tool."""

    resolved_items: List[PaymentItem] = []
    for raw_item in items:
        if not isinstance(raw_item, dict):
            raise TypeError("Each item must be provided as a mapping with 'name' and 'quantity'.")

        name = raw_item.get("name")
        quantity = raw_item.get("quantity")
        if not name or quantity is None:
            raise ValueError("Each item must include both 'name' and 'quantity' fields.")

        try:
            quantity_int = int(quantity)
        except (TypeError, ValueError) as exc:
            raise ValueError("Item 'quantity' must be an integer value.") from exc

        if quantity_int <= 0:
            raise ValueError("Item 'quantity' must be greater than zero.")

        if client is None:
            product_payload = await prepare_find_product_tool.func(query=name)
        else:
            product_payload = await prepare_find_product_with_client(query=name, client=client)

        products = (product_payload or {}).get("data") or []
        if not products:
            raise ValueError(f"No product information returned for item '{name}'.")

        product = products[0]
        try:
            resolved_items.append(
                PaymentItem(
                    sku=str(product["sku"]),
                    name=str(product["name"]),
                    quantity=quantity_int,
                    unit_price=float(product["price"]),
                    currency=str(product.get("currency", "USD")),
                )
            )
        except KeyError as exc:
            missing_key = exc.args[0]
            raise ValueError(
                f"Product information for '{name}' is missing the required '{missing_key}' field."
            ) from exc

    return resolved_items


async def prepare_create_order_payload(
    items: List[Any],
    customer: Any,
    channel: Literal["redirect", "qr"],
    *,
    note: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Build the full payload required to call the payment agent's order skill.

    The helper returns both the structured :class:`~a2a.types.Task` and the
    flattened payment request payload so the salesperson agent can either pass
    the task wholesale to the A2A client or extract the JSON body to call the
    remote skill directly.
    """
    client = get_salesperson_mcp_client()
    channel_enum = PaymentChannel(channel)
    resolved_items = await _resolve_items_via_product_tool(items)

    task = await build_salesperson_create_order_task(
        resolved_items,
        customer,
        channel_enum,
        note=note,
        metadata=metadata,
        mcp_client=client,
    )
    payment_request = extract_payment_request(task)
    return {
        "correlation_id": payment_request.correlation_id,
        "payment_request": payment_request.model_dump(mode="json"),
        "task": task.model_dump(mode="json"),
    }


async def prepare_query_status_payload(
    correlation_id: str,
) -> Dict[str, Any]:
    """Build the task and payload needed for the payment status skill."""
    task = await build_salesperson_query_status_task(correlation_id)
    status_request = extract_status_request(task)
    return {
        "correlation_id": status_request.correlation_id,
        "status_request": status_request.model_dump(mode="json"),
        "task": task.model_dump(mode="json"),
    }


async def prepare_create_order_payload_with_client(
    items: List[Any],
    customer: Any,
    channel: Literal["redirect", "qr"],
    *,
    note: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None,
    client: SalespersonMcpClient,
) -> Dict[str, Any]:
    """Build the full payload required to call the payment agent's order skill.

    The helper returns both the structured :class:`~a2a.types.Task` and the
    flattened payment request payload so the salesperson agent can either pass
    the task wholesale to the A2A client or extract the JSON body to call the
    remote skill directly.
    """
    channel_enum = PaymentChannel(channel)
    resolved_items = await _resolve_items_via_product_tool(items, client=client)

    task = await build_salesperson_create_order_task(
        resolved_items,
        customer,
        channel_enum,
        note=note,
        metadata=metadata,
        mcp_client=client,
    )
    payment_request = extract_payment_request(task)
    return {
        "correlation_id": payment_request.correlation_id,
        "payment_request": payment_request.model_dump(mode="json"),
        "task": task.model_dump(mode="json"),
    }


prepare_create_order_payload_tool = FunctionTool(prepare_create_order_payload)
prepare_query_status_payload_tool = FunctionTool(prepare_query_status_payload)


__all__ = [
    "build_salesperson_create_order_task",
    "build_salesperson_query_status_task",
    "prepare_create_order_payload",
    "prepare_query_status_payload",
    "prepare_create_order_payload_tool",
    "prepare_query_status_payload_tool",
    "prepare_create_order_payload_with_client",
    "extract_payment_request",
    "extract_status_request",
]