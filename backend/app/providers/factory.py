"""Provider factory — business services resolve providers here, never by vendor name."""

from __future__ import annotations

import app.providers.bootstrap  # noqa: F401 — ensure adapters are registered

from typing import TYPE_CHECKING

from app.providers.messaging import MessagingProvider
from app.providers.number_provisioning import NumberProvisioningProvider
from app.providers.regulatory import RegulatoryProvider
from app.providers.capabilities import Capability
from app.providers.registry import ProviderRegistry, get_registry
from app.providers.resolution import resolve_provider_context
from app.providers.services import ProviderService
from app.providers.storage import StorageProvider
from app.providers.telephony import TelephonyProvider
from app.providers.voice import VoiceProvider
from app.services.call_service import CallService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models import Business


class ProviderFactory:
    """Resolves the correct provider instance from configuration and business context."""

    def __init__(self, registry: ProviderRegistry | None = None) -> None:
        self._registry = registry or get_registry()

    @classmethod
    def instance(cls) -> ProviderFactory:
        return cls()

    def _context(
        self,
        business: Business | None,
        db: Session | None,
        *,
        resource_provider: str | None = None,
    ) -> tuple[str | None, dict[str, str]]:
        if business is None:
            return None, {}
        return resolve_provider_context(business, db, resource_provider=resource_provider)

    _KNOWN_CPAAS = frozenset(
        {
            "telnyx",
            "twilio",
            "vonage",
            "plivo",
            "signalwire",
            "voipms",
            "bandwidth",
            "sinch",
            "messagebird",
        }
    )

    @classmethod
    def _env_cpaas_override(cls) -> str | None:
        """Honor VOICE_PROVIDER / TELEPHONY_PROVIDER so Twilio/Vonage can be primary."""
        from app.integrations.provider_resolution import _env_override

        for setting in ("voice_provider", "telephony_provider"):
            value = _env_override(setting)
            if value and value in cls._KNOWN_CPAAS:
                return value
        return None

    @classmethod
    def _env_service_override(cls, setting_name: str) -> str | None:
        from app.integrations.provider_resolution import _env_override

        value = _env_override(setting_name)
        if value and value in cls._KNOWN_CPAAS:
            return value
        return None

    def get_telephony_provider(
        self,
        country: str | None = None,
        *,
        business: Business | None = None,
        db: Session | None = None,
        resource_provider: str | None = None,
    ) -> TelephonyProvider:
        resolved_country, overrides = self._context(business, db, resource_provider=resource_provider)
        provider = self._registry.get_default(
            ProviderService.TELEPHONY,
            country=country or resolved_country,
            business_overrides=overrides,
            resource_provider=resource_provider or self._env_cpaas_override(),
        )
        return provider  # type: ignore[return-value]

    def get_number_provider(
        self,
        country: str | None = None,
        *,
        business: Business | None = None,
        db: Session | None = None,
        number_type: str | None = None,
        required_capabilities: tuple[str, ...] = (),
    ) -> NumberProvisioningProvider:
        resolved_country, overrides = self._context(business, db)
        provider = self._registry.select(
            ProviderService.NUMBERS,
            country=country or resolved_country,
            business_overrides=overrides,
            number_type=number_type,
            required_capabilities=required_capabilities,
            resource_provider=(
                self._env_service_override("number_provisioning_provider")
                or self._env_cpaas_override()
            ),
        )
        return provider  # type: ignore[return-value]

    def get_regulatory_provider(
        self,
        country: str | None = None,
        *,
        business: Business | None = None,
        db: Session | None = None,
    ) -> RegulatoryProvider:
        resolved_country, overrides = self._context(business, db)
        provider = self._registry.get_default(
            ProviderService.REGULATORY,
            country=country or resolved_country,
            business_overrides=overrides,
            resource_provider=(
                self._env_service_override("regulatory_provider")
                or self._env_cpaas_override()
            ),
        )
        return provider  # type: ignore[return-value]

    def get_voice_provider(
        self,
        country: str | None = None,
        *,
        business: Business | None = None,
        db: Session | None = None,
    ) -> VoiceProvider:
        resolved_country, overrides = self._context(business, db)
        provider = self._registry.get_default(
            ProviderService.VOICE,
            country=country or resolved_country,
            business_overrides=overrides,
        )
        return provider  # type: ignore[return-value]

    def get_messaging_provider(
        self,
        country: str | None = None,
        *,
        business: Business | None = None,
        db: Session | None = None,
        resource_provider: str | None = None,
        required_capabilities: tuple[str, ...] = (),
        exclude_simulated: bool = False,
    ) -> MessagingProvider:
        resolved_country, overrides = self._context(business, db, resource_provider=resource_provider)
        provider = self._registry.select(
            ProviderService.MESSAGING,
            country=country or resolved_country,
            business_overrides=overrides,
            resource_provider=resource_provider,
            required_capabilities=required_capabilities,
            exclude_simulated=exclude_simulated,
        )
        return provider  # type: ignore[return-value]

    def get_messaging_provider_for_capability(
        self,
        capability: str,
        *,
        country: str | None = None,
        business: Business | None = None,
        db: Session | None = None,
    ) -> MessagingProvider:
        return self.get_messaging_provider(
            country,
            business=business,
            db=db,
            required_capabilities=(capability,),
        )

    def get_storage_provider(self) -> StorageProvider:
        provider = self._registry.get_default(ProviderService.STORAGE)
        return provider  # type: ignore[return-value]

    def get_call_service(
        self,
        *,
        business: Business | None = None,
        db: Session | None = None,
        resource_provider: str | None = None,
    ) -> CallService:
        telephony = self.get_telephony_provider(
            business=business,
            db=db,
            resource_provider=resource_provider,
        )
        return CallService(telephony)

    def health_check(self) -> dict:
        return {
            service: {name: health.__dict__ for name, health in providers.items()}
            for service, providers in self._registry.health_check().items()
        }


