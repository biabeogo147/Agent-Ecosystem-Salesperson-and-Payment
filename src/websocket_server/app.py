import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import WS_SERVER_HOST, WS_SERVER_PORT
from src.websocket_server.routers import ws_router, auth_router
from src.websocket_server.services import start_notification_receiver


_notification_receiver_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    from src.websocket_server import get_ws_server_logger

    global _notification_receiver_task

    logger = get_ws_server_logger()
    logger.info(f"WebSocket Server starting on {WS_SERVER_HOST}:{WS_SERVER_PORT}")

    # TODO: xem lại notification receiver
    _notification_receiver_task = asyncio.create_task(start_notification_receiver())
    logger.info("Notification receiver started")

    yield

    # Shutdown
    logger.info("WebSocket Server shutting down...")
    if _notification_receiver_task and not _notification_receiver_task.done():
        _notification_receiver_task.cancel()
        try:
            await _notification_receiver_task
        except asyncio.CancelledError:
            pass
    logger.info("Notification receiver stopped")


app = FastAPI(
    title="WebSocket Notification Server",
    description="Real-time notification server for payment status updates",
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
app.include_router(ws_router)


if __name__ == "__main__":
    import uvicorn
    from src.websocket_server import get_ws_server_logger

    logger = get_ws_server_logger()
    logger.info(f"Starting WebSocket Server on {WS_SERVER_HOST}:{WS_SERVER_PORT}")
    uvicorn.run(app, host=WS_SERVER_HOST, port=WS_SERVER_PORT)
