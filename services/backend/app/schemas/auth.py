# Auth schemas are now defined inline in routers/auth.py
# This file kept for backward compatibility
from app.routers.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
    UpdatePushTokenRequest,
    UpdateSettingsRequest,
)

__all__ = [
    "RegisterRequest",
    "LoginRequest",
    "TokenResponse",
    "UserResponse",
    "UpdatePushTokenRequest",
    "UpdateSettingsRequest",
]
