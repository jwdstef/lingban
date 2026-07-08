"""记忆管理接口 - 查看、删除、分类统计"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import String, cast, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.memory import Memory
from app.models.user import User

router = APIRouter()


# ── Schemas ──

class MemoryResponse(BaseModel):
    id: str
    category: str
    content: str
    importance: int
    emotion_tags: list[str]
    recall_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CategoryStats(BaseModel):
    category: str
    count: int


class MemoryListResponse(BaseModel):
    memories: list[MemoryResponse]
    total: int
    has_more: bool
    categories: list[CategoryStats]


class BatchDeleteRequest(BaseModel):
    memory_ids: list[str]


class UpdateMemoryRequest(BaseModel):
    content: str | None = None
    category: str | None = None
    importance: int | None = Field(default=None, ge=1, le=10)
    emotion_tags: list[str] | None = None


class UpdateMemoryToggleRequest(BaseModel):
    memory_enabled: bool


# ── 分类定义 ──

CATEGORY_LABELS = {
    "daily": "日常",
    "emotion": "情绪",
    "preference": "偏好",
    "event": "事件",
    "person": "人物",
    "fact": "事实",
}


# ── 获取记忆列表 ──

def _parse_memory_id(memory_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(memory_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid memory id") from exc


def _serialize_memory(memory: Memory) -> MemoryResponse:
    return MemoryResponse(
        id=str(memory.id),
        category=memory.category,
        content=memory.content,
        importance=memory.importance,
        emotion_tags=memory.emotion_tags or [],
        recall_count=memory.recall_count,
        created_at=memory.created_at,
    )


def _search_filter(search: str):
    pattern = f"%{search.strip()}%"
    return or_(
        Memory.content.ilike(pattern),
        Memory.category.ilike(pattern),
        cast(Memory.emotion_tags, String).ilike(pattern),
    )


@router.put("/toggle")
async def toggle_memory(
    data: UpdateMemoryToggleRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enable or disable future memory extraction for the current user."""
    settings = {**(user.settings or {}), "memory_enabled": data.memory_enabled}
    if data.memory_enabled:
        settings.pop("memory_disabled_at", None)
    else:
        settings["memory_disabled_at"] = datetime.now(timezone.utc).isoformat()

    user.settings = settings
    await db.flush()
    return {"status": "ok", "settings": settings}


