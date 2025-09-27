"""Server-side utilities for the payment agent."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, Awaitable

from a2a.types import Message, Task, AgentCard, MessageSendParams
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from my_a2a_common.a2a_salesperson_payment.messages import build_payment_response_message
from my_a2a_common.payment_schemas import PaymentRequest, PaymentResponse, NextAction
from my_a2a_common.payment_schemas.payment_enums import (
    NextActionType,
    PaymentAction,
    PaymentStatus,
)

from my_agent.payment_agent.payment_a2a.payment_agent_skills import CREATE_ORDER_SKILL_ID, QUERY_STATUS_SKILL_ID
from utils.response_format_a2a import ResponseFormatA2A
from utils.status import Status


logger = logging.getLogger(__name__)


class PaymentAgentHandler:
    """Route incoming tasks to business logic and guard the responses."""

    def __init__(
        self,
        *,
        create_order_tool: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]],
        query_status_tool: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]],
        agent_card: AgentCard,
    ) -> None:
        self._create_order_tool = create_order_tool
        self._query_status_tool = query_status_tool
        self._agent_card = agent_card

    async def handle_message_send(self, request: Request) -> Response:
        try:
            payload = await request.json()
        except (json.JSONDecodeError, ValueError):
            return ResponseFormatA2A(
                status=Status.JSON_INVALID,
                message="Invalid JSON payload"
            ).to_response()

        request_id = payload.get("id")
        if payload.get("jsonrpc") != "2.0":
            return ResponseFormatA2A(
                request_id=request_id,
                status=Status.JSON_RPC_VERSION_INVALID,
                message="Invalid JSON-RPC version"
            ).to_response()

        if payload.get("method") != "message.send":
            return ResponseFormatA2A(
                request_id=request_id,
                status=Status.METHOD_NOT_FOUND,
                message="Unsupported method"
            ).to_response()

        params_payload = payload.get("params")
        if params_payload is None:
            return ResponseFormatA2A(
                request_id=request_id,
                status=Status.MISSING_PARAMS,
                message="Missing params"
            ).to_response()

        try:
            params = MessageSendParams.model_validate(params_payload)
        except ValidationError as exc:
            return ResponseFormatA2A(
                request_id=request_id,
                status=Status.INVALID_PARAMS,
                message="Invalid params",
                data=exc.errors()
            ).to_response()

        metadata = params.metadata or {}
        task_payload = metadata.get("task")
        if task_payload is None:
            return ResponseFormatA2A(
                request_id=request_id,
                status=Status.MISSING_TASK_METADATA,
                message="Missing task metadata"
            ).to_response()

        try:
            task = Task.model_validate(task_payload)
        except ValidationError as exc:
            return ResponseFormatA2A(
                request_id=request_id,
                status=Status.INVALID_TASK_PAYLOAD,
                message="Invalid task payload",
                data=exc.errors(),
            ).to_response()

        try:
            message = await self.handle_task(task)
        except Exception as exc:
            logger.exception("Error while handling task")
            return ResponseFormatA2A(
                request_id=request_id,
                status=Status.UNKNOWN_ERROR,
                message="Internal error",
                data=str(exc),
            ).to_response()

        response_format = ResponseFormatA2A(data=message.model_dump(mode="json")).to_response()
        return response_format

    async def handle_agent_card(self, _: Request) -> Response:
        return JSONResponse(self._agent_card.model_dump(mode="json"))

    async def handle_task(self, task: Task) -> Message:
        """Inspect the task metadata to decide which skill to execute."""
        from my_a2a_common.a2a_salesperson_payment.content import extract_status_request, extract_payment_request

        skill_id = (task.metadata or {}).get("skill_id")
        if skill_id == CREATE_ORDER_SKILL_ID:
            request = extract_payment_request(task)
            payload = request.model_dump(mode="json")
            raw_response = await self._create_order_tool(payload)
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
            raw_response = await self._query_status_tool(payload)
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