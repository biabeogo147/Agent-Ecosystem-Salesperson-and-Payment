import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from src.websocket_server.connection_manager import manager
from src.websocket_server.services import (
    authenticate_websocket,
    extract_token_from_query,
    handle_chat_message,
)


ws_router = APIRouter(tags=["WebSocket"])


@ws_router.websocket("/ws/{session_id}")
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
    from src.websocket_server import get_ws_server_logger
    logger = get_ws_server_logger()

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
                            conversation_id=conversation_id,
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
