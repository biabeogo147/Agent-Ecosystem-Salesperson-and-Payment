from datetime import datetime

from src.data.postgres.connection import db_connection
from src.data.elasticsearch.connection import es_connection
from src.data.redis.sync_tracker import (
    get_unsynced_skus,
    mark_skus_as_synced,
    clear_sync_state,
    get_sync_stats
)
from src.config import ELASTIC_INDEX
from src.utils.logger import logger


def sync_products_to_elastic():
    """
    Sync products from PostgreSQL to Elasticsearch using Redis-optimized approach.

    Workflow:
    1. Query products updated in last minute (or all if first run)
    2. Use Redis to check which SKUs are not yet synced (O(1) lookup)
    3. Index only unsynced products to Elasticsearch
    4. Mark synced SKUs in Redis

    This is EXTREMELY efficient:
    - Redis Set lookup: O(1) per SKU
    - No scrolling Elasticsearch
    - No timestamp file management
    - Persistent state in Redis
    """
    pg = db_connection
    es = es_connection.get_client()

    try:
        # Get products updated in last 60 seconds (to catch recent changes)
        # This query is super fast thanks to index on updated_at
        one_minute_ago = datetime.utcnow()
        from datetime import timedelta
        one_minute_ago = one_minute_ago - timedelta(seconds=60)

        session = pg.get_session()
        try:
            from src.data.models.db_entity.product import Product
            products = session.query(Product).filter(
                Product.updated_at >= one_minute_ago
            ).all()

            # On first run or if no recent products, get all
            if not products:
                # Check if we have any sync state
                stats = get_sync_stats()
                if stats["total_synced"] == 0:
                    logger.info("📊 First sync - getting all products")
                    products = session.query(Product).all()
                else:
                    logger.info("ℹ️ No new products to sync")
                    return
        finally:
            session.close()

        if not products:
            logger.info("ℹ️ No products found")
            return

        # Extract SKUs and create product map
        product_map = {p.sku: p for p in products}
        all_skus = list(product_map.keys())

        logger.info(f"📦 Checking {len(all_skus)} products")

        # Use Redis to get unsynced SKUs (SUPER FAST - O(n) with pipelining)
        unsynced_skus = get_unsynced_skus(all_skus)

        if not unsynced_skus:
            logger.info(f"✅ All {len(all_skus)} products already synced")
            return

        logger.info(f"🔄 Found {len(unsynced_skus)} new products to sync")

        # Prepare bulk actions for unsynced products only
        actions = [
            {
                "_op_type": "index",
                "_index": ELASTIC_INDEX,
                "_id": sku,
                "_source": product_map[sku].to_dict()
            }
            for sku in unsynced_skus
        ]

        # Bulk index to Elasticsearch
        from elasticsearch.helpers import bulk
        bulk(es, actions)

        # Mark as synced in Redis
        mark_skus_as_synced(list(unsynced_skus))

        logger.info(
            f"✅ Synced {len(actions)} products to Elasticsearch "
            f"(skipped {len(all_skus) - len(unsynced_skus)} already synced)"
        )

        # Log stats
        stats = get_sync_stats()
        logger.info(f"📊 Total synced products in Redis: {stats['total_synced']}")

    except Exception as e:
        logger.error(f"❌ Failed to sync products to Elasticsearch: {str(e)}")
        raise


def force_full_resync():
    """
    Force a full resync of all products.

    This will:
    1. Clear all sync state from Redis
    2. Re-index all products from PostgreSQL to Elasticsearch

    Use this when:
    - Elasticsearch index was recreated
    - You suspect data inconsistency
    - Initial setup
    """
    logger.info("🔄 Forcing full resync - clearing Redis sync state...")

    # Clear Redis sync state
    clear_sync_state()

    logger.info("🔄 Starting full product sync...")

    # Trigger sync (will sync all products since Redis state is empty)
    sync_products_to_elastic()

    logger.info("✅ Full resync completed!")


def get_sync_statistics() -> dict:
    """
    Get current sync statistics.

    Returns:
        Dictionary with sync stats
    """
    return get_sync_stats()
