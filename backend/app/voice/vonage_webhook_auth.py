"""Vonage signed webhook validation (HS256 JWT in Authorization header)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging

from jose import JWTError, jwt

logger = logging.getLogger(__name__)


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _payload_hash_for_request(
    *,
    body: bytes,
    method: str,
    query_params: dict[str, str],
) -> str:
    if method.upper() == "GET" and query_params:
        ordered = json.dumps(query_params, separators=(",", ":"), ensure_ascii=False)
        return _sha256_hex(ordered.encode("utf-8"))
    return _sha256_hex(body)


def validate_vonage_signed_webhook(
    *,
    authorization: str | None,
    signature_secret: str,
    body: bytes,
    method: str,
    query_params: dict[str, str] | None = None,
) -> bool:
    """
    Verify Vonage signed webhook JWT and optional payload_hash claim.
    """
    if not signature_secret:
        return False
    if not authorization or not authorization.lower().startswith("bearer "):
        return False

    token = authorization.split(" ", 1)[1].strip()
    try:
        claims = jwt.decode(token, signature_secret, algorithms=["HS256"])
    except JWTError:
        logger.warning("Invalid Vonage webhook JWT")
        return False

    expected_hash = claims.get("payload_hash")
    if expected_hash:
        computed = _payload_hash_for_request(
            body=body,
            method=method,
            query_params=query_params or {},
        )
        if not hmac.compare_digest(computed, str(expected_hash)):
            logger.warning("Vonage webhook payload_hash mismatch")
            return False

    return True
