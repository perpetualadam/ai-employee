"""Detect inbound CPaaS provider from webhook headers for multi-primary deployments."""

from __future__ import annotations

from fastapi import Request

from app.config import get_settings


def detect_voice_webhook_provider(request: Request) -> str | None:
    """
    Infer telephony provider from signature/auth headers.

    Used so a single ``/voice/*`` route can accept multiple CPaaS primaries.
    """
    headers = request.headers
    settings = get_settings()

    if (
        headers.get("X-Plivo-Signature-V2")
        or headers.get("X-Plivo-Signature-V3")
        or headers.get("x-plivo-signature-v2")
    ):
        return "plivo"

    if headers.get("telnyx-signature-ed25519") or headers.get("Telnyx-Signature-Ed25519"):
        return "telnyx"

    if headers.get("X-Twilio-Signature") or headers.get("x-twilio-signature"):
        # SignalWire Compatibility API reuses Twilio signature headers.
        # Prefer the explicitly configured primary when only one is set.
        sw = bool(settings.signalwire_project_id and settings.signalwire_api_token)
        tw = bool(settings.twilio_account_sid and settings.twilio_auth_token)
        voice = (settings.voice_provider or "auto").lower().strip()
        if voice == "signalwire" and sw:
            return "signalwire"
        if voice == "twilio" and tw:
            return "twilio"
        if sw and not tw:
            return "signalwire"
        if tw:
            return "twilio"
        if sw:
            return "signalwire"
        return "twilio"

    authorization = headers.get("Authorization") or headers.get("authorization") or ""
    if authorization.lower().startswith("bearer ") and (
        settings.vonage_signature_secret or settings.vonage_api_secret
    ):
        return "vonage"

    # VoIP.ms SMS URL callbacks are typically unsigned GET with from/to/message.
    query = request.query_params if hasattr(request, "query_params") else {}
    if (
        settings.voipms_api_username
        and settings.voipms_api_password
        and (query.get("from") or query.get("message") or query.get("to"))
    ):
        return "voipms"

    return None


def detect_sms_webhook_provider(request: Request) -> str | None:
    """Infer SMS CPaaS from inbound webhook headers (same signals as voice)."""
    return detect_voice_webhook_provider(request)
