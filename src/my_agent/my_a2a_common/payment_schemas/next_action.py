from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field

from src.my_agent.my_a2a_common.payment_schemas.payment_enums.next_action_type import NextActionType


class NextAction(BaseModel):
    type: NextActionType = Field(default=NextActionType.NONE)
    expires_at: Optional[str] = Field(default=None, description="Expiration time of the action in ISO 8601 format")
    url: Optional[str] = Field(default=None, description="URL to redirect the user to (if type is REDIRECT)")
    qr_code_url: Optional[str] = Field(default=None, description="URL of the QR code image (if type is SHOW_QR)")
