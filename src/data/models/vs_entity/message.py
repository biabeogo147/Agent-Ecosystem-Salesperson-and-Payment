import datetime

from pydantic import BaseModel, Field
from typing import List, Optional

from data.models.enum.message_role import MessageRole


class Message(BaseModel):
    id: int = Field(..., description="Unique ID of the message")
    text: str = Field(..., description="Original text content")
    embedding: List[float] = Field(..., description="Vector embedding of the text")

    # Metadata
    role: MessageRole = Field(..., description="Role of the message sender")
    conversation_id: Optional[int] = Field(default=None, description="Conversation identifier")
    created_at: Optional[datetime] = Field(default_factory=datetime.datetime.now, description="Creation timestamp")