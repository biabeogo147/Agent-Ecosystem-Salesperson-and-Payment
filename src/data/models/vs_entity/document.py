import datetime

from pymilvus import CollectionSchema, DataType
from pydantic import BaseModel, Field
from typing import List, Optional


class Document(BaseModel):
    id: int = Field(..., description="Unique document ID")
    text: str = Field(..., description="Full text content of the document")
    embedding: List[float] = Field(..., description="Vector embedding of the document content")

    # Metadata
    title: str = Field(..., description="Document title or short summary")
    product_id: Optional[int] = Field(default=None, description="Associated product ID if applicable")
    merchant_id: Optional[int] = Field(default=None, description="Associated merchant ID if applicable")
    chunk_id: Optional[int] = Field(default=None, description="Chunk identifier if document is split")
    created_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.now, description="Creation timestamp")