# Module-level convenience API
def get_factory() -> ProviderFactory:
    return ProviderFactory.instance()


def get_telephony_provider(
    country: str | None = None,
    *,
    business: Business | None = None,
    db: Session | None = None,
    resource_provider: str | None = None,
) -> TelephonyProvider:
    return get_factory().get_telephony_provider(
        country,
        business=business,
        db=db,
        resource_provider=resource_provider,
    )


def get_number_provisioning_provider(
    country: str | None = None,
    *,
    business: Business | None = None,
    db: Session | None = None,
) -> NumberProvisioningProvider:
    return get_factory().get_number_provider(country, business=business, db=db)


def get_regulatory_provider(
    country: str | None = None,
    *,
    business: Business | None = None,
    db: Session | None = None,
) -> RegulatoryProvider:
    return get_factory().get_regulatory_provider(country, business=business, db=db)


def get_voice_ai_provider(
    country: str | None = None,
    *,
    business: Business | None = None,
    db: Session | None = None,
) -> VoiceProvider:
    return get_factory().get_voice_provider(country, business=business, db=db)


def get_messaging_provider(
    country: str | None = None,
    *,
    business: Business | None = None,
    db: Session | None = None,
    resource_provider: str | None = None,
) -> MessagingProvider:
    return get_factory().get_messaging_provider(
        country,
        business=business,
        db=db,
        resource_provider=resource_provider,
    )


def get_storage_provider() -> StorageProvider:
    return get_factory().get_storage_provider()


def get_call_service(
    *,
    business: Business | None = None,
    db: Session | None = None,
    resource_provider: str | None = None,
) -> CallService:
    return get_factory().get_call_service(
        business=business,
        db=db,
        resource_provider=resource_provider,
    )


def list_provider_registry() -> dict[str, list[str]]:
    registry = get_registry()
    return {service.value: registry.list_registered(service) for service in ProviderService}
