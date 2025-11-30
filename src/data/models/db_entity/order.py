from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, DECIMAL, Enum, Index
from sqlalchemy.orm import relationship
from src.data.models import Base

from src.data.models.enum.order_status import OrderStatus


class Order(Base):
    """Order with multiple line items. context_id correlates with salesperson agent."""
    __tablename__ = "order"

    id = Column(Integer, primary_key=True, autoincrement=True)
    context_id = Column(String, nullable=False, index=True)  # Correlation ID from salesperson
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    total_amount = Column(DECIMAL(18, 2), nullable=False)
    currency = Column(String, nullable=False, default="USD")
    status = Column(Enum(OrderStatus, name="order_status_enum"), nullable=False, default=OrderStatus.PENDING)
    note = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", backref="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_order_context_id", "context_id"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "context_id": self.context_id,
            "user_id": self.user_id,
            "total_amount": float(self.total_amount),
            "currency": self.currency,
            "status": self.status.value,
            "note": self.note,
            "items": [item.to_dict() for item in self.items] if self.items else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }