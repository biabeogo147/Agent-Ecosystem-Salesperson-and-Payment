from __future__ import annotations

import json
from uuid import uuid4

from a2a.types import Message, Task, AgentCard, MessageSendParams, AgentCapabilities, Part, TextPart, Role, DataPart
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.config import PAYMENT_AGENT_SERVER_HOST, PAYMENT_AGENT_SERVER_PORT
from src.my_agent.my_a2a_common.constants import JSON_MEDIA_TYPE, PAYMENT_REQUEST_ARTIFACT_NAME, \
    PAYMENT_STATUS_ARTIFACT_NAME, PAYMENT_AGENT_NAME
from src.my_agent.my_a2a_common.payment_schemas import PaymentRequest, PaymentResponse, NextAction, QueryStatusRequest
from src.my_agent.my_a2a_common.payment_schemas.payment_enums import (
    NextActionType,
    PaymentAction,
    PaymentStatus,
)

from src.my_agent.payment_agent.payment_a2a.payment_agent_skills import CREATE_ORDER_SKILL_ID, QUERY_STATUS_SKILL_ID, \
    CREATE_ORDER_SKILL, QUERY_STATUS_SKILL
from src.my_agent.payment_agent.payment_mcp_client import PaymentMcpClient, get_payment_mcp_client
from src.my_agent.payment_agent import a2a_payment_logger as logger
from src.utils.response_format_jsonrpc import ResponseFormatJSONRPC
from src.utils.status import Status


