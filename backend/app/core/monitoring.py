"""Production monitoring — Sentry and dependency health checks."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings

logger = logging.getLogger(__name__)
_sentry_initialized = False


def init_sentry() -> bool:
    """Initialize Sentry when SENTRY_DSN is set. Returns True if active."""
    global _sentry_initialized
    settings = get_settings()
    if not settings.sentry_dsn or _sentry_initialized:
        return bool(settings.sentry_dsn and _sentry_initialized)

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.sentry_environment,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            ],
            send_default_pii=False,
        )
        _sentry_initialized = True
        logger.info("Sentry initialized", extra={"environment": settings.sentry_environment})
        return True
    except ImportError:
        logger.warning("sentry-sdk not installed — skipping Sentry initialization")
        return False


def sentry_active() -> bool:
    """True when Sentry SDK initialized successfully."""
    return _sentry_initialized


def check_database(db: Session) -> dict:
    try:
        db.execute(text("SELECT 1"))
        return {"ok": True}
    except Exception as exc:
        logger.exception("Database health check failed")
        return {"ok": False, "error": str(exc)}
