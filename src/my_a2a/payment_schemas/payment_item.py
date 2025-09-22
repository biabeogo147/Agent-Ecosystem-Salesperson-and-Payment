from __future__ import annotations
from pydantic import BaseModel, Field

class PaymentItem(BaseModel):
    sku: str = Field(...)
    name: str = Field(...)
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    currency: str = Field(default="USD")
