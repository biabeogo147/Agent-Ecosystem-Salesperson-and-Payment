from datetime import datetime
from src.data.postgres.connection import db_connection
from src.data.models.db_entity.product import Product
from src.data.redis.cache_ops import get_cached_value, set_cached_value, delete_cached_value
from src.data.redis.cache_keys import CacheKeys, TTL
from src.utils.logger import get_current_logger

logger = get_current_logger()


def find_product_by_sku(sku: str, use_cache: bool = True) -> Product | None:
    """
    Find a product by its SKU in PostgreSQL with Redis caching.

    Args:
        sku: Product SKU to search for
        use_cache: Whether to use Redis cache (default: True)

    Returns:
        Product object if found, None otherwise
    """
    cache_key = CacheKeys.product_by_sku(sku)

    if use_cache:
        try:
            cached = get_cached_value(cache_key)
            if cached:
                logger.debug(f"Cache HIT: {cache_key}")
                return Product(**cached)
        except Exception as e:
            logger.warning(f"Cache read failed for {cache_key}, using DB: {e}")

    logger.debug(f"Cache MISS: {cache_key}")
    session = db_connection.get_session()
    try:
        product = session.query(Product).filter(Product.sku == sku).first()

        if product and use_cache:
            try:
                set_cached_value(cache_key, product.to_dict(), ttl=TTL.PRODUCT)
                logger.debug(f"Cached product: {cache_key}")
            except Exception as e:
                logger.warning(f"Failed to cache product {sku}: {e}")

        return product
    finally:
        session.close()


def update_product_stock(sku: str, new_stock: int) -> bool:
    """
    Update the stock of a product by its SKU in PostgreSQL.
    Invalidates cache after successful update.

    Args:
        sku: Product SKU
        new_stock: New stock quantity

    Returns:
        True if updated successfully, False otherwise
    """
    session = db_connection.get_session()
    try:
        product = session.query(Product).filter(Product.sku == sku).first()
        if not product:
            logger.warning(f"Product {sku} not found for stock update")
            return False

        product.stock = new_stock
        session.commit()
        logger.info(f"Updated stock for {sku}: {new_stock}")

        # Invalidate cache after successful update
        try:
            cache_key = CacheKeys.product_by_sku(sku)
            delete_cached_value(cache_key)
            logger.debug(f"Invalidated cache: {cache_key}")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache for {sku}: {e}")

        return True
    except Exception as e:
        logger.error(f"Failed to update stock for {sku}: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def get_all_products() -> list[Product]:
    """
    Get all products from PostgreSQL.

    Returns:
        List of all Product objects
    """
    session = db_connection.get_session()
    try:
        products = session.query(Product).all()
        return products
    finally:
        session.close()


def get_products_updated_since(timestamp: datetime) -> list[Product]:
    """
    Get products that were created or updated after the given timestamp.

    This is used for efficient incremental syncing to Elasticsearch.

    Args:
        timestamp: Datetime to filter from

    Returns:
        List of Product objects updated since timestamp
    """
    session = db_connection.get_session()
    try:
        products = session.query(Product).filter(
            Product.updated_at > timestamp
        ).all()
        logger.info(f"Found {len(products)} products updated since {timestamp}")
        return products
    finally:
        session.close()


def get_products_by_merchant(merchant_id: int) -> list[Product]:
    """
    Get all products for a specific merchant.

    Args:
        merchant_id: Merchant ID to filter by

    Returns:
        List of Product objects for the merchant
    """
    session = db_connection.get_session()
    try:
        products = session.query(Product).filter(
            Product.merchant_id == merchant_id
        ).all()
        return products
    finally:
        session.close()
