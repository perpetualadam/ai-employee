"""Plivo webhook signature validation (V2 HMAC-SHA256)."""

from __future__ import annotations

import base64
import hashlib
import hmac


def validate_plivo_signature_v2(
    uri: str,
    nonce: str,
    signature: str,
    auth_token: str,
) -> bool:
    """
    Validate ``X-Plivo-Signature-V2``.

    Message = callback URI + nonce; HMAC-SHA256 with auth token; base64 digest.
    """
    if not uri or not nonce or not signature or not auth_token:
        return False
    message = f"{uri}{nonce}".encode("utf-8")
    digest = hmac.new(auth_token.encode("utf-8"), message, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    # Plivo may send comma-separated signatures when multiple tokens are active.
    candidates = [part.strip() for part in signature.split(",") if part.strip()]
    return any(hmac.compare_digest(expected, candidate) for candidate in candidates)
