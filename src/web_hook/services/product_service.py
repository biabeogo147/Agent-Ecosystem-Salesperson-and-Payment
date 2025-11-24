from typing import Optional, List

from src.data.postgres.connection import db_connection
from src.data.models.db_entity.product import Product
from src.data.redis.cache_ops import get_cached_value, set_cached_value, delete_cached_value, clear_pattern
from src.data.redis.cache_keys import CacheKeys, CachePatterns, TTL
from src.web_hook.schemas.product_schemas import ProductCreate, ProductUpdate
from src.web_hook import webhook_logger as logger


def create_product(data: ProductCreate) -> Product:
    session = db_connection.get_session()
    try:
        existing = session.query(Product).filter(Product.sku == data.sku).first()
        if existing:
            raise ValueError(f"Product with SKU '{data.sku}' already exists")

        product = Product(
            sku=data.sku,
            name=data.name,
            price=data.price,
            currency=data.currency,
            stock=data.stock,
            merchant_id=data.merchant_id
        )
        session.add(product)
        session.commit()
        session.refresh(product)

        try:
            clear_pattern(CachePatterns.products_by_merchant_pattern(data.merchant_id))
            clear_pattern(CachePatterns.all_products_pattern())
            logger.debug(f"Invalidated cache for new product: {data.sku}")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache for new product {data.sku}: {e}")

        return product
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def update_product(sku: str, data: ProductUpdate) -> Product:
    session = db_connection.get_session()
    try:
        product = session.query(Product).filter(Product.sku == sku).first()
        if not product:
            raise ValueError(f"Product with SKU '{sku}' not found")
        
        if product.merchant_id != data.merchant_id:
             raise ValueError(f"Merchant '{data.merchant_id}' is not authorized to update this product")

        if data.name is not None:
            product.name = data.name
        if data.price is not None:
            product.price = data.price
        if data.currency is not None:
            product.currency = data.currency
        if data.stock is not None:
            product.stock = data.stock

        session.commit()
        session.refresh(product)

        try:
            delete_cached_value(CacheKeys.product_by_sku(sku))
            delete_cached_value(CacheKeys.product_by_merchant_and_sku(product.merchant_id, sku))
            clear_pattern(CachePatterns.products_by_merchant_pattern(product.merchant_id))
            clear_pattern(CachePatterns.search_products_pattern())
            logger.debug(f"Invalidated cache for updated product: {sku}")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache for updated product {sku}: {e}")

        return product
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_product(sku: str, merchant_id: int) -> Optional[Product]:
    cache_key = CacheKeys.product_by_merchant_and_sku(merchant_id, sku)

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
        query = session.query(Product).filter(
            Product.sku == sku,
            Product.merchant_id == merchant_id
        )
        product = query.first()

        if product:
            try:
                set_cached_value(cache_key, product.to_dict(), ttl=TTL.PRODUCT)
                logger.debug(f"Cached product: {cache_key}")
            except Exception as e:
                logger.warning(f"Failed to cache product {sku}: {e}")

        return product
    finally:
        session.close()


def get_all_products(merchant_id: int) -> List[Product]:
    cache_key = (CacheKeys.products_by_merchant(merchant_id)
                 if merchant_id is not None
                 else CacheKeys.all_products())

    try:
        cached = get_cached_value(cache_key)
        if cached:
            logger.debug(f"Cache HIT: {cache_key}")
            return [Product(**p) for p in cached]
    except Exception as e:
        logger.warning(f"Cache read failed for {cache_key}, using DB: {e}")

    logger.debug(f"Cache MISS: {cache_key}")
    session = db_connection.get_session()
    try:
        query = session.query(Product)
        if merchant_id is not None:
            query = query.filter(Product.merchant_id == merchant_id)
        products = query.all()

        try:
            products_dict = [p.to_dict() for p in products]
            set_cached_value(cache_key, products_dict, ttl=TTL.PRODUCT_LIST)
            logger.debug(f"Cached products: {cache_key}")
        except Exception as e:
            logger.warning(f"Failed to cache products: {e}")

        return products
    finally:
        session.close()


def delete_product(sku: str, merchant_id: int) -> bool:
    session = db_connection.get_session()
    try:
        product = session.query(Product).filter(Product.sku == sku).first()
        if not product:
            return False
        
        if product.merchant_id != merchant_id:
             raise ValueError(f"Merchant '{merchant_id}' is not authorized to delete this product")

        session.delete(product)
        session.commit()

        try:
            delete_cached_value(CacheKeys.product_by_sku(sku))
            delete_cached_value(CacheKeys.product_by_merchant_and_sku(merchant_id, sku))
            clear_pattern(CachePatterns.products_by_merchant_pattern(merchant_id))
            clear_pattern(CachePatterns.all_products_pattern())
            logger.debug(f"Invalidated cache for deleted product: {sku}")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache for deleted product {sku}: {e}")

        return True
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()