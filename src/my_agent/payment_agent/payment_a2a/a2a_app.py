from __future__ import annotations

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import PAYMENT_AGENT_SERVER_PORT
from src.my_agent.payment_agent.payment_a2a.payment_agent_handler import PAYMENT_HANDLER
from src.utils.logger import set_app_context, AppLogger


class AppContextMiddleware(BaseHTTPMiddleware):
    """Middleware to set app logger context for all requests."""

    async def dispatch(self, request, call_next):
        with set_app_context(AppLogger.A2A_PAYMENT):
            response = await call_next(request)
        return response


routes = [
    Route("/.well-known/agent-card.json", PAYMENT_HANDLER.handle_agent_card, methods=["GET"]),
    Route("/", PAYMENT_HANDLER.handle_message_send, methods=["POST"]),
]

middleware = [
    Middleware(AppContextMiddleware)
]

a2a_app = Starlette(debug=False, routes=routes, middleware=middleware)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(a2a_app, host="0.0.0.0", port=PAYMENT_AGENT_SERVER_PORT)