"""Chat service for agent conversation handling."""
import asyncio

from google.adk.events.event import Event

from src.my_agent.salesperson_agent import salesperson_agent_logger as logger
from src.data.postgres.conversation_ops import update_conversation_title
from src.data.postgres.message_ops import save_user_assistant_pair
from src.data.redis.conversation_cache import append_to_cached_history
from src.utils.client.openai_client import summarize_to_title


def extract_agent_response(event: Event | None) -> str:
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


async def save_chat_and_update_title(
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
