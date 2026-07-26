"""Production security policy validation and internal route authentication."""

from __future__ import annotations

import logging

from fastapi import Header, HTTPException, status

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

_INSECURE_SECRET_KEYS = frozenset(
    {
        "change-me-in-production-use-openssl-rand-hex-32",
        "change-me-use-openssl-rand-hex-32",
    }
)


def validate_security_policy(settings: Settings | None = None) -> None:
    """Fail fast when obvious insecure defaults are used outside local debug."""
    cfg = settings or get_settings()
    if cfg.debug:
        logger.warning("DEBUG=true — security checks relaxed for local development")
        return

    if cfg.secret_key.strip() in _INSECURE_SECRET_KEYS:
        raise RuntimeError(
            "SECRET_KEY is set to a known insecure default. "
            "Generate one with: openssl rand -hex 32"
        )

    if not cfg.cron_secret.strip():
        logger.warning(
            "CRON_SECRET is unset — /internal and /admin routes will reject requests"
        )

    if "*" in cfg.allowed_host_list:
        logger.warning("ALLOWED_HOSTS=* — host header validation is disabled")


def verify_internal_secret(x_cron_secret: str | None = Header(default=None)) -> None:
    """Protect cron/admin routes — always requires CRON_SECRET (no debug bypass)."""
    settings = get_settings()
    if not settings.cron_secret.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CRON_SECRET is not configured.",
        )
    if x_cron_secret != settings.cron_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal secret",
        )
