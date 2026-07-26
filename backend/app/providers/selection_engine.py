"""Provider selection — capability, country, priority, health, and failover aware."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Iterable

from app.providers.base import BaseProvider
from app.providers.capabilities import ProviderCapabilities
from app.providers.configuration import ProviderConfiguration
from app.providers.exceptions import CapabilityNotSupportedError, ProviderUnavailableError
from app.providers.health import ProviderHealth
from app.providers.metrics import get_provider_metrics
from app.providers.services import ProviderService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SelectionCriteria:
    service: ProviderService
    country: str | None = None
    required_capabilities: frozenset[str] = field(default_factory=frozenset)
    number_type: str | None = None
    business_overrides: dict[str, str] | None = None
    resource_provider: str | None = None
    require_healthy: bool = True
    exclude_simulated: bool = False


class ProviderSelectionEngine:
    """Selects the optimal registered provider for a request context."""

    def __init__(
        self,
        registry: object,
        configuration: ProviderConfiguration | None = None,
    ) -> None:
        self._registry = registry
        self._configuration = configuration or registry._configuration  # type: ignore[attr-defined]

    def select(self, criteria: SelectionCriteria) -> BaseProvider:
        if criteria.resource_provider:
            provider = self._registry.get(criteria.service, criteria.resource_provider)  # type: ignore[attr-defined]
            self._validate_provider(provider, criteria, strict_country=False)
            return provider

        if criteria.business_overrides and criteria.service.value in (criteria.business_overrides or {}):
            override_name = criteria.business_overrides[criteria.service.value]
            provider = self._registry.get(criteria.service, override_name)  # type: ignore[attr-defined]
            try:
                self._validate_provider(provider, criteria)
                if not criteria.require_healthy or self._is_healthy(provider, criteria.service):
                    return provider
            except CapabilityNotSupportedError:
                pass

        candidates = self._ordered_candidates(criteria)
        last_health: ProviderHealth | None = None
        metrics = get_provider_metrics()

        for index, name in enumerate(candidates):
            provider = self._registry._providers[criteria.service].get(name)  # type: ignore[attr-defined]
            if provider is None:
                continue
            try:
                self._validate_provider(provider, criteria)
            except CapabilityNotSupportedError:
                continue

            health = provider.health(service=criteria.service.value)
            metrics.record_health_check(provider.provider_name, criteria.service.value)
            if criteria.require_healthy and not health.healthy:
                last_health = health
                continue

            if index > 0:
                metrics.record_retry(candidates[0], criteria.service.value)
                logger.warning(
                    "Failover selected provider",
                    extra={
                        "service": criteria.service.value,
                        "primary": candidates[0],
                        "selected": name,
                    },
                )
            return provider

        if criteria.required_capabilities:
            raise CapabilityNotSupportedError(
                service=criteria.service.value,
                required=sorted(criteria.required_capabilities),
                country=criteria.country,
            )

        detail = last_health.status if last_health else "not registered"
        raise ProviderUnavailableError(
            f"No healthy provider for service '{criteria.service.value}' "
            f"(tried: {', '.join(candidates)} — {detail})",
        )

    def _ordered_candidates(self, criteria: SelectionCriteria) -> list[str]:
        primary = self._configuration.resolve(
            criteria.service,
            country=criteria.country,
            business_overrides=criteria.business_overrides,
        )
        priority = self._configuration.priority_chain(
            criteria.service,
            criteria.country,
            primary,
        )
        registered = sorted(self._registry._providers[criteria.service].keys())  # type: ignore[attr-defined]
        ordered: list[str] = []
        for name in [*priority, *registered]:
            if name not in ordered:
                ordered.append(name)
        return ordered

    def _validate_provider(
        self,
        provider: BaseProvider,
        criteria: SelectionCriteria,
        *,
        strict_country: bool = True,
    ) -> None:
        caps = provider.get_capabilities()
        if criteria.exclude_simulated and caps.simulated:
            raise CapabilityNotSupportedError(
                service=criteria.service.value,
                required=sorted(criteria.required_capabilities),
                country=criteria.country,
                provider=provider.provider_name,
            )
        if criteria.required_capabilities and not caps.supports(*criteria.required_capabilities):
            raise CapabilityNotSupportedError(
                service=criteria.service.value,
                required=sorted(criteria.required_capabilities),
                country=criteria.country,
                provider=provider.provider_name,
            )
        if strict_country and criteria.country and not caps.supports_country(criteria.country):
            raise CapabilityNotSupportedError(
                service=criteria.service.value,
                required=[f"country:{criteria.country}"],
                country=criteria.country,
                provider=provider.provider_name,
            )
        if criteria.number_type and not caps.supports_number_type(criteria.number_type):
            raise CapabilityNotSupportedError(
                service=criteria.service.value,
                required=[f"number_type:{criteria.number_type}"],
                country=criteria.country,
                provider=provider.provider_name,
            )

    @staticmethod
    def _is_healthy(provider: BaseProvider, service: ProviderService) -> bool:
        return provider.health(service=service.value).healthy

    def list_capable(
        self,
        service: ProviderService,
        *,
        required: Iterable[str] = (),
        country: str | None = None,
    ) -> list[tuple[BaseProvider, ProviderCapabilities]]:
        required_set = frozenset(required)
        matches: list[tuple[BaseProvider, ProviderCapabilities]] = []
        for provider in self._registry._providers[service].values():  # type: ignore[attr-defined]
            caps = provider.get_capabilities()
            if required_set and not caps.supports(*required_set):
                continue
            if country and not caps.supports_country(country):
                continue
            matches.append((provider, caps))
        return matches
