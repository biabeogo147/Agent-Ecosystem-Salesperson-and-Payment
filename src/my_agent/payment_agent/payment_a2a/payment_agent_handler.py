"""Server-side utilities for the payment agent."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, Awaitable

from a2a.types import Message, Task, AgentCard, MessageSendParams, AgentCapabilities
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from config import PAYMENT_AGENT_SERVER_HOST, PAYMENT_AGENT_SERVER_PORT
from my_a2a_common.a2a_salesperson_payment.constants import JSON_MEDIA_TYPE
from my_a2a_common.a2a_salesperson_payment.messages import build_payment_response_message
from my_a2a_common.payment_schemas import PaymentRequest, PaymentResponse, NextAction
from my_a2a_common.payment_schemas.payment_enums import (
    NextActionType,
    PaymentAction,
    PaymentStatus,
)

from my_agent.payment_agent.payment_a2a.payment_agent_skills import CREATE_ORDER_SKILL_ID, QUERY_STATUS_SKILL_ID, \
    CREATE_ORDER_SKILL, QUERY_STATUS_SKILL
from my_agent.payment_agent.payment_mcp_client import create_order, query_order_status
from utils.response_format_a2a import ResponseFormatA2A
from utils.status import Status


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("payment_agent_handler.log")
    ]
)
logger = logging.getLogger("payment_agent_handler")


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
        logger.info("PaymentAgentHandler initialised with skills: create_order, query_status")

    async def handle_message_send(self, request: Request) -> Response:
        try:
            payload = await request.json()
        except (json.JSONDecodeError, ValueError):
            logger.warning("message.send: invalid JSON body")
            return ResponseFormatA2A(
                status=Status.JSON_INVALID,
                message="Invalid JSON payload"
            ).to_response()

        request_id = payload.get("id")
        logger.info("message.send received (id=%s)", request_id)

        if payload.get("jsonrpc") != "2.0":
            logger.warning("message.send: invalid JSON-RPC version: %s", payload.get("jsonrpc"))
            return ResponseFormatA2A(
                request_id=request_id,
                status=Status.JSON_RPC_VERSION_INVALID,
                message="Invalid JSON-RPC version"
            ).to_response()

        if payload.get("method") != "message.send":
            logger.warning("message.send: unsupported method: %s", payload.get("method"))
            return ResponseFormatA2A(
                request_id=request_id,
                status=Status.METHOD_NOT_FOUND,
                message="Unsupported method"
            ).to_response()

        params_payload = payload.get("params")
        if params_payload is None:
            logger.warning("message.send: missing params")
            return ResponseFormatA2A(
                request_id=request_id,
                status=Status.MISSING_PARAMS,
                message="Missing params"
            ).to_response()

        try:
            params = MessageSendParams.model_validate(params_payload)
        except ValidationError as exc:
            logger.warning("message.send: invalid params (errors=%d)", len(exc.errors()))
            return ResponseFormatA2A(
                request_id=request_id,
                status=Status.INVALID_PARAMS,
                message="Invalid params",
                data=exc.errors()
            ).to_response()

        metadata = params.metadata or {}
        task_payload = metadata.get("task")
        if task_payload is None:
            logger.warning("message.send: missing task metadata")
            return ResponseFormatA2A(
                request_id=request_id,
                status=Status.MISSING_TASK_METADATA,
                message="Missing task metadata"
            ).to_response()

        hinted_skill = (task_payload.get("metadata") or {}).get("skill_id")
        if hinted_skill:
            logger.debug("message.send: hinted skill_id=%s", hinted_skill)

        try:
            task = Task.model_validate(task_payload)
        except ValidationError as exc:
            logger.warning("message.send: invalid task payload (errors=%d)", len(exc.errors()))
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

        logger.info("message.send handled successfully (id=%s)", request_id)
        response_format = ResponseFormatA2A(data=message.model_dump(mode="json")).to_response()
        return response_format

    async def handle_agent_card(self, _: Request) -> Response:
        logger.debug("agent-card requested")
        return JSONResponse(self._agent_card.model_dump(mode="json"))

    async def handle_task(self, task: Task) -> Message:
        """Inspect the task metadata to decide which skill to execute."""
        from my_a2a_common.a2a_salesperson_payment.content import extract_status_request, extract_payment_request

        skill_id = (task.metadata or {}).get("skill_id")
        logger.info("Dispatching task (skill_id=%s)", skill_id)

        if skill_id == CREATE_ORDER_SKILL_ID:
            request = extract_payment_request(task)
            logger.debug("create_order: correlation_id=%s", request.correlation_id)
            payload = request.model_dump(mode="json")
            raw_response = await self._create_order_tool(payload)
            response = PaymentResponse.model_validate(raw_response)
            validate_payment_response(
                response,
                expected_correlation_id=request.correlation_id,
                request=request,
            )
            logger.info("create_order done (correlation_id=%s, status=%s)", response.correlation_id, response.status.value)
            return build_payment_response_message(response)

        if skill_id == QUERY_STATUS_SKILL_ID:
            status_request = extract_status_request(task)
            logger.debug("query_status: correlation_id=%s", status_request.correlation_id)
            payload = status_request.model_dump(mode="json")
            raw_response = await self._query_status_tool(payload)
            response = PaymentResponse.model_validate(raw_response)
            validate_payment_response(
                response,
                expected_correlation_id=status_request.correlation_id,
            )
            logger.info("query_status done (correlation_id=%s, status=%s)", response.correlation_id, response.status.value)
            return build_payment_response_message(response)

        logger.warning("Unsupported skill requested: %s", skill_id)
        raise ValueError(f"Unsupported skill: {skill_id}")


def validate_payment_response(
    response: PaymentResponse,
    *,
    expected_correlation_id: str,
    request: PaymentRequest | None = None,
) -> None:
    """Run the safety checks required before replying to the salesperson."""
    logger.debug(
        "Validating response (cid_resp=%s, cid_exp=%s, status=%s, next=%s)",
        response.correlation_id,
        expected_correlation_id,
        getattr(response.status, "value", response.status),
        getattr(getattr(response, "next_action", None), "type", None),
    )

    if response.correlation_id != expected_correlation_id:
        logger.warning("Validation failed: correlation_id mismatch (expected=%s, got=%s)",
                       expected_correlation_id, response.correlation_id)
        raise ValueError("Correlation ID mismatch between request and response")

    if request is not None:
        next_action = response.next_action or NextAction()
        if request.action is PaymentAction.CREATE_ORDER:
            if next_action.type == NextActionType.REDIRECT and not (
                response.pay_url or next_action.url
            ):
                logger.warning("Validation failed: redirect without pay_url/url (cid=%s)", response.correlation_id)
                raise ValueError("Redirect action requires a pay_url or next_action.url")
            if next_action.type == NextActionType.SHOW_QR and not (
                response.qr_code_url or next_action.qr_code_url
            ):
                logger.warning("Validation failed: SHOW_QR without qr_code_url (cid=%s)", response.correlation_id)
                raise ValueError("SHOW_QR action requires a QR code URL")

    allowed_statuses = {
        PaymentStatus.PENDING,
        PaymentStatus.SUCCESS,
        PaymentStatus.FAILED,
        PaymentStatus.CANCELLED,
    }
    if response.status not in allowed_statuses:
        logger.warning("Validation failed: unsupported status %s (cid=%s)", response.status, response.correlation_id)
        raise ValueError(f"Unsupported payment status: {response.status}")

    if response.status is PaymentStatus.SUCCESS and not response.order_id:
        logger.warning("Validation failed: SUCCESS without order_id (cid=%s)", response.correlation_id)
        raise ValueError("Successful payments must include an order_id")


def build_payment_agent_card(base_url: str) -> AgentCard:
    """Describe the payment agent using the official SDK models."""
    capabilities = AgentCapabilities(
        streaming=False,
        push_notifications=False,
        state_transition_history=False,
    )

    logger.debug("Building agent card (base_url=%s)", base_url)
    return AgentCard(
        name="Payment Agent",
        description="Processes checkout requests coming from the salesperson agent.",
        version="1.0.0",
        url=base_url,
        default_input_modes=[JSON_MEDIA_TYPE],
        default_output_modes=[JSON_MEDIA_TYPE],
        capabilities=capabilities,
        skills=[CREATE_ORDER_SKILL, QUERY_STATUS_SKILL],
    )


_CARD_BASE_URL = f"http://{PAYMENT_AGENT_SERVER_HOST}:{PAYMENT_AGENT_SERVER_PORT}/"
_PAYMENT_HANDLER = PaymentAgentHandler(
    create_order_tool=create_order,
    query_status_tool=query_order_status,
    agent_card=build_payment_agent_card(_CARD_BASE_URL),
)


__all__ = [
    "PaymentAgentHandler",
    "validate_payment_response",
]