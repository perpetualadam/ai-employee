"""Specification: provider registry, factory, configuration, and failover."""

from __future__ import annotations

import unittest

from app.providers.configuration import ProviderConfiguration
from app.providers.factory import ProviderFactory
from app.providers.mocks import MockTelephonyProvider
from app.providers.registry import ProviderRegistry, reset_registry
from app.providers.services import ProviderService


class ProviderConfigurationSpecification(unittest.TestCase):
    def test_gb_resolves_from_country_config(self) -> None:
        config = ProviderConfiguration()
        name = config.resolve(ProviderService.TELEPHONY, country="GB")
        self.assertEqual(name, "telnyx")

    def test_us_voice_defaults_to_openai(self) -> None:
        config = ProviderConfiguration()
        name = config.resolve(ProviderService.VOICE, country="US")
        self.assertEqual(name, "openai")

    def test_business_override_wins(self) -> None:
        config = ProviderConfiguration()
        name = config.resolve(
            ProviderService.TELEPHONY,
            country="US",
            business_overrides={"telephony": "mock"},
        )
        self.assertEqual(name, "mock")

    def test_resource_provider_wins_over_country(self) -> None:
        config = ProviderConfiguration()
        name = config.resolve(
            ProviderService.TELEPHONY,
            country="US",
            resource_provider="twilio",
        )
        self.assertEqual(name, "twilio")


class ProviderRegistrySpecification(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = reset_registry(for_tests=True)

    def test_register_and_get(self) -> None:
        self.assertIn("mock", self.registry.list_registered(ProviderService.TELEPHONY))
        provider = self.registry.get(ProviderService.TELEPHONY, "mock")
        self.assertEqual(provider.provider_name, "mock")

    def test_get_for_country_uses_configuration(self) -> None:
        provider = self.registry.get_for_country(ProviderService.VOICE, "GB")
        self.assertEqual(provider.provider_name, "mock")

    def test_health_check_reports_all_services(self) -> None:
        report = self.registry.health_check()
        self.assertIn("telephony", report)
        self.assertIn("mock", report["telephony"])

    def test_failover_selects_next_healthy_provider(self) -> None:
        unhealthy = MockTelephonyProvider(name="primary", configured=False)
        healthy = MockTelephonyProvider(name="backup", configured=True)
        reg = ProviderRegistry(
            ProviderConfiguration(
                {
                    "defaults": {"telephony": "primary"},
                    "countries": {},
                    "failover": {"telephony": ["primary", "backup"]},
                }
            )
        )
        reg.register(ProviderService.TELEPHONY, unhealthy)
        reg.register(ProviderService.TELEPHONY, healthy)
        selected = reg.get_with_failover(ProviderService.TELEPHONY, "primary")
        self.assertEqual(selected.provider_name, "backup")


class ProviderFactorySpecification(unittest.TestCase):
    def setUp(self) -> None:
        reset_registry(for_tests=True)

    def test_factory_resolves_by_country(self) -> None:
        factory = ProviderFactory.instance()
        numbers = factory.get_number_provider(country="US")
        self.assertEqual(numbers.provider_name, "mock")

    def test_factory_resolves_gb_voice_from_country_config(self) -> None:
        factory = ProviderFactory.instance()
        voice = factory.get_voice_provider(country="GB")
        self.assertEqual(voice.provider_name, "mock")

    def test_factory_health_check(self) -> None:
        factory = ProviderFactory.instance()
        health = factory.health_check()
        self.assertIn("numbers", health)


if __name__ == "__main__":
    unittest.main()
