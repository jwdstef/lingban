import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Memory(Base):
    """长期记忆"""

    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    character_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    category: Mapped[str] = mapped_column(String(50), nullable=False)
    # daily, emotion, preference, event, person, fact
    content: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[int] = mapped_column(default=5)  # 1-10

    # 情感标签
    emotion_tags: Mapped[dict] = mapped_column(JSONB, default=list)
    # ["焦虑", "工作压力"]

    # 记忆来源
    source_message_id: Mapped[str] = mapped_column(String(100), nullable=True)

    # 向量 ID（用于 Qdrant 检索）
    vector_id: Mapped[str] = mapped_column(String(100), nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
