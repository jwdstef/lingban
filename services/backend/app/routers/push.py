"""Push token and notification click APIs."""

import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.memory import ProactiveMessage
from app.models.push import PushDelivery, PushToken
from app.models.user import User

router = APIRouter()


PushProvider = Literal["apns", "jpush", "fcm"]
PermissionStatus = Literal["granted", "denied", "unknown"]


class RegisterPushTokenRequest(BaseModel):
    platform: PushProvider
    provider: PushProvider | None = None
    token: str = Field(min_length=1, max_length=1000)
    permission_status: PermissionStatus = "unknown"
    device_id: str | None = Field(default=None, max_length=100)
    app_version: str | None = Field(default=None, max_length=50)


class PushTokenResponse(BaseModel):
    status: str = "ok"
    token_id: str
    platform: str
    provider: str
    permission_status: str
    push_enabled: bool


class PushClickRequest(BaseModel):
    delivery_id: str | None = None
    proactive_message_id: str | None = None
    deep_link: str | None = Field(default=None, max_length=500)


class PushClickResponse(BaseModel):
    status: str = "ok"
    delivery_id: str | None = None
    proactive_message_id: str
    push_status: str
    delivered: bool
    clicked_at: str


def _parse_uuid(value: str, field_name: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}") from exc


def _push_settings(user: User) -> dict:
    return {
        "push_enabled": True,
        "push_permission_status": "unknown",
        **(user.settings or {}),
    }


@router.post("/tokens", response_model=PushTokenResponse)
async def register_push_token(
    data: RegisterPushTokenRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register or update the current device push token."""
    provider = data.provider or data.platform
    settings = _push_settings(user)
    settings.update(
        {
            "push_enabled": data.permission_status == "granted",
            "push_permission_status": data.permission_status,
            "push_device_id": data.device_id,
            "push_app_version": data.app_version,
            "push_updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    user.push_token = data.token
    user.push_platform = provider
    user.settings = settings
    token_result = await db.execute(
        select(PushToken).where(
            PushToken.provider == provider,
            PushToken.token == data.token,
        )
    )
    push_token = token_result.scalar_one_or_none()
    if not push_token:
        push_token = PushToken(
            user_id=user.id,
            platform=data.platform,
            provider=provider,
            token=data.token,
        )
        db.add(push_token)

    push_token.user_id = user.id
    push_token.platform = data.platform
    push_token.provider = provider
    push_token.token = data.token
    push_token.permission_status = data.permission_status
    push_token.device_id = data.device_id
    push_token.app_version = data.app_version
    push_token.is_active = data.permission_status == "granted"
    await db.flush()

    return PushTokenResponse(
        token_id=str(push_token.id),
        platform=data.platform,
        provider=provider,
        permission_status=data.permission_status,
        push_enabled=settings["push_enabled"],
    )


@router.post("/click", response_model=PushClickResponse)
async def record_push_click(
    data: PushClickRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record a push click and mark the related proactive message opened."""
    message_id = data.proactive_message_id or data.delivery_id
    if not message_id:
        raise HTTPException(
            status_code=400,
            detail="delivery_id or proactive_message_id is required",
        )

    parsed_id = _parse_uuid(message_id, "delivery_id")
    delivery = None
    if data.delivery_id:
        delivery_result = await db.execute(
            select(PushDelivery).where(
                PushDelivery.id == parsed_id,
                PushDelivery.user_id == user.id,
            )
        )
        delivery = delivery_result.scalar_one_or_none()

    proactive_message_id = delivery.proactive_message_id if delivery else parsed_id
    result = await db.execute(
        select(ProactiveMessage).where(
            ProactiveMessage.id == proactive_message_id,
            ProactiveMessage.user_id == user.id,
        )
    )
    message = result.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=404, detail="Push delivery not found")

    clicked_at = datetime.now(timezone.utc)
    message.push_status = "clicked"
    message.delivered = True
    if delivery:
        delivery.status = "clicked"
        delivery.clicked_at = clicked_at
    await db.flush()

    return PushClickResponse(
        delivery_id=str(delivery.id) if delivery else None,
        proactive_message_id=str(message.id),
        push_status=message.push_status,
        delivered=message.delivered,
        clicked_at=clicked_at.isoformat(),
    )
