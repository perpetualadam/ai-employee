"""
Composition root — wire external adapters from environment config.

Production pattern: business logic imports from here (or domain/services), never from
vendor SDK modules directly. Provider names are resolved via ProviderConfiguration.
"""

from __future__ import annotations

from functools import lru_cache

from app.ai.groq_provider import GroqProvider
from app.ai.provider import AIProvider
from app.config import get_settings
from app.integrations.adapters.dev_email import DevEmailProvider
from app.integrations.adapters.resend_email import ResendEmailAdapter
from app.integrations.adapters.smtp_email import SmtpEmailProvider
from app.integrations.adapters.telnyx_duplex import TelnyxDuplexMediaAdapter
from app.integrations.adapters.telnyx_sms_inbound import TelnyxSmsInboundAdapter
from app.integrations.adapters.telnyx_voice import TelnyxVoiceCallControl
from app.integrations.adapters.telnyx_webhooks import TelnyxVoiceWebhookAdapter
from app.integrations.adapters.twilio_duplex import TwilioDuplexMediaAdapter
from app.integrations.adapters.vonage_duplex import VonageDuplexMediaAdapter
from app.integrations.adapter_selection import select_adapter
from app.integrations.adapters.call_recording import build_call_recording_adapter
from app.integrations.contracts import (
    CallRecordingAdapter,
    EmailProvider,
    SmsInboundAdapter,
    VoiceCallControl,
    VoiceWebhookAdapter,
)
from app.integrations.provider_resolution import (
    resolve_sms_cpaas_name,
    resolve_telephony_adapter_name,
)
from app.models import Business
from app.providers.services import ProviderService
from app.services.messaging.dev_sms import DevSmsProvider
from app.services.messaging.factory import get_sms_provider, get_sms_provider_for_business
from app.services.messaging.provider import SmsProvider
from app.services.messaging.telnyx_sms import TelnyxSmsProvider
from app.services.messaging.twilio_sms import TwilioSmsProvider
from app.services.messaging.vonage_sms import VonageSmsProvider
from app.voice.duplex.contracts import DuplexMediaAdapter

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
    "resend": ResendEmailAdapter,
}
_DUPLEX_ADAPTERS: dict[str, type[DuplexMediaAdapter]] = {
    "telnyx": TelnyxDuplexMediaAdapter,
    "twilio": TwilioDuplexMediaAdapter,
    "vonage": VonageDuplexMediaAdapter,
}
_AI_PROVIDERS = {
    "groq": GroqProvider,
}


def register_voice_control(name: str, cls: type[VoiceCallControl]) -> None:
    _VOICE_CONTROLS[name.lower()] = cls


def register_voice_webhook(name: str, cls: type[VoiceWebhookAdapter]) -> None:
    _VOICE_WEBHOOKS[name.lower()] = cls


def register_sms_inbound(name: str, cls: type[SmsInboundAdapter]) -> None:
    _SMS_INBOUND[name.lower()] = cls


def register_duplex_adapter(name: str, cls: type[DuplexMediaAdapter]) -> None:
    _DUPLEX_ADAPTERS[name.lower()] = cls


@lru_cache
def _duplex_adapter(name: str) -> DuplexMediaAdapter:
    cls = _DUPLEX_ADAPTERS[name]
    return cls()


@lru_cache
def _voice_control(name: str) -> VoiceCallControl:
    cls = _VOICE_CONTROLS[name]
    return cls()


@lru_cache
def _voice_webhook(name: str) -> VoiceWebhookAdapter:
    cls = _VOICE_WEBHOOKS[name]
    return cls()


@lru_cache
def _sms_inbound(name: str) -> SmsInboundAdapter:
    cls = _SMS_INBOUND[name]
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
    """Live call transfer / TeXML control — resolved from ProviderConfiguration."""
    primary = resolve_telephony_adapter_name(business=business)
    return select_adapter(
        {name: lambda n=name: _voice_control(n) for name in _VOICE_CONTROLS},
        ProviderService.TELEPHONY,
        primary,
    )


