"""Telnyx TeXML webhook signature validation."""

import base64
import logging
import time

from fastapi import HTTPException, Request, status
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

from app.config import get_settings

logger = logging.getLogger(__name__)

# Telnyx allows ~5 minutes of clock skew for signed webhooks.
_MAX_WEBHOOK_AGE_SECONDS = 300


def _decode_public_key(raw_key: str) -> VerifyKey:
    """Accept base64 or PEM-style Telnyx public key material."""
    cleaned = raw_key.strip()
    if "BEGIN PUBLIC KEY" in cleaned:
        lines = [line for line in cleaned.splitlines() if not line.startswith("-----")]
        cleaned = "".join(lines)
    key_bytes = base64.b64decode(cleaned)
    return VerifyKey(key_bytes)


def _verify_ed25519_signature(payload: bytes, timestamp: str, signature_b64: str, public_key: str) -> bool:
    try:
        ts = int(timestamp)
    except ValueError:
        return False

    if abs(time.time() - ts) > _MAX_WEBHOOK_AGE_SECONDS:
        return False

    signed_payload = f"{timestamp}|{payload.decode('utf-8')}".encode("utf-8")
    signature = base64.b64decode(signature_b64)
    verify_key = _decode_public_key(public_key)
    try:
        verify_key.verify(signed_payload, signature)
    except BadSignatureError:
        return False
    return True


async def validate_telnyx_webhook(request: Request) -> dict[str, str]:
    """
    Validate Telnyx Ed25519 webhook signature when headers are present.
    Returns request parameters as a flat dict (query string for GET, form for POST).
    """
    settings = get_settings()
    body = await request.body()

    timestamp = request.headers.get("telnyx-timestamp", "")
    signature = request.headers.get("telnyx-signature-ed25519", "")

    if signature and timestamp and settings.telnyx_public_key:
        if not _verify_ed25519_signature(body, timestamp, signature, settings.telnyx_public_key):
            logger.warning("Invalid Telnyx webhook signature")
            if not settings.debug:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid webhook signature",
                )
    elif not settings.telnyx_public_key and not settings.debug:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telnyx is not configured",
        )

    if request.method == "GET":
        return {k: v for k, v in request.query_params.items()}

    if body:
        from urllib.parse import parse_qs

        parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
        return {k: v[0] if v else "" for k, v in parsed.items()}

    form = await request.form()
    return {k: str(v) for k, v in form.items()}
