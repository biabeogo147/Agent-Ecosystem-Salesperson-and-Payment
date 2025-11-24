from sqlalchemy import Column, String, DECIMAL, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func

from src.data.models import Base

class Product(Base):
    __tablename__ = 'product'

    sku = Column(String, primary_key=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    price = Column(DECIMAL(18, 2), nullable=False)
    currency = Column(String, nullable=False, default="USD")
    stock = Column(Integer, nullable=False)
    merchant_id = Column(Integer, ForeignKey('merchant.id'), nullable=True, index=True)  # Index for merchant filtering
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False, index=True)  # Index for sync queries

    def to_dict(self):
        return {
            "sku": self.sku,
            "name": self.name,
            "price": float(self.price),
            "currency": self.currency,
            "stock": self.stock,
            "merchant_id": self.merchant_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
