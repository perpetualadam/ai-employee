"""Specification: Twilio and Vonage stub providers prove extensibility."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.integrations.adapters.twilio_stubs import TwilioVoiceCallControl
from app.integrations.registry import get_voice_call_control, list_registered_integrations
from app.providers.bootstrap import bootstrap_integration_adapters, bootstrap_providers
from app.providers.configuration import ProviderConfiguration
from app.providers.factory import ProviderFactory
from app.providers.registry import ProviderRegistry
from app.providers.services import ProviderService
from app.providers.twilio.telephony import TwilioTelephonyProvider
from app.providers.vonage.telephony import VonageTelephonyProvider


class ProviderStubRegistrationSpecification(unittest.TestCase):
    def test_bootstrap_registers_twilio_and_vonage(self) -> None:
        registry = ProviderRegistry()
        bootstrap_providers(registry)

        for service in (
            ProviderService.TELEPHONY,
            ProviderService.NUMBERS,
            ProviderService.REGULATORY,
        ):
            registered = registry.list_registered(service)
            self.assertIn("telnyx", registered)
            self.assertIn("twilio", registered)
            self.assertIn("vonage", registered)

    @patch("app.config.get_settings")
    def test_factory_resolves_twilio_from_business_override(self, settings_mock) -> None:
        settings_mock.return_value = MagicMock(twilio_account_sid="AC-test", twilio_auth_token="secret")
        config = ProviderConfiguration(
            {
                "defaults": {"telephony": "telnyx", "numbers": "telnyx", "regulatory": "telnyx"},
                "countries": {"US": {"telephony": "telnyx"}},
                "failover": {"telephony": ["telnyx", "twilio"]},
            }
        )
        registry = ProviderRegistry(config)
        bootstrap_providers(registry)
        factory = ProviderFactory(registry)
        business = MagicMock(country="US", provider_config={"telephony": "twilio"})

        provider = factory.get_telephony_provider(business=business)

        self.assertIsInstance(provider, TwilioTelephonyProvider)

    @patch("app.config.get_settings")
    def test_factory_resolves_vonage_from_resource_provider(self, settings_mock) -> None:
        settings_mock.return_value = MagicMock(vonage_api_key="key", vonage_api_secret="secret")
        config = ProviderConfiguration(
            {
                "defaults": {"telephony": "telnyx"},
                "countries": {},
                "failover": {"telephony": ["telnyx", "vonage"]},
            }
        )
        registry = ProviderRegistry(config)
        bootstrap_providers(registry)
        factory = ProviderFactory(registry)

        provider = factory.get_telephony_provider(resource_provider="vonage")

        self.assertIsInstance(provider, VonageTelephonyProvider)

    @patch("app.integrations.provider_resolution.get_settings")
    @patch("app.integrations.provider_resolution.get_provider_configuration")
    def test_integration_registry_lists_twilio_adapters(
        self,
        config_mock,
        settings_mock,
    ) -> None:
        bootstrap_integration_adapters()
        config_mock.return_value = ProviderConfiguration(
            {
                "defaults": {"telephony": "twilio"},
                "countries": {},
                "failover": {"telephony": ["twilio"]},
            }
        )
        settings_mock.return_value = MagicMock(
            voice_provider="auto",
            sms_provider="auto",
            twilio_account_sid="AC-test",
            twilio_auth_token="secret",
        )
        business = MagicMock(country="US", provider_config={"telephony": "twilio"})

        control = get_voice_call_control(business=business)

        self.assertIsInstance(control, TwilioVoiceCallControl)
        self.assertEqual(control.provider_name, "twilio")

    def test_list_registered_integrations_includes_stubs(self) -> None:
        bootstrap_integration_adapters()
        registered = list_registered_integrations()

        self.assertIn("twilio", registered["voice"])
        self.assertIn("vonage", registered["voice"])
        self.assertIn("twilio", registered["sms_outbound"])
        self.assertIn("vonage", registered["sms_outbound"])


if __name__ == "__main__":
    unittest.main()
