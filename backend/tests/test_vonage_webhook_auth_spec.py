"""Vonage signed webhook validation tests."""

from __future__ import annotations

import hashlib
import json
import time
import unittest

from jose import jwt

from app.voice.vonage_webhook_auth import validate_vonage_signed_webhook


class VonageWebhookAuthSpecification(unittest.TestCase):
    def _signed_authorization(
        self,
        *,
        secret: str,
        body: bytes,
        method: str = "POST",
        query_params: dict[str, str] | None = None,
    ) -> str:
        payload_hash = hashlib.sha256(body).hexdigest()
        token = jwt.encode(
            {
                "iat": int(time.time()),
                "payload_hash": payload_hash,
            },
            secret,
            algorithm="HS256",
        )
        return f"Bearer {token}"

    def test_accepts_valid_signed_webhook(self) -> None:
        body = json.dumps({"uuid": "call-1", "from": "+15551112222"}).encode("utf-8")
        auth = self._signed_authorization(secret="vonage-secret", body=body)
        self.assertTrue(
            validate_vonage_signed_webhook(
                authorization=auth,
                signature_secret="vonage-secret",
                body=body,
                method="POST",
            )
        )

    def test_rejects_invalid_secret(self) -> None:
        body = b'{"uuid":"call-1"}'
        auth = self._signed_authorization(secret="vonage-secret", body=body)
        self.assertFalse(
            validate_vonage_signed_webhook(
                authorization=auth,
                signature_secret="other-secret",
                body=body,
                method="POST",
            )
        )

    def test_rejects_tampered_body(self) -> None:
        body = b'{"uuid":"call-1"}'
        auth = self._signed_authorization(secret="vonage-secret", body=body)
        self.assertFalse(
            validate_vonage_signed_webhook(
                authorization=auth,
                signature_secret="vonage-secret",
                body=b'{"uuid":"call-2"}',
                method="POST",
            )
        )

    def test_rejects_missing_authorization(self) -> None:
        self.assertFalse(
            validate_vonage_signed_webhook(
                authorization=None,
                signature_secret="vonage-secret",
                body=b"{}",
                method="POST",
            )
        )


if __name__ == "__main__":
    unittest.main()
