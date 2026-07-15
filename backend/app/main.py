"""FastAPI application entry point."""

import logging

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api import appointments, auth, billing, business, calls, conversations, customers, dashboard, internal, jobs, onboarding, phone, public, receptionist, sms, voice
from app.config import get_settings
from app.core.logging_config import setup_logging
from app.core.monitoring import check_database, init_sentry, sentry_active
from app.core.rate_limit import _rate_limit_exceeded_handler, limiter
from app.database import get_db

settings = get_settings()
setup_logging(debug=settings.debug)
init_sentry()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if not settings.debug and "*" not in settings.allowed_host_list:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_host_list)

app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(business.router, prefix=settings.api_v1_prefix)
app.include_router(phone.router, prefix=settings.api_v1_prefix)
app.include_router(dashboard.router, prefix=settings.api_v1_prefix)
app.include_router(customers.router, prefix=settings.api_v1_prefix)
app.include_router(jobs.router, prefix=settings.api_v1_prefix)
app.include_router(appointments.router, prefix=settings.api_v1_prefix)
app.include_router(receptionist.router, prefix=settings.api_v1_prefix)
app.include_router(conversations.router, prefix=settings.api_v1_prefix)
app.include_router(public.router, prefix=settings.api_v1_prefix)
app.include_router(sms.router, prefix=settings.api_v1_prefix)
app.include_router(voice.router, prefix=settings.api_v1_prefix)
app.include_router(calls.router, prefix=settings.api_v1_prefix)
app.include_router(internal.router, prefix=settings.api_v1_prefix)
app.include_router(billing.router, prefix=settings.api_v1_prefix)
app.include_router(onboarding.router, prefix=settings.api_v1_prefix)


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready(db=Depends(get_db)) -> dict:
    db_status = check_database(db)
    ready = db_status.get("ok", False)
    return {
        "status": "ok" if ready else "degraded",
        "database": db_status,
    }


@app.get("/health")
def health_check(db=Depends(get_db)) -> dict:
    from app.integrations.registry import (
        get_email_provider,
        get_sms_provider,
        get_voice_call_control,
        list_registered_integrations,
    )
    from app.services.voice_mode_service import VoiceModeService
    from app.voice import telnyx_client

    sms = get_sms_provider()
    email = get_email_provider()
    voice = get_voice_call_control()
    settings = get_settings()
    db_status = check_database(db)
    return {
        "status": "ok" if db_status.get("ok") else "degraded",
        "database": db_status,
        "providers": {
            "ai": settings.ai_provider,
            "sms": sms.provider_name,
            "sms_configured": sms.is_configured(),
            "email": email.provider_name,
            "email_configured": email.is_configured(),
            "voice": voice.provider_name,
            "voice_configured": voice.is_configured(),
            "outbound_configured": telnyx_client.is_outbound_call_configured(),
            "phone_provisioning_configured": telnyx_client.is_phone_provisioning_configured(),
        },
        "voice_mode": VoiceModeService.status(),
        "monitoring": {"sentry": sentry_active()},
        "registered_adapters": list_registered_integrations(),
    }