@router.get("/{character_id}", response_model=MemoryListResponse)
async def get_memories(
    character_id: str,
    category: str | None = None,
    search: str | None = Query(default=None, alias="query", min_length=1, max_length=120),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取记忆列表（支持分类筛选）"""
    # 基础查询条件
    base_where = [
        Memory.user_id == user.id,
        Memory.character_id == character_id,
        Memory.is_active == True,
    ]

    # 查询记忆列表
    list_where = list(base_where)
    if category:
        list_where.append(Memory.category == category)
    if search and search.strip():
        list_where.append(_search_filter(search))

    query = select(Memory).where(*list_where)
    query = query.order_by(Memory.importance.desc(), Memory.created_at.desc())
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    memories = result.scalars().all()

    # 总数
    total_query = select(func.count()).select_from(Memory).where(*list_where)
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    # 分类统计
    category_query = (
        select(Memory.category, func.count())
        .where(*base_where)
        .group_by(Memory.category)
    )
    category_result = await db.execute(category_query)
    categories = [
        CategoryStats(category=row[0], count=row[1])
        for row in category_result.fetchall()
    ]

    return MemoryListResponse(
        memories=[_serialize_memory(m) for m in memories],
        total=total,
        has_more=offset + limit < total,
        categories=categories,
    )


# ── 批量删除记忆 ──

@router.post("/{character_id}/batch-delete")
async def batch_delete_memories(
    character_id: str,
    data: BatchDeleteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """批量删除记忆"""
    if not data.memory_ids:
        return {"status": "ok", "deleted_count": 0}

    parsed_ids = [_parse_memory_id(memory_id) for memory_id in data.memory_ids]

    # 批量软删除
    result = await db.execute(
        update(Memory)
        .where(
            Memory.id.in_(parsed_ids),
            Memory.user_id == user.id,
            Memory.character_id == character_id,
        )
        .values(is_active=False)
    )
    await db.flush()

    return {"status": "ok", "deleted_count": result.rowcount}


# ── 清空所有记忆 ──

@router.delete("/{character_id}/all")
async def clear_all_memories(
    character_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """清空与某角色的所有记忆（软删除）"""
    result = await db.execute(
        update(Memory)
        .where(
            Memory.user_id == user.id,
            Memory.character_id == character_id,
            Memory.is_active == True,
        )
        .values(is_active=False)
    )
    await db.flush()

    return {"status": "ok", "deleted_count": result.rowcount}


# ── 获取分类标签 ──

@router.get("/{character_id}/categories")
async def get_categories(
    character_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取记忆分类列表（带数量统计）"""
    query = (
        select(Memory.category, func.count())
        .where(
            Memory.user_id == user.id,
            Memory.character_id == character_id,
            Memory.is_active == True,
        )
        .group_by(Memory.category)
    )
    result = await db.execute(query)
    rows = result.fetchall()

    categories = []
    for cat, count in rows:
        categories.append({
            "key": cat,
            "label": CATEGORY_LABELS.get(cat, cat),
            "count": count,
        })

    # 按数量降序排列
    categories.sort(key=lambda x: x["count"], reverse=True)

    return {"categories": categories}


# ── 获取单条记忆详情 ──

@router.get("/{character_id}/{memory_id}", response_model=MemoryResponse)
async def get_memory_detail(
    character_id: str,
    memory_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取单条记忆详情"""
    parsed_id = _parse_memory_id(memory_id)
    result = await db.execute(
        select(Memory).where(
            Memory.id == parsed_id,
            Memory.user_id == user.id,
            Memory.character_id == character_id,
            Memory.is_active == True,
        )
    )
    memory = result.scalar_one_or_none()
    if not memory:
        raise HTTPException(status_code=404, detail="记忆不存在")

    return _serialize_memory(memory)


# ── 删除单条记忆 ──

@router.put("/{character_id}/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    character_id: str,
    memory_id: str,
    data: UpdateMemoryRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Edit one active memory and clear stale embedding when content changes."""
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No memory fields to update")

    parsed_id = _parse_memory_id(memory_id)
    result = await db.execute(
        select(Memory).where(
            Memory.id == parsed_id,
            Memory.user_id == user.id,
            Memory.character_id == character_id,
            Memory.is_active == True,
        )
    )
    memory = result.scalar_one_or_none()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    if "content" in updates:
        content = (data.content or "").strip()
        if not content:
            raise HTTPException(status_code=400, detail="Memory content cannot be empty")
        if content != memory.content:
            memory.content = content
            memory.embedding = None

    if "category" in updates:
        category = (data.category or "").strip()
        if category not in CATEGORY_LABELS:
            raise HTTPException(status_code=400, detail="Invalid memory category")
        memory.category = category

    if "importance" in updates:
        memory.importance = data.importance

    if "emotion_tags" in updates:
        memory.emotion_tags = [
            tag.strip()
            for tag in (data.emotion_tags or [])
            if tag and tag.strip()
        ]

    memory.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return _serialize_memory(memory)


@router.delete("/{character_id}/{memory_id}")
async def delete_memory(
    character_id: str,
    memory_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除单条记忆（软删除）"""
    parsed_id = _parse_memory_id(memory_id)
    result = await db.execute(
        select(Memory).where(
            Memory.id == parsed_id,
            Memory.user_id == user.id,
            Memory.character_id == character_id,
            Memory.is_active == True,
        )
    )
    memory = result.scalar_one_or_none()
    if not memory:
        raise HTTPException(status_code=404, detail="记忆不存在")

    memory.is_active = False
    await db.flush()
    return {"status": "ok", "deleted_count": 1}
