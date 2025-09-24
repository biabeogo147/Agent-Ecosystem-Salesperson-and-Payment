"""Utility tools that the salesperson agent can invoke while handling payments."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from config import CANCEL_URL, RETURN_URL

from google.adk.tools import FunctionTool


@dataclass(frozen=True)
class PaymentUrls:
    """Bundle the return and cancel URLs generated for a payment session."""

    return_url: str
    cancel_url: str


def generate_correlation_id(prefix: str = "payment") -> str:
    """Create a unique correlation identifier used to track payment requests."""

    return f"{prefix}-{uuid.uuid4()}"


def generate_return_url(correlation_id: str) -> str:
    """Build the return URL that the payment gateway should redirect to."""

    return f"{RETURN_URL}?cid={correlation_id}"


def generate_cancel_url(correlation_id: str) -> str:
    """Build the cancel URL that the payment gateway should redirect to."""

    return f"{CANCEL_URL}?cid={correlation_id}"


def get_payment_urls(correlation_id: str) -> PaymentUrls:
    """Convenience helper that returns both return and cancel URLs."""

    return PaymentUrls(
        return_url=generate_return_url(correlation_id),
        cancel_url=generate_cancel_url(correlation_id),
    )


generate_correlation_id_tool = FunctionTool(generate_correlation_id)
generate_return_url_tool = FunctionTool(generate_return_url)
generate_cancel_url_tool = FunctionTool(generate_cancel_url)