from src.data.redis.connection import redis_connection
from src.data.redis.cache_keys import CacheKeys
from src.utils.logger import get_current_logger


async def mark_skus_as_synced(skus: list[str]) -> bool:
    """
    Mark SKUs as synced to Elasticsearch by adding to Redis Set (async).

    Args:
        skus: List of SKUs to mark as synced

    Returns:
        True if successful, False otherwise
    """
    logger = get_current_logger()
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


async def get_unsynced_skus(all_skus: list[str]) -> set[str]:
    """
    Get SKUs that are not yet synced from a list (async).

    This is much more efficient than checking Elasticsearch.

    Args:
        all_skus: List of all SKUs to check

    Returns:
        Set of SKUs that are not synced
    """
    logger = get_current_logger()
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


async def get_sync_stats() -> dict:
    """
    Get statistics about sync state (async).

    Returns:
        Dictionary with sync statistics
    """
    logger = get_current_logger()
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
