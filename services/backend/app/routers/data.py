"""User data portability and account deletion APIs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.character import UserCharacterRelation
from app.models.chat import ChatMessage
from app.models.memory import EmotionDiary, Memory, ProactiveMessage
from app.models.payment import PaymentOrder
from app.models.push import PushDelivery, PushToken
from app.models.user import User

router = APIRouter()


class DeleteAccountRequest(BaseModel):
    confirm: str = Field(description='Must be exactly "DELETE".')
    reason: str | None = Field(default=None, max_length=500)


def _iso(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _safe_user(user: User) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "phone": user.phone,
        "email": user.email,
        "nickname": user.nickname,
        "avatar_url": user.avatar_url,
        "selected_character_id": user.selected_character_id,
        "emotion_profile": user.emotion_profile or {},
        "settings": user.settings or {},
        "created_at": _iso(user.created_at),
        "updated_at": _iso(user.updated_at),
    }


def _relationship(row: UserCharacterRelation) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "character_id": row.character_id,
        "level": row.level,
        "label": row.label,
        "intimacy": row.intimacy,
        "milestones": row.milestones or [],
        "first_chat_at": _iso(row.first_chat_at),
        "last_chat_at": _iso(row.last_chat_at),
        "consecutive_days": row.consecutive_days,
        "created_at": _iso(row.created_at),
        "updated_at": _iso(row.updated_at),
    }


def _chat(row: ChatMessage) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "character_id": row.character_id,
        "role": row.role,
        "content": row.content,
        "message_type": row.message_type,
        "is_proactive": row.is_proactive,
        "created_at": _iso(row.created_at),
    }


def _memory(row: Memory) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "character_id": row.character_id,
        "category": row.category,
        "content": row.content,
        "importance": row.importance,
        "emotion_tags": row.emotion_tags or [],
        "source_message_id": str(row.source_message_id) if row.source_message_id else None,
        "recall_count": row.recall_count,
        "is_active": row.is_active,
        "created_at": _iso(row.created_at),
        "updated_at": _iso(row.updated_at),
    }


def _emotion(row: EmotionDiary) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "date": _iso(row.date),
        "dominant_emotion": row.dominant_emotion,
        "intensity": row.intensity,
        "triggers": row.triggers or [],
        "created_at": _iso(row.created_at),
    }


def _proactive(row: ProactiveMessage) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "character_id": row.character_id,
        "trigger_type": row.trigger_type,
        "content": row.content,
        "delivered": row.delivered,
        "replied": row.replied,
        "push_status": row.push_status,
        "push_error": row.push_error,
        "created_at": _iso(row.created_at),
    }


def _push_token(row: PushToken) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "platform": row.platform,
        "provider": row.provider,
        "permission_status": row.permission_status,
        "device_id": row.device_id,
        "app_version": row.app_version,
        "is_active": row.is_active,
        "created_at": _iso(row.created_at),
        "updated_at": _iso(row.updated_at),
    }


def _push_delivery(row: PushDelivery) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "push_token_id": str(row.push_token_id) if row.push_token_id else None,
        "proactive_message_id": (
            str(row.proactive_message_id) if row.proactive_message_id else None
        ),
        "provider": row.provider,
        "notification_type": row.notification_type,
        "title": row.title,
        "body": row.body,
        "deep_link": row.deep_link,
        "status": row.status,
        "failure_reason": row.failure_reason,
        "sent_at": _iso(row.sent_at),
        "clicked_at": _iso(row.clicked_at),
        "created_at": _iso(row.created_at),
    }


def _payment_order(row: PaymentOrder) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "provider": row.provider,
        "plan": row.plan,
        "out_trade_no": row.out_trade_no,
        "prepay_id": row.prepay_id,
        "amount_cents": row.amount_cents,
        "currency": row.currency,
        "status": row.status,
        "transaction_id": row.transaction_id,
        "paid_at": _iso(row.paid_at),
        "created_at": _iso(row.created_at),
        "updated_at": _iso(row.updated_at),
    }


async def _all(db: AsyncSession, model, user_id):
    result = await db.execute(select(model).where(model.user_id == user_id))
    return result.scalars().all()


@router.get("/export")
async def export_user_data(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export the current user's portable data as JSON."""
    relationships = await _all(db, UserCharacterRelation, user.id)
    chat_messages = await _all(db, ChatMessage, user.id)
    memories = await _all(db, Memory, user.id)
    emotion_records = await _all(db, EmotionDiary, user.id)
    proactive_messages = await _all(db, ProactiveMessage, user.id)
    push_tokens = await _all(db, PushToken, user.id)
    push_deliveries = await _all(db, PushDelivery, user.id)
    payment_orders = await _all(db, PaymentOrder, user.id)

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user": _safe_user(user),
        "relationships": [_relationship(row) for row in relationships],
        "chat_messages": [_chat(row) for row in chat_messages],
        "memories": [_memory(row) for row in memories],
        "emotion_diary": [_emotion(row) for row in emotion_records],
        "proactive_messages": [_proactive(row) for row in proactive_messages],
        "push_tokens": [_push_token(row) for row in push_tokens],
        "push_deliveries": [_push_delivery(row) for row in push_deliveries],
        "payment_orders": [_payment_order(row) for row in payment_orders],
    }


@router.post("/delete-account")
async def delete_account(
    data: DeleteAccountRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Request account deletion; permanent deletion is scheduled after 30 days."""
    if data.confirm != "DELETE":
        raise HTTPException(status_code=400, detail='confirm must be "DELETE"')

    now = datetime.now(timezone.utc)
    scheduled_at = now + timedelta(days=30)
    settings = {
        **(user.settings or {}),
        "account_status": "pending_deletion",
        "account_deletion_requested_at": now.isoformat(),
        "account_deletion_scheduled_at": scheduled_at.isoformat(),
    }
    if data.reason:
        settings["account_deletion_reason"] = data.reason

    user.settings = settings
    user.push_token = None
    user.push_platform = None
    await db.execute(
        update(PushToken)
        .where(PushToken.user_id == user.id)
        .values(is_active=False, permission_status="denied")
    )
    await db.flush()

    return {
        "status": "pending_deletion",
        "scheduled_deletion_at": scheduled_at.isoformat(),
    }
