"""Server-side utilities for the payment agent."""

from __future__ import annotations

from typing import Any, Callable, Dict

from a2a.types import Message, Task

from my_a2a.payment_schemas import PaymentRequest, PaymentResponse
from my_a2a.payment_schemas.payment_enums import (
    NextActionType,
    PaymentAction,
    PaymentStatus,
)
from my_a2a.payment_schemas.next_action import NextAction

from my_a2a.a2a_payment.messages import build_payment_response_message
from my_agent.payment_agent.payment_a2a.skills import CREATE_ORDER_SKILL_ID, QUERY_STATUS_SKILL_ID
from my_a2a.a2a_payment.tasks import extract_payment_request, extract_status_request


class PaymentAgentHandler:
    """Route incoming tasks to business logic and guard the responses."""

    def __init__(
        self,
        *,
        create_order_tool: Callable[[Dict[str, Any]], Dict[str, Any]],
        query_status_tool: Callable[[Dict[str, Any]], Dict[str, Any]],
    ) -> None:
        self._create_order_tool = create_order_tool
        self._query_status_tool = query_status_tool

    def handle_task(self, task: Task) -> Message:
        """Inspect the task metadata to decide which skill to execute."""

        skill_id = (task.metadata or {}).get("skill_id")
        if skill_id == CREATE_ORDER_SKILL_ID:
            request = extract_payment_request(task)
            payload = request.model_dump(mode="json")
            raw_response = self._create_order_tool(payload)
            response = PaymentResponse.model_validate(raw_response)
            validate_payment_response(
                response,
                expected_correlation_id=request.correlation_id,
                request=request,
            )
            return build_payment_response_message(response)

        if skill_id == QUERY_STATUS_SKILL_ID:
            status_request = extract_status_request(task)
            payload = status_request.model_dump(mode="json")
            raw_response = self._query_status_tool(payload)
            response = PaymentResponse.model_validate(raw_response)
            validate_payment_response(
                response,
                expected_correlation_id=status_request.correlation_id,
            )
            return build_payment_response_message(response)

        raise ValueError(f"Unsupported skill: {skill_id}")


def validate_payment_response(
    response: PaymentResponse,
    *,
    expected_correlation_id: str,
    request: PaymentRequest | None = None,
) -> None:
    """Run the safety checks required before replying to the salesperson."""

    if response.correlation_id != expected_correlation_id:
        raise ValueError("Correlation ID mismatch between request and response")

    if request is not None:
        next_action = response.next_action or NextAction()
        if request.action is PaymentAction.CREATE_ORDER:
            if next_action.type == NextActionType.REDIRECT and not (
                response.pay_url or next_action.url
            ):
                raise ValueError("Redirect action requires a pay_url or next_action.url")
            if next_action.type == NextActionType.SHOW_QR and not (
                response.qr_code_url or next_action.qr_code_url
            ):
                raise ValueError("SHOW_QR action requires a QR code URL")

    allowed_statuses = {
        PaymentStatus.PENDING,
        PaymentStatus.SUCCESS,
        PaymentStatus.FAILED,
        PaymentStatus.CANCELLED,
    }
    if response.status not in allowed_statuses:
        raise ValueError(f"Unsupported payment status: {response.status}")

    if response.status is PaymentStatus.SUCCESS and not response.order_id:
        raise ValueError("Successful payments must include an order_id")

__all__ = [
    "PaymentAgentHandler",
    "validate_payment_response",
]
