from datetime import datetime
from pydantic import BaseModel


class MemoryResponse(BaseModel):
    id: str
    category: str
    content: str
    importance: int
    emotion_tags: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class MemoryListResponse(BaseModel):
    memories: list[MemoryResponse]
    total: int
    stats: dict  # {"total": 128, "this_week": 12, "important": 5}
