"""Redis module for caching and state management."""

from src.data.redis.connection import RedisConnection, redis_connection
from src.data.redis.cache_ops import (
    get_cached_value,
    set_cached_value,
    delete_cached_value,
    clear_pattern
)
from src.data.redis.cache_keys import CacheKeys, CachePatterns, TTL
from src.data.redis.sync_tracker import (
    mark_skus_as_synced,
    is_sku_synced,
    get_all_synced_skus,
    get_unsynced_skus,
    remove_synced_sku,
    clear_sync_state,
    get_sync_stats
)

__all__ = [
    # Connection
    "RedisConnection",
    "redis_connection",
    # Cache operations
    "get_cached_value",
    "set_cached_value",
    "delete_cached_value",
    "clear_pattern",
    # Cache keys and TTL
    "CacheKeys",
    "CachePatterns",
    "TTL",
    # Sync tracking
    "mark_skus_as_synced",
    "is_sku_synced",
    "get_all_synced_skus",
    "get_unsynced_skus",
    "remove_synced_sku",
    "clear_sync_state",
    "get_sync_stats"
]
