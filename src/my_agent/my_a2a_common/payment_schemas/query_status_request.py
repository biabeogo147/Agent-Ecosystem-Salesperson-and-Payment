from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from src.my_agent.my_a2a_common.payment_schemas.payment_enums import PaymentAction, ProtocolVersion


class QueryStatusRequest(BaseModel):
    protocol: ProtocolVersion = Field(default=ProtocolVersion.A2A_V1)
    context_id: str = Field(..., description="Correlation ID of the original payment request")
    order_id: Optional[int] = Field(default=None, description="Specific order ID to query (optional)")
    from_agent: str = Field(default="salesperson_agent")
    to_agent: str = Field(default="payment_agent")
    action: PaymentAction = Field(default=PaymentAction.QUERY_STATUS)