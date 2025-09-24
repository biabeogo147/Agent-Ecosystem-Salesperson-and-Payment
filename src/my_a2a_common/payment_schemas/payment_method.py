from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field

from my_a2a_common.payment_schemas.payment_enums import *


class PaymentMethod(BaseModel):
    type: PaymentMethodType = Field(default=PaymentMethodType.PAYGATE)
    channel: PaymentChannel = Field(
        default=PaymentChannel.REDIRECT,
        description="Redirect customer to provider's site or show QR code (if supported by provider)"
    )
    return_url: Optional[str] = Field(
        default=None,
        description="URL returned to after payment success"
    )
    cancel_url: Optional[str] = Field(
        default=None,
        description="URL returned to after payment cancellation"
    )
