import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, DateTime, Boolean, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.core.config import settings
from app.core.database import Base


class Memory(Base):
    """长期记忆 - 使用 pgvector 做向量检索"""

    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    character_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    category: Mapped[str] = mapped_column(String(50), nullable=False)  # daily/emotion/preference/event/person/fact
    content: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[int] = mapped_column(Integer, default=5)  # 1-10

    # 情感标签
    emotion_tags: Mapped[dict] = mapped_column(JSONB, default=list)

    # 记忆来源
    source_message_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # pgvector embedding column. Deferred so regular memory queries avoid
    # loading the large vector payload.
    embedding: Mapped[list[float] | None] = mapped_column(
        "embedding",
        Vector(settings.embedding_dimensions),
        nullable=True,
        deferred=True,
    )

    # 召回统计
    recall_count: Mapped[int] = mapped_column(Integer, default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index(
            "idx_memories_active",
            "user_id", "character_id", "is_active", "created_at",
        ),
    )


class ProactiveMessage(Base):
    """主动关怀消息记录"""

    __tablename__ = "proactive_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    character_id: Mapped[str] = mapped_column(String(50), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)  # time/silence/emotion/event/weather/anniversary
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # 推送状态
    delivered: Mapped[bool] = mapped_column(Boolean, default=False)
    replied: Mapped[bool] = mapped_column(Boolean, default=False)
    push_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/sent/failed/clicked
    push_error: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class EmotionDiary(Base):
    """每日情绪记录"""

    __tablename__ = "emotion_diary"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    dominant_emotion: Mapped[str | None] = mapped_column(String(50), nullable=True)
    intensity: Mapped[float | None] = mapped_column(nullable=True)
    triggers: Mapped[dict] = mapped_column(JSONB, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
