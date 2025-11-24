from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    text: str = Field(..., description="Document text content")
    title: str = Field(..., description="Document title")
    product_sku: str = Field(..., description="Associated product SKU")
    chunk_id: int = Field(..., description="Chunk ID if document is split")
    merchant_id: int = Field(..., description="Associated merchant ID")