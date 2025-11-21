from pydantic import BaseModel, Field
from typing import Optional


class DocumentCreate(BaseModel):
    text: str = Field(..., description="Document text content")
    title: str = Field(..., description="Document title")
    product_sku: Optional[str] = Field(default=None, description="Associated product SKU")
    chunk_id: Optional[int] = Field(default=None, description="Chunk ID if document is split")