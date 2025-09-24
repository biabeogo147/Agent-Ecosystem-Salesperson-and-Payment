"""Utilities that assemble complete A2A ``Task`` objects for payments."""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence
from uuid import uuid4

from a2a.types import Task, TaskState, TaskStatus

from my_a2a.payment_schemas import (
    CustomerInfo,
    PaymentItem,
    PaymentMethod,
    PaymentRequest,
    QueryStatusRequest,
)
from my_a2a.payment_schemas.payment_enums import PaymentChannel

from .constants import PAYMENT_REQUEST_KIND, PAYMENT_STATUS_KIND
from .content import build_artifact, extract_payload_from_parts
from .messages import build_create_order_message, build_query_status_message
from .skills import CREATE_ORDER_SKILL_ID, QUERY_STATUS_SKILL_ID


def _ensure_payment_item(item: Any) -> PaymentItem:
    if isinstance(item, PaymentItem):
        return item
    return PaymentItem.model_validate(item)


def _ensure_customer(customer: Any) -> CustomerInfo:
    if isinstance(customer, CustomerInfo):
        return customer
    return CustomerInfo.model_validate(customer)


def _base_task_metadata(skill_id: str, correlation_id: str) -> Dict[str, Any]:
    return {
        "skill_id": skill_id,
        "correlation_id": correlation_id,
    }


async def build_create_order_task(
    items: Sequence[Any],
    customer: Any,
    channel: PaymentChannel,
    correlation_id: str,
    return_url: str, cancel_url: str,
    *,
    note: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None,
) -> Task:
    """Create a ``Task`` ready to be sent to the payment agent.

    The helper ensures the salesperson injects the required system fields
    (correlation ID, return URL and cancel URL) before handing off the work to
    the remote agent.
    """
    method = PaymentMethod(
        channel=channel,
        return_url=return_url,
        cancel_url=cancel_url,
    )

    payment_request = PaymentRequest(
        correlation_id=correlation_id,
        items=[_ensure_payment_item(item) for item in items],
        customer=_ensure_customer(customer),
        method=method,
        note=note,
        metadata=metadata,
    )

    message = build_create_order_message(payment_request)

    request_payload = payment_request.model_dump(mode="json")
    artifact = build_artifact(
        PAYMENT_REQUEST_KIND,
        request_payload,
        description="Structured payment order request sent by the salesperson agent.",
    )

    task_metadata = _base_task_metadata(CREATE_ORDER_SKILL_ID, correlation_id)
    if metadata:
        task_metadata["client_metadata"] = metadata

    return Task(
        id=str(uuid4()),
        context_id=correlation_id,
        history=[message],
        artifacts=[artifact],
        status=TaskStatus(state=TaskState.submitted),
        metadata=task_metadata,
    )


async def build_query_status_task(correlation_id: str) -> Task:
    """Construct a task for querying payment status."""
    status_request = QueryStatusRequest(correlation_id=correlation_id)
    message = build_query_status_message(status_request)

    artifact = build_artifact(
        PAYMENT_STATUS_KIND,
        status_request.model_dump(mode="json"),
        description="Status lookup request for an existing payment correlation.",
    )

    task_metadata = _base_task_metadata(QUERY_STATUS_SKILL_ID, correlation_id)

    return Task(
        id=str(uuid4()),
        context_id=correlation_id,
        history=[message],
        artifacts=[artifact],
        status=TaskStatus(state=TaskState.submitted),
        metadata=task_metadata,
    )


def extract_payment_request(task: Task) -> PaymentRequest:
    """Retrieve the ``PaymentRequest`` carried inside a task."""
    if not task.history:
        raise ValueError("Task contains no messages")

    payload = extract_payload_from_parts(
        task.history[-1].parts,
        expected_kind=PAYMENT_REQUEST_KIND,
    )
    return PaymentRequest.model_validate(payload)


def extract_status_request(task: Task) -> QueryStatusRequest:
    """Retrieve the status request payload from the task."""
    if not task.history:
        raise ValueError("Task contains no messages")

    payload = extract_payload_from_parts(
        task.history[-1].parts,
        expected_kind=PAYMENT_STATUS_KIND,
    )
    return QueryStatusRequest.model_validate(payload)

__all__ = [
    "build_create_order_task",
    "build_query_status_task",
    "extract_payment_request",
    "extract_status_request",
]
