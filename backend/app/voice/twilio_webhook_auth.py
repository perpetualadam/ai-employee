"""Twilio webhook request signature validation."""

from __future__ import annotations

import base64
import hashlib
import hmac


def validate_twilio_signature(
    url: str,
    params: dict[str, str],
    signature: str,
    auth_token: str,
) -> bool:
    """
    Validate X-Twilio-Signature using Twilio's documented HMAC-SHA1 scheme.
    """
    if not signature or not auth_token:
        return False

    payload = url + "".join(key + params[key] for key in sorted(params.keys()))
    digest = hmac.new(
        auth_token.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)
