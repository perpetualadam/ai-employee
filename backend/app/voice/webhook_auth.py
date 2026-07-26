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


def _decode_signature_header(signature_header: str) -> bytes:
    """Accept raw base64 or Standard Webhooks-style `v1a,<sig>` / `v1,<sig>`."""
    cleaned = signature_header.strip()
    if "," in cleaned:
        cleaned = cleaned.split(",", 1)[1]
    return base64.b64decode(cleaned)


def _build_signed_payload(timestamp: str, body: bytes) -> bytes:
    """
    Telnyx signs `{timestamp}|{raw_body}`.
    For TeXML GET callbacks the body is empty, so the signed string is `{timestamp}|`.
    """
    return f"{timestamp}|".encode("utf-8") + body


def _build_standard_webhooks_payload(msg_id: str, timestamp: str, body: bytes) -> bytes:
    """Standard Webhooks asymmetric format: `{msg_id}.{timestamp}.{body}`."""
    body_text = body.decode("utf-8") if body else ""
    return f"{msg_id}.{timestamp}.{body_text}".encode("utf-8")


def _verify_signed_payload(
    signed_payload: bytes,
    signature_header: str,
    public_key: str,
) -> bool:
    try:
        signature = _decode_signature_header(signature_header)
        verify_key = _decode_public_key(public_key)
        verify_key.verify(signed_payload, signature)
    except (BadSignatureError, ValueError):
        return False
    return True


def verify_telnyx_webhook_signature(
    body: bytes,
    timestamp: str,
    signature_header: str,
    public_key: str,
    *,
    query_string: bytes | None = None,
    webhook_id: str | None = None,
) -> bool:
    """
    Verify a Telnyx webhook signature against candidate payload formats.
    Returns True when any supported format matches.
    """
    try:
        ts = int(timestamp)
    except ValueError:
        return False

    if abs(time.time() - ts) > _MAX_WEBHOOK_AGE_SECONDS:
        return False

    candidates: list[bytes] = [_build_signed_payload(timestamp, body)]

    if webhook_id:
        candidates.append(_build_standard_webhooks_payload(webhook_id, timestamp, body))

    # Legacy fallback: some integrations documented query signing for GET.
    if query_string:
        candidates.append(_build_signed_payload(timestamp, query_string))

    for signed_payload in candidates:
        if _verify_signed_payload(signed_payload, signature_header, public_key):
            return True
    return False


async def validate_telnyx_webhook(request: Request) -> dict[str, str]:
    """
    Validate Telnyx Ed25519 webhook signature when headers are present.
    Returns request parameters as a flat dict (query string for GET, form for POST).
    """
    settings = get_settings()
    body = await request.body()

    timestamp = request.headers.get("telnyx-timestamp", "")
    signature = request.headers.get("telnyx-signature-ed25519", "")
    webhook_id = request.headers.get("webhook-id") or request.headers.get("telnyx-webhook-id")
    query_bytes = request.url.query.encode("utf-8") if request.url.query else None

    if settings.telnyx_public_key:
        if not signature or not timestamp:
            logger.warning(
                "Telnyx webhook missing signature headers",
                extra={"method": request.method, "path": request.url.path},
            )
            if not settings.debug:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Missing webhook signature",
                )
        elif not verify_telnyx_webhook_signature(
            body,
            timestamp,
            signature,
            settings.telnyx_public_key,
            query_string=query_bytes if request.method == "GET" and not body else None,
            webhook_id=webhook_id,
        ):
            logger.warning(
                "Invalid Telnyx webhook signature",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "body_len": len(body),
                    "query_len": len(query_bytes or b""),
                },
            )
            if not settings.debug:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid webhook signature",
                )
    elif not settings.debug:
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
