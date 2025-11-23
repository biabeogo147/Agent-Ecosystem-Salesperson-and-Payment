from sqlalchemy import Column, Integer, String, DateTime, func
from src.data.models import Base

class Merchant(Base):
    __tablename__ = "merchant"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at),
        }
