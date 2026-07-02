"""Resolve SMS provider from env and optional business country."""

from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.domain.telecom import get_telecom_profile
from app.models import Business
from app.services.messaging.dev_sms import DevSmsProvider
from app.services.messaging.provider import SmsProvider
from app.services.messaging.telnyx_sms import TelnyxSmsProvider

_PROVIDERS: dict[str, type[SmsProvider]] = {
    "telnyx": TelnyxSmsProvider,
    "dev": DevSmsProvider,
}


@lru_cache
def _provider_instance(name: str) -> SmsProvider:
    cls = _PROVIDERS.get(name, DevSmsProvider)
    return cls()


def get_sms_provider(name: str | None = None) -> SmsProvider:
    """Return a provider by explicit name (defaults to SMS_PROVIDER env)."""
    settings = get_settings()
    provider_name = (name or settings.sms_provider or "telnyx").lower()
    if provider_name == "auto":
        return _auto_select_provider(None)
    return _provider_instance(provider_name)


def get_sms_provider_for_business(business: Business | None) -> SmsProvider:
    """Pick provider from env, or auto-select from country recommendations."""
    settings = get_settings()
    if (settings.sms_provider or "telnyx").lower() == "auto":
        return _auto_select_provider(business)
    return get_sms_provider(settings.sms_provider)


def _auto_select_provider(business: Business | None) -> SmsProvider:
    if business is not None:
        profile = get_telecom_profile(business.country)
        for name in profile.recommended_sms_providers:
            provider = _provider_instance(name)
            if provider.is_configured():
                return provider
    telnyx = _provider_instance("telnyx")
    if telnyx.is_configured():
        return telnyx
    return _provider_instance("dev")
