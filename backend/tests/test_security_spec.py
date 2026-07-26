"""Security policy, internal auth, and webhook hardening tests."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from nacl.signing import SigningKey

from app.core.security_policy import validate_security_policy, verify_internal_secret
from app.voice.twilio_webhook_auth import validate_twilio_signature
from app.voice.webhook_auth import verify_telnyx_webhook_signature


class SecurityPolicySpecification(unittest.TestCase):
    def test_rejects_default_secret_key_in_production(self) -> None:
        settings = MagicMock()
        settings.debug = False
        settings.secret_key = "change-me-in-production-use-openssl-rand-hex-32"
        settings.cron_secret = "configured"
        settings.allowed_host_list = ["api.example.com"]

        with self.assertRaises(RuntimeError):
            validate_security_policy(settings)

    def test_allows_insecure_defaults_in_debug(self) -> None:
        settings = MagicMock()
        settings.debug = True
        validate_security_policy(settings)

    def test_internal_secret_requires_cron_secret(self) -> None:
        with patch("app.core.security_policy.get_settings") as settings_mock:
            settings_mock.return_value.cron_secret = ""
            with self.assertRaises(HTTPException) as ctx:
                verify_internal_secret(None)
            self.assertEqual(ctx.exception.status_code, 503)

    def test_internal_secret_rejects_wrong_value(self) -> None:
        with patch("app.core.security_policy.get_settings") as settings_mock:
            settings_mock.return_value.cron_secret = "expected"
            with self.assertRaises(HTTPException) as ctx:
                verify_internal_secret("wrong")
            self.assertEqual(ctx.exception.status_code, 403)

    def test_internal_secret_accepts_matching_value(self) -> None:
        with patch("app.core.security_policy.get_settings") as settings_mock:
            settings_mock.return_value.cron_secret = "expected"
            verify_internal_secret("expected")


class TwilioWebhookSignatureSpecification(unittest.TestCase):
    def test_validates_twilio_signature(self) -> None:
        params = {"CallSid": "CA123", "From": "+15551234567"}
        url = "https://api.example.com/api/v1/voice/inbound"
        payload = url + "CallSidCA123From+15551234567"
        digest = hmac.new(b"auth-token", payload.encode("utf-8"), hashlib.sha1).digest()
        signature = base64.b64encode(digest).decode("utf-8")

        self.assertTrue(
            validate_twilio_signature(url, params, signature, "auth-token"),
        )

    def test_rejects_invalid_twilio_signature(self) -> None:
        self.assertFalse(
            validate_twilio_signature(
                "https://api.example.com/api/v1/voice/inbound",
                {"CallSid": "CA123"},
                "bad-signature",
                "auth-token",
            )
        )


class TelnyxWebhookEnforcementSpecification(unittest.TestCase):
    def test_requires_signature_when_public_key_configured(self) -> None:
        signing_key = SigningKey.generate()
        public_key = base64.b64encode(bytes(signing_key.verify_key)).decode()
        timestamp = str(int(time.time()))
        body = b""
        signed_payload = f"{timestamp}|".encode("utf-8")
        signature = base64.b64encode(signing_key.sign(signed_payload).signature).decode()

        self.assertTrue(
            verify_telnyx_webhook_signature(body, timestamp, signature, public_key),
        )
        other_key = base64.b64encode(bytes(SigningKey.generate().verify_key)).decode()
        self.assertFalse(
            verify_telnyx_webhook_signature(body, timestamp, signature, other_key),
        )


if __name__ == "__main__":
    unittest.main()
