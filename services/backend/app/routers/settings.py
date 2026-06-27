from fastapi import APIRouter, Depends
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("")
async def get_settings(user: User = Depends(get_current_user)):
    """获取用户设置"""
    return {
        "push_enabled": True,
        "voice_call_enabled": True,
        "dnd_start": "23:00",
        "dnd_end": "08:00",
        "proactive_level": "medium",
    }


@router.put("")
async def update_settings(
    data: dict,
    user: User = Depends(get_current_user),
):
    """更新用户设置"""
    # TODO: 持久化设置到数据库
    return {"status": "ok", "updated": list(data.keys())}
