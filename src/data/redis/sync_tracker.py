"""Redis-based sync state tracking for Elasticsearch sync optimization."""

from src.data.redis.connection import redis_connection
from src.utils.logger import get_current_logger

logger = get_current_logger()


SYNCED_SKUS_KEY = "elasticsearch:synced_skus"


def mark_skus_as_synced(skus: list[str]) -> bool:
    """
    Mark SKUs as synced to Elasticsearch by adding to Redis Set.

    Args:
        skus: List of SKUs to mark as synced

    Returns:
        True if successful, False otherwise
    """
    if not skus:
        return True

    try:
        redis = redis_connection.get_client()
        # SADD is O(1) per element, very fast
        redis.sadd(SYNCED_SKUS_KEY, *skus)
        logger.debug(f"Marked {len(skus)} SKUs as synced in Redis")
        return True
    except Exception as e:
        logger.error(f"Failed to mark SKUs as synced in Redis: {e}")
        return False


def is_sku_synced(sku: str) -> bool:
    """
    Check if a SKU is already synced to Elasticsearch.

    This is an O(1) operation in Redis Set.

    Args:
        sku: SKU to check

    Returns:
        True if synced, False otherwise
    """
    try:
        redis = redis_connection.get_client()
        return redis.sismember(SYNCED_SKUS_KEY, sku)
    except Exception as e:
        logger.error(f"Failed to check SKU sync status in Redis: {e}")
        return False


def get_all_synced_skus() -> set[str]:
    """
    Get all synced SKUs from Redis.

    Returns:
        Set of synced SKUs
    """
    try:
        redis = redis_connection.get_client()
        skus = redis.smembers(SYNCED_SKUS_KEY)
        logger.info(f"Retrieved {len(skus)} synced SKUs from Redis")
        return skus
    except Exception as e:
        logger.error(f"Failed to get synced SKUs from Redis: {e}")
        return set()


def get_unsynced_skus(all_skus: list[str]) -> set[str]:
    """
    Get SKUs that are not yet synced from a list.

    This is much more efficient than checking Elasticsearch.

    Args:
        all_skus: List of all SKUs to check

    Returns:
        Set of SKUs that are not synced
    """
    try:
        redis = redis_connection.get_client()

        # Use pipeline for batch operations
        pipe = redis.pipeline()
        for sku in all_skus:
            pipe.sismember(SYNCED_SKUS_KEY, sku)

        results = pipe.execute()

        # Filter out SKUs that are already synced
        unsynced = [sku for sku, is_synced in zip(all_skus, results) if not is_synced]

        logger.info(f"Found {len(unsynced)}/{len(all_skus)} unsynced SKUs")
        return set(unsynced)

    except Exception as e:
        logger.error(f"Failed to get unsynced SKUs from Redis: {e}")
        # Fallback: return all SKUs if Redis fails
        return set(all_skus)


def remove_synced_sku(sku: str) -> bool:
    """
    Remove a SKU from synced set (e.g., when product is deleted).

    Args:
        sku: SKU to remove

    Returns:
        True if successful, False otherwise
    """
    try:
        redis = redis_connection.get_client()
        redis.srem(SYNCED_SKUS_KEY, sku)
        logger.debug(f"Removed SKU {sku} from synced set")
        return True
    except Exception as e:
        logger.error(f"Failed to remove SKU from Redis: {e}")
        return False


def clear_sync_state() -> bool:
    """
    Clear all sync state from Redis.

    Use this when forcing a full resync or resetting sync tracking.

    Returns:
        True if successful, False otherwise
    """
    try:
        redis = redis_connection.get_client()
        redis.delete(SYNCED_SKUS_KEY)
        logger.info("Cleared all sync state from Redis")
        return True
    except Exception as e:
        logger.error(f"Failed to clear sync state from Redis: {e}")
        return False


def get_sync_stats() -> dict:
    """
    Get statistics about sync state.

    Returns:
        Dictionary with sync statistics
    """
    try:
        redis = redis_connection.get_client()
        synced_count = redis.scard(SYNCED_SKUS_KEY)

        return {
            "total_synced": synced_count,
            "redis_healthy": redis_connection.health_check()
        }
    except Exception as e:
        logger.error(f"Failed to get sync stats from Redis: {e}")
        return {
            "total_synced": 0,
            "redis_healthy": False
        }
