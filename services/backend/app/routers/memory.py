from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.memory import Memory
from app.models.user import User
from app.schemas.memory import MemoryResponse, MemoryListResponse

router = APIRouter()


@router.get("/{character_id}", response_model=MemoryListResponse)
async def get_memories(
    character_id: str,
    category: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取记忆列表"""
    query = select(Memory).where(
        Memory.user_id == user.id,
        Memory.character_id == character_id,
        Memory.is_active == True,
    )
    if category:
        query = query.where(Memory.category == category)

    query = query.order_by(Memory.created_at.desc())
    result = await db.execute(query)
    memories = result.scalars().all()

    # 统计
    total_query = (
        select(func.count())
        .select_from(Memory)
        .where(Memory.user_id == user.id, Memory.character_id == character_id, Memory.is_active == True)
    )
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    important_query = (
        select(func.count())
        .select_from(Memory)
        .where(
            Memory.user_id == user.id,
            Memory.character_id == character_id,
            Memory.is_active == True,
            Memory.importance >= 8,
        )
    )
    important_result = await db.execute(important_query)
    important = important_result.scalar() or 0

    return MemoryListResponse(
        memories=[
            MemoryResponse(
                id=str(m.id),
                category=m.category,
                content=m.content,
                importance=m.importance,
                emotion_tags=m.emotion_tags or [],
                created_at=m.created_at,
            )
            for m in memories
        ],
        total=total,
        stats={"total": total, "important": important},
    )


@router.delete("/{character_id}/{memory_id}")
async def delete_memory(
    character_id: str,
    memory_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除记忆（软删除）"""
    result = await db.execute(
        select(Memory).where(
            Memory.id == memory_id,
            Memory.user_id == user.id,
            Memory.character_id == character_id,
        )
    )
    memory = result.scalar_one_or_none()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    memory.is_active = False
    await db.flush()
    return {"status": "ok"}
