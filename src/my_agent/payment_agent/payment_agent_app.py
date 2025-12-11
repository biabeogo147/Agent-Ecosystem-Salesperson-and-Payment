from __future__ import annotations

# Patch asyncio.create_task to preserve context (MUST be first)
from src.utils.async_context import patch_asyncio_create_task
patch_asyncio_create_task()

from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import PAYMENT_AGENT_SERVER_PORT
from src.my_agent.payment_agent import a2a_payment_logger as logger
from src.my_agent.payment_agent.routers import a2a_router
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


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup
    logger.info("Payment Agent App starting...")
    start_subscriber_background()
    logger.info("Payment callback subscriber started")
    yield
    # Shutdown
    logger.info("Payment Agent App shutting down...")
    await stop_subscriber()
    logger.info("Payment callback subscriber stopped")


payment_agent_app = FastAPI(
    title="Payment Agent",
    description="A2A Payment Agent for processing checkout requests",
    version="1.0.0",
    lifespan=lifespan
)

payment_agent_app.add_middleware(AppContextMiddleware)
payment_agent_app.include_router(a2a_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(payment_agent_app, host="0.0.0.0", port=PAYMENT_AGENT_SERVER_PORT)
