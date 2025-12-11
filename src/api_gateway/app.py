# Patch asyncio.create_task to preserve context (MUST be first)
from src.utils.async_context import patch_asyncio_create_task
patch_asyncio_create_task()

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import API_GATEWAY_HOST, API_GATEWAY_PORT
from src.api_gateway.routers import ws_router, auth_router, conversation_router
from src.api_gateway.services import start_notification_receiver


_notification_receiver_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    from src.api_gateway import get_api_gateway_logger

    global _notification_receiver_task

    logger = get_api_gateway_logger()
    logger.info(f"API Gateway starting on {API_GATEWAY_HOST}:{API_GATEWAY_PORT}")

    _notification_receiver_task = asyncio.create_task(start_notification_receiver())
    logger.info("Notification receiver started")

    yield

    # Shutdown
    logger.info("API Gateway shutting down...")
    if _notification_receiver_task and not _notification_receiver_task.done():
        _notification_receiver_task.cancel()
        try:
            await _notification_receiver_task
        except asyncio.CancelledError:
            pass
    logger.info("Notification receiver stopped")


app = FastAPI(
    title="API Gateway",
    description="API Gateway for real-time chat and notification server",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth")
app.include_router(conversation_router, prefix="/conversations")
app.include_router(ws_router)


if __name__ == "__main__":
    import uvicorn
    from src.api_gateway import get_api_gateway_logger

    logger = get_api_gateway_logger()
    logger.info(f"Starting API Gateway on {API_GATEWAY_HOST}:{API_GATEWAY_PORT}")
    uvicorn.run(app, host=API_GATEWAY_HOST, port=API_GATEWAY_PORT)
