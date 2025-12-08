from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from google.adk.sessions import InMemorySessionService

from src.my_agent.salesperson_agent import salesperson_agent_logger as logger
from src.my_agent.salesperson_agent.routers import agent_router, set_session_service
from src.config import SALESPERSON_AGENT_APP_HOST, SALESPERSON_AGENT_APP_PORT


_session_service: InMemorySessionService | None = None
_subscriber_task = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Application lifespan manager."""
    global _session_service, _subscriber_task

    logger.info(f"Salesperson Agent App starting on {SALESPERSON_AGENT_APP_HOST}:{SALESPERSON_AGENT_APP_PORT}")

    # Initialize session service
    _session_service = InMemorySessionService()
    set_session_service(_session_service)
    logger.info("Session service initialized")

    # Start notification subscriber
    from src.my_agent.salesperson_agent.salesperson_notification_subscriber import (
        start_subscriber_background,
        stop_subscriber
    )
    _subscriber_task = start_subscriber_background()
    logger.info("Notification subscriber started")

    yield

    # Shutdown
    logger.info("Salesperson Agent App shutting down...")
    await stop_subscriber()
    logger.info("Notification subscriber stopped")


app = FastAPI(
    title="Salesperson Agent App",
    description="Internal API for WebSocket Server to interact with ADK Salesperson Agent",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(agent_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=SALESPERSON_AGENT_APP_HOST,
        port=SALESPERSON_AGENT_APP_PORT
    )
