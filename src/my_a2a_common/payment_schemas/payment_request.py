from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, model_validator

from .payment_enums import *
from .payment_item import PaymentItem
from .customer_info import CustomerInfo
from .payment_method import PaymentMethod

class PaymentRequest(BaseModel):
    protocol: ProtocolVersion = Field(default=ProtocolVersion.A2A_V1)
    context_id: str = Field(..., description="Unique transaction ID in the client system")
    from_agent: str = Field(default="salesperson_agent")
    to_agent: str = Field(default="payment_agent")
    action: PaymentAction = Field(default=PaymentAction.CREATE_ORDER)

    items: List[PaymentItem]
    customer: CustomerInfo
    method: PaymentMethod

    note: Optional[str] = Field(default=None)
    metadata: Optional[Dict[str, str]] = Field(default=None)

    @model_validator(mode="after")
    def _non_empty_items(self):
        if not self.items:
            raise ValueError("items must be a non-empty list")
        return self
