"""Session management service for ADK agent."""
import time

from google.adk.sessions import InMemorySessionService
from google.adk.events.event import Event
from google.genai.types import Content, Part

from src.my_agent.salesperson_agent import salesperson_agent_logger as logger
from src.data.postgres.conversation_ops import get_conversation_with_messages
from src.data.redis.conversation_cache import get_cached_history, cache_conversation_history

# ADK app name for session service
APP_NAME = "salesperson-agent"


async def recover_session_from_storage(conversation_id: int) -> tuple[list[dict], bool]:
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


async def inject_history_to_session(
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


async def inject_single_message_to_session(
    session_service: InMemorySessionService,
    user_id: int,
    conversation_id: int,
    message: str,
    role: str = "model"  # model = assistant in ADK
) -> bool:
    """
    Inject a single message into ADK session.

    Used to inject payment notifications or other system messages into
    an active user session so the agent is aware of external events.

    Args:
        session_service: The ADK session service
        user_id: User ID
        conversation_id: Conversation ID (used as session_id)
        message: Message content to inject
        role: Message role ("model" for assistant, "user" for user)

    Returns:
        True if injection successful, False if session not found
    """
    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=str(user_id),
        session_id=str(conversation_id)
    )

    if not session:
        logger.debug(f"Session not found for injection: user={user_id}, conv={conversation_id}")
        return False

    event = Event(
        invocation_id=f"notification-{int(time.time() * 1000)}",
        author=role,
        content=Content(role=role, parts=[Part(text=message)])
    )
    await session_service.append_event(session, event)
    logger.debug(f"Injected message to session: user={user_id}, conv={conversation_id}")
    return True
