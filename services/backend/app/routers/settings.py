from fastapi import APIRouter, Depends
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("")
async def get_settings(user: User = Depends(get_current_user)):
    """获取用户设置"""
    defaults = {
        "push_enabled": True,
        "voice_call_enabled": False,
        "dnd_start": "23:00",
        "dnd_end": "08:00",
        "proactive_level": "medium",
    }
    return {**defaults, **user.settings}
