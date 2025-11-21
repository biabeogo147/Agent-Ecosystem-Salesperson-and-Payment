from pydantic import BaseModel, Field
from typing import Optional


class ProductCreate(BaseModel):
    sku: str = Field(..., description="Product SKU (unique identifier)")
    name: str = Field(..., description="Product name")
    price: float = Field(..., gt=0, description="Product price")
    currency: str = Field(default="USD", description="Currency code")
    stock: int = Field(..., ge=0, description="Stock quantity")


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = Field(default=None, gt=0)
    currency: Optional[str] = None
    stock: Optional[int] = Field(default=None, ge=0)