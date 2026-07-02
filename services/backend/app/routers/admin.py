"""管理后台 API"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import User, Character, UserCharacterRelation, ChatMessage, Memory

router = APIRouter()


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
