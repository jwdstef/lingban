from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter()


# ── Schemas ──

class RegisterRequest(BaseModel):
    phone: str | None = None
    email: str | None = None
    nickname: str
    password: str


class LoginRequest(BaseModel):
    phone: str | None = None
    email: str | None = None
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    nickname: str
    phone: str | None
    email: str | None
    avatar_url: str
    selected_character_id: str | None
    push_token: str | None
    push_platform: str | None

    model_config = {"from_attributes": True}


class UpdatePushTokenRequest(BaseModel):
    push_token: str
    push_platform: str  # apns / jpush / fcm


class UpdateSettingsRequest(BaseModel):
    settings: dict


# ── Auth Endpoints ──

@router.post("/register", response_model=TokenResponse)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """注册新用户"""
    if not data.phone and not data.email:
        raise HTTPException(status_code=400, detail="手机号或邮箱至少填一个")

    if data.phone:
        result = await db.execute(select(User).where(User.phone == data.phone))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="该手机号已注册")

    if data.email:
        result = await db.execute(select(User).where(User.email == data.email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="该邮箱已注册")

    user = User(
        phone=data.phone,
        email=data.email,
        nickname=data.nickname,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    await db.flush()

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    if not data.phone and not data.email:
        raise HTTPException(status_code=400, detail="手机号或邮箱至少填一个")

    if data.phone:
        result = await db.execute(select(User).where(User.phone == data.phone))
    else:
        result = await db.execute(select(User).where(User.email == data.email))

    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="账号或密码错误")

    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return UserResponse(
        id=str(user.id),
        nickname=user.nickname,
        phone=user.phone,
        email=user.email,
        avatar_url=user.avatar_url,
        selected_character_id=user.selected_character_id,
        push_token=user.push_token,
        push_platform=user.push_platform,
    )


@router.post("/push-token")
async def update_push_token(
    data: UpdatePushTokenRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """注册/更新推送 Token"""
    if data.push_platform not in ("apns", "jpush", "fcm"):
        raise HTTPException(status_code=400, detail="不支持的推送平台")

    user.push_token = data.push_token
    user.push_platform = data.push_platform
    await db.flush()
    return {"status": "ok"}


@router.put("/settings")
async def update_settings(
    data: UpdateSettingsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新用户设置"""
    user.settings = {**user.settings, **data.settings}
    await db.flush()
    return {"status": "ok", "settings": user.settings}
