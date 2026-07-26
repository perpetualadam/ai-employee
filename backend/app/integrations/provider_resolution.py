"""Resolve integration adapter names from ProviderConfiguration — no hardcoded vendors."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.config import get_settings
from app.providers.configuration import get_provider_configuration
from app.providers.resolution import resolve_provider_context
from app.providers.services import ProviderService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models import Business

# Messaging adapters that delegate SMS to the telephony CPaaS.
_NON_CPAAS_MESSAGING = frozenset({"composite", "local", "resend", "mock"})


def _env_override(setting_name: str) -> str | None:
    settings = get_settings()
    raw = getattr(settings, setting_name, None)
    if raw is None:
        return None
    value = str(raw).lower().strip()
    if value in ("", "auto"):
        return None
    return value


def resolve_provider_name(
    service: ProviderService,
    *,
    business: Business | None = None,
    db: Session | None = None,
    env_setting: str | None = None,
    resource_provider: str | None = None,
) -> str:
    """Resolve a provider name using env override, business context, then country config."""
    env = _env_override(env_setting) if env_setting else None
    if env:
        return env

    country: str | None = None
    overrides: dict[str, str] = {}
    if business is not None:
        country, overrides = resolve_provider_context(business, db, resource_provider=resource_provider)

    return get_provider_configuration().resolve(
        service,
        country=country,
        business_overrides=overrides,
        resource_provider=resource_provider,
    )


def resolve_telephony_adapter_name(
    *,
    business: Business | None = None,
    db: Session | None = None,
) -> str:
    """Voice call control / webhook CPaaS — driven by telephony service config."""
    return resolve_provider_name(
        ProviderService.TELEPHONY,
        business=business,
        db=db,
        env_setting="voice_provider",
    )


def resolve_sms_cpaas_name(
    *,
    business: Business | None = None,
    db: Session | None = None,
) -> str:
    """Underlying SMS CPaaS for inbound webhooks and non-composite outbound SMS."""
    messaging = resolve_provider_name(
        ProviderService.MESSAGING,
        business=business,
        db=db,
        env_setting="sms_provider",
    )
    if messaging in _NON_CPAAS_MESSAGING:
        return resolve_provider_name(
            ProviderService.TELEPHONY,
            business=business,
            db=db,
            env_setting="voice_provider",
        )
    return messaging


def resolve_sms_outbound_name(
    *,
    business: Business | None = None,
    db: Session | None = None,
) -> str:
    """Outbound SMS sender — ``dev`` env forces the dev adapter; otherwise CPaaS from config."""
    env = _env_override("sms_provider")
    if env == "dev":
        return "dev"
    return resolve_sms_cpaas_name(business=business, db=db)


def adapter_failover_chain(service: ProviderService, primary: str) -> list[str]:
    return get_provider_configuration().failover_chain(service, primary)
