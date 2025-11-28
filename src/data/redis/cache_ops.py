import json
from typing import Any
from src.data.redis.connection import redis_connection
from src.utils.logger import get_current_logger


async def get_cached_value(key: str) -> Any | None:
    """
    Get value from Redis cache (async).

    Args:
        key: Cache key

    Returns:
        Cached value or None if not found
    """
    logger = get_current_logger()
    try:
        redis = await redis_connection.get_client()
        value = await redis.get(key)

        if value is None:
            return None

        # Try to decode JSON if possible
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    except Exception as e:
        logger.error(f"Failed to get cached value for key '{key}': {e}")
        return None


async def set_cached_value(key: str, value: Any, ttl: int = None) -> bool:
    """
    Set value in Redis cache (async).

    Args:
        key: Cache key
        value: Value to cache (will be JSON-encoded if not string)
        ttl: Time to live in seconds (optional)

    Returns:
        True if successful, False otherwise
    """
    logger = get_current_logger()
    try:
        redis = await redis_connection.get_client()

        # Encode value as JSON if not string
        if not isinstance(value, str):
            value = json.dumps(value)

        if ttl:
            await redis.setex(key, ttl, value)
        else:
            await redis.set(key, value)

        logger.debug(f"Cached value for key '{key}' (TTL: {ttl}s)")
        return True

    except Exception as e:
        logger.error(f"Failed to set cached value for key '{key}': {e}")
        return False


async def delete_cached_value(key: str) -> bool:
    """
    Delete value from Redis cache (async).

    Args:
        key: Cache key

    Returns:
        True if deleted, False if not found or error
    """
    logger = get_current_logger()
    try:
        redis = await redis_connection.get_client()
        result = await redis.delete(key)
        return result > 0

    except Exception as e:
        logger.error(f"Failed to delete cached value for key '{key}': {e}")
        return False


async def clear_pattern(pattern: str) -> int:
    """
    Delete all keys matching a pattern using SCAN (async, non-blocking).

    Args:
        pattern: Redis key pattern (e.g., "user:*", "cache:product:*")

    Returns:
        Number of keys deleted
    """
    logger = get_current_logger()
    try:
        redis = await redis_connection.get_client()
        deleted = 0
        cursor = 0

        # Use SCAN instead of KEYS to avoid blocking Redis server
        # SCAN is cursor-based and works incrementally
        while True:
            cursor, keys = await redis.scan(cursor, match=pattern, count=100)

            if keys:
                deleted += await redis.delete(*keys)

            if cursor == 0:
                break

        logger.info(f"Deleted {deleted} keys matching pattern '{pattern}'")
        return deleted

    except Exception as e:
        logger.error(f"Failed to clear pattern '{pattern}': {e}")
        return 0
