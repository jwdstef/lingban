from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage
from app.models.user import User

SubscriptionPlan = Literal["free", "basic", "pro"]


PLAN_CATALOG = [
    {
        "id": "free",
        "name": "基础版",
        "price_cny": 0,
        "chat_daily_limit": 20,
        "proactive_daily_limit": 2,
        "features": ["1 个预制角色", "基础聊天和语音消息", "每日 1-2 次主动关怀"],
    },
    {
        "id": "basic",
        "name": "进阶版",
        "price_cny": 29,
        "chat_daily_limit": 200,
        "proactive_daily_limit": 5,
        "features": ["解锁 3 个官方角色", "深度长期记忆", "高质量语音回复", "情绪趋势报告"],
    },
    {
        "id": "pro",
        "name": "专业版",
        "price_cny": 99,
        "chat_daily_limit": 500,
        "proactive_daily_limit": 10,
        "features": ["包含进阶版全部能力", "人工专业支持入口", "定期陪伴方案复核"],
    },
]

PLAN_BY_ID = {plan["id"]: plan for plan in PLAN_CATALOG}
SUBSCRIPTION_PERIOD_DAYS = 30


class SubscriptionLimitError(RuntimeError):
    def __init__(self, quota: dict):
        self.quota = quota
        super().__init__("Daily chat quota has been used up")


@dataclass(frozen=True)
class EffectiveSubscription:
    plan: SubscriptionPlan
    status: str
    previous_plan: str | None
    expires_at: datetime | None
    cancel_at_period_end: bool
    chat_daily_limit: int
    proactive_daily_limit: int


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _day_window(now: datetime) -> tuple[datetime, datetime]:
    now = now.astimezone(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def get_effective_subscription(
    user: User,
    now: datetime | None = None,
) -> EffectiveSubscription:
    settings = user.settings or {}
    now = now or datetime.now(timezone.utc)
    requested_plan = str(settings.get("subscription_plan") or "free")
    if requested_plan not in PLAN_BY_ID:
        requested_plan = "free"

    expires_at = _parse_datetime(settings.get("subscription_expires_at"))
    cancel_at_period_end = bool(settings.get("subscription_cancel_at_period_end", False))

    status = "active"
    effective_plan = requested_plan
    previous_plan = None
    if requested_plan != "free" and expires_at and expires_at <= now:
        previous_plan = requested_plan
        effective_plan = "free"
        status = "expired"
        cancel_at_period_end = False
    elif requested_plan != "free" and cancel_at_period_end:
        status = "cancel_at_period_end"

    plan_data = PLAN_BY_ID[effective_plan]
    return EffectiveSubscription(
        plan=effective_plan,  # type: ignore[arg-type]
        status=status,
        previous_plan=previous_plan,
        expires_at=expires_at,
        cancel_at_period_end=cancel_at_period_end,
        chat_daily_limit=int(plan_data["chat_daily_limit"]),
        proactive_daily_limit=int(plan_data["proactive_daily_limit"]),
    )


def get_plan_amount_cents(plan: str) -> int:
    plan_data = PLAN_BY_ID.get(plan)
    if not plan_data:
        raise ValueError(f"Unknown subscription plan: {plan}")
    return int(plan_data["price_cny"]) * 100


def activate_paid_subscription(
    user: User,
    plan: SubscriptionPlan,
    provider: str,
    now: datetime | None = None,
) -> datetime:
    from app.core.user_settings import merge_user_settings

    if plan == "free" or plan not in PLAN_BY_ID:
        raise ValueError(f"Cannot activate paid subscription plan: {plan}")

    now = now or datetime.now(timezone.utc)
    settings = user.settings or {}
    current_expires_at = _parse_datetime(settings.get("subscription_expires_at"))
    current_plan = str(settings.get("subscription_plan") or "free")
    base_time = (
        current_expires_at
        if current_plan == plan and current_expires_at and current_expires_at > now
        else now
    )
    expires_at = base_time + timedelta(days=SUBSCRIPTION_PERIOD_DAYS)
    user.settings = merge_user_settings(
        settings,
        {
            "subscription_plan": plan,
            "subscription_status": "active",
            "subscription_provider": provider,
            "subscription_expires_at": expires_at.isoformat(),
            "subscription_cancel_at_period_end": False,
            "subscription_last_payment_at": now.isoformat(),
        },
    )
    return expires_at


async def _daily_user_message_count(
    user: User,
    db: AsyncSession,
    now: datetime,
) -> int:
    start, end = _day_window(now)
    result = await db.execute(
        select(func.count())
        .select_from(ChatMessage)
        .where(
            ChatMessage.user_id == user.id,
            ChatMessage.role == "user",
            ChatMessage.created_at >= start,
            ChatMessage.created_at < end,
        )
    )
    return int(result.scalar() or 0)


async def get_subscription_overview(
    user: User,
    db: AsyncSession,
    now: datetime | None = None,
) -> dict:
    now = now or datetime.now(timezone.utc)
    subscription = get_effective_subscription(user, now=now)
    used = await _daily_user_message_count(user, db, now)
    remaining = max(subscription.chat_daily_limit - used, 0)
    _, reset_at = _day_window(now)

    return {
        "plan": subscription.plan,
        "status": subscription.status,
        "previous_plan": subscription.previous_plan,
        "expires_at": subscription.expires_at.isoformat()
        if subscription.expires_at
        else None,
        "cancel_at_period_end": subscription.cancel_at_period_end,
        "quota": {
            "chat_daily": {
                "limit": subscription.chat_daily_limit,
                "used": used,
                "remaining": remaining,
                "reset_at": reset_at.isoformat(),
            },
            "proactive_daily": {
                "limit": subscription.proactive_daily_limit,
            },
        },
        "plans": PLAN_CATALOG,
    }


class SubscriptionService:
    async def ensure_chat_quota(
        self,
        user: User,
        db: AsyncSession,
        now: datetime | None = None,
    ) -> dict:
        overview = await get_subscription_overview(user=user, db=db, now=now)
        quota = overview["quota"]["chat_daily"]
        if quota["remaining"] <= 0:
            raise SubscriptionLimitError(quota)
        return quota


subscription_service = SubscriptionService()
