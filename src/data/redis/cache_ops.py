import json
from typing import Any
from src.data.redis.connection import redis_connection
from src.utils.logger import logger


def get_cached_value(key: str) -> Any | None:
    """
    Get value from Redis cache.

    Args:
        key: Cache key

    Returns:
        Cached value or None if not found
    """
    try:
        redis = redis_connection.get_client()
        value = redis.get(key)

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


def set_cached_value(key: str, value: Any, ttl: int = None) -> bool:
    """
    Set value in Redis cache.

    Args:
        key: Cache key
        value: Value to cache (will be JSON-encoded if not string)
        ttl: Time to live in seconds (optional)

    Returns:
        True if successful, False otherwise
    """
    try:
        redis = redis_connection.get_client()

        # Encode value as JSON if not string
        if not isinstance(value, str):
            value = json.dumps(value)

        if ttl:
            redis.setex(key, ttl, value)
        else:
            redis.set(key, value)

        logger.debug(f"Cached value for key '{key}' (TTL: {ttl}s)")
        return True

    except Exception as e:
        logger.error(f"Failed to set cached value for key '{key}': {e}")
        return False


def delete_cached_value(key: str) -> bool:
    """
    Delete value from Redis cache.

    Args:
        key: Cache key

    Returns:
        True if deleted, False if not found or error
    """
    try:
        redis = redis_connection.get_client()
        result = redis.delete(key)
        return result > 0

    except Exception as e:
        logger.error(f"Failed to delete cached value for key '{key}': {e}")
        return False


def exists(key: str) -> bool:
    """
    Check if a key exists in Redis.

    Args:
        key: Cache key

    Returns:
        True if key exists, False otherwise
    """
    try:
        redis = redis_connection.get_client()
        return redis.exists(key) > 0

    except Exception as e:
        logger.error(f"Failed to check key existence for '{key}': {e}")
        return False


def get_ttl(key: str) -> int | None:
    """
    Get remaining TTL for a key.

    Args:
        key: Cache key

    Returns:
        TTL in seconds, -1 if no expiry, -2 if key doesn't exist, None on error
    """
    try:
        redis = redis_connection.get_client()
        return redis.ttl(key)

    except Exception as e:
        logger.error(f"Failed to get TTL for key '{key}': {e}")
        return None


def increment(key: str, amount: int = 1) -> int | None:
    """
    Increment a numeric value in Redis.

    Args:
        key: Cache key
        amount: Amount to increment (default 1)

    Returns:
        New value after increment, None on error
    """
    try:
        redis = redis_connection.get_client()
        return redis.incrby(key, amount)

    except Exception as e:
        logger.error(f"Failed to increment key '{key}': {e}")
        return None


def decrement(key: str, amount: int = 1) -> int | None:
    """
    Decrement a numeric value in Redis.

    Args:
        key: Cache key
        amount: Amount to decrement (default 1)

    Returns:
        New value after decrement, None on error
    """
    try:
        redis = redis_connection.get_client()
        return redis.decrby(key, amount)

    except Exception as e:
        logger.error(f"Failed to decrement key '{key}': {e}")
        return None


def clear_pattern(pattern: str) -> int:
    """
    Delete all keys matching a pattern.

    Args:
        pattern: Redis key pattern (e.g., "user:*", "cache:product:*")

    Returns:
        Number of keys deleted
    """
    try:
        redis = redis_connection.get_client()
        keys = redis.keys(pattern)

        if not keys:
            return 0

        deleted = redis.delete(*keys)
        logger.info(f"Deleted {deleted} keys matching pattern '{pattern}'")
        return deleted

    except Exception as e:
        logger.error(f"Failed to clear pattern '{pattern}': {e}")
        return 0