class PaymentA2AHandler:
    """Route incoming tasks to business logic and guard the responses."""

    def __init__(
        self,
        *,
        payment_client: PaymentMcpClient,
        agent_card: AgentCard,
    ) -> None:
        self._payment_client = payment_client
        self._agent_card = agent_card
        logger.info("PaymentAgentHandler initialised with PaymentMcpClient")

    async def handle_message_send(self, request: Request) -> Response:
        try:
            payload = await request.json()
        except (json.JSONDecodeError, ValueError):
            logger.warning("message.send: invalid JSON body")
            return ResponseFormatJSONRPC(
                status=Status.JSON_INVALID,
                message="Invalid JSON payload"
            ).to_response()

        request_id = payload.get("id")
        logger.info("message.send received (id=%s)", request_id)
        logger.debug("Payload: %s", payload)

        if payload.get("jsonrpc") != "2.0":
            logger.warning("message.send: invalid JSON-RPC version: %s", payload.get("jsonrpc"))
            return ResponseFormatJSONRPC(
                id=request_id,
                status=Status.JSON_RPC_VERSION_INVALID,
                message="Invalid JSON-RPC version"
            ).to_response()

        if payload.get("method") != "message.send":
            logger.warning("message.send: unsupported method: %s", payload.get("method"))
            return ResponseFormatJSONRPC(
                id=request_id,
                status=Status.METHOD_NOT_FOUND,
                message="Unsupported method"
            ).to_response()

        params_payload = payload.get("params")
        if params_payload is None:
            logger.warning("message.send: missing params")
            return ResponseFormatJSONRPC(
                id=request_id,
                status=Status.MISSING_PARAMS,
                message="Missing params"
            ).to_response()

        try:
            params = MessageSendParams.model_validate(params_payload)
        except ValidationError as exc:
            logger.warning("message.send: invalid params (errors=%d)", len(exc.errors()))
            return ResponseFormatJSONRPC(
                id=request_id,
                status=Status.INVALID_PARAMS,
                message="Invalid params",
                data=exc.errors()
            ).to_response()

        metadata = params.metadata or {}
        task_payload = metadata.get("task")
        if task_payload is None:
            logger.warning("message.send: missing task metadata")
            return ResponseFormatJSONRPC(
                id=request_id,
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
            return ResponseFormatJSONRPC(
                id=request_id,
                status=Status.INVALID_TASK_PAYLOAD,
                message="Invalid task payload",
                data=exc.errors(),
            ).to_response()

        try:
            message = await self.handle_task(task)
        except Exception as exc:
            logger.exception("Error while handling task")
            return ResponseFormatJSONRPC(
                id=request_id,
                status=Status.UNKNOWN_ERROR,
                message="Internal error",
                data=str(exc),
            ).to_response()

        logger.info("message.send handled successfully (id=%s)", request_id)
        response_format = ResponseFormatJSONRPC(data=message.model_dump(mode="json")).to_response()
        return response_format

    async def handle_agent_card(self, _: Request) -> Response:
        logger.debug("agent-card requested")
        return JSONResponse(self._agent_card.model_dump(mode="json"))

    async def handle_task(self, task: Task) -> Message:
        """Inspect the task metadata to decide which skill to execute."""

        skill_id = (task.metadata or {}).get("skill_id")
        logger.info("Dispatching task (skill_id=%s)", skill_id)

        if skill_id == CREATE_ORDER_SKILL_ID:
            request = _extract_payment_request(task)
            logger.debug("create_order: context_id=%s", request.context_id)

            items_list = [item.model_dump(mode="json") for item in request.items]
            
            raw_response = await self._payment_client.create_order(
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
            logger.info("create_order done (context_id=%s, status=%s)", response.context_id, response.status.value)

            return _build_payment_response_message(response)

        if skill_id == QUERY_STATUS_SKILL_ID:
            status_request = _extract_status_request(task)
            logger.debug("query_status: context_id=%s", status_request.context_id)

            raw_response = await self._payment_client.query_order_status(
                context_id=status_request.context_id,
                order_id=status_request.order_id
            )
            response = PaymentResponse.model_validate(raw_response)
            validate_payment_response(
                response,
                expected_context_id=status_request.context_id,
            )
            logger.info("query_status done (context_id=%s, status=%s)", response.context_id, response.status.value)

            return _build_payment_response_message(response)

        logger.warning("Unsupported skill requested: %s", skill_id)
        raise ValueError(f"Unsupported skill: {skill_id}")


def validate_payment_response(
    response: PaymentResponse,
    *,
    expected_context_id: str,
    request: PaymentRequest | None = None,
) -> None:
    """Run the safety checks required before replying to the salesperson."""
    logger.debug(
        "Validating response (cid_resp=%s, cid_exp=%s, status=%s, next=%s)",
        response.context_id,
        expected_context_id,
        getattr(response.status, "value", response.status),
        getattr(getattr(response, "next_action", None), "type", None),
    )

    if response.context_id != expected_context_id:
        logger.warning("Validation failed: context_id mismatch (expected=%s, got=%s)",
                       expected_context_id, response.context_id)
        raise ValueError("Correlation ID mismatch between request and response")

    if request is not None:
        next_action = response.next_action or NextAction()
        if request.action is PaymentAction.CREATE_ORDER:
            if next_action.type == NextActionType.REDIRECT and not (
                response.pay_url or next_action.url
            ):
                logger.warning("Validation failed: redirect without pay_url/url (cid=%s)", response.context_id)
                raise ValueError("Redirect action requires a pay_url or next_action.url")
            if next_action.type == NextActionType.SHOW_QR and not (
                response.qr_code_url or next_action.qr_code_url
            ):
                logger.warning("Validation failed: SHOW_QR without qr_code_url (cid=%s)", response.context_id)
                raise ValueError("SHOW_QR action requires a QR code URL")

    allowed_statuses = {
        PaymentStatus.PENDING,
        PaymentStatus.SUCCESS,
        PaymentStatus.FAILED,
        PaymentStatus.CANCELLED,
    }
    if response.status not in allowed_statuses:
        logger.warning("Validation failed: unsupported status %s (cid=%s)", response.status, response.context_id)
        raise ValueError(f"Unsupported payment status: {response.status}")

    if response.status is PaymentStatus.SUCCESS and not response.order_id:
        logger.warning("Validation failed: SUCCESS without order_id (cid=%s)", response.context_id)
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


def _extract_payment_request(task: Task) -> PaymentRequest:
    """Retrieve the ``PaymentRequest`` carried inside a task."""
    if not task.history:
        raise ValueError("Task contains no messages")

    payload = None
    for artifact in task.artifacts:
        if artifact.name == PAYMENT_REQUEST_ARTIFACT_NAME:
            payload = artifact.parts[0].root.data
            break

    return PaymentRequest.model_validate(payload)


def _extract_status_request(task: Task) -> QueryStatusRequest:
    """Retrieve the status request payload from the task."""
    if not task.history:
        raise ValueError("Task contains no messages")

    payload = None
    for artifact in task.artifacts:
        if artifact.name == PAYMENT_STATUS_ARTIFACT_NAME:
            payload = artifact.parts[0].root.data
            break

    return QueryStatusRequest.model_validate(payload)


def _build_payment_response_message(response: PaymentResponse) -> Message:
    """Return the gateway's answer as an agent message."""
    return Message(
        message_id=str(uuid4()),
        role=Role.agent,
        context_id=response.context_id,
        parts=[
            Part(
                root=TextPart(
                    text=f"Payment agent replies with status {response.status.value}.",
                    metadata={"speaker": PAYMENT_AGENT_NAME},
                )
            ),
            Part(
                root=DataPart(
                    data=response.model_dump(mode="json"),
                )
            )
        ],
    )


_CARD_BASE_URL = f"http://{PAYMENT_AGENT_SERVER_HOST}:{PAYMENT_AGENT_SERVER_PORT}/"
PAYMENT_HANDLER = PaymentA2AHandler(
    payment_client=get_payment_mcp_client(),
    agent_card=build_payment_agent_card(_CARD_BASE_URL),
)