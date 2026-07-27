"""Multi-primary webhook header detection."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.integrations.webhook_dispatch import (
    detect_sms_webhook_provider,
    detect_voice_webhook_provider,
)


class WebhookDispatchSpecification(unittest.TestCase):
    def test_detects_twilio_from_signature_header(self) -> None:
        request = MagicMock()
        request.headers = {"X-Twilio-Signature": "abc"}
        self.assertEqual(detect_voice_webhook_provider(request), "twilio")

    def test_detects_telnyx_from_ed25519_header(self) -> None:
        request = MagicMock()
        request.headers = {"telnyx-signature-ed25519": "sig"}
        self.assertEqual(detect_voice_webhook_provider(request), "telnyx")

    @patch("app.integrations.webhook_dispatch.get_settings")
    def test_detects_vonage_from_bearer_authorization(self, settings_mock) -> None:
        settings_mock.return_value = MagicMock(
            vonage_signature_secret="secret",
            vonage_api_secret="",
        )
        request = MagicMock()
        request.headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.e30.sig"}
        self.assertEqual(detect_voice_webhook_provider(request), "vonage")

    def test_unknown_headers_return_none(self) -> None:
        request = MagicMock()
        request.headers = {}
        request.query_params = {}
        with patch(
            "app.integrations.webhook_dispatch.get_settings",
            return_value=MagicMock(
                voipms_api_username="",
                voipms_api_password="",
                signalwire_project_id="",
                signalwire_api_token="",
                twilio_account_sid="",
                twilio_auth_token="",
                voice_provider="auto",
                vonage_signature_secret="",
                vonage_api_secret="",
            ),
        ):
            self.assertIsNone(detect_voice_webhook_provider(request))
            self.assertIsNone(detect_sms_webhook_provider(request))

    def test_detects_plivo_from_signature_header(self) -> None:
        request = MagicMock()
        request.headers = {"X-Plivo-Signature-V2": "sig"}
        request.query_params = {}
        self.assertEqual(detect_voice_webhook_provider(request), "plivo")

    @patch("app.integrations.webhook_dispatch.get_settings")
    def test_detects_voipms_from_sms_callback_query(self, settings_mock) -> None:
        settings_mock.return_value = MagicMock(
            voipms_api_username="user",
            voipms_api_password="pass",
            signalwire_project_id="",
            signalwire_api_token="",
            twilio_account_sid="",
            twilio_auth_token="",
            voice_provider="auto",
            vonage_signature_secret="",
            vonage_api_secret="",
        )
        request = MagicMock()
        request.headers = {}
        request.query_params = {"from": "5551111", "to": "5552222", "message": "hi"}
        self.assertEqual(detect_sms_webhook_provider(request), "voipms")


if __name__ == "__main__":
    unittest.main()
