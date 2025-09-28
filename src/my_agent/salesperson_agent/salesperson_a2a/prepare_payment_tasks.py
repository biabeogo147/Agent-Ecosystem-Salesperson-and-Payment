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

from typing import Any, Dict, Optional, Tuple, List
from uuid import uuid4

from a2a.types import Task, TaskStatus, TaskState, Message, Role, Part, TextPart, DataPart, Artifact

from my_a2a_common.payment_schemas import *
from my_a2a_common.payment_schemas.payment_enums import PaymentChannel
from my_a2a_common.constants import SALESPERSON_AGENT_NAME, PAYMENT_REQUEST_ARTIFACT_NAME, \
    PAYMENT_STATUS_ARTIFACT_NAME

from my_agent.payment_agent.payment_a2a.payment_agent_skills import CREATE_ORDER_SKILL_ID, QUERY_STATUS_SKILL_ID
from my_agent.salesperson_agent.salesperson_mcp_client import (
    SalespersonMcpClient,
    get_salesperson_mcp_client
)


async def _default_context_id_factory(prefix: str, *, client: SalespersonMcpClient | None = None) -> str:
    """Fetch a correlation ID by delegating to the MCP server."""
    client = client or get_salesperson_mcp_client()
    return await client.generate_context_id(prefix=prefix)


async def _default_url_factory(context_id: str, *, client: SalespersonMcpClient | None = None) -> Tuple[str, str]:
    """Return the pair of return/cancel URLs used by the payment gateway."""
    client = client or get_salesperson_mcp_client()
    return (
        await client.generate_return_url(context_id),
        await client.generate_cancel_url(context_id),
    )


def _ensure_customer(customer: Any) -> CustomerInfo:
    if isinstance(customer, CustomerInfo):
        return customer
    return CustomerInfo.model_validate(customer)


async def _resolve_items_via_product_tool(
    items: List[Dict],
    *,
    client: SalespersonMcpClient,
) -> List[PaymentItem]:
    """Normalise item payloads by looking up product metadata via the product tool."""
    resolved_items: List[PaymentItem] = []
    for raw_item in items:
        if not isinstance(raw_item, dict):
            raise TypeError("Each item must be provided as a mapping with 'name' and 'quantity'.")

        sku = raw_item.get("sku")
        name = raw_item.get("name")
        if not sku and not name:
            raise ValueError("Each item must include either 'sku' or 'name' field.")

        quantity = raw_item.get("quantity")
        if quantity is None:
            raise ValueError("Each item must include both 'name' and 'quantity' fields.")

        try:
            quantity_int = int(quantity)
        except (TypeError, ValueError) as exc:
            raise ValueError("Item 'quantity' must be an integer value.") from exc

        if quantity_int <= 0:
            raise ValueError("Item 'quantity' must be greater than zero.")

        product_payload = await client.find_product(query=name or sku)

        products = (product_payload or {}).get("data") or []
        if not products:
            raise ValueError(f"No product information returned for item '{name or sku}'.")

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
                f"Product information for '{name or sku}' is missing the required '{missing_key}' field."
            ) from exc

    return resolved_items


async def prepare_create_order_payload(
    items: List[Dict],
    customer: Dict[str, str],
    channel: PaymentChannel,
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
    return await prepare_create_order_payload_with_client(
        items,
        customer,
        channel,
        note=note,
        metadata=metadata,
        client=client,
    )


async def prepare_query_status_payload(context_id: str) -> Dict[str, Any]:
    """Build the task and payload needed for the payment status skill."""
    status_request = QueryStatusRequest(context_id=context_id)
    status_request_json = status_request.model_dump(mode="json")

    message = Message(
        message_id=str(uuid4()),
        role=Role.user,
        context_id=status_request.context_id,
        parts=[
            Part(
                root=TextPart(
                    text="Salesperson checks the status of the existing payment order.",
                    metadata={"speaker": SALESPERSON_AGENT_NAME},
                )
            ),
            Part(
                root=DataPart(
                    data=status_request_json
                )
            ),
        ],
    )

    artifact = Artifact(
        artifact_id=str(uuid4()),
        name=PAYMENT_STATUS_ARTIFACT_NAME,
        description="Status lookup request for an existing payment context id.",
        parts=[
            Part(
                root=DataPart(
                    data=status_request_json
                )
            ),
        ],
    )

    task_metadata = {
        "skill_id": QUERY_STATUS_SKILL_ID,
        "context_id": context_id,
    }

    task = Task(
        id=str(uuid4()),
        context_id=context_id,
        history=[message],
        artifacts=[artifact],
        status=TaskStatus(state=TaskState.submitted),
        metadata=task_metadata,
    )

    return {
        "context_id": status_request.context_id,
        "status_request": status_request.model_dump(mode="json"),
        "task": task.model_dump(mode="json"),
    }


async def prepare_create_order_payload_with_client(
    items: List[Dict],
    customer: Dict[str, str],
    channel: PaymentChannel,
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
    resolved_items = await _resolve_items_via_product_tool(items, client=client)

    context_id = await _default_context_id_factory("payment", client=client)
    return_url, cancel_url = await _default_url_factory(context_id, client=client)

    method = PaymentMethod(
        channel=channel,
        return_url=return_url,
        cancel_url=cancel_url,
    )

    payment_request = PaymentRequest(
        context_id=context_id,
        items=resolved_items,
        customer=_ensure_customer(customer),
        method=method,
        note=note,
        metadata=metadata,
    )

    request_payload = payment_request.model_dump(mode="json")

    message = Message(
        message_id=str(uuid4()),
        role=Role.user,
        context_id=payment_request.context_id,
        parts=[
            Part(
                root=TextPart(
                    text="Salesperson asks the payment agent to create an order.",
                    metadata={"speaker": SALESPERSON_AGENT_NAME},
                )
            ),
            Part(
                root=DataPart(
                    data=request_payload
                )
            ),
        ],
    )

    artifact = Artifact(
        artifact_id=str(uuid4()),
        name=PAYMENT_REQUEST_ARTIFACT_NAME,
        description="Structured payment order request sent by the salesperson agent.",
        parts=[
            Part(
                root=DataPart(
                    data=request_payload
                )
            ),
        ],
    )

    task_metadata = {
        "skill_id": CREATE_ORDER_SKILL_ID,
        "context_id": context_id,
    }
    if metadata:
        task_metadata["client_metadata"] = metadata

    task = Task(
        id=str(uuid4()),
        context_id=context_id,
        history=[message],
        artifacts=[artifact],
        status=TaskStatus(state=TaskState.submitted),
        metadata=task_metadata,
    )

    return {
        "context_id": payment_request.context_id,
        "payment_request": payment_request.model_dump(mode="json"),
        "task": task.model_dump(mode="json"),
    }


__all__ = [
    "prepare_create_order_payload",
    "prepare_query_status_payload",
    "prepare_create_order_payload_with_client",
]