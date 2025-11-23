from __future__ import annotations

from starlette.applications import Starlette
from starlette.routing import Route

from src.config import PAYMENT_AGENT_SERVER_PORT
from src.my_agent.payment_agent.payment_a2a.payment_agent_handler import PAYMENT_HANDLER


routes = [
    Route("/.well-known/agent-card.json", PAYMENT_HANDLER.handle_agent_card, methods=["GET"]),
    Route("/", PAYMENT_HANDLER.handle_message_send, methods=["POST"]),
]
a2a_app = Starlette(debug=False, routes=routes)
__all__ = ["a2a_app"]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(a2a_app, host="0.0.0.0", port=PAYMENT_AGENT_SERVER_PORT)