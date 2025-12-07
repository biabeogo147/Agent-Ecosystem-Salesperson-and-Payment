from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.events.event import Event
from google.genai.types import Content, Part

# ADK app name for session service
APP_NAME = "salesperson-agent"

from src.my_agent.salesperson_agent.agent import root_agent
from src.my_agent.salesperson_agent import salesperson_agent_logger as logger
from src.config import SALESPERSON_AGENT_APP_HOST, SALESPERSON_AGENT_APP_PORT

from src.data.postgres.conversation_ops import (
    create_conversation,
    get_conversation_with_messages,
    update_conversation_title
)
from src.data.postgres.message_ops import save_user_assistant_pair
from src.data.redis.conversation_cache import (
    get_cached_history,
    append_to_cached_history,
    cache_conversation_history
)
from src.utils.client.openai_client import summarize_to_title, ChatCompletionError


_session_service: InMemorySessionService | None = None
_subscriber_task: asyncio.Task | None = None


def _extract_agent_response(event: Event | None) -> str:
    """
    Extract text response from final agent event.

    Args:
        event: Final event from Runner.run_async

    Returns:
        Agent's text response
    """
    if event is None:
        return "No response from agent"

    try:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, 'text') and part.text:
                    return part.text

        return "Agent response unavailable"

    except Exception as e:
        logger.error(f"Failed to extract response: {e}")
        return f"Error extracting response: {str(e)}"


async def _save_chat_and_update_title(
    conversation_id: int,
    user_message: str,
    assistant_message: str,
    is_first_message: bool
) -> None:
    """
    Background task to save chat to DB and update title if needed.

    Args:
        conversation_id: Integer ID of conversation
        user_message: User's message content
        assistant_message: Agent's response content
        is_first_message: Whether this is the first message in conversation
    """
    try:
        if is_first_message:
            # First message: save, cache, and generate title in parallel
            results = await asyncio.gather(
                save_user_assistant_pair(conversation_id, user_message, assistant_message),
                append_to_cached_history(conversation_id, user_message, assistant_message),
                summarize_to_title(user_message, max_words=10),
                return_exceptions=True
            )
            # Update title if generated successfully
            title_result = results[2]
            if isinstance(title_result, str):
                await update_conversation_title(conversation_id, title_result)
                logger.info(f"Generated title for conversation {conversation_id}: {title_result}")
            elif isinstance(title_result, Exception):
                logger.warning(f"Failed to generate title: {title_result}")
        else:
            # Existing conversation: just save and cache in parallel
            await asyncio.gather(
                save_user_assistant_pair(conversation_id, user_message, assistant_message),
                append_to_cached_history(conversation_id, user_message, assistant_message)
            )

    except Exception as e:
        logger.error(f"Failed to save chat history: {e}")


async def _recover_session_from_storage(conversation_id: int) -> tuple[list[dict], bool]:
    """
    Recover conversation history from Redis cache or DB fallback.

    Args:
        conversation_id: Integer ID of conversation

    Returns:
        Tuple of (history list, is_first_message flag)
        History format: [{"role": "user"|"model", "content": "..."}]
    """
    cached_history = await get_cached_history(conversation_id)

    if cached_history:
        # Convert assistant -> model for ADK compatibility
        history = [
            {"role": "model" if msg["role"] == "assistant" else msg["role"], "content": msg["content"]}
            for msg in cached_history
        ]
        logger.info(f"Recovered history from Redis: {conversation_id} ({len(history)} messages)")
        return history, len(history) == 0

    result = await get_conversation_with_messages(conversation_id)
    if result:
        conv, messages = result
        # Convert assistant -> model for ADK compatibility
        history = [
            {"role": "model" if msg.role.value == "assistant" else msg.role.value, "content": msg.content}
            for msg in messages
        ]
        await cache_conversation_history(conversation_id, [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ])
        logger.info(f"Recovered history from DB: {conversation_id} ({len(history)} messages)")
        return history, len(history) == 0

    logger.info(f"No history found for conversation: {conversation_id}")
    return [], True


