"""Redis-based sync state tracking for Elasticsearch sync optimization (async)."""

from src.data.redis.connection import redis_connection
from src.data.redis.cache_keys import CacheKeys
from src.utils.logger import get_current_logger

logger = get_current_logger()


async def mark_skus_as_synced(skus: list[str]) -> bool:
    """
    Mark SKUs as synced to Elasticsearch by adding to Redis Set (async).

    Args:
        skus: List of SKUs to mark as synced

    Returns:
        True if successful, False otherwise
    """
    if not skus:
        return True

    try:
        redis = await redis_connection.get_client()
        synced_key = CacheKeys.elasticsearch_synced_skus()
        await redis.sadd(synced_key, *skus)
        logger.debug(f"Marked {len(skus)} SKUs as synced in Redis")
        return True
    except Exception as e:
        logger.error(f"Failed to mark SKUs as synced in Redis: {e}")
        return False


async def is_sku_synced(sku: str) -> bool:
    """
    Check if a SKU is already synced to Elasticsearch (async).

    This is an O(1) operation in Redis Set.

    Args:
        sku: SKU to check

    Returns:
        True if synced, False otherwise
    """
    try:
        redis = await redis_connection.get_client()
        synced_key = CacheKeys.elasticsearch_synced_skus()
        return await redis.sismember(synced_key, sku)
    except Exception as e:
        logger.error(f"Failed to check SKU sync status in Redis: {e}")
        return False


async def get_all_synced_skus() -> set[str]:
    """
    Get all synced SKUs from Redis (async).

    Returns:
        Set of synced SKUs
    """
    try:
        redis = await redis_connection.get_client()
        synced_key = CacheKeys.elasticsearch_synced_skus()
        skus = await redis.smembers(synced_key)
        logger.info(f"Retrieved {len(skus)} synced SKUs from Redis")
        return skus
    except Exception as e:
        logger.error(f"Failed to get synced SKUs from Redis: {e}")
        return set()


async def get_unsynced_skus(all_skus: list[str]) -> set[str]:
    """
    Get SKUs that are not yet synced from a list (async).

    This is much more efficient than checking Elasticsearch.

    Args:
        all_skus: List of all SKUs to check

    Returns:
        Set of SKUs that are not synced
    """
    try:
        redis = await redis_connection.get_client()
        synced_key = CacheKeys.elasticsearch_synced_skus()

        pipe = redis.pipeline()
        for sku in all_skus:
            pipe.sismember(synced_key, sku)

        results = await pipe.execute()

        unsynced = [sku for sku, is_synced in zip(all_skus, results) if not is_synced]

        logger.info(f"Found {len(unsynced)}/{len(all_skus)} unsynced SKUs")
        return set(unsynced)

    except Exception as e:
        logger.error(f"Failed to get unsynced SKUs from Redis: {e}")
        return set(all_skus)


async def remove_synced_sku(sku: str) -> bool:
    """
    Remove a SKU from synced set (e.g., when product is deleted) (async).

    Args:
        sku: SKU to remove

    Returns:
        True if successful, False otherwise
    """
    try:
        redis = await redis_connection.get_client()
        synced_key = CacheKeys.elasticsearch_synced_skus()
        await redis.srem(synced_key, sku)
        logger.debug(f"Removed SKU {sku} from synced set")
        return True
    except Exception as e:
        logger.error(f"Failed to remove SKU from Redis: {e}")
        return False


async def clear_sync_state() -> bool:
    """
    Clear all sync state from Redis (async).

    Use this when forcing a full resync or resetting sync tracking.

    Returns:
        True if successful, False otherwise
    """
    try:
        redis = await redis_connection.get_client()
        synced_key = CacheKeys.elasticsearch_synced_skus()
        await redis.delete(synced_key)
        logger.info("Cleared all sync state from Redis")
        return True
    except Exception as e:
        logger.error(f"Failed to clear sync state from Redis: {e}")
        return False


async def get_sync_stats() -> dict:
    """
    Get statistics about sync state (async).

    Returns:
        Dictionary with sync statistics
    """
    try:
        redis = await redis_connection.get_client()
        synced_key = CacheKeys.elasticsearch_synced_skus()
        synced_count = await redis.scard(synced_key)

        return {
            "total_synced": synced_count,
            "redis_healthy": await redis_connection.health_check()
        }
    except Exception as e:
        logger.error(f"Failed to get sync stats from Redis: {e}")
        return {
            "total_synced": 0,
            "redis_healthy": False
        }
