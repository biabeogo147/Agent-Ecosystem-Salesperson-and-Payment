import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware

from src.config import WS_SERVER_HOST, WS_SERVER_PORT
from src.my_agent.salesperson_agent.websocket_server import ws_server_logger as logger
from src.my_agent.salesperson_agent.websocket_server.connection_manager import manager
from src.my_agent.salesperson_agent.websocket_server.auth import (
    auth_router,
)
from my_agent.salesperson_agent.websocket_server.auth import extract_token_from_query, authenticate_websocket

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
    logger.info(f"Notification pushed to {sent_count} client(s) for session: {session_id}")


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

    from src.my_agent.salesperson_agent.salesperson_notification_subscriber import (
        start_subscriber_with_callback,
        stop_subscriber,
    )

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth")


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(None)
):
    """
    WebSocket endpoint for clients to connect and receive notifications.

    Flow:
    1. Client connects with JWT token in query param: /ws/{session_id}?token=<JWT>
    2. Server validates JWT and extracts user_id
    3. Client sends initial message: {"type": "register", "conversation_id": "..."}
    4. Server registers session in Redis for multi-device notification
    5. Client receives notifications for that conversation

    Args:
        websocket: The WebSocket connection
        session_id: The chat session ID to subscribe to
        token: JWT token for authentication (query param)
    """
    # Step 1: Authenticate using auth module
    validated_token = extract_token_from_query(token)
    user_info = await authenticate_websocket(websocket, validated_token, session_id)
    if not user_info:
        # authenticate_websocket already closed the connection with appropriate error
        return

    user_id = user_info.user_id

    # Step 2: Accept connection
    await manager.connect(websocket, session_id)

    try:
        # Step 3: Wait for initial register message with conversation_id
        try:
            first_message_raw = await asyncio.wait_for(
                websocket.receive_text(),
                timeout=30.0  # 30 seconds timeout for registration
            )
            first_message = json.loads(first_message_raw)
        except asyncio.TimeoutError:
            logger.warning(f"Registration timeout for session {session_id}")
            await websocket.send_json({
                "type": "error",
                "message": "Registration timeout. Please send register message."
            })
            manager.disconnect(websocket, session_id)
            return
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in register message for session {session_id}")
            await websocket.send_json({
                "type": "error",
                "message": "Invalid JSON format"
            })
            manager.disconnect(websocket, session_id)
            return

        # Step 4: Validate register message
        if first_message.get("type") != "register":
            logger.warning(f"First message is not register for session {session_id}")
            await websocket.send_json({
                "type": "error",
                "message": "First message must be type 'register'"
            })
            manager.disconnect(websocket, session_id)
            return

        conversation_id = first_message.get("conversation_id")
        if not conversation_id:
            logger.warning(f"Missing conversation_id in register message for session {session_id}")
            await websocket.send_json({
                "type": "error",
                "message": "Missing conversation_id in register message"
            })
            manager.disconnect(websocket, session_id)
            return

        # Step 5: Register session in Redis for multi-device notification
        await manager.register_session(session_id, user_id, conversation_id)

        # Send confirmation
        await websocket.send_json({
            "type": "registered",
            "session_id": session_id,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "message": "Successfully registered for notifications"
        })
        logger.info(
            f"Session registered: session_id={session_id}, "
            f"user_id={user_id}, conversation_id={conversation_id}"
        )

        # Step 6: Keep connection alive, receive any client messages
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received from client [{session_id}]: {data}")

            # Handle ping/pong for keepalive
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
        logger.info(f"Client disconnected from session: {session_id}")

    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        manager.disconnect(websocket, session_id)


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting WebSocket Server on {WS_SERVER_HOST}:{WS_SERVER_PORT}")
    uvicorn.run(app, host=WS_SERVER_HOST, port=WS_SERVER_PORT)
