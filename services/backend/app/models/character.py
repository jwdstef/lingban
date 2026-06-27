import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Text, DateTime, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Character(Base):
    """官方预制角色"""

    __tablename__ = "characters"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)  # 来源 IP
    description: Mapped[str] = mapped_column(Text, nullable=False)
    avatar_url: Mapped[str] = mapped_column(String(500), default="")
    color: Mapped[int] = mapped_column(Integer, default=0xFF8B5CF6)

    # 人格参数
    personality: Mapped[dict] = mapped_column(JSON, nullable=False)
    # {
    #   "tsundere": 80,       # 傲娇度
    #   "sharp_tongued": 70,  # 毒舌度
    #   "gentle": 30,         # 温柔度
    #   "active": 60,         # 活跃度
    #   "mature": 70,         # 成熟度
    #   "self_reference": "本姑娘",
    #   "user_reference": "你/小子",
    #   "catchphrases": ["哼", "别误会了"],
    # }

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
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    character_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # 关系等级
    level: Mapped[int] = mapped_column(Integer, default=1)
    label: Mapped[str] = mapped_column(String(50), default="陌生")
    intimacy: Mapped[int] = mapped_column(Integer, default=0)

    # 关系成长档案
    milestones: Mapped[dict] = mapped_column(JSON, default=list)
    # [{"event": "first_chat", "date": "2025-01-01", "description": "第一次对话"}]

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
