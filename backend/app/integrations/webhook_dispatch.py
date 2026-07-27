"""Detect inbound CPaaS provider from webhook headers for multi-primary deployments."""

from __future__ import annotations

from fastapi import Request

from app.config import get_settings


def detect_voice_webhook_provider(request: Request) -> str | None:
    """
    Infer telephony provider from signature/auth headers.

    Used so a single ``/voice/*`` route can accept Telnyx, Twilio, and Vonage
    when multiple primaries are configured.
    """
    headers = request.headers
    if headers.get("X-Twilio-Signature") or headers.get("x-twilio-signature"):
        return "twilio"
    if headers.get("telnyx-signature-ed25519") or headers.get("Telnyx-Signature-Ed25519"):
        return "telnyx"
    authorization = headers.get("Authorization") or headers.get("authorization") or ""
    settings = get_settings()
    if authorization.lower().startswith("bearer ") and (
        settings.vonage_signature_secret or settings.vonage_api_secret
    ):
        return "vonage"
    return None


def detect_sms_webhook_provider(request: Request) -> str | None:
    """Infer SMS CPaaS from inbound webhook headers (same signals as voice)."""
    return detect_voice_webhook_provider(request)
