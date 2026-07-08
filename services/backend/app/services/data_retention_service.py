"""User data export and retention helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.character import UserCharacterRelation
from app.models.chat import ChatMessage
from app.models.memory import EmotionDiary, Memory, ProactiveMessage
from app.models.payment import PaymentOrder
from app.models.push import PushDelivery, PushToken
from app.models.user import User


async def permanently_delete_user_data(user_id: UUID, db: AsyncSession) -> None:
    """Delete a user's account and dependent product data."""
    await db.execute(delete(PushDelivery).where(PushDelivery.user_id == user_id))
    await db.execute(delete(PushToken).where(PushToken.user_id == user_id))
    await db.execute(delete(ProactiveMessage).where(ProactiveMessage.user_id == user_id))
    await db.execute(delete(ChatMessage).where(ChatMessage.user_id == user_id))
    await db.execute(delete(Memory).where(Memory.user_id == user_id))
    await db.execute(delete(EmotionDiary).where(EmotionDiary.user_id == user_id))
    await db.execute(delete(PaymentOrder).where(PaymentOrder.user_id == user_id))
    await db.execute(
        delete(UserCharacterRelation).where(UserCharacterRelation.user_id == user_id)
    )
    await db.execute(delete(User).where(User.id == user_id))


async def cleanup_due_deleted_accounts(db: AsyncSession) -> int:
    """Permanently delete accounts whose 30-day deletion window has elapsed."""
    result = await db.execute(select(User))
    users = result.scalars().all()
    now = datetime.now(timezone.utc)
    deleted = 0

    for user in users:
        settings = user.settings or {}
        if settings.get("account_status") != "pending_deletion":
            continue

        scheduled_at = _parse_datetime(settings.get("account_deletion_scheduled_at"))
        if scheduled_at and scheduled_at <= now:
            await permanently_delete_user_data(user.id, db)
            deleted += 1

    return deleted


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
