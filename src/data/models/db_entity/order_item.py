from sqlalchemy import Column, Integer, String, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship
from src.data.models import Base


class OrderItem(Base):
    __tablename__ = "order_item"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("order.id", ondelete="CASCADE"), nullable=False)
    product_sku = Column(String, ForeignKey("product.sku"), nullable=False)
    product_name = Column(String, nullable=False)  # Snapshot at order time
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(DECIMAL(18, 2), nullable=False)
    currency = Column(String, nullable=False, default="USD")

    order = relationship("Order", back_populates="items")
    product = relationship("Product")

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "product_sku": self.product_sku,
            "product_name": self.product_name,
            "quantity": self.quantity,
            "unit_price": float(self.unit_price),
            "currency": self.currency,
        }
