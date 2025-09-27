"""Helpers to build and read ``Part`` and ``Artifact`` objects."""

from __future__ import annotations

from typing import Iterable
from uuid import uuid4

from a2a.types import Artifact, DataPart, Part, Task

from .constants import JSON_MEDIA_TYPE, PAYMENT_REQUEST_KIND, PAYMENT_STATUS_KIND
from ..payment_schemas import PaymentRequest, QueryStatusRequest


def build_data_part(kind: str, payload: dict) -> Part:
    """Wrap a JSON payload in a :class:`DataPart` with helpful metadata."""
    data_part = DataPart(
        data=payload,
        metadata={
            "data_type": kind,
            "media_type": JSON_MEDIA_TYPE,
        },
    )
    return Part(root=data_part)


def build_artifact(kind: str, payload: dict, *, description: str) -> Artifact:
    """Create an :class:`Artifact` that stores the structured payload.

    Artifacts group the raw data in a way that downstream tools can discover the
    serialization format and semantic meaning through the metadata we attach to
    the contained :class:`DataPart`.
    """
    return Artifact(
        artifact_id=str(uuid4()),
        name=kind,
        description=description,
        parts=[build_data_part(kind, payload)],
    )


def extract_payload_from_parts(parts: Iterable[Part], *, expected_kind: str) -> dict:
    """Look for a ``DataPart`` with the desired ``data_type`` metadata."""
    for part in parts:
        if isinstance(part.root, DataPart):
            metadata = part.root.metadata or {}
            if metadata.get("data_type") == expected_kind:
                return part.root.data
    raise ValueError(f"No part with data_type '{expected_kind}' found")


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
    "build_data_part",
    "build_artifact",
    "extract_payload_from_parts",
    "extract_payment_request",
    "extract_status_request",
]