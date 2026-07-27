"""VoIP.ms REST API parity — SMS, DID provisioning, SIP routing."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from app.providers.bootstrap import bootstrap_providers
from app.providers.configuration import ProviderConfiguration
from app.providers.exceptions import ProviderUnavailableError
from app.providers.factory import ProviderFactory
from app.providers.registry import ProviderRegistry
from app.providers.voipms.number_provisioning import VoipMsNumberProvisioningProvider
from app.providers.voipms.telephony import VoipMsTelephonyProvider
from app.services.messaging.voipms_sms import VoipMsSmsProvider
from app.voice.voice_markup import VoipMsVoiceMarkup


class VoipMsParitySpecification(unittest.TestCase):
    def test_configured_from_api_credentials(self) -> None:
        provider = VoipMsTelephonyProvider()
        with patch("app.voice.voipms_client.is_voipms_configured", return_value=True):
            self.assertTrue(provider.is_configured())

    def test_send_sms_and_receive_payload(self) -> None:
        provider = VoipMsTelephonyProvider()
        with patch("app.voice.voipms_client.send_sms", return_value={"id": "99"}):
            result = asyncio.run(
                provider.send_sms(from_number="5551234567", to_number="5557654321", text="hi")
            )
        self.assertEqual(result.external_id, "99")

        parsed = asyncio.run(
            provider.receive_sms({"from": "5551111", "to": "5552222", "message": "hello"})
        )
        self.assertEqual(parsed["text"], "hello")

    def test_outbound_call_unavailable_by_design(self) -> None:
        provider = VoipMsTelephonyProvider()
        with self.assertRaises(ProviderUnavailableError):
            asyncio.run(
                provider.outbound_call(
                    from_number="+1",
                    to_number="+2",
                    webhook_url="https://example.com",
                )
            )

    def test_transfer_updates_did_routing(self) -> None:
        provider = VoipMsTelephonyProvider()
        with patch(
            "app.providers.voipms.telephony.get_settings",
            return_value=MagicMock(voipms_did="5551234567", voipms_phone_number="", voipms_routing=""),
        ):
            with patch("app.voice.voipms_client.set_did_routing") as route:
                asyncio.run(provider.transfer_call("call", "5559999999"))
                route.assert_called_once()

    def test_sms_provider_and_numbers(self) -> None:
        sms = VoipMsSmsProvider()
        with patch("app.voice.voipms_client.is_voipms_configured", return_value=True):
            with patch(
                "app.services.messaging.voipms_sms.get_settings",
                return_value=MagicMock(voipms_did="5551234567", voipms_phone_number=""),
            ):
                with patch("app.voice.voipms_client.send_sms", return_value={"id": "1"}):
                    self.assertTrue(sms.send_sms("", "5557654321", "x")["sent"])

        numbers = VoipMsNumberProvisioningProvider()
        with patch("app.voice.voipms_client.is_phone_provisioning_configured", return_value=True):
            with patch(
                "app.voice.voipms_client.search_available_phone_numbers",
                return_value=[{"phone_number": "+15551212", "region": "NY", "cost": "1"}],
            ):
                found = numbers.search_numbers("US", prefix="212")
            self.assertEqual(found[0]["phone_number"], "+15551212")
            with patch(
                "app.voice.voipms_client.create_number_order",
                return_value={"id": "5551212", "status": "success"},
            ):
                order = numbers.purchase_number("+15551212")
            self.assertEqual(order.external_id, "5551212")

    def test_markup_returns_ok_for_callbacks(self) -> None:
        markup = VoipMsVoiceMarkup()
        self.assertEqual(markup.build_empty(), "ok")
        self.assertEqual(markup.content_type, "text/plain")

    @patch("app.providers.factory.ProviderFactory._env_cpaas_override", return_value="voipms")
    @patch("app.config.get_settings")
    def test_factory_honors_voice_provider_env(self, settings_mock, _env) -> None:
        settings_mock.return_value = MagicMock(
            voipms_api_username="user@example.com",
            voipms_api_password="secret",
            voice_provider="voipms",
        )
        config = ProviderConfiguration(
            {
                "defaults": {"telephony": "telnyx"},
                "countries": {},
                "failover": {"telephony": ["telnyx", "voipms"]},
            }
        )
        registry = ProviderRegistry(config)
        bootstrap_providers(registry)
        factory = ProviderFactory(registry)
        self.assertIsInstance(factory.get_telephony_provider(), VoipMsTelephonyProvider)


if __name__ == "__main__":
    unittest.main()
