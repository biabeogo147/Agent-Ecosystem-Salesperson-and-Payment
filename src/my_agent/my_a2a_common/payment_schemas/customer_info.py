from __future__ import annotations
from typing import Optional, Dict
from pydantic import BaseModel, Field, EmailStr

class CustomerInfo(BaseModel):
    name: Optional[str] = Field(default=None)
    email: Optional[EmailStr] = Field(default=None)
    phone: Optional[str] = Field(default=None)
    shipping_address: Optional[str] = Field(default=None)
