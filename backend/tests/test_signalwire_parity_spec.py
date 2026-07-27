"""SignalWire Compatibility API parity with Telnyx/Twilio."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from app.providers.bootstrap import bootstrap_providers
from app.providers.configuration import ProviderConfiguration
from app.providers.factory import ProviderFactory
from app.providers.registry import ProviderRegistry
from app.providers.signalwire.number_provisioning import SignalWireNumberProvisioningProvider
from app.providers.signalwire.telephony import SignalWireTelephonyProvider
from app.services.messaging.signalwire_sms import SignalWireSmsProvider
from app.voice.voice_markup import SignalWireVoiceMarkup


class SignalWireParitySpecification(unittest.TestCase):
    def test_configured_from_space_credentials(self) -> None:
        provider = SignalWireTelephonyProvider()
        with patch("app.voice.signalwire_client.is_signalwire_configured", return_value=True):
            self.assertTrue(provider.is_configured())

    def test_answer_outbound_end_sms_transfer(self) -> None:
        provider = SignalWireTelephonyProvider()
        with patch("app.voice.signalwire_client.update_call_cxml") as update:
            asyncio.run(provider.answer_call("CA1", {"markup": "<Response/>"}))
            update.assert_called_once_with("CA1", "<Response/>")

        with patch("app.voice.signalwire_client.is_outbound_call_configured", return_value=True):
            with patch(
                "app.voice.signalwire_client.initiate_call",
                return_value={"id": "CA-out", "call_control_id": "CA-out"},
            ):
                result = asyncio.run(
                    provider.outbound_call(
                        from_number="+15550001111",
                        to_number="+15550002222",
                        webhook_url="https://example.com/voice",
                    )
                )
        self.assertEqual(result.external_id, "CA-out")

        with patch("app.voice.signalwire_client.end_call") as end:
            asyncio.run(provider.end_call("CA-end"))
            end.assert_called_once()

        with patch("app.voice.signalwire_client.send_sms", return_value={"id": "SM1"}):
            sms = asyncio.run(
                provider.send_sms(from_number="+1", to_number="+2", text="hi")
            )
        self.assertEqual(sms.external_id, "SM1")

        with patch("app.voice.signalwire_client.update_call_cxml") as update:
            with patch(
                "app.integrations.adapters.signalwire_adapters.SignalWireVoiceCallControl.is_configured",
                return_value=True,
            ):
                asyncio.run(provider.transfer_call("CA-x", "+15550009999"))
                self.assertIn("<Dial", update.call_args[0][1])

    def test_sms_and_numbers(self) -> None:
        sms = SignalWireSmsProvider()
        with patch("app.voice.signalwire_client.is_signalwire_configured", return_value=True):
            with patch(
                "app.services.messaging.signalwire_sms.get_settings",
                return_value=MagicMock(signalwire_phone_number="+15550001111"),
            ):
                with patch(
                    "app.voice.signalwire_client.send_sms",
                    return_value={"id": "SM9"},
                ):
                    self.assertTrue(sms.send_sms("+1", "+2", "x")["sent"])

        numbers = SignalWireNumberProvisioningProvider()
        with patch("app.voice.signalwire_client.is_phone_provisioning_configured", return_value=True):
            with patch(
                "app.voice.signalwire_client.search_available_phone_numbers",
                return_value=[{"phone_number": "+15551212", "region": "NY", "cost": None}],
            ):
                found = numbers.search_numbers("US", prefix="212")
            self.assertEqual(found[0]["phone_number"], "+15551212")

    def test_markup_is_cxml_gather(self) -> None:
        markup = SignalWireVoiceMarkup()
        xml = markup.build_say_and_gather(
            "Hello",
            "https://api.example.com",
            "call-1",
            call_sid="CA1",
            country="US",
        )
        self.assertIn("<Gather", xml)
        self.assertEqual(markup.provider_name, "signalwire")

    @patch("app.providers.factory.ProviderFactory._env_cpaas_override", return_value="signalwire")
    @patch("app.config.get_settings")
    def test_factory_honors_voice_provider_env(self, settings_mock, _env) -> None:
        settings_mock.return_value = MagicMock(
            signalwire_project_id="proj",
            signalwire_api_token="token",
            signalwire_space_url="example.signalwire.com",
            voice_provider="signalwire",
        )
        config = ProviderConfiguration(
            {
                "defaults": {"telephony": "telnyx"},
                "countries": {},
                "failover": {"telephony": ["telnyx", "signalwire"]},
            }
        )
        registry = ProviderRegistry(config)
        bootstrap_providers(registry)
        factory = ProviderFactory(registry)
        self.assertIsInstance(factory.get_telephony_provider(), SignalWireTelephonyProvider)


if __name__ == "__main__":
    unittest.main()
