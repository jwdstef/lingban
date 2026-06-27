from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.character import Character
from app.models.user import User

router = APIRouter()


@router.get("")
async def list_characters(db: AsyncSession = Depends(get_db)):
    """获取所有可用角色"""
    result = await db.execute(select(Character).order_by(Character.created_at))
    characters = result.scalars().all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "source": c.source,
            "description": c.description,
            "avatar_url": c.avatar_url,
            "color": c.color,
            "personality": c.personality,
        }
        for c in characters
    ]


@router.get("/{character_id}")
async def get_character(character_id: str, db: AsyncSession = Depends(get_db)):
    """获取角色详情"""
    result = await db.execute(select(Character).where(Character.id == character_id))
    character = result.scalar_one_or_none()
    if not character:
        return {"error": "Character not found"}, 404
    return {
        "id": character.id,
        "name": character.name,
        "source": character.source,
        "description": character.description,
        "personality": character.personality,
        "system_prompt": character.system_prompt,
    }


@router.post("/select")
async def select_character(
    data: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """选择当前角色"""
    character_id = data.get("character_id")
    user.selected_character_id = character_id
    await db.flush()
    return {"status": "ok", "selected_character_id": character_id}
