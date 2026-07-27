"""Plivo production parity with Telnyx — telephony, SMS, numbers, regulatory, markup."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from app.providers.bootstrap import bootstrap_providers
from app.providers.configuration import ProviderConfiguration
from app.providers.factory import ProviderFactory
from app.providers.plivo.number_provisioning import PlivoNumberProvisioningProvider
from app.providers.plivo.regulatory import PlivoRegulatoryProvider
from app.providers.plivo.telephony import PlivoTelephonyProvider
from app.providers.registry import ProviderRegistry
from app.services.messaging.plivo_sms import PlivoSmsProvider
from app.voice.plivo_webhook_auth import validate_plivo_signature_v2
from app.voice.voice_markup import PlivoVoiceMarkup


class PlivoParitySpecification(unittest.TestCase):
    def test_telephony_is_configured_from_credentials(self) -> None:
        provider = PlivoTelephonyProvider()
        with patch("app.voice.plivo_client.is_plivo_configured", return_value=True):
            self.assertTrue(provider.is_configured())

    def test_answer_call_pushes_plivo_xml(self) -> None:
        provider = PlivoTelephonyProvider()
        with patch("app.voice.plivo_client.update_call_xml") as update:
            asyncio.run(provider.answer_call("uuid-1", {"markup": "<Response><Hangup/></Response>"}))
            update.assert_called_once_with("uuid-1", "<Response><Hangup/></Response>")

    def test_outbound_end_sms_and_transfer(self) -> None:
        provider = PlivoTelephonyProvider()
        with patch("app.voice.plivo_client.is_outbound_call_configured", return_value=True):
            with patch(
                "app.voice.plivo_client.initiate_call",
                return_value={"id": "req-1", "call_control_id": "req-1"},
            ):
                result = asyncio.run(
                    provider.outbound_call(
                        from_number="+15550001111",
                        to_number="+15550002222",
                        webhook_url="https://example.com/voice",
                    )
                )
        self.assertEqual(result.external_id, "req-1")

        with patch("app.voice.plivo_client.end_call") as end:
            asyncio.run(provider.end_call("uuid-end"))
            end.assert_called_once_with("uuid-end")

        with patch("app.voice.plivo_client.send_sms", return_value={"id": "msg-1"}):
            sms = asyncio.run(
                provider.send_sms(from_number="+15550001111", to_number="+15550003333", text="hi")
            )
        self.assertEqual(sms.external_id, "msg-1")

        with patch("app.voice.plivo_client.update_call_xml") as update:
            with patch(
                "app.integrations.adapters.plivo_adapters.PlivoVoiceCallControl.is_configured",
                return_value=True,
            ):
                asyncio.run(provider.transfer_call("uuid-xfer", "+15550004444"))
                update.assert_called_once()
                self.assertIn("<Dial>", update.call_args[0][1])

    def test_sms_provider_sends_via_client(self) -> None:
        sms = PlivoSmsProvider()
        with patch("app.voice.plivo_client.is_plivo_configured", return_value=True):
            with patch(
                "app.services.messaging.plivo_sms.get_settings",
                return_value=MagicMock(plivo_phone_number="+15550001111"),
            ):
                with patch("app.voice.plivo_client.send_sms", return_value={"id": "m9"}) as send:
                    result = sms.send_sms("+15550001111", "+15550002222", "ping")
        self.assertTrue(result["sent"])
        send.assert_called_once()

    def test_number_provisioning_search_purchase(self) -> None:
        provider = PlivoNumberProvisioningProvider()
        with patch("app.voice.plivo_client.is_phone_provisioning_configured", return_value=True):
            with patch(
                "app.voice.plivo_client.search_available_phone_numbers",
                return_value=[{"phone_number": "+14155550100", "region": "CA", "cost": "1"}],
            ):
                found = provider.search_numbers("US", prefix="415")
            self.assertEqual(found[0]["phone_number"], "+14155550100")
            with patch(
                "app.voice.plivo_client.create_number_order",
                return_value={"id": "14155550100", "status": "success"},
            ):
                order = provider.purchase_number("+14155550100")
            self.assertEqual(order.external_id, "14155550100")

    def test_regulatory_compliance_application(self) -> None:
        provider = PlivoRegulatoryProvider()
        with patch("app.voice.plivo_client.is_plivo_configured", return_value=True):
            with patch(
                "app.voice.plivo_client.create_end_user",
                return_value={"end_user_id": "eu-1"},
            ):
                eu = provider.create_end_user(business_id="biz", payload={"friendly_name": "Acme"})
            self.assertEqual(eu.external_id, "eu-1")
            with patch(
                "app.voice.plivo_client.create_compliance_application",
                return_value={"compliance_application_uuid": "ca-1"},
            ):
                bundle = provider.create_regulatory_bundle(country_code="US", end_user_id="eu-1")
            self.assertEqual(bundle.external_id, "ca-1")

    def test_plivo_markup_is_getinput_not_twiml_gather(self) -> None:
        markup = PlivoVoiceMarkup()
        xml = markup.build_say_and_gather(
            "How can I help?",
            "https://api.example.com",
            "call-1",
            call_sid="uuid-1",
            country="US",
        )
        self.assertIn("<GetInput", xml)
        self.assertIn('inputType="speech"', xml)
        self.assertNotIn("<Gather", xml)

    def test_signature_v2_validation(self) -> None:
        import base64
        import hashlib
        import hmac

        uri = "https://example.com/voice"
        nonce = "12345"
        token = "secret"
        digest = hmac.new(token.encode(), f"{uri}{nonce}".encode(), hashlib.sha256).digest()
        signature = base64.b64encode(digest).decode()
        self.assertTrue(validate_plivo_signature_v2(uri, nonce, signature, token))
        self.assertFalse(validate_plivo_signature_v2(uri, nonce, "bad", token))

    @patch("app.providers.factory.ProviderFactory._env_cpaas_override", return_value="plivo")
    @patch("app.config.get_settings")
    def test_factory_honors_voice_provider_env_for_plivo(self, settings_mock, _env) -> None:
        settings_mock.return_value = MagicMock(
            plivo_auth_id="MA...",
            plivo_auth_token="token",
            voice_provider="plivo",
        )
        config = ProviderConfiguration(
            {
                "defaults": {"telephony": "telnyx"},
                "countries": {},
                "failover": {"telephony": ["telnyx", "plivo"]},
            }
        )
        registry = ProviderRegistry(config)
        bootstrap_providers(registry)
        factory = ProviderFactory(registry)
        self.assertIsInstance(factory.get_telephony_provider(), PlivoTelephonyProvider)


if __name__ == "__main__":
    unittest.main()
