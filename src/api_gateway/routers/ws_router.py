import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from src.api_gateway.connection_manager import manager
from src.api_gateway.services import (
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
    1. Client connects with JWT token: /ws/{session_id}?token=<JWT>
    2. Server validates JWT and accepts connection
    3. Client sends messages:
       - {"type": "register", "conversation_id": 123} → Join conversation
       - {"type": "chat", "message": "Hello"} → Send chat (creates new conv if needed)
       - {"type": "ping"} → Keepalive
    4. Server responds with notifications for registered conversation
    """
    from src.api_gateway import get_api_gateway_logger
    logger = get_api_gateway_logger()

    validated_token = extract_token_from_query(token)
    user_info = await authenticate_websocket(websocket, validated_token, session_id)
    if not user_info:
        return

    user_id = user_info.user_id
    conversation_id = None

    await manager.connect(websocket, session_id)

    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received from client [{session_id}]: {data}")

            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from client [{session_id}]: {data}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
                continue

            msg_type = msg.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "register":
                new_conv_id = await handle_msg_register(websocket, session_id, user_id, msg)
                if new_conv_id:
                    conversation_id = new_conv_id

            elif msg_type == "chat":
                new_conv_id = await handle_msg_chat(websocket, session_id, user_id, conversation_id, msg)
                if new_conv_id:
                    conversation_id = new_conv_id

            else:
                logger.warning(f"Unknown message type from client: {msg_type}")

    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
        await manager.disconnect_agent(session_id)
        logger.info(f"Client disconnected from session: {session_id}")

    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        manager.disconnect(websocket, session_id)
        await manager.disconnect_agent(session_id)


async def handle_msg_register(
    websocket: WebSocket,
    session_id: str,
    user_id: int,
    msg: dict
) -> int | None:
    """
    Handle register message - join a conversation for notifications.

    Args:
        websocket: Client WebSocket connection
        session_id: Browser session ID
        user_id: Authenticated user ID
        msg: Message dict containing conversation_id

    Returns:
        conversation_id if registration successful, None otherwise
    """
    from src.api_gateway import get_api_gateway_logger
    logger = get_api_gateway_logger()

    new_conv_id = msg.get("conversation_id")
    if not new_conv_id:
        await websocket.send_json({
            "type": "error",
            "message": "Missing conversation_id in register message"
        })
        return None

    await manager.register_session(session_id, user_id, new_conv_id)
    await websocket.send_json({
        "type": "registered",
        "session_id": session_id,
        "user_id": user_id,
        "conversation_id": new_conv_id,
        "message": "Successfully registered for notifications"
    })
    logger.info(
        f"Session registered: session_id={session_id}, "
        f"user_id={user_id}, conversation_id={new_conv_id}"
    )
    return new_conv_id


async def handle_msg_chat(
    websocket: WebSocket,
    session_id: str,
    user_id: int,
    conversation_id: int | None,
    msg: dict
) -> int | None:
    """
    Handle chat message - send to agent and stream response.

    Args:
        websocket: Client WebSocket connection
        session_id: Browser session ID
        user_id: Authenticated user ID
        conversation_id: Current conversation ID (None for new conversation)
        msg: Message dict containing message text

    Returns:
        conversation_id (new ID if conversation was created)
    """
    from src.api_gateway import get_api_gateway_logger
    logger = get_api_gateway_logger()

    message_text = msg.get("message")
    if not message_text:
        await websocket.send_json({
            "type": "error",
            "message": "Missing message in chat request"
        })
        return conversation_id

    new_conv_id = await handle_chat_message(
        websocket=websocket,
        conversation_id=conversation_id,
        message=message_text,
        user_id=user_id,
        session_id=session_id
    )

    # Update conversation_id if new conversation was created
    if new_conv_id and new_conv_id != conversation_id:
        await manager.register_session(session_id, user_id, new_conv_id)
        logger.info(f"Session registered with new conversation: {new_conv_id}")

    return new_conv_id