from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, DECIMAL, Integer

Base = declarative_base()

class ProductModel(Base):
    __tablename__ = 'products'
    
    sku = Column(String, primary_key=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    price = Column(DECIMAL(18, 2), nullable=False)
    currency = Column(String, nullable=False, default="USD")
    stock = Column(Integer, nullable=False)