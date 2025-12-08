from __future__ import annotations
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, model_validator

from src.my_agent.my_a2a_common.payment_schemas.payment_enums import *
from src.my_agent.my_a2a_common.payment_schemas.payment_item import PaymentItem
from src.my_agent.my_a2a_common.payment_schemas.customer_info import CustomerInfo

class PaymentRequest(BaseModel):
    protocol: ProtocolVersion = Field(default=ProtocolVersion.A2A_V1)
    context_id: str = Field(..., description="Unique transaction ID in the client system")
    from_agent: str = Field(default="salesperson_agent")
    to_agent: str = Field(default="payment_agent")
    action: PaymentAction = Field(default=PaymentAction.CREATE_ORDER)

    items: List[PaymentItem]
    customer: CustomerInfo
    channel: PaymentChannel

    note: Optional[str] = Field(default=None)
    user_id: Optional[int] = Field(default=None, description="User ID associated with this order")
    conversation_id: Optional[int] = Field(default=None, description="Conversation ID for multi-session notification")
    metadata: Optional[Dict[str, str]] = Field(default=None)

    @model_validator(mode="after")
    def _non_empty_items(self):
        if not self.items:
            raise ValueError("items must be a non-empty list")
        return self
