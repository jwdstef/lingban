"""管理后台 API"""
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_auth import require_admin
from app.core.database import get_db
from app.models import (
    AuditLog,
    ChatMessage,
    Character,
    Memory,
    ProactiveMessage,
    PushDelivery,
    PushToken,
    SafetyEvent,
    User,
    UserCharacterRelation,
)
from app.services.safety_service import REVIEW_STATUSES, review_event

router = APIRouter(dependencies=[Depends(require_admin)])


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _short_id(value: Any) -> str:
    return str(value)[:8]


def _mask_secret(value: str | None, visible: int = 6) -> str | None:
    if not value:
        return None
    if len(value) <= visible * 2:
        return f"{value[:visible]}..."
    return f"{value[:visible]}...{value[-visible:]}"


def _serialize_chat_message(message: ChatMessage) -> dict[str, Any]:
    return {
        "id": str(message.id),
        "short_id": _short_id(message.id),
        "user_id": str(message.user_id),
        "character_id": message.character_id,
        "role": message.role,
        "content": message.content,
        "message_type": message.message_type,
        "emotion_tags": message.emotion_tags or [],
        "is_proactive": message.is_proactive,
        "created_at": _iso(message.created_at),
    }


def _serialize_proactive_message(message: ProactiveMessage) -> dict[str, Any]:
    return {
        "id": str(message.id),
        "short_id": _short_id(message.id),
        "user_id": str(message.user_id),
        "character_id": message.character_id,
        "trigger_type": message.trigger_type,
        "content": message.content,
        "delivered": message.delivered,
        "replied": message.replied,
        "push_status": message.push_status,
        "push_error": message.push_error,
        "created_at": _iso(message.created_at),
    }


def _serialize_push_delivery(delivery: PushDelivery) -> dict[str, Any]:
    return {
        "id": str(delivery.id),
        "short_id": _short_id(delivery.id),
        "user_id": str(delivery.user_id),
        "push_token_id": str(delivery.push_token_id) if delivery.push_token_id else None,
        "proactive_message_id": (
            str(delivery.proactive_message_id)
            if delivery.proactive_message_id
            else None
        ),
        "provider": delivery.provider,
        "notification_type": delivery.notification_type,
        "title": delivery.title,
        "body": delivery.body,
        "deep_link": delivery.deep_link,
        "status": delivery.status,
        "provider_message_id": delivery.provider_message_id,
        "failure_reason": delivery.failure_reason,
        "sent_at": _iso(delivery.sent_at),
        "clicked_at": _iso(delivery.clicked_at),
        "created_at": _iso(delivery.created_at),
    }


class ReviewSafetyEventRequest(BaseModel):
    status: str
    note: str | None = None
    reviewed_by: str = "admin"


def _serialize_safety_event(event: SafetyEvent) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "short_id": _short_id(event.id),
        "event_type": event.event_type,
        "severity": event.severity,
        "user_id": str(event.user_id),
        "character_id": event.character_id,
        "source": event.source,
        "source_message_id": (
            str(event.source_message_id) if event.source_message_id else None
        ),
        "content": event.content_excerpt,
        "matched_terms": event.matched_terms or [],
        "created_at": _iso(event.created_at),
        "updated_at": _iso(event.updated_at),
        "status": event.status,
        "review_note": event.review_note,
        "reviewed_by": event.reviewed_by,
        "reviewed_at": _iso(event.reviewed_at),
    }


def _serialize_audit_log(log: AuditLog) -> dict[str, Any]:
    return {
        "id": str(log.id),
        "short_id": _short_id(log.id),
        "actor_type": log.actor_type,
        "actor_id": log.actor_id,
        "action": log.action,
        "target_type": log.target_type,
        "target_id": log.target_id,
        "metadata": log.event_metadata or {},
        "created_at": _iso(log.created_at),
    }


