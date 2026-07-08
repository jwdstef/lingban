"""Relationship detail APIs."""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.character import UserCharacterRelation
from app.models.user import User
from app.services.relationship_service import relationship_service

router = APIRouter()


class RelationResponse(BaseModel):
    character_id: str
    level: int
    label: str
    intimacy: int
    consecutive_days: int
    first_chat_at: datetime | None
    last_chat_at: datetime | None
    milestones: list[dict]


def serialize_relation(
    character_id: str,
    relation: UserCharacterRelation,
) -> RelationResponse:
    return RelationResponse(
        character_id=character_id,
        level=relation.level,
        label=relation.label,
        intimacy=relation.intimacy,
        consecutive_days=relation.consecutive_days,
        first_chat_at=relation.first_chat_at,
        last_chat_at=relation.last_chat_at,
        milestones=relation.milestones or [],
    )


@router.get("/{character_id}", response_model=RelationResponse)
async def get_relationship(
    character_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's relationship details with one character."""
    relation = await relationship_service.get_or_create(user.id, character_id, db)
    return serialize_relation(character_id, relation)
