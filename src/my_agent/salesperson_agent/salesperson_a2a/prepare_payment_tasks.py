from __future__ import annotations

from typing import Any, Dict, Optional, List
from uuid import uuid4

from a2a.types import Task, TaskStatus, TaskState, Message, Role, Part, TextPart, DataPart, Artifact

from src.my_agent.my_a2a_common.payment_schemas import *
from src.my_agent.my_a2a_common.payment_schemas.payment_enums import PaymentChannel
from src.my_agent.my_a2a_common.constants import SALESPERSON_AGENT_NAME, PAYMENT_REQUEST_ARTIFACT_NAME, \
    PAYMENT_STATUS_ARTIFACT_NAME

from src.my_agent.payment_agent.payment_a2a.payment_agent_skills import CREATE_ORDER_SKILL_ID, QUERY_STATUS_SKILL_ID
from src.my_agent.salesperson_agent.salesperson_mcp_client import (
    SalespersonMcpClient,
    get_salesperson_mcp_client
)


def _generate_context_id(prefix: str = "ctx") -> str:
    """Generate context_id locally at salesperson agent.

    This is generated locally without calling MCP to avoid unnecessary network calls.
    The context_id is used to correlate payment requests across agents.
    """
    return f"{prefix}_{uuid4().hex[:12]}"


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


async def _reserve_stock_for_items(
    items: List[PaymentItem],
    *,
    client: SalespersonMcpClient,
) -> None:
    """Reserve stock cho tất cả items. Raise error nếu không đủ hàng."""
    for item in items:
        result = await client.reserve_stock(sku=item.sku, quantity=item.quantity)
        # Response format: {"status": "00", "message": "SUCCESS", "data": true/false}
        # Status.SUCCESS.value = "00"
        status = result.get("status", "")
        if status != "00":  # Not SUCCESS
            message = result.get("message", "Failed to reserve stock")
            raise ValueError(f"Cannot reserve stock for '{item.name}' (SKU: {item.sku}): {message}")


async def prepare_create_order_payload(
    items: List[Dict],
    customer: Dict[str, str],
    channel: PaymentChannel,
    user_id: int,
    conversation_id: int,
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
    from src.my_agent.salesperson_agent import salesperson_agent_logger

    client = get_salesperson_mcp_client()
    resolved_items = await _resolve_items_via_product_tool(items, client=client)
    await _reserve_stock_for_items(resolved_items, client=client)

    context_id = _generate_context_id(prefix="payment")

    salesperson_agent_logger.info(f"user_id: {user_id}")
    salesperson_agent_logger.info(f"conversation_id: {conversation_id}")
    salesperson_agent_logger.info(f"context_id: {context_id}")
    salesperson_agent_logger.info(f"Resolved items: {resolved_items}")
    salesperson_agent_logger.info(f"Customer: {customer}")
    salesperson_agent_logger.info(f"Channel: {channel}")
    salesperson_agent_logger.info(f"Note: {note}")
    salesperson_agent_logger.info(f"Metadata: {metadata}")

    payment_request = PaymentRequest(
        context_id=context_id,
        items=resolved_items,
        customer=_ensure_customer(customer),
        channel=channel,
        note=note,
        user_id=user_id,
        conversation_id=conversation_id,
        metadata=metadata,
    )

    request_payload = payment_request.model_dump(mode="json")

    message = Message(
        message_id=str(uuid4()),
        role=Role.user,
        context_id=context_id,
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


async def prepare_query_status_payload(
    context_id: str,
    order_id: Optional[int] = None
) -> Dict[str, Any]:
    """Build the task and payload needed for the payment status skill.

    Args:
        context_id: Correlation ID of the original payment request
        order_id: Optional specific order ID to query (if not provided, returns all orders for context_id)
    """
    status_request = QueryStatusRequest(context_id=context_id, order_id=order_id)
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
    if order_id:
        task_metadata["order_id"] = order_id

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
        "order_id": order_id,
        "status_request": status_request.model_dump(mode="json"),
        "task": task.model_dump(mode="json"),
    }