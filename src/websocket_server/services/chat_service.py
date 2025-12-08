from fastapi import WebSocket

from src.config import SALESPERSON_AGENT_APP_WS_URL
from src.websocket_server.streaming.agent_stream_client import AgentStreamClient


async def handle_chat_message(
    websocket: WebSocket,
    conversation_id: str,
    message: str,
    user_id: int
) -> None:
    """
    Handle chat message by streaming from Salesperson Agent App.

    Establishes WebSocket connection to Agent App and forwards streaming responses
    to the browser client.

    Args:
        websocket: Client WebSocket connection
        conversation_id: Conversation ID for ADK session history
        message: User's message text
        user_id: Authenticated user ID
    """
    from src.websocket_server import get_ws_server_logger
    logger = get_ws_server_logger()
    try:
        logger.info(f"Handling chat for conversation {conversation_id}")

        async with AgentStreamClient(SALESPERSON_AGENT_APP_WS_URL) as agent_client:
            # Send message to agent
            await agent_client.send({
                "type": "chat",
                "conversation_id": conversation_id,
                "message": message,
                "user_id": user_id
            })

            # Stream responses back to browser
            async for msg in agent_client.receive():
                msg_type = msg.get("type")

                if msg_type == "token":
                    logger.debug(f"Streaming token: {msg.get('token')}")
                    await websocket.send_json({
                        "type": "chat_token",
                        "token": msg.get("token")
                    })

                elif msg_type == "complete":
                    # Send complete response
                    await websocket.send_json({
                        "type": "chat_response",
                        "conversation_id": conversation_id,
                        "content": msg.get("content")
                    })
                    logger.info(f"Chat response sent for conversation {conversation_id}")
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
