"""Tests for Telnyx webhook signature verification."""

import base64
import time
import unittest

from nacl.signing import SigningKey

from app.voice.webhook_auth import (
    _build_signed_payload,
    verify_telnyx_webhook_signature,
)


class TelnyxWebhookSignatureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.signing_key = SigningKey.generate()
        self.public_key_b64 = base64.b64encode(bytes(self.signing_key.verify_key)).decode()

    def _sign(self, signed_payload: bytes) -> str:
        signature = self.signing_key.sign(signed_payload).signature
        return base64.b64encode(signature).decode()

    def test_empty_get_body_matches_texml_gather(self) -> None:
        """TeXML GET gather callbacks sign an empty raw body."""
        timestamp = str(int(time.time()))
        body = b""
        signed_payload = _build_signed_payload(timestamp, body)
        signature = self._sign(signed_payload)

        self.assertTrue(
            verify_telnyx_webhook_signature(
                body,
                timestamp,
                signature,
                self.public_key_b64,
            )
        )

    def test_post_form_body(self) -> None:
        timestamp = str(int(time.time()))
        body = b"SpeechResult=hello&Confidence=0.91"
        signed_payload = _build_signed_payload(timestamp, body)
        signature = self._sign(signed_payload)

        self.assertTrue(
            verify_telnyx_webhook_signature(
                body,
                timestamp,
                signature,
                self.public_key_b64,
            )
        )

    def test_standard_webhooks_signature_prefix(self) -> None:
        timestamp = str(int(time.time()))
        body = b'{"data":{"event_type":"call.initiated"}}'
        signed_payload = _build_signed_payload(timestamp, body)
        signature = f"v1a,{self._sign(signed_payload)}"

        self.assertTrue(
            verify_telnyx_webhook_signature(
                body,
                timestamp,
                signature,
                self.public_key_b64,
            )
        )

    def test_rejects_tampered_body(self) -> None:
        timestamp = str(int(time.time()))
        body = b"SpeechResult=hello"
        signed_payload = _build_signed_payload(timestamp, body)
        signature = self._sign(signed_payload)

        self.assertFalse(
            verify_telnyx_webhook_signature(
                b"SpeechResult=goodbye",
                timestamp,
                signature,
                self.public_key_b64,
            )
        )


if __name__ == "__main__":
    unittest.main()
