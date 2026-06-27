from datetime import datetime
from pydantic import BaseModel, Field


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1)
    message_type: str = "text"  # text, voice, image


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    message_type: str
    is_proactive: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessageResponse]
    has_more: bool
    total: int
