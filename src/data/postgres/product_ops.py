from datetime import datetime
from src.data.postgres.connection import db_connection
from src.data.models.db_entity.product import Product
from src.utils.logger import logger


def find_product_by_sku(sku: str) -> Product | None:
    """
    Find a product by its SKU in PostgreSQL.

    Args:
        sku: Product SKU to search for

    Returns:
        Product object if found, None otherwise
    """
    session = db_connection.get_session()
    try:
        product = session.query(Product).filter(Product.sku == sku).first()
        return product
    finally:
        session.close()


def update_product_stock(sku: str, new_stock: int) -> bool:
    """
    Update the stock of a product by its SKU in PostgreSQL.

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
        # updated_at will be automatically updated by trigger
        session.commit()
        logger.info(f"Updated stock for {sku}: {new_stock}")
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
