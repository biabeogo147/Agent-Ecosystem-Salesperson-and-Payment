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

from typing import Any, Dict, Optional, Sequence, Tuple

from a2a.types import Task
from google.adk.tools import FunctionTool

from my_a2a_common import build_create_order_task, build_query_status_task, extract_payment_request, extract_status_request
from my_a2a_common.payment_schemas.payment_enums import PaymentChannel

from my_agent.salesperson_agent.salesperson_mcp_client import (
    SalespersonMcpClient,
    get_salesperson_mcp_client,
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


async def build_salesperson_create_order_task(
    items: Sequence[Any],
    customer: Any,
    channel: PaymentChannel,
    *,
    note: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None,
    mcp_client: SalespersonMcpClient | None = None,
) -> Task:
    """Create the payment order task with the required system fields injected.

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
    client = mcp_client or get_salesperson_mcp_client()
    correlation_id = await _default_correlation_id_factory("payment", client=client)
    return_url, cancel_url = await _default_url_factory(correlation_id, client=client)

    return await build_create_order_task(
        items,
        customer,
        channel,
        correlation_id,
        return_url,
        cancel_url,
        note=note,
        metadata=metadata,
    )


async def build_salesperson_query_status_task(correlation_id: str) -> Task:
    """Wrapper that exposes query-status functionality alongside create order."""
    return await build_query_status_task(correlation_id)


async def prepare_create_order_payload(
    items: Sequence[Any],
    customer: Any,
    channel: PaymentChannel,
    *,
    note: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None,
    mcp_client: SalespersonMcpClient | None = None,
) -> Dict[str, Any]:
    """Build the full payload required to call the payment agent's order skill.

    The helper returns both the structured :class:`~a2a.types.Task` and the
    flattened payment request payload so the salesperson agent can either pass
    the task wholesale to the A2A client or extract the JSON body to call the
    remote skill directly.
    """
    client = mcp_client or get_salesperson_mcp_client()
    task = await build_salesperson_create_order_task(
        items,
        customer,
        channel,
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


prepare_create_order_payload_tool = FunctionTool(prepare_create_order_payload)
prepare_query_status_payload_tool = FunctionTool(prepare_query_status_payload)


__all__ = [
    "build_salesperson_create_order_task",
    "build_salesperson_query_status_task",
    "prepare_create_order_payload",
    "prepare_query_status_payload",
    "prepare_create_order_payload_tool",
    "prepare_query_status_payload_tool",
]