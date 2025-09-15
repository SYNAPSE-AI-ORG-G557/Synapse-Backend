import uuid
from datetime import datetime
from pydantic import BaseModel, Field

class MessageCreate(BaseModel):
    """Schema for creating a new message."""
    content: str = Field(..., min_length=1, description="The text content of the message.")

class MessagePublic(BaseModel):
    """Public-facing schema for a message."""
    uuid: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True