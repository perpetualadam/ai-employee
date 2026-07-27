"""Twilio production parity with Telnyx — telephony, SMS, numbers, regulatory, markup."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from app.providers.bootstrap import bootstrap_providers
from app.providers.configuration import ProviderConfiguration
from app.providers.factory import ProviderFactory
from app.providers.registry import ProviderRegistry
from app.providers.twilio.number_provisioning import TwilioNumberProvisioningProvider
from app.providers.twilio.regulatory import TwilioRegulatoryProvider
from app.providers.twilio.telephony import TwilioTelephonyProvider
from app.services.call_service import CallService
from app.services.messaging.twilio_sms import TwilioSmsProvider
from app.voice.voice_markup import TwilioVoiceMarkup


class TwilioParitySpecification(unittest.TestCase):
    def test_telephony_is_configured_from_credentials(self) -> None:
        provider = TwilioTelephonyProvider()
        with patch("app.voice.twilio_client.is_twilio_configured", return_value=True):
            self.assertTrue(provider.is_configured())
        with patch("app.voice.twilio_client.is_twilio_configured", return_value=False):
            self.assertFalse(provider.is_configured())

    def test_answer_call_accepts_markup_or_texml_alias(self) -> None:
        provider = TwilioTelephonyProvider()
        with patch("app.voice.twilio_client.update_call_twiml") as update:
            asyncio.run(provider.answer_call("CA1", {"markup": "<Response/>"}))
            update.assert_called_once_with("CA1", "<Response/>")
        with patch("app.voice.twilio_client.update_call_twiml") as update:
            asyncio.run(provider.answer_call("CA2", {"texml": "<Response><Hangup/></Response>"}))
            update.assert_called_once_with("CA2", "<Response><Hangup/></Response>")

    def test_outbound_transfer_end_and_sms_use_real_client(self) -> None:
        provider = TwilioTelephonyProvider()

        with patch("app.voice.twilio_client.is_outbound_call_configured", return_value=True):
            with patch(
                "app.voice.twilio_client.initiate_call",
                return_value={"id": "CA-out", "call_control_id": "CA-out"},
            ) as initiate:
                result = asyncio.run(
                    provider.outbound_call(
                        from_number="+15550001111",
                        to_number="+15550002222",
                        webhook_url="https://example.com/voice",
                    )
                )
        self.assertEqual(result.external_id, "CA-out")
        initiate.assert_called_once()

        with patch("app.voice.twilio_client.end_call") as end:
            asyncio.run(provider.end_call("CA-end"))
            end.assert_called_once_with("CA-end")

        with patch(
            "app.voice.twilio_client.send_sms",
            return_value={"id": "SM123", "raw": {}},
        ) as send:
            sms = asyncio.run(
                provider.send_sms(from_number="+15550001111", to_number="+15550003333", text="hi")
            )
        self.assertEqual(sms.external_id, "SM123")
        send.assert_called_once()

        with patch("app.voice.twilio_client.update_call_twiml") as update:
            with patch(
                "app.integrations.adapters.twilio_stubs.TwilioVoiceCallControl.is_configured",
                return_value=True,
            ):
                asyncio.run(provider.transfer_call("CA-xfer", "+15550004444"))
                update.assert_called_once()
                self.assertIn("<Dial", update.call_args[0][1])
                self.assertNotIn("TeXML", update.call_args[0][1])

    def test_receive_sms_normalizes_twilio_payload(self) -> None:
        provider = TwilioTelephonyProvider()
        parsed = asyncio.run(
            provider.receive_sms({"From": "+1", "To": "+2", "Body": "hello"})
        )
        self.assertEqual(parsed, {"from": "+1", "to": "+2", "text": "hello"})

    def test_sms_provider_sends_via_client(self) -> None:
        sms = TwilioSmsProvider()
        with patch("app.voice.twilio_client.is_twilio_configured", return_value=True):
            with patch(
                "app.services.messaging.twilio_sms.get_settings",
                return_value=MagicMock(
                    twilio_phone_number="+15550001111",
                    twilio_messaging_service_sid="",
                ),
            ):
                with patch(
                    "app.voice.twilio_client.send_sms",
                    return_value={"id": "SM9"},
                ) as send:
                    result = sms.send_sms("+15550001111", "+15550002222", "ping")
        self.assertTrue(result["sent"])
        self.assertEqual(result["id"], "SM9")
        send.assert_called_once()

    def test_number_provisioning_search_purchase_configure(self) -> None:
        provider = TwilioNumberProvisioningProvider()
        with patch("app.voice.twilio_client.is_phone_provisioning_configured", return_value=True):
            with patch("app.voice.twilio_client.is_twilio_configured", return_value=True):
                with patch(
                    "app.voice.twilio_client.search_available_phone_numbers",
                    return_value=[{"phone_number": "+15551212", "region": "NY", "cost": None}],
                ) as search:
                    found = provider.search_numbers("US", prefix="212", limit=5)
                self.assertEqual(found[0]["phone_number"], "+15551212")
                search.assert_called_once()

                with patch(
                    "app.voice.twilio_client.create_number_order",
                    return_value={"id": "PN123", "status": "success"},
                ):
                    order = provider.purchase_number("+15551212")
                self.assertEqual(order.external_id, "PN123")

                with patch(
                    "app.voice.twilio_client.configure_phone_number",
                    return_value={"sid": "PN123"},
                ) as configure:
                    with patch(
                        "app.providers.twilio.number_provisioning.get_settings",
                        return_value=MagicMock(
                            public_api_url="https://api.example.com",
                            twilio_messaging_service_sid="MG123",
                        ),
                    ):
                        provider.configure_voice("PN123")
                        provider.configure_sms("PN123")
                self.assertEqual(configure.call_count, 2)

    def test_regulatory_methods_call_twilio_compliance_api(self) -> None:
        provider = TwilioRegulatoryProvider()
        with patch("app.voice.twilio_client.is_twilio_configured", return_value=True):
            with patch(
                "app.voice.twilio_client.create_end_user",
                return_value={"sid": "IT123"},
            ) as create_eu:
                result = provider.create_end_user(
                    business_id="biz-1",
                    payload={"friendly_name": "Acme", "business_name": "Acme LLC"},
                )
            self.assertEqual(result.external_id, "IT123")
            create_eu.assert_called_once()

            with patch(
                "app.voice.twilio_client.create_regulatory_bundle",
                return_value={"sid": "BU123"},
            ):
                with patch("app.voice.twilio_client.assign_bundle_item") as assign:
                    bundle = provider.create_regulatory_bundle(
                        country_code="US",
                        end_user_id="IT123",
                    )
            self.assertEqual(bundle.external_id, "BU123")
            assign.assert_called_once()

            with patch(
                "app.voice.twilio_client.submit_regulatory_bundle",
                return_value={"sid": "BU123", "status": "pending-review"},
            ) as submit:
                submitted = provider.submit_bundle("BU123")
            self.assertEqual(submitted.external_id, "BU123")
            submit.assert_called_once_with("BU123")

    def test_twilio_outbound_answer_is_twiml_not_telnyx_default(self) -> None:
        markup = TwilioVoiceMarkup()
        twiml = markup.build_outbound_answer(
            "Acme Plumbing",
            "+15550009999",
            reason="Following up on your booking",
            country="US",
        )
        self.assertIn("<Dial", twiml)
        self.assertIn("+15550009999", twiml)
        self.assertIn("Following up on your booking", twiml)
        self.assertNotIn("TeXML", twiml)

    def test_call_service_markup_alias(self) -> None:
        class _Prov:
            provider_name = "twilio"

            def is_configured(self) -> bool:
                return True

            async def answer_call(self, call_id, webhook_response):
                self.last = (call_id, webhook_response)
                from app.providers.base import ProviderResult

                return ProviderResult(provider="twilio", external_id=call_id)

        prov = _Prov()
        service = CallService(prov)  # type: ignore[arg-type]
        asyncio.run(service.answer_call("CA9", markup="<Response/>"))
        self.assertEqual(prov.last[1]["markup"], "<Response/>")
        asyncio.run(service.answer_call("CA9", texml="<Response><Hangup/></Response>"))
        self.assertEqual(prov.last[1]["texml"], "<Response><Hangup/></Response>")

    @patch("app.providers.factory.ProviderFactory._env_cpaas_override", return_value="twilio")
    @patch("app.config.get_settings")
    def test_factory_honors_voice_provider_env_for_telephony(
        self,
        settings_mock,
        _env_mock,
    ) -> None:
        settings_mock.return_value = MagicMock(
            twilio_account_sid="ACxxx",
            twilio_auth_token="secret",
            voice_provider="twilio",
            telephony_provider="auto",
        )
        config = ProviderConfiguration(
            {
                "defaults": {"telephony": "telnyx", "numbers": "telnyx", "regulatory": "telnyx"},
                "countries": {},
                "failover": {"telephony": ["telnyx", "twilio"]},
            }
        )
        registry = ProviderRegistry(config)
        bootstrap_providers(registry)
        factory = ProviderFactory(registry)

        provider = factory.get_telephony_provider()
        self.assertIsInstance(provider, TwilioTelephonyProvider)


if __name__ == "__main__":
    unittest.main()
