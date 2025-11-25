import datetime
import asyncio

from sqlalchemy import select
from src.data.postgres.connection import db_connection
from src.data.elasticsearch.connection import es_connection
from src.data.redis.sync_tracker import (
    get_unsynced_skus,
    mark_skus_as_synced,
    get_sync_stats
)
from src.config import ELASTIC_INDEX
from src.utils.logger import get_current_logger

logger = get_current_logger()


async def sync_products_to_elastic():
    """
    Sync products from PostgreSQL to Elasticsearch using Redis-optimized approach (async).

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
        one_minute_ago = datetime.datetime.now(datetime.UTC)
        from datetime import timedelta
        one_minute_ago = one_minute_ago - timedelta(seconds=60)

        session = pg.get_session()
        try:
            async with session:
                from src.data.models.db_entity.product import Product
                
                result = await session.execute(
                    select(Product).filter(Product.updated_at >= one_minute_ago)
                )
                products = list(result.scalars().all())

                if not products:
                    stats = await get_sync_stats()
                    if stats["total_synced"] == 0:
                        logger.info("📊 First sync - loading products in batches for memory efficiency")
                        # Use pagination to avoid loading all products into memory at once
                        batch_size = 1000
                        offset = 0
                        products = []
                        while True:
                            batch_result = await session.execute(
                                select(Product).limit(batch_size).offset(offset)
                            )
                            batch = list(batch_result.scalars().all())
                            if not batch:
                                break
                            products.extend(batch)
                            offset += batch_size
                            logger.info(f"  Loaded {len(products)} products so far...")
                    else:
                        logger.info("ℹ️ No new products to sync")
                        return
        except Exception as e:
            logger.error(f"Error querying products: {e}")
            raise

        if not products:
            logger.info("ℹ️ No products found")
            return

        product_map = {p.sku: p for p in products}
        all_skus = list(product_map.keys())

        logger.info(f"📦 Checking {len(all_skus)} products")

        # Use Redis to get unsynced SKUs
        unsynced_skus = await get_unsynced_skus(all_skus)

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
        from elasticsearch.helpers import async_bulk
        await async_bulk(es, actions)

        await mark_skus_as_synced(list(unsynced_skus))

        logger.info(
            f"✅ Synced {len(actions)} products to Elasticsearch "
            f"(skipped {len(all_skus) - len(unsynced_skus)} already synced)"
        )

        stats = await get_sync_stats()
        logger.info(f"📊 Total synced products in Redis: {stats['total_synced']}")

    except Exception as e:
        logger.error(f"❌ Failed to sync products to Elasticsearch: {str(e)}")
        raise


# For backward compatibility with scripts that might call this non-async
def sync_products_to_elastic_sync():
    """Synchronous wrapper for async sync function."""
    asyncio.run(sync_products_to_elastic())