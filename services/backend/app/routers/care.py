"""Proactive care APIs."""

import re
import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.memory import ProactiveMessage
from app.models.user import User
from app.services.relationship_service import relationship_service

router = APIRouter()


class CareMessageResponse(BaseModel):
    id: str
    character_id: str
    trigger_type: str
    content: str
    delivered: bool
    replied: bool
    push_status: str
    push_error: str | None
    created_at: datetime


class CareMessageListResponse(BaseModel):
    messages: list[CareMessageResponse]
    total: int
    has_more: bool


class UpdateCareFrequencyRequest(BaseModel):
    proactive_level: Literal["off", "quiet", "low", "medium", "high"]


class UpdateDndRequest(BaseModel):
    dnd_enabled: bool = True
    dnd_start: str = "23:00"
    dnd_end: str = "08:00"

    @field_validator("dnd_start", "dnd_end")
    @classmethod
    def validate_time(cls, value: str) -> str:
        if not _TIME_RE.match(value):
            raise ValueError("time must use HH:MM format")
        return value


_TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def _settings_with_defaults(user: User) -> dict:
    return {
        "push_enabled": True,
        "voice_call_enabled": False,
        "dnd_enabled": True,
        "dnd_start": "23:00",
        "dnd_end": "08:00",
        "proactive_level": "medium",
        **(user.settings or {}),
    }


def _serialize_message(message: ProactiveMessage) -> CareMessageResponse:
    return CareMessageResponse(
        id=str(message.id),
        character_id=message.character_id,
        trigger_type=message.trigger_type,
        content=message.content,
        delivered=message.delivered,
        replied=message.replied,
        push_status=message.push_status,
        push_error=message.push_error,
        created_at=message.created_at,
    )


def _parse_message_id(message_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(message_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid message id") from exc


@router.put("/frequency")
async def update_care_frequency(
    data: UpdateCareFrequencyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update proactive care frequency for the current user."""
    settings = _settings_with_defaults(user)
    settings["proactive_level"] = data.proactive_level
    user.settings = settings
    await db.flush()
    return {"status": "ok", "settings": settings}


@router.put("/dnd")
async def update_care_dnd(
    data: UpdateDndRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update proactive care do-not-disturb window."""
    settings = _settings_with_defaults(user)
    settings.update(
        {
            "dnd_enabled": data.dnd_enabled,
            "dnd_start": data.dnd_start,
            "dnd_end": data.dnd_end,
        }
    )
    user.settings = settings
    await db.flush()
    return {"status": "ok", "settings": settings}


@router.get("/messages", response_model=CareMessageListResponse)
async def list_care_messages(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    character_id: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List proactive care messages for the current user."""
    base_where = [ProactiveMessage.user_id == user.id]
    if character_id:
        base_where.append(ProactiveMessage.character_id == character_id)

    total_result = await db.execute(
        select(func.count()).select_from(ProactiveMessage).where(*base_where)
    )
    total = total_result.scalar() or 0

    result = await db.execute(
        select(ProactiveMessage)
        .where(*base_where)
        .order_by(ProactiveMessage.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    messages = result.scalars().all()

    return CareMessageListResponse(
        messages=[_serialize_message(message) for message in messages],
        total=total,
        has_more=offset + limit < total,
    )


@router.post("/messages/{message_id}/click", response_model=CareMessageResponse)
async def mark_care_message_clicked(
    message_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record that a proactive care message was opened."""
    parsed_id = _parse_message_id(message_id)
    result = await db.execute(
        select(ProactiveMessage).where(
            ProactiveMessage.id == parsed_id,
            ProactiveMessage.user_id == user.id,
        )
    )
    message = result.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=404, detail="Care message not found")

    message.push_status = "clicked"
    message.delivered = True
    await db.flush()
    return _serialize_message(message)


@router.post("/messages/{message_id}/reply", response_model=CareMessageResponse)
async def mark_care_message_replied(
    message_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record that the user replied to a proactive care message."""
    parsed_id = _parse_message_id(message_id)
    result = await db.execute(
        select(ProactiveMessage).where(
            ProactiveMessage.id == parsed_id,
            ProactiveMessage.user_id == user.id,
        )
    )
    message = result.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=404, detail="Care message not found")

    if not message.replied:
        message.replied = True
        await relationship_service.on_reply_proactive(user.id, message.character_id, db)

    await db.flush()
    return _serialize_message(message)