def get_voice_webhook_adapter(business: Business | None = None) -> VoiceWebhookAdapter:
    primary = resolve_telephony_adapter_name(business=business)
    return select_adapter(
        {name: lambda n=name: _voice_webhook(n) for name in _VOICE_WEBHOOKS},
        ProviderService.TELEPHONY,
        primary,
    )


def get_voice_webhook_adapter_for_request(
    request,
    business: Business | None = None,
) -> VoiceWebhookAdapter:
    """Prefer header-detected CPaaS so multi-primary inbound shares one route."""
    from app.integrations.webhook_dispatch import detect_voice_webhook_provider

    detected = detect_voice_webhook_provider(request)
    if detected and detected in _VOICE_WEBHOOKS:
        return _voice_webhook(detected)
    return get_voice_webhook_adapter(business)


def get_sms_inbound_adapter(business: Business | None = None) -> SmsInboundAdapter:
    primary = resolve_sms_cpaas_name(business=business)
    return select_adapter(
        {name: lambda n=name: _sms_inbound(n) for name in _SMS_INBOUND},
        ProviderService.TELEPHONY,
        primary,
    )


def get_sms_inbound_adapter_for_request(
    request,
    business: Business | None = None,
) -> SmsInboundAdapter:
    from app.integrations.webhook_dispatch import detect_sms_webhook_provider

    detected = detect_sms_webhook_provider(request)
    if detected and detected in _SMS_INBOUND:
        return _sms_inbound(detected)
    return get_sms_inbound_adapter(business)


def get_duplex_media_adapter(business: Business | None = None, db=None) -> DuplexMediaAdapter:
    """Resolve duplex media adapter from tenant telephony CPaaS (Telnyx, Twilio, Vonage)."""
    primary = resolve_telephony_adapter_name(business=business, db=db)
    return select_adapter(
        {name: lambda n=name: _duplex_adapter(n) for name in _DUPLEX_ADAPTERS},
        ProviderService.TELEPHONY,
        primary,
    )


def get_email_provider() -> EmailProvider:
    settings = get_settings()
    name = (settings.email_provider or "auto").lower()
    if name == "auto":
        resend = ResendEmailAdapter()
        if resend.is_configured():
            return resend
        smtp = SmtpEmailProvider()
        return smtp if smtp.is_configured() else DevEmailProvider()
    return _email_provider(name)


def get_call_recording_adapter(provider: str | None = None) -> CallRecordingAdapter:
    """Resolve call-recording adapter for a telephony CPaaS name."""
    return build_call_recording_adapter(provider)


def list_registered_integrations() -> dict[str, list[str]]:
    """Diagnostics — which adapter names are registered (for ops / health checks)."""
    return {
        "ai": list(_AI_PROVIDERS.keys()),
        "voice": list(_VOICE_CONTROLS.keys()),
        "voice_webhook": list(_VOICE_WEBHOOKS.keys()),
        "sms_outbound": list(_SMS_OUTBOUND_PROVIDERS().keys()),
        "sms_inbound": list(_SMS_INBOUND.keys()),
        "duplex": list(_DUPLEX_ADAPTERS.keys()),
        "call_recording": ["telnyx", "twilio", "signalwire", "vonage", "plivo"],
        "email": list(_EMAIL_PROVIDERS.keys()),
    }


def _SMS_OUTBOUND_PROVIDERS() -> dict[str, type[SmsProvider]]:
    return {
        "telnyx": TelnyxSmsProvider,
        "dev": DevSmsProvider,
        "twilio": TwilioSmsProvider,
        "vonage": VonageSmsProvider,
    }


__all__ = [
    "get_ai_provider",
    "get_call_recording_adapter",
    "get_duplex_media_adapter",
    "get_email_provider",
    "get_sms_inbound_adapter",
    "get_sms_provider",
    "get_sms_provider_for_business",
    "get_voice_call_control",
    "get_voice_webhook_adapter",
    "list_registered_integrations",
    "register_duplex_adapter",
    "register_sms_inbound",
    "register_voice_control",
    "register_voice_webhook",
    "CallRecordingAdapter",
    "DevSmsProvider",
    "EmailProvider",
    "SmsInboundAdapter",
    "SmsProvider",
    "TelnyxSmsProvider",
    "VoiceCallControl",
    "VoiceWebhookAdapter",
]