async def _paginate(db: AsyncSession, query, page: int, page_size: int):
    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    return total, result.scalars().all()


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """用户列表"""
    query = select(User)

    if search:
        query = query.where(
            (User.nickname.ilike(f"%{search}%"))
            | (User.phone.ilike(f"%{search}%"))
            | (User.email.ilike(f"%{search}%"))
        )

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页
    query = query.order_by(desc(User.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    users = result.scalars().all()

    return {
        "items": [
            {
                "id": str(u.id),
                "nickname": u.nickname,
                "phone": u.phone,
                "email": u.email,
                "selected_character_id": u.selected_character_id,
                "push_token": u.push_token,
                "push_platform": u.push_platform,
                "emotion_profile": u.emotion_profile,
                "settings": u.settings,
                "created_at": u.created_at.isoformat(),
                "updated_at": u.updated_at.isoformat(),
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/users/{user_id}")
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """用户详情"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "用户不存在")

    # 获取关系信息
    relation = None
    if user.selected_character_id:
        rel_result = await db.execute(
            select(UserCharacterRelation).where(
                UserCharacterRelation.user_id == user.id,
                UserCharacterRelation.character_id == user.selected_character_id,
            )
        )
        rel = rel_result.scalar_one_or_none()
        if rel:
            relation = {
                "character_id": rel.character_id,
                "level": rel.level,
                "label": rel.label,
                "intimacy": rel.intimacy,
                "consecutive_days": rel.consecutive_days,
                "last_chat_at": rel.last_chat_at.isoformat() if rel.last_chat_at else None,
            }

    relationships_result = await db.execute(
        select(UserCharacterRelation)
        .where(UserCharacterRelation.user_id == user.id)
        .order_by(desc(UserCharacterRelation.updated_at))
    )
    relationships = relationships_result.scalars().all()

    push_tokens_result = await db.execute(
        select(PushToken)
        .where(PushToken.user_id == user.id)
        .order_by(desc(PushToken.updated_at))
        .limit(10)
    )
    push_tokens = push_tokens_result.scalars().all()

    chat_count = await db.execute(
        select(func.count(ChatMessage.id)).where(ChatMessage.user_id == user.id)
    )
    memory_count = await db.execute(
        select(func.count(Memory.id)).where(Memory.user_id == user.id)
    )
    care_count = await db.execute(
        select(func.count(ProactiveMessage.id)).where(ProactiveMessage.user_id == user.id)
    )
    delivery_count = await db.execute(
        select(func.count(PushDelivery.id)).where(PushDelivery.user_id == user.id)
    )

    return {
        "id": str(user.id),
        "nickname": user.nickname,
        "phone": user.phone,
        "email": user.email,
        "selected_character_id": user.selected_character_id,
        "push_token": user.push_token,
        "push_platform": user.push_platform,
        "emotion_profile": user.emotion_profile,
        "settings": user.settings,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
        "relation": relation,
        "relationships": [
            {
                "character_id": rel.character_id,
                "level": rel.level,
                "label": rel.label,
                "intimacy": rel.intimacy,
                "consecutive_days": rel.consecutive_days,
                "last_chat_at": _iso(rel.last_chat_at),
                "updated_at": _iso(rel.updated_at),
            }
            for rel in relationships
        ],
        "push_tokens": [
            {
                "id": str(token.id),
                "platform": token.platform,
                "provider": token.provider,
                "token_preview": _mask_secret(token.token),
                "permission_status": token.permission_status,
                "device_id": token.device_id,
                "app_version": token.app_version,
                "is_active": token.is_active,
                "updated_at": _iso(token.updated_at),
            }
            for token in push_tokens
        ],
        "metrics": {
            "chat_messages": chat_count.scalar() or 0,
            "memories": memory_count.scalar() or 0,
            "proactive_messages": care_count.scalar() or 0,
            "push_deliveries": delivery_count.scalar() or 0,
        },
    }


@router.post("/users/{user_id}/ban")
async def ban_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """封禁用户"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "用户不存在")

    settings = user.settings or {}
    settings["banned"] = True
    user.settings = settings
    await db.commit()
    return {"message": "已封禁"}


@router.post("/users/{user_id}/unban")
async def unban_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """解封用户"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "用户不存在")

    settings = user.settings or {}
    settings["banned"] = False
    user.settings = settings
    await db.commit()
    return {"message": "已解封"}


@router.get("/dashboard/stats")
async def dashboard_stats(db: AsyncSession = Depends(get_db)):
    """仪表盘统计"""
    # 用户总数
    user_count = await db.execute(select(func.count(User.id)))
    total_users = user_count.scalar() or 0

    # 今日活跃（今天有聊天的用户）
    today_active = await db.execute(
        select(func.count(func.distinct(ChatMessage.user_id))).where(
            func.date(ChatMessage.created_at) == func.current_date()
        )
    )
    today_active_users = today_active.scalar() or 0

    # 消息总数
    msg_count = await db.execute(select(func.count(ChatMessage.id)))
    total_messages = msg_count.scalar() or 0

    # 记忆总数
    memory_count = await db.execute(select(func.count(Memory.id)))
    total_memories = memory_count.scalar() or 0

    # 角色分布
    char_result = await db.execute(
        select(User.selected_character_id, func.count(User.id))
        .where(User.selected_character_id.isnot(None))
        .group_by(User.selected_character_id)
    )
    character_distribution = {row[0]: row[1] for row in char_result.all()}

    return {
        "total_users": total_users,
        "today_active_users": today_active_users,
        "total_messages": total_messages,
        "total_memories": total_memories,
        "character_distribution": character_distribution,
    }


@router.get("/dashboard/trends")
async def dashboard_trends(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
):
    """趋势数据"""
    # 每日消息数
    result = await db.execute(
        select(
            func.date(ChatMessage.created_at).label("date"),
            func.count(ChatMessage.id).label("count"),
        )
        .where(func.date(ChatMessage.created_at) >= func.current_date() - days)
        .group_by(func.date(ChatMessage.created_at))
        .order_by(func.date(ChatMessage.created_at))
    )
    messages_trend = [{"date": str(row.date), "count": row.count} for row in result.all()]

    # 每日新增用户
    user_result = await db.execute(
        select(
            func.date(User.created_at).label("date"),
            func.count(User.id).label("count"),
        )
        .where(func.date(User.created_at) >= func.current_date() - days)
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at))
    )
    users_trend = [{"date": str(row.date), "count": row.count} for row in user_result.all()]

    return {
        "messages_trend": messages_trend,
        "users_trend": users_trend,
    }


@router.get("/messages")
async def list_chat_messages(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Query(None),
    character_id: str = Query(None),
    role: str = Query(None),
    message_type: str = Query(None),
    search: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """对话抽检列表."""
    query = select(ChatMessage)

    if user_id:
        query = query.where(ChatMessage.user_id == user_id)
    if character_id:
        query = query.where(ChatMessage.character_id == character_id)
    if role:
        query = query.where(ChatMessage.role == role)
    if message_type:
        query = query.where(ChatMessage.message_type == message_type)
    if search:
        query = query.where(ChatMessage.content.ilike(f"%{search}%"))

    query = query.order_by(desc(ChatMessage.created_at))
    total, messages = await _paginate(db, query, page, page_size)

    return {
        "items": [_serialize_chat_message(message) for message in messages],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/care/messages")
async def list_admin_care_messages(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Query(None),
    character_id: str = Query(None),
    push_status: str = Query(None),
    trigger_type: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """主动关怀发送记录."""
    query = select(ProactiveMessage)

    if user_id:
        query = query.where(ProactiveMessage.user_id == user_id)
    if character_id:
        query = query.where(ProactiveMessage.character_id == character_id)
    if push_status:
        query = query.where(ProactiveMessage.push_status == push_status)
    if trigger_type:
        query = query.where(ProactiveMessage.trigger_type == trigger_type)

    query = query.order_by(desc(ProactiveMessage.created_at))
    total, messages = await _paginate(db, query, page, page_size)

    return {
        "items": [_serialize_proactive_message(message) for message in messages],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/push/deliveries")
async def list_push_deliveries(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Query(None),
    provider: str = Query(None),
    status: str = Query(None),
    notification_type: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """推送投递排查记录."""
    query = select(PushDelivery)

    if user_id:
        query = query.where(PushDelivery.user_id == user_id)
    if provider:
        query = query.where(PushDelivery.provider == provider)
    if status:
        query = query.where(PushDelivery.status == status)
    if notification_type:
        query = query.where(PushDelivery.notification_type == notification_type)

    query = query.order_by(desc(PushDelivery.created_at))
    total, deliveries = await _paginate(db, query, page, page_size)

    return {
        "items": [_serialize_push_delivery(delivery) for delivery in deliveries],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/safety/events")
async def list_safety_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Query(None),
    character_id: str = Query(None),
    status: str = Query(None),
    event_type: str = Query(None),
    severity: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """安全事件列表."""
    query = select(SafetyEvent)

    if user_id:
        query = query.where(SafetyEvent.user_id == user_id)
    if character_id:
        query = query.where(SafetyEvent.character_id == character_id)
    if status:
        query = query.where(SafetyEvent.status == status)
    if event_type:
        query = query.where(SafetyEvent.event_type == event_type)
    if severity:
        query = query.where(SafetyEvent.severity == severity)

    query = query.order_by(desc(SafetyEvent.created_at))
    total, events = await _paginate(db, query, page, page_size)

    return {
        "items": [_serialize_safety_event(event) for event in events],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/safety/events/{event_id}/review")
async def review_safety_event(
    event_id: str,
    data: ReviewSafetyEventRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update safety event review status and write audit log."""
    if data.status not in REVIEW_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported safety event status")

    result = await db.execute(select(SafetyEvent).where(SafetyEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Safety event not found")

    reviewed = await review_event(
        db,
        event,
        status=data.status,
        reviewed_by=data.reviewed_by,
        note=data.note,
    )
    await db.commit()
    await db.refresh(reviewed)
    return _serialize_safety_event(reviewed)


@router.get("/audit/logs")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    actor_type: str = Query(None),
    target_type: str = Query(None),
    target_id: str = Query(None),
    action: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Administrative and system audit log list."""
    query = select(AuditLog)

    if actor_type:
        query = query.where(AuditLog.actor_type == actor_type)
    if target_type:
        query = query.where(AuditLog.target_type == target_type)
    if target_id:
        query = query.where(AuditLog.target_id == target_id)
    if action:
        query = query.where(AuditLog.action == action)

    query = query.order_by(desc(AuditLog.created_at))
    total, logs = await _paginate(db, query, page, page_size)

    return {
        "items": [_serialize_audit_log(log) for log in logs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/memories")
async def list_memories(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Query(None),
    character_id: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """记忆列表"""
    query = select(Memory)

    if user_id:
        query = query.where(Memory.user_id == user_id)
    if character_id:
        query = query.where(Memory.character_id == character_id)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页
    query = query.order_by(desc(Memory.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    memories = result.scalars().all()

    return {
        "items": [
            {
                "id": str(m.id),
                "user_id": str(m.user_id),
                "character_id": m.character_id,
                "content": m.content,
                "category": m.category,
                "importance": m.importance,
                "created_at": m.created_at.isoformat(),
            }
            for m in memories
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str, db: AsyncSession = Depends(get_db)):
    """删除记忆"""
    result = await db.execute(select(Memory).where(Memory.id == memory_id))
    memory = result.scalar_one_or_none()
    if not memory:
        raise HTTPException(404, "记忆不存在")

    await db.delete(memory)
    await db.commit()
    return {"message": "已删除"}
