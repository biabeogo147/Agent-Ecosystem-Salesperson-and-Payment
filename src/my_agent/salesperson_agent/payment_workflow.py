"""High-level helpers that prepare payloads for the payment agent."""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from google.adk.tools import FunctionTool

from my_a2a import (
    extract_payment_request,
    extract_status_request,
)
from my_a2a.payment_schemas.payment_enums import PaymentChannel

from .payment_tasks import (
    build_salesperson_create_order_task,
    build_salesperson_query_status_task,
)
from .salesperson_mcp_client import (
    SalespersonMcpClient,
    get_salesperson_mcp_client,
)


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
    "prepare_create_order_payload",
    "prepare_query_status_payload",
    "prepare_create_order_payload_tool",
    "prepare_query_status_payload_tool",
]
