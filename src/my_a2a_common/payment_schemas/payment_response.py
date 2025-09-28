from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field

from .payment_enums.payment_status import PaymentStatus
from .next_action import NextAction

class PaymentResponse(BaseModel):
    context_id: str = Field(..., description="The same ID as in the request")
    status: PaymentStatus = Field(default=PaymentStatus.PENDING)

    provider_name: Optional[str] = Field(default=None, description="Provider name")
    order_id: Optional[str] = Field(default=None, description="Order ID on provider")
    pay_url: Optional[str] = Field(default=None, description="URL to redirect customer (if any)")
    qr_code_url: Optional[str] = Field(default=None, description="QR code image URL (if any)")
    expires_at: Optional[str] = Field(default=None, description="ISO8601 expiration time of pay_url or qr_code_url")

    next_action: NextAction = Field(
        default_factory=lambda: NextAction(),
        description="REDIRECT/SHOW_QR/ASK_USER/NONE"
    )
