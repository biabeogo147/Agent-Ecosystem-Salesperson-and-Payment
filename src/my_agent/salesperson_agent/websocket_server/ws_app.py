"""
WebSocket server application for real-time notifications.

This FastAPI application provides:
1. WebSocket endpoint for frontend clients to receive real-time notifications
2. Redis subscriber for payment notifications (integrated via lifespan)
3. Automatic push of payment status updates to connected clients
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from src.config import WS_SERVER_HOST, WS_SERVER_PORT
from src.my_agent.salesperson_agent.websocket_server import ws_server_logger as logger
from src.my_agent.salesperson_agent.websocket_server.connection_manager import manager


# Global reference to subscriber task
_subscriber_task: asyncio.Task | None = None


async def notification_callback(session_id: str, message: dict) -> None:
    """
    Callback function called when a notification is processed.
    Sends the message to all WebSocket clients in the given session.

    Args:
        session_id: The chat session ID
        message: The notification message to send
    """
    sent_count = await manager.send_to_session(session_id, message)
    logger.info(
        f"Notification pushed to {sent_count} client(s) for session: {session_id}"
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    Application lifespan manager.

    Startup:
    - Starts the Redis notification subscriber as a background task

    Shutdown:
    - Stops the notification subscriber
    """
    global _subscriber_task

    logger.info(f"WebSocket Server starting on {WS_SERVER_HOST}:{WS_SERVER_PORT}")

    # Import here to avoid circular imports
    from src.my_agent.salesperson_agent.salesperson_notification_subscriber import (
        start_subscriber_with_callback,
        stop_subscriber,
    )

    # Start notification subscriber with our callback
    _subscriber_task = start_subscriber_with_callback(notification_callback)
    logger.info("Notification subscriber started as background task")

    yield

    # Shutdown
    logger.info("WebSocket Server shutting down...")
    await stop_subscriber()
    logger.info("Notification subscriber stopped")


app = FastAPI(
    title="WebSocket Notification Server",
    description="Real-time notification server for payment status updates",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for clients to connect and receive notifications.

    Clients connect with their session_id (chat session ID) and will receive
    all payment status updates for that session.

    Args:
        websocket: The WebSocket connection
        session_id: The chat session ID to subscribe to
    """
    await manager.connect(websocket, session_id)

    try:
        while True:
            # Keep connection alive, receive any client messages
            data = await websocket.receive_text()
            logger.debug(f"Received from client [{session_id}]: {data}")

    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
        logger.info(f"Client disconnected from session: {session_id}")

    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        manager.disconnect(websocket, session_id)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_sessions": len(manager.get_active_sessions()),
        "total_connections": manager.get_connection_count()
    }


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting WebSocket Server on {WS_SERVER_HOST}:{WS_SERVER_PORT}")
    uvicorn.run(app, host=WS_SERVER_HOST, port=WS_SERVER_PORT)
