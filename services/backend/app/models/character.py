import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, JSON, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Character(Base):
    """官方预制角色"""

    __tablename__ = "characters"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    avatar_url: Mapped[str] = mapped_column(String(500), default="")
    color: Mapped[int] = mapped_column(Integer, default=0xFF8B5CF6)

    # 人格参数
    personality: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # 系统 Prompt
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class UserCharacterRelation(Base):
    """用户与角色的关系"""

    __tablename__ = "user_character_relations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    character_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("characters.id"), nullable=False, index=True
    )

    # 关系等级
    level: Mapped[int] = mapped_column(Integer, default=1)
    label: Mapped[str] = mapped_column(String(50), default="陌生")
    intimacy: Mapped[int] = mapped_column(Integer, default=0)

    # 关系里程碑
    milestones: Mapped[dict] = mapped_column(JSONB, default=list)

    # 互动追踪
    first_chat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_chat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_days: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
