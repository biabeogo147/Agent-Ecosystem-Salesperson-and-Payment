from fastapi import WebSocket

from src.api_gateway.connection_manager import manager


async def handle_chat_message(
    websocket: WebSocket,
    conversation_id: int | None,
    message: str,
    user_id: int,
    session_id: str
) -> int | None:
    """
    Handle chat message using persistent connection to Salesperson Agent App.

    Uses ConnectionManager to get/create persistent agent connection per session.

    Args:
        websocket: Client WebSocket connection
        conversation_id: Conversation ID for ADK session history (None for new conversation)
        message: User's message text
        user_id: Authenticated user ID
        session_id: Browser session ID for persistent agent connection

    Returns:
        conversation_id from Agent response (new ID if conversation was created)
    """
    from src.api_gateway import get_api_gateway_logger
    logger = get_api_gateway_logger()
    result_conversation_id = conversation_id

    try:
        logger.info(f"Handling chat for conversation {conversation_id}, session {session_id}")

        agent_client = await manager.connect_agent(session_id)

        async for msg in agent_client.send_and_receive({
            "type": "chat",
            "conversation_id": conversation_id,
            "message": message,
            "user_id": user_id
        }):
            msg_type = msg.get("type")

            if msg_type == "token":
                logger.debug(f"Streaming token: {msg.get('token')}")
                await websocket.send_json({
                    "type": "chat_token",
                    "token": msg.get("token")
                })

            elif msg_type == "complete":
                # Get conversation_id from response (may be new if created by Agent)
                result_conversation_id = msg.get("conversation_id", conversation_id)
                # Send complete response
                await websocket.send_json({
                    "type": "chat_response",
                    "conversation_id": result_conversation_id,
                    "content": msg.get("content")
                })
                logger.info(f"Chat response sent for conversation {result_conversation_id}")
                break

            elif msg_type == "error":
                # Forward error to browser
                await websocket.send_json({
                    "type": "error",
                    "message": msg.get("message", "Agent error")
                })
                logger.error(f"Agent error for conversation {conversation_id}: {msg.get('message')}")
                break

    except Exception as e:
        logger.error(f"Chat streaming error for conversation {conversation_id}: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Chat error: {str(e)}"
            })
        except Exception:
            pass

    return result_conversation_id
