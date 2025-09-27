"""Starlette application that exposes the payment agent over JSON-RPC."""

from __future__ import annotations

from a2a.types import AgentCapabilities, AgentCard
from starlette.applications import Starlette
from starlette.routing import Route

from my_a2a_common.a2a_salesperson_payment.constants import JSON_MEDIA_TYPE
from config import PAYMENT_AGENT_SERVER_HOST, PAYMENT_AGENT_SERVER_PORT

from payment_agent_handler import PaymentAgentHandler
from payment_agent_skills import CREATE_ORDER_SKILL, QUERY_STATUS_SKILL
from my_agent.payment_agent.payment_mcp_client import create_order, query_order_status


def build_payment_agent_card(base_url: str) -> AgentCard:
    """Describe the payment agent using the official SDK models."""
    capabilities = AgentCapabilities(
        streaming=False,
        push_notifications=False,
        state_transition_history=False,
    )

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

routes = [
    Route("/.well-known/agent.json", _PAYMENT_HANDLER.handle_agent_card, methods=["GET"]),
    Route("/", _PAYMENT_HANDLER.handle_message_send, methods=["POST"]),
]


a2a_app = Starlette(debug=False, routes=routes)


__all__ = ["a2a_app", "build_payment_agent_card"]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(a2a_app, host=PAYMENT_AGENT_SERVER_HOST, port=PAYMENT_AGENT_SERVER_PORT)