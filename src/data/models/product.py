from sqlalchemy import Column, String, DECIMAL, Integer
from data.models import Base

class Product(Base):
    __tablename__ = 'products'

    sku = Column(String, primary_key=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    price = Column(DECIMAL(18, 2), nullable=False)
    currency = Column(String, nullable=False, default="USD")
    stock = Column(Integer, nullable=False)

    def to_dict(self):
        return {
            "sku": self.sku,
            "name": self.name,
            "price": float(self.price),
            "currency": self.currency,
            "stock": self.stock
        }
