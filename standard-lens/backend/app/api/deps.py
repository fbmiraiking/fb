"""Shared API dependencies."""

import secrets

from fastapi import Header, HTTPException, status

from app.core.config import get_settings


def require_admin_token(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> None:
    """Protect administrative endpoints with a shared token from .env."""
    settings = get_settings()
    if not settings.admin_sync_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="管理员同步令牌未配置，请设置 ADMIN_SYNC_TOKEN",
        )
    if not x_admin_token or not secrets.compare_digest(
        x_admin_token.encode("utf-8"),
        settings.admin_sync_token.encode("utf-8"),
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="管理员令牌无效",
            headers={"WWW-Authenticate": "Bearer"},
        )
