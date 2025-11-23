from sqlalchemy import Column, String, DECIMAL, Integer, ForeignKey
from src.data.models import Base

class Product(Base):
    __tablename__ = 'product'

    sku = Column(String, primary_key=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    price = Column(DECIMAL(18, 2), nullable=False)
    currency = Column(String, nullable=False, default="USD")
    stock = Column(Integer, nullable=False)
    merchant_id = Column(Integer, ForeignKey('merchant.id'), nullable=True)

    def to_dict(self):
        return {
            "sku": self.sku,
            "name": self.name,
            "price": float(self.price),
            "currency": self.currency,
            "stock": self.stock,
            "merchant_id": self.merchant_id
        }
