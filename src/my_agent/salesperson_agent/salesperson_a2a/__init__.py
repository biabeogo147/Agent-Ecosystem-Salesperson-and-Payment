"""Utilities for delegating payment tasks over A2A."""

from .client import (
    SalespersonA2AClient,
    get_salesperson_a2a_client,
    set_salesperson_a2a_client,
)
from .payment_tasks import (
    extract_payment_request,
    extract_status_request,
    prepare_create_order_payload,
    prepare_create_order_payload_tool,
    prepare_create_order_payload_with_client,
    prepare_query_status_payload,
    prepare_query_status_payload_tool,
)
from .remote_agent import get_remote_payment_agent, get_payment_agent_card


__all__ = [
    "SalespersonA2AClient",
    "get_salesperson_a2a_client",
    "set_salesperson_a2a_client",
    "extract_payment_request",
    "extract_status_request",
    "get_payment_agent_card",
    "get_remote_payment_agent",
    "prepare_create_order_payload",
    "prepare_create_order_payload_tool",
    "prepare_create_order_payload_with_client",
    "prepare_query_status_payload",
    "prepare_query_status_payload_tool",
]

