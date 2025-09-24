"""Helpers for building payment-related A2A tasks for the salesperson agent.

This module keeps the orchestration logic in one place so new developers can
read through the step-by-step flow:

1. Create a correlation ID that uniquely identifies the payment request.
2. Generate the return and cancel URLs bound to that correlation ID.
3. Use the shared :mod:`my_a2a` helpers to build the task payload that will be
   sent to the remote payment agent.

The high-level function :func:`build_salesperson_create_order_task` exposes an
easy-to-use wrapper around :func:`my_a2a.build_create_order_task` while still
following the protocol requirements from the payment team.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence, Tuple

from my_a2a import build_create_order_task, build_query_status_task
from my_a2a.payment_schemas.payment_enums import PaymentChannel

from .skills import (
    generate_cancel_url,
    generate_correlation_id,
    generate_return_url,
)


def _default_correlation_id_factory(prefix: str) -> str:
    """Delegate to :func:`generate_correlation_id` for actual ID creation."""

    return generate_correlation_id(prefix=prefix)


def _default_url_factory(correlation_id: str) -> Tuple[str, str]:
    """Return the pair of return/cancel URLs used by the payment gateway."""

    return (
        generate_return_url(correlation_id),
        generate_cancel_url(correlation_id),
    )


def build_salesperson_create_order_task(
    items: Sequence[Any],
    customer: Any,
    channel: PaymentChannel,
    *,
    note: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None,
) -> "Task":
    """Create the payment order task with the required system fields injected.

    Parameters
    ----------
    items:
        Collection of items the customer wants to purchase. The helper accepts
        both raw dictionaries and :class:`~my_a2a.payment_schemas.PaymentItem`
        instances; the underlying :func:`build_create_order_task` takes care of
        normalising them.
    customer:
        Information about the customer. Either a dictionary or a
        :class:`~my_a2a.payment_schemas.CustomerInfo` instance.
    channel:
        Which payment channel to use (``REDIRECT`` or ``QR``).
    note, metadata:
        Optional fields that are passed straight through to the payment agent.

    Returns
    -------
    Task
        A fully-prepared :class:`~a2a.types.Task` instance ready to be sent to
        the remote payment agent.
    """

    return build_create_order_task(
        items,
        customer,
        channel,
        _default_correlation_id_factory,
        _default_url_factory,
        note=note,
        metadata=metadata,
    )


def build_salesperson_query_status_task(correlation_id: str) -> "Task":
    """Wrapper that exposes query-status functionality alongside create order."""

    return build_query_status_task(correlation_id)


__all__ = [
    "build_salesperson_create_order_task",
    "build_salesperson_query_status_task",
]
