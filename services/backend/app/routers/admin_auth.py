"""Admin authentication helpers."""

from fastapi import APIRouter, Depends

from app.core.admin_auth import require_admin

router = APIRouter()


@router.post("/verify")
async def verify_admin_token(_: None = Depends(require_admin)):
    return {"status": "ok"}
