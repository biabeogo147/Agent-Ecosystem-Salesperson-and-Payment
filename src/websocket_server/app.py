"""
WebSocket server application for real-time notifications and chat.

This FastAPI application provides:
1. WebSocket endpoint for frontend clients to receive real-time notifications
2. Redis subscriber for payment notifications from Salesperson Agent
3. Chat message handling via WebSocket to Salesperson Agent App
4. JWT authentication for WebSocket connections
5. Multi-session notification broadcasting via Redis session mapping
"""
import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware

from src.config import WS_SERVER_HOST, WS_SERVER_PORT, SALESPERSON_AGENT_APP_WS_URL
from src.utils.response_format import ResponseFormat
from src.websocket_server import ws_server_logger as logger
from src.websocket_server.connection_manager import manager
from src.websocket_server.auth import (
    auth_router,
    authenticate_websocket,
    extract_token_from_query,
)
from src.data.redis.connection import redis_connection
from src.data.redis.cache_keys import CacheKeys
from src.websocket_server.streaming.agent_stream_client import AgentStreamClient


_notification_receiver_task: asyncio.Task | None = None


async def start_notification_receiver() -> None:
    """
    Subscribe to Redis channel for payment notifications from Salesperson Agent.
    
    Receives notifications published by Salesperson Agent and broadcasts them
    to connected WebSocket clients based on user_id and conversation_id.
    """
    logger.info("Starting notification receiver...")
    
    try:
        redis = await redis_connection.get_client()
        pubsub = redis.pubsub()
        
        await pubsub.subscribe(CacheKeys.websocket_notification())
        logger.info(f"Subscribed to Redis channel: {CacheKeys.websocket_notification()}")
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    
                    notification = json.loads(data)
                    logger.debug(f"Received notification: {notification}")
                    
                    # Broadcast to users based on user_id and conversation_id
                    user_id = notification.get("user_id")
                    conversation_id = notification.get("conversation_id")
                    
                    if user_id and conversation_id:
                        sent_count = await manager.broadcast_to_user_conversation(
                            user_id=user_id,
                            conversation_id=conversation_id,
                            message=notification
                        )
                        logger.info(
                            f"Broadcast notification to {sent_count} connections: "
                            f"user_id={user_id}, conversation_id={conversation_id}"
                        )
                    else:
                        logger.warning(f"Notification missing user_id or conversation_id: {notification}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse notification message: {e}")
                except Exception as e:
                    logger.error(f"Error processing notification: {e}")
                    
    except asyncio.CancelledError:
        logger.info("Notification receiver cancelled")
        raise
    except Exception as e:
        logger.error(f"Notification receiver error: {e}")
        raise


async def handle_chat_message(
    websocket: WebSocket,
    session_id: str,
    message: str,
    user_id: int
) -> None:
    """
    Handle chat message by streaming from Salesperson Agent App.
    
    Establishes WebSocket connection to Agent App and forwards streaming responses
    to the browser client.
    
    Args:
        websocket: Client WebSocket connection
        session_id: Chat session ID
        message: User's message text
        user_id: Authenticated user ID
    """
    try:
        logger.info(f"Handling chat for session {session_id}")
        
        async with AgentStreamClient(SALESPERSON_AGENT_APP_WS_URL) as agent_client:
            # Send message to agent
            await agent_client.send({
                "type": "chat",
                "session_id": session_id,
                "message": message,
                "user_id": user_id
            })
            
            # Stream responses back to browser
            async for msg in agent_client.receive():
                msg_type = msg.get("type")
                
                if msg_type == "token":
                    # TODO: Forward streaming tokens to browser
                    # For now, just log them
                    logger.debug(f"Streaming token: {msg.get('token')}")
                    await websocket.send_json({
                        "type": "chat_token",
                        "token": msg.get("token")
                    })
                    
                elif msg_type == "complete":
                    # Send complete response
                    await websocket.send_json({
                        "type": "chat_response",
                        "session_id": session_id,
                        "content": msg.get("content")
                    })
                    logger.info(f"Chat response sent for session {session_id}")
                    break
                    
                elif msg_type == "error":
                    # Forward error to browser
                    await websocket.send_json({
                        "type": "error",
                        "message": msg.get("message", "Agent error")
                    })
                    logger.error(f"Agent error for session {session_id}: {msg.get('message')}")
                    break
                    
    except Exception as e:
        logger.error(f"Chat streaming error for session {session_id}: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Chat error: {str(e)}"
            })
        except Exception:
            pass  # WebSocket might be closed


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    Application lifespan manager.

    Startup:
    - Starts the Redis notification subscriber as a background task

    Shutdown:
    - Stops the notification subscriber
    """
    global _notification_receiver_task

    logger.info(f"WebSocket Server starting on {WS_SERVER_HOST}:{WS_SERVER_PORT}")

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

            # Parse message
            try:
                msg = json.loads(data)
                msg_type = msg.get("type")
                
                if msg_type == "ping":
                    # Keepalive
                    await websocket.send_json({"type": "pong"})
                    
                elif msg_type == "chat":
                    # Handle chat message
                    message_text = msg.get("message")
                    if message_text:
                        await handle_chat_message(
                            websocket=websocket,
                            session_id=session_id,
                            message=message_text,
                            user_id=user_id
                        )
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Missing message in chat request"
                        })
                else:
                    logger.warning(f"Unknown message type from client: {msg_type}")
                    
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from client [{session_id}]: {data}")

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
