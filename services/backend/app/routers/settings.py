from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.user_settings import merge_user_settings
from app.models.user import User

router = APIRouter()


class UpdateSettingsRequest(BaseModel):
    settings: dict


@router.get("")
async def get_settings(user: User = Depends(get_current_user)):
    """获取用户设置"""
    defaults = {
        "push_enabled": True,
        "voice_call_enabled": False,
        "dnd_start": "23:00",
        "dnd_end": "08:00",
        "proactive_level": "medium",
        "memory_enabled": True,
    }
    return {**defaults, **(user.settings or {})}


@router.put("")
async def update_settings(
    data: UpdateSettingsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user settings."""
    user.settings = merge_user_settings(user.settings, data.settings)
    await db.flush()
    return {"status": "ok", "settings": user.settings}
