"""HttpOnly auth cookie helpers."""

from __future__ import annotations

from fastapi import Response

from app.config import get_settings

AUTH_COOKIE_NAME = "access_token"


def set_auth_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        path="/",
        secure=not settings.debug,
        samesite="lax",
    )
