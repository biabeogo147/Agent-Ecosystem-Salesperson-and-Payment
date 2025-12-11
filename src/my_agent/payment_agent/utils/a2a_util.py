from __future__ import annotations

from uuid import uuid4

from a2a.types import Task, Message, Role, Part, TextPart, DataPart, AgentCard, AgentCapabilities
from my_agent.my_a2a_common.constants import PAYMENT_REQUEST_ARTIFACT_NAME, PAYMENT_STATUS_ARTIFACT_NAME, \
    PAYMENT_AGENT_NAME, JSON_MEDIA_TYPE
from my_agent.my_a2a_common.payment_schemas import PaymentRequest, QueryStatusRequest, PaymentResponse, NextAction
from my_agent.my_a2a_common.payment_schemas.payment_enums import PaymentAction, NextActionType, PaymentStatus
from my_agent.payment_agent import a2a_payment_logger as logger
from my_agent.payment_agent.payment_a2a.payment_agent_skills import CREATE_ORDER_SKILL, QUERY_STATUS_SKILL


def extract_payment_request(task: Task) -> PaymentRequest:
    """Retrieve the PaymentRequest carried inside a task."""
    if not task.history:
        raise ValueError("Task contains no messages")

    payload = None
    for artifact in task.artifacts:
        if artifact.name == PAYMENT_REQUEST_ARTIFACT_NAME:
            payload = artifact.parts[0].root.data
            break

    return PaymentRequest.model_validate(payload)


def extract_status_request(task: Task) -> QueryStatusRequest:
    """Retrieve the status request payload from the task."""
    if not task.history:
        raise ValueError("Task contains no messages")

    payload = None
    for artifact in task.artifacts:
        if artifact.name == PAYMENT_STATUS_ARTIFACT_NAME:
            payload = artifact.parts[0].root.data
            break

    return QueryStatusRequest.model_validate(payload)


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
        logger.warning(
            "Validation failed: context_id mismatch (expected=%s, got=%s)",
            expected_context_id, response.context_id
        )
        raise ValueError("Correlation ID mismatch between request and response")

    if request is not None:
        next_action = response.next_action or NextAction()
        if request.action is PaymentAction.CREATE_ORDER:
            if next_action.type == NextActionType.REDIRECT and not (
                response.pay_url or next_action.url
            ):
                logger.warning(
                    "Validation failed: redirect without pay_url/url (cid=%s)",
                    response.context_id
                )
                raise ValueError("Redirect action requires a pay_url or next_action.url")
            if next_action.type == NextActionType.SHOW_QR and not (
                response.qr_code_url or next_action.qr_code_url
            ):
                logger.warning(
                    "Validation failed: SHOW_QR without qr_code_url (cid=%s)",
                    response.context_id
                )
                raise ValueError("SHOW_QR action requires a QR code URL")

    allowed_statuses = {
        PaymentStatus.PENDING,
        PaymentStatus.SUCCESS,
        PaymentStatus.FAILED,
        PaymentStatus.CANCELLED,
    }
    if response.status not in allowed_statuses:
        logger.warning(
            "Validation failed: unsupported status %s (cid=%s)",
            response.status, response.context_id
        )
        raise ValueError(f"Unsupported payment status: {response.status}")

    if response.status is PaymentStatus.SUCCESS and not response.order_id:
        logger.warning(
            "Validation failed: SUCCESS without order_id (cid=%s)",
            response.context_id
        )
        raise ValueError("Successful payments must include an order_id")


def build_payment_response_message(response: PaymentResponse) -> Message:
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
