from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

admin_security = HTTPBearer(auto_error=False)


def expected_admin_token() -> str:
    if settings.admin_api_token:
        return settings.admin_api_token
    if settings.debug:
        return "dev-admin-token"
    return ""


async def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(admin_security),
) -> None:
    token = expected_admin_token()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin token is not configured",
        )

    if credentials is None or credentials.credentials != token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token",
        )
