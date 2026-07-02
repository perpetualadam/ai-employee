"""
Composition root — wire external adapters from environment config.

Production pattern: business logic imports from here (or domain/services), never from
vendor SDK modules directly. To swap Telnyx → Twilio, add an adapter and register it.
"""

from __future__ import annotations

from functools import lru_cache

from app.ai.groq_provider import GroqProvider
from app.ai.provider import AIProvider
from app.config import get_settings
from app.domain.telecom import get_telecom_profile
from app.integrations.adapters.dev_email import DevEmailProvider
from app.integrations.adapters.smtp_email import SmtpEmailProvider
from app.integrations.adapters.telnyx_sms_inbound import TelnyxSmsInboundAdapter
from app.integrations.adapters.telnyx_voice import TelnyxVoiceCallControl
from app.integrations.adapters.telnyx_webhooks import TelnyxVoiceWebhookAdapter
from app.integrations.contracts import (
    EmailProvider,
    SmsInboundAdapter,
    VoiceCallControl,
    VoiceWebhookAdapter,
)
from app.models import Business
from app.services.messaging.dev_sms import DevSmsProvider
from app.services.messaging.factory import get_sms_provider, get_sms_provider_for_business
from app.services.messaging.provider import SmsProvider
from app.services.messaging.telnyx_sms import TelnyxSmsProvider

_VOICE_CONTROLS: dict[str, type[VoiceCallControl]] = {
    "telnyx": TelnyxVoiceCallControl,
}
_VOICE_WEBHOOKS: dict[str, type[VoiceWebhookAdapter]] = {
    "telnyx": TelnyxVoiceWebhookAdapter,
}
_SMS_INBOUND: dict[str, type[SmsInboundAdapter]] = {
    "telnyx": TelnyxSmsInboundAdapter,
}
_EMAIL_PROVIDERS: dict[str, type[EmailProvider]] = {
    "smtp": SmtpEmailProvider,
    "dev": DevEmailProvider,
}
_AI_PROVIDERS = {
    "groq": GroqProvider,
}


@lru_cache
def _voice_control(name: str) -> VoiceCallControl:
    cls = _VOICE_CONTROLS.get(name, TelnyxVoiceCallControl)
    return cls()


@lru_cache
def _voice_webhook(name: str) -> VoiceWebhookAdapter:
    cls = _VOICE_WEBHOOKS.get(name, TelnyxVoiceWebhookAdapter)
    return cls()


@lru_cache
def _sms_inbound(name: str) -> SmsInboundAdapter:
    cls = _SMS_INBOUND.get(name, TelnyxSmsInboundAdapter)
    return cls()


@lru_cache
def _email_provider(name: str) -> EmailProvider:
    cls = _EMAIL_PROVIDERS.get(name, DevEmailProvider)
    return cls()


def get_ai_provider() -> AIProvider:
    settings = get_settings()
    name = (settings.ai_provider or "groq").lower()
    cls = _AI_PROVIDERS.get(name, GroqProvider)
    return cls(api_key=settings.groq_api_key, model=settings.groq_model)


def get_voice_call_control(business: Business | None = None) -> VoiceCallControl:
    """Live call transfer / TeXML control — swap via VOICE_PROVIDER env."""
    settings = get_settings()
    provider_name = (settings.voice_provider or "telnyx").lower()
    if provider_name == "auto":
        return _auto_voice_control(business)
    return _voice_control(provider_name)


def get_voice_webhook_adapter() -> VoiceWebhookAdapter:
    settings = get_settings()
    name = (settings.voice_provider or "telnyx").lower()
    if name == "auto":
        name = "telnyx"
    return _voice_webhook(name)


def get_sms_inbound_adapter() -> SmsInboundAdapter:
    settings = get_settings()
    name = (settings.sms_provider or "telnyx").lower()
    if name in ("auto", "dev"):
        name = "telnyx"
    return _sms_inbound(name)


def get_email_provider() -> EmailProvider:
    settings = get_settings()
    name = (settings.email_provider or "auto").lower()
    if name == "auto":
        smtp = SmtpEmailProvider()
        return smtp if smtp.is_configured() else DevEmailProvider()
    return _email_provider(name)


def _auto_voice_control(business: Business | None) -> VoiceCallControl:
    if business is not None:
        profile = get_telecom_profile(business.country)
        for candidate in profile.recommended_voice_providers:
            control = _voice_control(candidate)
            if control.is_configured():
                return control
    telnyx = _voice_control("telnyx")
    return telnyx if telnyx.is_configured() else telnyx


def list_registered_integrations() -> dict[str, list[str]]:
    """Diagnostics — which adapter names are registered (for ops / health checks)."""
    return {
        "ai": list(_AI_PROVIDERS.keys()),
        "voice": list(_VOICE_CONTROLS.keys()),
        "voice_webhook": list(_VOICE_WEBHOOKS.keys()),
        "sms_outbound": ["telnyx", "dev"],
        "sms_inbound": list(_SMS_INBOUND.keys()),
        "email": list(_EMAIL_PROVIDERS.keys()),
    }


__all__ = [
    "get_ai_provider",
    "get_email_provider",
    "get_sms_inbound_adapter",
    "get_sms_provider",
    "get_sms_provider_for_business",
    "get_voice_call_control",
    "get_voice_webhook_adapter",
    "list_registered_integrations",
    "DevSmsProvider",
    "EmailProvider",
    "SmsInboundAdapter",
    "SmsProvider",
    "TelnyxSmsProvider",
    "VoiceCallControl",
    "VoiceWebhookAdapter",
]
