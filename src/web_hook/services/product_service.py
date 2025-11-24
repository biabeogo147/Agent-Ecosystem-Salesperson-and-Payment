from typing import Optional, List

from src.data.postgres.connection import db_connection
from src.data.models.db_entity.product import Product
from src.web_hook.schemas.product_schemas import ProductCreate, ProductUpdate


def create_product(data: ProductCreate) -> Product:
    """Create a new product in the database."""
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
        return product
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def update_product(sku: str, data: ProductUpdate) -> Product:
    """Update an existing product."""
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
        return product
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_product(sku: str, merchant_id: int) -> Optional[Product]:
    """Get product by SKU, optionally verifying merchant_id."""
    session = db_connection.get_session()
    try:
        query = session.query(Product).filter(Product.sku == sku)
        if merchant_id is not None:
            query = query.filter(Product.merchant_id == merchant_id)
        return query.first()
    finally:
        session.close()


def get_all_products(merchant_id: int) -> List[Product]:
    """Get all products, optionally filtered by merchant_id."""
    session = db_connection.get_session()
    try:
        query = session.query(Product)
        if merchant_id is not None:
            query = query.filter(Product.merchant_id == merchant_id)
        return query.all()
    finally:
        session.close()


def delete_product(sku: str, merchant_id: int) -> bool:
    """Delete a product by SKU."""
    session = db_connection.get_session()
    try:
        product = session.query(Product).filter(Product.sku == sku).first()
        if not product:
            return False
        
        if product.merchant_id != merchant_id:
             raise ValueError(f"Merchant '{merchant_id}' is not authorized to delete this product")
             
        session.delete(product)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()