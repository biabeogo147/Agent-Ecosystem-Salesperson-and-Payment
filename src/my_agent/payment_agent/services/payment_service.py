from __future__ import annotations

from a2a.types import Task, Message

from my_agent.my_a2a_common.payment_schemas.payment_enums import PaymentStatus
from src.my_agent.my_a2a_common.payment_schemas import PaymentResponse
from src.my_agent.payment_agent.payment_mcp_client import get_payment_mcp_client
from src.my_agent.payment_agent.payment_a2a.payment_agent_skills import (
    CREATE_ORDER_SKILL_ID,
    QUERY_STATUS_SKILL_ID,
)
from my_agent.payment_agent.utils.a2a_util import extract_payment_request, extract_status_request, \
    validate_payment_response, build_payment_response_message
from src.my_agent.payment_agent import a2a_payment_logger as logger


async def handle_task(task: Task) -> Message:
    """
    Inspect the task metadata to decide which skill to execute.

    Args:
        task: The A2A task containing skill_id and payload

    Returns:
        Message containing the payment response

    Raises:
        ValueError: If skill_id is not supported
    """
    skill_id = (task.metadata or {}).get("skill_id")
    logger.info("Dispatching task (skill_id=%s)", skill_id)

    if skill_id == CREATE_ORDER_SKILL_ID:
        return await create_order(task)

    if skill_id == QUERY_STATUS_SKILL_ID:
        return await query_gateway_status(task)

    logger.warning("Unsupported skill requested: %s", skill_id)
    raise ValueError(f"Unsupported skill: {skill_id}")


async def create_order(task: Task) -> Message:
    """
    Create a payment order via MCP client.

    Args:
        task: Task containing PaymentRequest in artifacts

    Returns:
        Message containing the payment response
    """
    request = extract_payment_request(task)
    logger.debug("create_order: context_id=%s", request.context_id)

    client = get_payment_mcp_client()
    items_list = [item.model_dump(mode="json") for item in request.items]

    raw_response = await client.create_order(
        context_id=request.context_id,
        items=items_list,
        channel=request.channel.value if hasattr(request.channel, 'value') else request.channel,
        customer_name=request.customer.name or "",
        customer_email=request.customer.email or "",
        customer_phone=request.customer.phone or "",
        customer_shipping_address=request.customer.shipping_address or "",
        note=request.note or "",
        user_id=request.user_id,
        conversation_id=request.conversation_id
    )

    response = PaymentResponse.model_validate(raw_response)
    validate_payment_response(
        response,
        expected_context_id=request.context_id,
        request=request,
    )

    logger.info(
        "create_order done (context_id=%s, status=%s)",
        response.context_id, response.status.value
    )
    return build_payment_response_message(response)


async def query_gateway_status(task: Task) -> Message:
    """
    Query payment order status via MCP client.

    Args:
        task: Task containing QueryStatusRequest in artifacts

    Returns:
        Message containing the payment response
    """
    request = extract_status_request(task)
    logger.debug("query_status: context_id=%s", request.context_id)

    client = get_payment_mcp_client()
    raw_response = await client.query_gateway_status(order_id=request.order_id)

    response = PaymentResponse(
        context_id=request.context_id,
        status=PaymentStatus(raw_response.get("order", {}).get("status", "FAILED")),
    )
    validate_payment_response(
        response,
        expected_context_id=request.context_id,
    )

    logger.info(
        "query_status done (context_id=%s, status=%s)",
        response.context_id, response.status.value
    )
    return build_payment_response_message(response)
