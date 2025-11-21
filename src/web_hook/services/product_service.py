from typing import Optional, List

from src.data.db_connection import db_connection
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
            stock=data.stock
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


def get_product(sku: str) -> Optional[Product]:
    """Get product by SKU."""
    session = db_connection.get_session()
    try:
        return session.query(Product).filter(Product.sku == sku).first()
    finally:
        session.close()


def get_all_products() -> List[Product]:
    """Get all products."""
    session = db_connection.get_session()
    try:
        return session.query(Product).all()
    finally:
        session.close()


def delete_product(sku: str) -> bool:
    """Delete a product by SKU."""
    session = db_connection.get_session()
    try:
        product = session.query(Product).filter(Product.sku == sku).first()
        if not product:
            return False
        session.delete(product)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()