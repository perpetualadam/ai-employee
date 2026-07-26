"""Central provider registry — registration, lookup, health, and failover-ready resolution."""

from __future__ import annotations

import logging
from typing import Iterable, TypeVar

from app.providers.base import BaseProvider
from app.providers.configuration import ProviderConfiguration, get_provider_configuration
from app.providers.exceptions import ProviderUnavailableError
from app.providers.health import ProviderHealth
from app.providers.selection_engine import ProviderSelectionEngine, SelectionCriteria
from app.providers.services import ProviderService

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseProvider)

_global_registry: ProviderRegistry | None = None


class ProviderRegistry:
    """Registers provider instances and resolves them by capability, country, or failover chain."""

    def __init__(self, configuration: ProviderConfiguration | None = None) -> None:
        self._configuration = configuration or get_provider_configuration()
        self._providers: dict[ProviderService, dict[str, BaseProvider]] = {
            service: {} for service in ProviderService
        }
        self._selection = ProviderSelectionEngine(self, self._configuration)

    def register(self, service: ProviderService, provider: BaseProvider) -> None:
        name = provider.provider_name.lower()
        self._providers[service][name] = provider
        logger.debug("Registered provider", extra={"service": service.value, "provider": name})

    def list_registered(self, service: ProviderService) -> list[str]:
        return sorted(self._providers[service].keys())

    def get(self, service: ProviderService, name: str) -> BaseProvider:
        provider = self._providers[service].get(name.lower())
        if provider is None:
            raise ProviderUnavailableError(
                f"Provider '{name}' is not registered for service '{service.value}'",
            )
        return provider

    def get_typed(self, service: ProviderService, name: str, expected_type: type[T]) -> T:
        provider = self.get(service, name)
        if not isinstance(provider, expected_type):
            raise TypeError(
                f"Provider '{name}' for {service.value} is {type(provider).__name__}, "
                f"expected {expected_type.__name__}",
            )
        return provider

    def select(
        self,
        service: ProviderService,
        *,
        country: str | None = None,
        required_capabilities: Iterable[str] = (),
        number_type: str | None = None,
        business_overrides: dict[str, str] | None = None,
        resource_provider: str | None = None,
        require_healthy: bool = True,
        exclude_simulated: bool = False,
    ) -> BaseProvider:
        return self._selection.select(
            SelectionCriteria(
                service=service,
                country=country,
                required_capabilities=frozenset(required_capabilities),
                number_type=number_type,
                business_overrides=business_overrides,
                resource_provider=resource_provider,
                require_healthy=require_healthy,
                exclude_simulated=exclude_simulated,
            ),
        )

    def get_default(
        self,
        service: ProviderService,
        *,
        country: str | None = None,
        business_overrides: dict[str, str] | None = None,
        resource_provider: str | None = None,
        required_capabilities: Iterable[str] = (),
        number_type: str | None = None,
        exclude_simulated: bool = False,
    ) -> BaseProvider:
        return self.select(
            service,
            country=country,
            business_overrides=business_overrides,
            resource_provider=resource_provider,
            required_capabilities=required_capabilities,
            number_type=number_type,
            exclude_simulated=exclude_simulated,
        )

    def get_for_country(
        self,
        service: ProviderService,
        country: str,
        *,
        business_overrides: dict[str, str] | None = None,
        resource_provider: str | None = None,
        required_capabilities: Iterable[str] = (),
    ) -> BaseProvider:
        return self.get_default(
            service,
            country=country,
            business_overrides=business_overrides,
            resource_provider=resource_provider,
            required_capabilities=required_capabilities,
        )

    def get_with_failover(self, service: ProviderService, primary: str) -> BaseProvider:
        return self.select(
            service,
            business_overrides={service.value: primary},
            require_healthy=True,
        )

    def health_check(self) -> dict[str, dict[str, ProviderHealth]]:
        report: dict[str, dict[str, ProviderHealth]] = {}
        for service in ProviderService:
            report[service.value] = {}
            for name, provider in self._providers[service].items():
                report[service.value][name] = provider.health(service=service.value)
        return report

    def discover(self) -> list[dict]:
        """Installed providers with live capabilities for admin/monitoring."""
        discovered: list[dict] = []
        for service in ProviderService:
            for name, provider in sorted(self._providers[service].items()):
                caps = provider.get_capabilities()
                health = provider.health(service=service.value)
                discovered.append(
                    {
                        "service": service.value,
                        "name": name,
                        "configured": provider.is_configured(),
                        "capabilities": caps.to_dict(),
                        "health": health.__dict__,
                        "latency_ms": health.latency_ms,
                        "version": caps.provider_version,
                    },
                )
        return discovered


def get_registry() -> ProviderRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = ProviderRegistry()
    return _global_registry


def reset_registry(for_tests: bool = False) -> ProviderRegistry:
    """Replace global registry — used in tests."""
    global _global_registry
    from app.providers.bootstrap import bootstrap_providers
    from app.providers.configuration import ProviderConfiguration
    from app.providers.mocks import (
        MockMessagingProvider,
        MockNumberProvisioningProvider,
        MockRegulatoryProvider,
        MockStorageProvider,
        MockTelephonyProvider,
        MockVoiceProvider,
    )

    if for_tests:
        test_config = ProviderConfiguration(
            {
                "defaults": {
                    "telephony": "mock",
                    "numbers": "mock",
                    "regulatory": "mock",
                    "voice": "mock",
                    "messaging": "mock",
                    "storage": "mock",
                },
                "countries": {
                    "GB": {"telephony": "mock", "numbers": "mock", "voice": "mock"},
                    "US": {"telephony": "mock", "numbers": "mock", "voice": "mock"},
                },
                "failover": {
                    "telephony": ["mock"],
                    "numbers": ["mock"],
                    "regulatory": ["mock"],
                    "voice": ["mock"],
                    "messaging": ["mock"],
                    "storage": ["mock"],
                },
                "priority": {
                    "GB": {"telephony": ["mock"], "numbers": ["mock"]},
                    "US": {"telephony": ["mock"], "numbers": ["mock"]},
                },
            }
        )
        _global_registry = ProviderRegistry(test_config)
    else:
        _global_registry = ProviderRegistry()

    bootstrap_providers(_global_registry)
    if for_tests:
        reg = _global_registry
        reg.register(ProviderService.TELEPHONY, MockTelephonyProvider())
        reg.register(ProviderService.NUMBERS, MockNumberProvisioningProvider())
        reg.register(ProviderService.REGULATORY, MockRegulatoryProvider())
        reg.register(ProviderService.VOICE, MockVoiceProvider())
        reg.register(ProviderService.MESSAGING, MockMessagingProvider())
        reg.register(ProviderService.STORAGE, MockStorageProvider())
    return _global_registry
