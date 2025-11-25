from datetime import datetime
from sqlalchemy import select
from src.data.postgres.connection import db_connection
from src.data.models.db_entity.product import Product
from src.data.redis.cache_ops import get_cached_value, set_cached_value, delete_cached_value
from src.data.redis.cache_keys import CacheKeys, TTL
from src.utils.logger import get_current_logger

logger = get_current_logger()


async def find_product_by_sku(sku: str, use_cache: bool = True) -> Product | None:
    """
    Find a product by its SKU in PostgreSQL with Redis caching (async).

    Args:
        sku: Product SKU to search for
        use_cache: Whether to use Redis cache (default: True)

    Returns:
        Product object if found, None otherwise
    """
    cache_key = CacheKeys.product_by_sku(sku)

    if use_cache:
        try:
            cached = await get_cached_value(cache_key)
            if cached:
                logger.debug(f"Cache HIT: {cache_key}")
                return Product(**cached)
        except Exception as e:
            logger.warning(f"Cache read failed for {cache_key}, using DB: {e}")

    logger.debug(f"Cache MISS: {cache_key}")
    session = db_connection.get_session()
    try:
        async with session:
            result = await session.execute(
                select(Product).filter(Product.sku == sku)
            )
            product = result.scalar_one_or_none()

            if product and use_cache:
                try:
                    await set_cached_value(cache_key, product.to_dict(), ttl=TTL.PRODUCT)
                    logger.debug(f"Cached product: {cache_key}")
                except Exception as e:
                    logger.warning(f"Failed to cache product {sku}: {e}")

            return product
    except Exception as e:
        logger.error(f"Error finding product by SKU {sku}: {e}")
        raise


async def update_product_stock(sku: str, new_stock: int) -> bool:
    """
    Update the stock of a product by its SKU in PostgreSQL (async).
    Invalidates cache after successful update.

    Args:
        sku: Product SKU
        new_stock: New stock quantity

    Returns:
        True if updated successfully, False otherwise
    """
    session = db_connection.get_session()
    try:
        async with session:
            result = await session.execute(
                select(Product).filter(Product.sku == sku)
            )
            product = result.scalar_one_or_none()
            
            if not product:
                logger.warning(f"Product {sku} not found for stock update")
                return False

            product.stock = new_stock
            await session.commit()
            logger.info(f"Updated stock for {sku}: {new_stock}")

            try:
                cache_key = CacheKeys.product_by_sku(sku)
                await delete_cached_value(cache_key)
                logger.debug(f"Invalidated cache: {cache_key}")
            except Exception as e:
                logger.warning(f"Failed to invalidate cache for {sku}: {e}")

            return True
    except Exception as e:
        logger.error(f"Failed to update stock for {sku}: {e}")
        await session.rollback()
        return False


async def get_all_products(limit: int = None, offset: int = 0) -> list[Product]:
    """
    Get products from PostgreSQL with optional pagination (async).

    Args:
        limit: Maximum number of products to return (None = all)
        offset: Number of products to skip

    Returns:
        List of Product objects
    """
    session = db_connection.get_session()
    try:
        async with session:
            query = select(Product)

            if limit is not None:
                query = query.limit(limit).offset(offset)

            result = await session.execute(query)
            products = result.scalars().all()
            return list(products)
    except Exception as e:
        logger.error(f"Error getting all products: {e}")
        raise


async def get_products_updated_since(timestamp: datetime) -> list[Product]:
    """
    Get products that were created or updated after the given timestamp (async).

    This is used for efficient incremental syncing to Elasticsearch.

    Args:
        timestamp: Datetime to filter from

    Returns:
        List of Product objects updated since timestamp
    """
    session = db_connection.get_session()
    try:
        async with session:
            result = await session.execute(
                select(Product).filter(Product.updated_at > timestamp)
            )
            products = result.scalars().all()
            logger.info(f"Found {len(products)} products updated since {timestamp}")
            return list(products)
    except Exception as e:
        logger.error(f"Error getting products updated since {timestamp}: {e}")
        raise


async def get_products_by_merchant(merchant_id: int) -> list[Product]:
    """
    Get all products for a specific merchant (async).

    Args:
        merchant_id: Merchant ID to filter by

    Returns:
        List of Product objects for the merchant
    """
    session = db_connection.get_session()
    try:
        async with session:
            result = await session.execute(
                select(Product).filter(Product.merchant_id == merchant_id)
            )
            products = result.scalars().all()
            return list(products)
    except Exception as e:
        logger.error(f"Error getting products by merchant {merchant_id}: {e}")
        raise
