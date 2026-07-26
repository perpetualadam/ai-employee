"""Specification: provider capabilities and selection engine."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.providers.capabilities import Capability, ProviderCapabilities
from app.providers.configuration import ProviderConfiguration
from app.providers.exceptions import CapabilityNotSupportedError
from app.providers.registry import ProviderRegistry, reset_registry
from app.providers.selection_engine import ProviderSelectionEngine, SelectionCriteria
from app.providers.services import ProviderService


class ProviderCapabilitiesSpecification(unittest.TestCase):
    def test_supports_required_features(self) -> None:
        caps = ProviderCapabilities(provider_name="demo", sms=True, voice=True, whatsapp=False)
        self.assertTrue(caps.supports(Capability.SMS, Capability.VOICE))
        self.assertFalse(caps.supports(Capability.WHATSAPP))

    def test_supports_country_with_glob(self) -> None:
        caps = ProviderCapabilities(provider_name="demo", country_support=frozenset({"GB", "US"}))
        self.assertTrue(caps.supports_country("GB"))
        self.assertFalse(caps.supports_country("DE"))

    def test_supported_features_lists_enabled_capabilities(self) -> None:
        caps = ProviderCapabilities(provider_name="demo", sms=True, email=True)
        self.assertIn(Capability.SMS, caps.supported_features())
        self.assertIn(Capability.EMAIL, caps.supported_features())


class ProviderSelectionEngineSpecification(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = reset_registry(for_tests=True)

    def test_selects_mock_provider_with_sms_capability(self) -> None:
        engine = ProviderSelectionEngine(self.registry)
        provider = engine.select(
            SelectionCriteria(
                service=ProviderService.MESSAGING,
                country="US",
                required_capabilities=frozenset({Capability.SMS}),
            ),
        )
        self.assertTrue(provider.get_capabilities().supports(Capability.SMS))

    def test_us_priority_prefers_configured_order(self) -> None:
        config = ProviderConfiguration(
            {
                "defaults": {"telephony": "mock"},
                "countries": {"US": {"telephony": "mock"}},
                "priority": {"US": {"telephony": ["mock", "telnyx", "twilio"]}},
                "failover": {"telephony": ["mock"]},
            }
        )
        registry = ProviderRegistry(config)
        from app.providers.bootstrap import bootstrap_providers

        bootstrap_providers(registry)
        from app.providers.mocks import MockTelephonyProvider

        registry.register(ProviderService.TELEPHONY, MockTelephonyProvider())
        engine = ProviderSelectionEngine(registry)
        provider = engine.select(
            SelectionCriteria(service=ProviderService.TELEPHONY, country="US"),
        )
        self.assertEqual(provider.provider_name, "mock")

    def test_missing_capability_raises_when_unavailable(self) -> None:
        engine = ProviderSelectionEngine(self.registry)
        with self.assertRaises(CapabilityNotSupportedError):
            engine.select(
                SelectionCriteria(
                    service=ProviderService.MESSAGING,
                    country="US",
                    required_capabilities=frozenset({Capability.MMS}),
                ),
            )

    def test_resource_provider_wins_over_priority(self) -> None:
        engine = ProviderSelectionEngine(self.registry)
        provider = engine.select(
            SelectionCriteria(
                service=ProviderService.TELEPHONY,
                resource_provider="mock",
            ),
        )
        self.assertEqual(provider.provider_name, "mock")

    def test_registry_discover_includes_capabilities(self) -> None:
        discovered = self.registry.discover()
        self.assertTrue(any(entry["name"] == "mock" for entry in discovered))
        mock_entry = next(entry for entry in discovered if entry["name"] == "mock")
        self.assertIn("capabilities", mock_entry)


class NotificationCapabilitySpecification(unittest.TestCase):
    @patch("app.services.notification_service.get_sms_provider_for_business")
    def test_is_sms_functional_uses_capabilities_not_vendor_name(self, provider_mock) -> None:
        from app.services.notification_service import NotificationService

        provider = MagicMock()
        provider.provider_name = "any_vendor"
        provider.is_configured.return_value = True
        provider.get_capabilities.return_value = ProviderCapabilities(
            provider_name="any_vendor",
            sms=True,
            simulated=False,
        )
        provider_mock.return_value = provider

        business = MagicMock()
        business.id = "biz-1"
        business.phone_number = "+15551111111"
        service = NotificationService(MagicMock(), business)
        self.assertTrue(service.is_sms_functional())

    @patch("app.services.notification_service.get_sms_provider_for_business")
    def test_simulated_provider_is_not_functional(self, provider_mock) -> None:
        from app.services.notification_service import NotificationService

        provider = MagicMock()
        provider.get_capabilities.return_value = ProviderCapabilities(
            provider_name="dev",
            sms=True,
            simulated=True,
        )
        provider.is_configured.return_value = True
        provider_mock.return_value = provider

        business = MagicMock()
        business.id = "biz-1"
        business.phone_number = "+15551111111"
        service = NotificationService(MagicMock(), business)
        self.assertFalse(service.is_sms_functional())


if __name__ == "__main__":
    unittest.main()
