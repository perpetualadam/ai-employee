"""Vonage production parity with Telnyx — telephony, SMS, numbers, regulatory, markup."""

from __future__ import annotations

import asyncio
import json
import unittest
from unittest.mock import MagicMock, patch

from app.providers.bootstrap import bootstrap_providers
from app.providers.configuration import ProviderConfiguration
from app.providers.factory import ProviderFactory
from app.providers.registry import ProviderRegistry
from app.providers.vonage.number_provisioning import VonageNumberProvisioningProvider
from app.providers.vonage.regulatory import VonageRegulatoryProvider
from app.providers.vonage.telephony import VonageTelephonyProvider
from app.services.messaging.vonage_sms import VonageSmsProvider
from app.voice.voice_markup import VonageVoiceMarkup


class VonageParitySpecification(unittest.TestCase):
    def test_telephony_is_configured_from_credentials(self) -> None:
        provider = VonageTelephonyProvider()
        with patch("app.voice.vonage_client.is_vonage_configured", return_value=True):
            self.assertTrue(provider.is_configured())
        with patch("app.voice.vonage_client.is_vonage_configured", return_value=False):
            self.assertFalse(provider.is_configured())

    def test_answer_call_accepts_markup_or_texml_alias(self) -> None:
        provider = VonageTelephonyProvider()
        ncco = '[{"action":"hangup"}]'
        with patch("app.voice.vonage_client.update_call_ncco") as update:
            asyncio.run(provider.answer_call("uuid-1", {"markup": ncco}))
            update.assert_called_once_with("uuid-1", ncco)

    def test_outbound_transfer_end_and_sms_use_real_client(self) -> None:
        provider = VonageTelephonyProvider()

        with patch("app.voice.vonage_client.is_outbound_call_configured", return_value=True):
            with patch(
                "app.voice.vonage_client.initiate_call",
                return_value={"id": "uuid-out", "call_control_id": "uuid-out"},
            ) as initiate:
                result = asyncio.run(
                    provider.outbound_call(
                        from_number="+15550001111",
                        to_number="+15550002222",
                        webhook_url="https://example.com/voice",
                    )
                )
        self.assertEqual(result.external_id, "uuid-out")
        initiate.assert_called_once()

        with patch("app.voice.vonage_client.end_call") as end:
            asyncio.run(provider.end_call("uuid-end"))
            end.assert_called_once_with("uuid-end")

        with patch(
            "app.voice.vonage_client.send_sms",
            return_value={"id": "msg-1", "raw": {}},
        ) as send:
            sms = asyncio.run(
                provider.send_sms(from_number="+15550001111", to_number="+15550003333", text="hi")
            )
        self.assertEqual(sms.external_id, "msg-1")
        send.assert_called_once()

        with patch("app.voice.vonage_client.update_call_ncco") as update:
            with patch(
                "app.integrations.adapters.vonage_stubs.VonageVoiceCallControl.is_configured",
                return_value=True,
            ):
                asyncio.run(provider.transfer_call("uuid-xfer", "+15550004444"))
                update.assert_called_once()
                payload = json.loads(update.call_args[0][1])
                self.assertEqual(payload[1]["action"], "connect")

    def test_receive_sms_normalizes_vonage_payload(self) -> None:
        provider = VonageTelephonyProvider()
        parsed = asyncio.run(
            provider.receive_sms({"from": "+1", "to": "+2", "text": "hello"})
        )
        self.assertEqual(parsed, {"from": "+1", "to": "+2", "text": "hello"})

    def test_sms_provider_sends_via_client(self) -> None:
        sms = VonageSmsProvider()
        with patch("app.voice.vonage_client.is_vonage_configured", return_value=True):
            with patch(
                "app.services.messaging.vonage_sms.get_settings",
                return_value=MagicMock(vonage_phone_number="+15550001111"),
            ):
                with patch(
                    "app.voice.vonage_client.send_sms",
                    return_value={"id": "msg-9"},
                ) as send:
                    result = sms.send_sms("+15550001111", "+15550002222", "ping")
        self.assertTrue(result["sent"])
        self.assertEqual(result["id"], "msg-9")
        send.assert_called_once()

    def test_number_provisioning_search_purchase_configure(self) -> None:
        provider = VonageNumberProvisioningProvider()
        with patch("app.voice.vonage_client.is_phone_provisioning_configured", return_value=True):
            with patch(
                "app.voice.vonage_client.search_available_phone_numbers",
                return_value=[{"phone_number": "+442071112233", "region": "GB", "cost": "1.00"}],
            ) as search:
                found = provider.search_numbers("GB", prefix="207", limit=5)
            self.assertEqual(found[0]["phone_number"], "+442071112233")
            search.assert_called_once()

            with patch(
                "app.voice.vonage_client.create_number_order",
                return_value={"id": "442071112233", "status": "success"},
            ):
                order = provider.purchase_number("+442071112233")
            self.assertEqual(order.external_id, "442071112233")

            with patch(
                "app.voice.vonage_client.configure_phone_number",
                return_value={"error-code": "200"},
            ) as configure:
                with patch(
                    "app.providers.vonage.number_provisioning.get_settings",
                    return_value=MagicMock(public_api_url="https://api.example.com"),
                ):
                    provider.configure_voice("442071112233")
                    provider.configure_sms("442071112233")
            self.assertEqual(configure.call_count, 2)

    def test_regulatory_methods_use_applications_and_media(self) -> None:
        provider = VonageRegulatoryProvider()
        with patch("app.voice.vonage_client.is_vonage_configured", return_value=True):
            with patch(
                "app.providers.vonage.regulatory.get_settings",
                return_value=MagicMock(public_api_url="https://api.example.com"),
            ):
                with patch(
                    "app.voice.vonage_client.create_application",
                    return_value={"id": "app-1"},
                ) as create_app:
                    result = provider.create_end_user(
                        business_id="biz-1",
                        payload={"friendly_name": "Acme"},
                    )
            self.assertEqual(result.external_id, "app-1")
            create_app.assert_called_once()

            with patch(
                "app.voice.vonage_client.upload_media",
                return_value={"id": "media-1"},
            ):
                doc = provider.upload_document(
                    file_bytes=b"%PDF",
                    filename="reg.pdf",
                    content_type="application/pdf",
                )
            self.assertEqual(doc.external_id, "media-1")

            with patch(
                "app.voice.vonage_client.get_application",
                return_value={"id": "app-1"},
            ):
                bundle = provider.create_regulatory_bundle(country_code="GB", end_user_id="app-1")
            self.assertEqual(bundle.external_id, "app-1:GB")

    def test_vonage_outbound_answer_is_ncco(self) -> None:
        markup = VonageVoiceMarkup()
        ncco = json.loads(
            markup.build_outbound_answer(
                "Acme Plumbing",
                "+15550009999",
                reason="Following up on your booking",
            )
        )
        self.assertEqual(ncco[0]["action"], "talk")
        self.assertEqual(ncco[2]["action"], "connect")
        self.assertEqual(ncco[2]["endpoint"][0]["number"], "+15550009999")

    def test_vonage_duplex_markup_is_ncco_not_texml(self) -> None:
        markup = VonageVoiceMarkup()
        with patch("app.services.voice_mode_service.get_settings") as settings_mock:
            settings_mock.return_value.voice_mode = "duplex"
            with patch(
                "app.services.voice_mode_service.get_speech_to_text_plugin",
                return_value=MagicMock(is_configured=lambda: True),
            ):
                with patch(
                    "app.services.voice_mode_service.get_duplex_media_adapter",
                    return_value=MagicMock(is_configured=lambda: True, supports_duplex=lambda: True),
                ):
                    ncco = json.loads(
                        markup.build_say_and_gather(
                            "Hello",
                            "https://api.example.com",
                            "call-1",
                            call_sid="uuid-1",
                            country="US",
                        )
                    )
        self.assertEqual(ncco[1]["action"], "connect")
        self.assertIn("websocket", ncco[1]["endpoint"][0]["type"])
        self.assertNotIn("<Response>", json.dumps(ncco))

    @patch("app.providers.factory.ProviderFactory._env_cpaas_override", return_value="vonage")
    @patch("app.config.get_settings")
    def test_factory_honors_voice_provider_env_for_vonage(
        self,
        settings_mock,
        _env_mock,
    ) -> None:
        settings_mock.return_value = MagicMock(
            vonage_api_key="key",
            vonage_api_secret="secret",
            voice_provider="vonage",
            telephony_provider="auto",
        )
        config = ProviderConfiguration(
            {
                "defaults": {"telephony": "telnyx", "numbers": "telnyx", "regulatory": "telnyx"},
                "countries": {},
                "failover": {"telephony": ["telnyx", "vonage"]},
            }
        )
        registry = ProviderRegistry(config)
        bootstrap_providers(registry)
        factory = ProviderFactory(registry)

        provider = factory.get_telephony_provider()
        self.assertIsInstance(provider, VonageTelephonyProvider)


if __name__ == "__main__":
    unittest.main()
