from __future__ import annotations

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import PAYMENT_AGENT_SERVER_PORT
from src.my_agent.payment_agent import a2a_payment_logger as logger
from src.my_agent.payment_agent.payment_a2a.payment_agent_handler import PAYMENT_HANDLER
from src.my_agent.payment_agent.payment_callback_subscriber import (
    start_subscriber_background,
    stop_subscriber
)
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


@a2a_app.on_event("startup")
async def startup_event():
    """Start background tasks on app startup."""
    logger.info("Payment Agent A2A Server starting...")
    # Start Redis callback subscriber as background task
    start_subscriber_background()
    logger.info("Payment callback subscriber started")


@a2a_app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on app shutdown."""
    logger.info("Payment Agent A2A Server shutting down...")
    await stop_subscriber()
    logger.info("Payment callback subscriber stopped")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(a2a_app, host="0.0.0.0", port=PAYMENT_AGENT_SERVER_PORT)