async def _inject_history_to_session(
    session_service: InMemorySessionService,
    session,
    history: list[dict]
) -> None:
    """
    Inject conversation history into ADK session using append_event.

    Args:
        session_service: The session service
        session: The session object
        history: List of message dicts with 'role' and 'content' keys
    """
    for i, msg in enumerate(history):
        event = Event(
            invocation_id=f"recovered-{i}",
            author=msg["role"],
            content=Content(role=msg["role"], parts=[Part(text=msg["content"])])
        )
        await session_service.append_event(session, event)

    logger.debug(f"Injected {len(history)} events to session")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    Application lifespan manager.

    Startup:
    - Initializes session service for agent conversations
    - Starts notification subscriber (moved from WebSocket Server)

    Shutdown:
    - Stops notification subscriber
    """
    global _session_service, _subscriber_task

    logger.info(f"Salesperson Agent App starting on {SALESPERSON_AGENT_APP_HOST}:{SALESPERSON_AGENT_APP_PORT}")

    # Initialize session service
    _session_service = InMemorySessionService()
    logger.info("Session service initialized")

    # Start notification subscriber
    from src.my_agent.salesperson_agent.salesperson_notification_subscriber import (
        start_subscriber_background,
        stop_subscriber
    )
    _subscriber_task = start_subscriber_background()
    logger.info("Notification subscriber started")

    yield

    # Shutdown
    logger.info("Salesperson Agent App shutting down...")
    await stop_subscriber()
    logger.info("Notification subscriber stopped")


app = FastAPI(
    title="Salesperson Agent App",
    description="Internal API for WebSocket Server to interact with ADK Salesperson Agent",
    version="1.0.0",
    lifespan=lifespan
)


@app.websocket("/agent/stream")
async def agent_stream_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for streaming chat responses.

    Protocol:
    Client sends: {"type": "chat", "conversation_id": null|int, "message": "...", "user_id": 123}
    Server sends: {"type": "complete", "conversation_id": int, "content": "..."}

    - conversation_id=null: New chat, server creates conversation and returns ID
    - conversation_id=int: Existing chat, server uses that ID

    TODO: Implement token-by-token streaming when ADK supports it.
    Currently sends complete response as single message.
    """
    await websocket.accept()
    logger.info("Agent stream client connected")

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "chat":
                conversation_id = data.get("conversation_id")  # Can be None or int
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

                            history, is_first_message = await _recover_session_from_storage(conversation_id)
                            if history:
                                await _inject_history_to_session(_session_service, session, history)

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

                    # Iterate through AsyncGenerator to get final event
                    final_event = None
                    async for event in runner.run_async(
                        user_id=user_id_str,
                        session_id=str(conversation_id),
                        new_message=user_content
                    ):
                        final_event = event

                    # Extract response from final event
                    response_text = _extract_agent_response(final_event)

                    # Send complete response with conversation_id (so browser can store it)
                    await websocket.send_json({
                        "type": "complete",
                        "conversation_id": conversation_id,  # Integer ID
                        "content": response_text
                    })

                    logger.info(f"Response sent for conversation {conversation_id}")

                    # Background save to DB and Redis (don't block response)
                    asyncio.create_task(_save_chat_and_update_title(
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

            elif data.get("type") == "authenticate":
                username = data.get("username")
                password = data.get("password")

                if not username or not password:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Missing username or password"
                    })
                    continue

                try:
                    logger.info(f"Processing authentication request for user: {username}")

                    from src.my_agent.salesperson_agent.salesperson_mcp_client import get_salesperson_mcp_client
                    client = get_salesperson_mcp_client()
                    result = await client.authenticate_user(username=username, password=password)

                    if result.get("status") == "00":
                        await websocket.send_json({
                            "type": "authenticate_response",
                            "status": "success",
                            "data": result.get("data")
                        })
                        logger.info(f"Authentication successful for user: {username}")
                    else:
                        await websocket.send_json({
                            "type": "authenticate_response",
                            "status": "failure",
                            "message": result.get("message", "Authentication failed")
                        })
                        logger.warning(f"Authentication failed for user: {username}")

                except Exception as e:
                    logger.error(f"Authentication error: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })

    except WebSocketDisconnect:
        logger.info("Agent stream client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=SALESPERSON_AGENT_APP_HOST,
        port=SALESPERSON_AGENT_APP_PORT
    )
