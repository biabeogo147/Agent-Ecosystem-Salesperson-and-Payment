"""Build and parse A2A ``Message`` instances for the payment flow."""

from __future__ import annotations

from uuid import uuid4

from a2a.types import Message, Part, Role, TextPart

from my_a2a.payment_schemas import (
    PaymentRequest,
    PaymentResponse,
    QueryStatusRequest,
)

from .constants import (
    PAYMENT_AGENT_NAME,
    PAYMENT_REQUEST_KIND,
    PAYMENT_RESPONSE_KIND,
    PAYMENT_STATUS_KIND,
    SALESPERSON_AGENT_NAME,
)
from .content import build_data_part, extract_payload_from_parts


_DEF_SUMMARY_METADATA = {"media_type": "text/plain"}


def _text_part(text: str, *, speaker: str) -> Part:
    """Create a short summary ``TextPart`` that names the speaker."""

    return Part(
        root=TextPart(
            text=text,
            metadata={"speaker": speaker, **_DEF_SUMMARY_METADATA},
        )
    )


def build_create_order_message(payment_request: PaymentRequest) -> Message:
    """Wrap the checkout request in a user message.

    The ``role`` is set to :class:`~a2a.types.Role.user` because the salesperson
    initiates the task. We re-use the correlation ID as the message ``context_id``
    to make it easier for the server to group related updates.
    """

    payload = payment_request.model_dump(mode="json")
    return Message(
        message_id=str(uuid4()),
        role=Role.user,
        context_id=payment_request.correlation_id,
        parts=[
            _text_part(
                "Salesperson asks the payment agent to create an order.",
                speaker=SALESPERSON_AGENT_NAME,
            ),
            build_data_part(PAYMENT_REQUEST_KIND, payload),
        ],
    )


def build_query_status_message(status_request: QueryStatusRequest) -> Message:
    """Construct a follow-up message asking for the payment status."""

    payload = status_request.model_dump(mode="json")
    return Message(
        message_id=str(uuid4()),
        role=Role.user,
        context_id=status_request.correlation_id,
        parts=[
            _text_part(
                "Salesperson checks the status of the existing payment order.",
                speaker=SALESPERSON_AGENT_NAME,
            ),
            build_data_part(PAYMENT_STATUS_KIND, payload),
        ],
    )


def build_payment_response_message(response: PaymentResponse) -> Message:
    """Return the gateway's answer as an agent message."""

    payload = response.model_dump(mode="json")
    summary = f"Payment agent replies with status {response.status.value}."
    return Message(
        message_id=str(uuid4()),
        role=Role.agent,
        context_id=response.correlation_id,
        parts=[
            _text_part(summary, speaker=PAYMENT_AGENT_NAME),
            build_data_part(PAYMENT_RESPONSE_KIND, payload),
        ],
    )


def extract_payment_response(message: Message) -> PaymentResponse:
    """Convert the structured data ``Part`` back into a ``PaymentResponse``."""

    payload = extract_payload_from_parts(message.parts, expected_kind=PAYMENT_RESPONSE_KIND)
    return PaymentResponse.model_validate(payload)

__all__ = [
    "build_create_order_message",
    "build_query_status_message",
    "build_payment_response_message",
    "extract_payment_response",
]
