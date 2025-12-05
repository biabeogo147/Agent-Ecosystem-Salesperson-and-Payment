"""Redis cache operations for conversation history."""

import json

from src.data.redis.connection import redis_connection
from src.data.redis.cache_keys import CacheKeys, TTL
from src.utils.logger import get_current_logger


async def cache_conversation_history(conversation_id: int, messages: list[dict]) -> None:
    """
    Cache conversation history to Redis.

    Args:
        conversation_id: Integer ID of conversation
        messages: List of message dicts with 'role' and 'content' keys
    """
    logger = get_current_logger()
    try:
        redis = await redis_connection.get_client()
        cache_key = CacheKeys.conversation_history(conversation_id)
        await redis.setex(cache_key, TTL.CONVERSATION_HISTORY, json.dumps(messages))
        logger.debug(f"Cached {len(messages)} messages for conversation {conversation_id}")
    except Exception as e:
        logger.error(f"Failed to cache conversation history: {e}")


async def get_cached_history(conversation_id: int) -> list[dict] | None:
    """
    Get cached conversation history from Redis.

    Args:
        conversation_id: Integer ID of conversation

    Returns:
        List of message dicts or None if not found/error
    """
    logger = get_current_logger()
    try:
        redis = await redis_connection.get_client()
        cache_key = CacheKeys.conversation_history(conversation_id)
        data = await redis.get(cache_key)
        if data:
            messages = json.loads(data)
            logger.debug(f"Cache HIT: {len(messages)} messages for conversation {conversation_id}")
            return messages
        logger.debug(f"Cache MISS: conversation {conversation_id}")
        return None
    except Exception as e:
        logger.error(f"Failed to get cached history: {e}")
        return None


async def append_to_cached_history(
    conversation_id: int,
    user_message: str,
    assistant_message: str,
    max_messages: int = 40
) -> None:
    """
    Append new messages to cached history (keep last N messages).

    Args:
        conversation_id: Integer ID of conversation
        user_message: User's message content
        assistant_message: Assistant's response content
        max_messages: Maximum messages to keep in cache
    """
    logger = get_current_logger()
    try:
        redis = await redis_connection.get_client()
        cache_key = CacheKeys.conversation_history(conversation_id)

        # Get existing history
        data = await redis.get(cache_key)
        history = json.loads(data) if data else []

        # Append new messages
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": assistant_message})

        # Keep only last N messages
        if len(history) > max_messages:
            history = history[-max_messages:]

        # Save back with TTL refresh
        await redis.setex(cache_key, TTL.CONVERSATION_HISTORY, json.dumps(history))
        logger.debug(f"Updated cached history for {conversation_id}: {len(history)} messages")

    except Exception as e:
        logger.error(f"Failed to append to cached history: {e}")


async def delete_cached_history(conversation_id: int) -> bool:
    """
    Delete cached conversation history.

    Args:
        conversation_id: Integer ID of conversation

    Returns:
        True if deleted, False otherwise
    """
    logger = get_current_logger()
    try:
        redis = await redis_connection.get_client()
        cache_key = CacheKeys.conversation_history(conversation_id)
        result = await redis.delete(cache_key)
        logger.debug(f"Deleted cached history for {conversation_id}")
        return result > 0
    except Exception as e:
        logger.error(f"Failed to delete cached history: {e}")
        return False
