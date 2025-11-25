from typing import Optional, List
import asyncio

from sqlalchemy import select
from src.data.postgres.connection import db_connection
from src.data.models.db_entity.product import Product
from src.data.redis.cache_ops import get_cached_value, set_cached_value, delete_cached_value, clear_pattern
from src.data.redis.cache_keys import CacheKeys, CachePatterns, TTL
from src.web_hook.schemas.product_schemas import ProductCreate, ProductUpdate
from src.web_hook import webhook_logger as logger


async def _invalidate_create_cache(merchant_id: int, sku: str):
    """Background task to invalidate cache after product creation."""
    try:
        await asyncio.gather(
            clear_pattern(CachePatterns.products_by_merchant_pattern(merchant_id)),
            clear_pattern(CachePatterns.all_products_pattern()),
            return_exceptions=True
        )
        logger.debug(f"Invalidated cache for new product: {sku}")
    except Exception as e:
        logger.warning(f"Failed to invalidate cache for new product {sku}: {e}")


async def _invalidate_update_cache(sku: str, merchant_id: int):
    """Background task to invalidate cache after product update."""
    try:
        await asyncio.gather(
            delete_cached_value(CacheKeys.product_by_sku(sku)),
            delete_cached_value(CacheKeys.product_by_merchant_and_sku(merchant_id, sku)),
            clear_pattern(CachePatterns.products_by_merchant_pattern(merchant_id)),
            clear_pattern(CachePatterns.search_products_pattern()),
            return_exceptions=True
        )
        logger.debug(f"Invalidated cache for updated product: {sku}")
    except Exception as e:
        logger.warning(f"Failed to invalidate cache for updated product {sku}: {e}")


async def _invalidate_delete_cache(sku: str, merchant_id: int):
    """Background task to invalidate cache after product deletion."""
    try:
        await asyncio.gather(
            delete_cached_value(CacheKeys.product_by_sku(sku)),
            delete_cached_value(CacheKeys.product_by_merchant_and_sku(merchant_id, sku)),
            clear_pattern(CachePatterns.products_by_merchant_pattern(merchant_id)),
            clear_pattern(CachePatterns.all_products_pattern()),
            return_exceptions=True
        )
        logger.debug(f"Invalidated cache for deleted product: {sku}")
    except Exception as e:
        logger.warning(f"Failed to invalidate cache for deleted product {sku}: {e}")


async def _set_product_cache_bg(cache_key: str, product_dict: dict):
    """Background task to cache product."""
    try:
        await set_cached_value(cache_key, product_dict, ttl=TTL.PRODUCT)
        logger.debug(f"Cached product: {cache_key}")
    except Exception as e:
        logger.warning(f"Failed to cache product: {e}")


async def _set_products_cache_bg(cache_key: str, products_dict: list):
    """Background task to cache product list."""
    try:
        await set_cached_value(cache_key, products_dict, ttl=TTL.PRODUCT_LIST)
        logger.debug(f"Cached products: {cache_key}")
    except Exception as e:
        logger.warning(f"Failed to cache products: {e}")


async def create_product(data: ProductCreate) -> Product:
    session = db_connection.get_session()
    try:
        async with session:
            result = await session.execute(
                select(Product).filter(Product.sku == data.sku)
            )
            existing = result.scalar_one_or_none()
            
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
            await session.commit()
            await session.refresh(product)

            asyncio.create_task(_invalidate_create_cache(data.merchant_id, data.sku))

            return product
    except Exception as e:
        await session.rollback()
        raise e


async def update_product(sku: str, data: ProductUpdate) -> Product:
    session = db_connection.get_session()
    try:
        async with session:
            result = await session.execute(
                select(Product).filter(Product.sku == sku)
            )
            product = result.scalar_one_or_none()
            
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

            await session.commit()
            await session.refresh(product)

            asyncio.create_task(_invalidate_update_cache(sku, product.merchant_id))

            return product
    except Exception as e:
        await session.rollback()
        raise e


async def get_product(sku: str, merchant_id: int) -> Optional[Product]:
    cache_key = CacheKeys.product_by_merchant_and_sku(merchant_id, sku)

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
                select(Product).filter(
                    Product.sku == sku,
                    Product.merchant_id == merchant_id
                )
            )
            product = result.scalar_one_or_none()

            if product:
                asyncio.create_task(_set_product_cache_bg(cache_key, product.to_dict()))

            return product
    except Exception as e:
        logger.error(f"Error getting product {sku}: {e}")
        raise


async def get_all_products(merchant_id: int) -> List[Product]:
    cache_key = (CacheKeys.products_by_merchant(merchant_id)
                 if merchant_id is not None
                 else CacheKeys.all_products())

    try:
        cached = await get_cached_value(cache_key)
        if cached:
            logger.debug(f"Cache HIT: {cache_key}")
            return [Product(**p) for p in cached]
    except Exception as e:
        logger.warning(f"Cache read failed for {cache_key}, using DB: {e}")

    logger.debug(f"Cache MISS: {cache_key}")
    session = db_connection.get_session()
    try:
        async with session:
            query = select(Product)
            if merchant_id is not None:
                query = query.filter(Product.merchant_id == merchant_id)
            
            result = await session.execute(query)
            products = result.scalars().all()

            products_dict = [p.to_dict() for p in products]
            asyncio.create_task(_set_products_cache_bg(cache_key, products_dict))

            return list(products)
    except Exception as e:
        logger.error(f"Error getting all products: {e}")
        raise


async def delete_product(sku: str, merchant_id: int) -> bool:
    session = db_connection.get_session()
    try:
        async with session:
            result = await session.execute(
                select(Product).filter(Product.sku == sku)
            )
            product = result.scalar_one_or_none()
            
            if not product:
                return False
            
            if product.merchant_id != merchant_id:
                 raise ValueError(f"Merchant '{merchant_id}' is not authorized to delete this product")

            await session.delete(product)
            await session.commit()

            asyncio.create_task(_invalidate_delete_cache(sku, merchant_id))

            return True
    except Exception as e:
        await session.rollback()
        raise e