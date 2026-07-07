"""Proactive care APIs."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.memory import ProactiveMessage
from app.models.user import User

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

    message.replied = True
    await db.flush()
    return _serialize_message(message)
