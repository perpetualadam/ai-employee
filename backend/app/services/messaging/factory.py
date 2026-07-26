"""Resolve SMS provider from ProviderConfiguration and optional business country."""

from __future__ import annotations

from functools import lru_cache

from app.integrations.adapter_selection import select_adapter
from app.integrations.provider_resolution import resolve_sms_outbound_name
from app.models import Business
from app.providers.services import ProviderService
from app.services.messaging.dev_sms import DevSmsProvider
from app.services.messaging.provider import SmsProvider
from app.services.messaging.telnyx_sms import TelnyxSmsProvider

_PROVIDERS: dict[str, type[SmsProvider]] = {
    "telnyx": TelnyxSmsProvider,
    "dev": DevSmsProvider,
}


def register_sms_outbound(name: str, cls: type[SmsProvider]) -> None:
    _PROVIDERS[name.lower()] = cls


@lru_cache
def _provider_instance(name: str) -> SmsProvider:
    cls = _PROVIDERS.get(name, DevSmsProvider)
    return cls()


def get_sms_provider(name: str | None = None) -> SmsProvider:
    """Return a provider by explicit name or from ProviderConfiguration."""
    if name:
        return _provider_instance(name.lower())
    primary = resolve_sms_outbound_name()
    return select_adapter(
        {n: lambda n=n: _provider_instance(n) for n in _PROVIDERS},
        ProviderService.MESSAGING,
        primary,
        fallbacks=["dev"],
    )


def get_sms_provider_for_business(business: Business | None) -> SmsProvider:
    """Pick SMS provider from configuration for the business country."""
    primary = resolve_sms_outbound_name(business=business)
    return select_adapter(
        {n: lambda n=n: _provider_instance(n) for n in _PROVIDERS},
        ProviderService.MESSAGING,
        primary,
        fallbacks=["dev"],
    )
