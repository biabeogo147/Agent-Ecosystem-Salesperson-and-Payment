from __future__ import annotations

from pydantic import BaseModel, Field

from .payment_enums import PaymentAction, ProtocolVersion


class QueryStatusRequest(BaseModel):
    protocol: ProtocolVersion = Field(default=ProtocolVersion.A2A_V1)
    context_id: str = Field(..., description="Correlation ID of the original payment request")
    from_agent: str = Field(default="salesperson_agent")
    to_agent: str = Field(default="payment_agent")
    action: PaymentAction = Field(default=PaymentAction.QUERY_STATUS)


__all__ = ["QueryStatusRequest"]
