import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from src.my_agent.salesperson_agent.agent import root_agent
from src.my_agent.salesperson_agent import salesperson_agent_logger as logger
from src.my_agent.salesperson_agent.services import (
    recover_session_from_storage,
    inject_history_to_session,
    extract_agent_response,
    save_chat_and_update_title,
)
from src.my_agent.salesperson_agent.context import current_user_id, current_conversation_id
from src.data.postgres.conversation_ops import create_conversation

# ADK app name for session service
APP_NAME = "salesperson-agent"

agent_router = APIRouter(tags=["Agent"])

# Session service reference (set by app.py)
_session_service: InMemorySessionService | None = None


def set_session_service(service: InMemorySessionService) -> None:
    """Set the session service reference."""
    global _session_service
    _session_service = service


def get_session_service() -> InMemorySessionService | None:
    """Get the session service reference."""
    return _session_service


@agent_router.websocket("/agent/stream")
async def agent_stream_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for utils chat responses.

    Protocol:
    Client sends: {"type": "chat", "conversation_id": null|int, "message": "...", "user_id": 123}
    Server sends: {"type": "complete", "conversation_id": int, "content": "..."}

    - conversation_id=null: New chat, server creates conversation and returns ID
    - conversation_id=int: Existing chat, server uses that ID
    """
    await websocket.accept()
    logger.info("Agent stream client connected")

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "chat":
                conversation_id = data.get("conversation_id")
                message = data.get("message")
                user_id = data.get("user_id")

                if not message:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Missing message"
                    })
                    continue

                try:
                    if not _session_service:
                        raise RuntimeError("Session service not initialized")

                    if not user_id:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Missing user_id"
                        })
                        continue

                    is_first_message = False
                    user_id_str = str(user_id)

                    if conversation_id is None:
                        conv = await create_conversation(user_id)
                        conversation_id = conv.id
                        is_first_message = True
                        logger.info(f"Created new conversation: {conversation_id} for user {user_id}")

                        await _session_service.create_session(
                            app_name=APP_NAME,
                            user_id=user_id_str,
                            session_id=str(conversation_id)
                        )
                    else:
                        session_id = str(conversation_id)
                        session = await _session_service.get_session(
                            app_name=APP_NAME,
                            user_id=user_id_str,
                            session_id=session_id
                        )

                        if not session:
                            session = await _session_service.create_session(
                                app_name=APP_NAME,
                                user_id=user_id_str,
                                session_id=session_id
                            )

                            history, is_first_message = await recover_session_from_storage(conversation_id)
                            if history:
                                await inject_history_to_session(_session_service, session, history)

                    user_content = Content(
                        role="user",
                        parts=[Part(text=message)]
                    )

                    logger.info(f"Processing chat for conversation {conversation_id}, user {user_id}")

                    runner = Runner(
                        agent=root_agent,
                        app_name=APP_NAME,
                        session_service=_session_service
                    )

                    # Set user_id, conversation_id context for tool access
                    user_id_token = current_user_id.set(user_id)
                    conversation_id_token = current_conversation_id.set(conversation_id)
                    try:
                        # Iterate through AsyncGenerator to get final event
                        final_event = None
                        async for event in runner.run_async(
                            user_id=user_id_str,
                            session_id=str(conversation_id),
                            new_message=user_content
                        ):
                            final_event = event
                    finally:
                        current_user_id.reset(user_id_token)
                        current_conversation_id.reset(conversation_id_token)

                    # Extract response from final event
                    response_text = extract_agent_response(final_event)

                    # Send complete response with conversation_id
                    await websocket.send_json({
                        "type": "complete",
                        "conversation_id": conversation_id,
                        "content": response_text
                    })

                    logger.info(f"Response sent for conversation {conversation_id}")

                    # Background save to DB and Redis
                    asyncio.create_task(save_chat_and_update_title(
                        conversation_id=conversation_id,
                        user_message=message,
                        assistant_message=response_text,
                        is_first_message=is_first_message
                    ))

                except Exception as e:
                    logger.error(f"Stream chat error: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })

    except WebSocketDisconnect:
        logger.info("Agent stream client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
