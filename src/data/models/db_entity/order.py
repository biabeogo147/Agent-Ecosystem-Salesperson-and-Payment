from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, DECIMAL, Enum
from sqlalchemy.orm import relationship
from src.data.models import Base

from src.data.models.enum.order_status import OrderStatus


class Order(Base):
    __tablename__ = "order"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    product_sku = Column(String, ForeignKey("products.sku"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    total_amount = Column(DECIMAL(18, 2), nullable=False)
    currency = Column(String, nullable=False, default="USD")
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", backref="orders")
    product = relationship("Product", backref="orders")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "product_sku": self.product_sku,
            "quantity": self.quantity,
            "total_amount": float(self.total_amount),
            "currency": self.currency,
            "status": self.status.value,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at)
        }