"""Detect inbound CPaaS provider from webhook headers for multi-primary deployments."""

from __future__ import annotations

from fastapi import Request

from app.config import get_settings


async def _twilio_compatible_account_sid(request: Request) -> str:
    """AccountSid from query string or form body (SignalWire project id / Twilio AC…)."""
    query = request.query_params if hasattr(request, "query_params") else None
    if query is not None:
        sid = (query.get("AccountSid") or "").strip()
        if sid:
            return sid
    try:
        form = await request.form()
    except Exception:
        return ""
    return str(form.get("AccountSid") or "").strip()


async def detect_voice_webhook_provider(request: Request) -> str | None:
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

    if headers.get("X-SignalWire-Signature") or headers.get("x-signalwire-signature"):
        return "signalwire"

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
        if tw and not sw:
            return "twilio"
        if sw and tw:
            # Co-configured: disambiguate via AccountSid (project id vs Twilio AC…).
            account_sid = await _twilio_compatible_account_sid(request)
            if account_sid and account_sid == settings.signalwire_project_id:
                return "signalwire"
            if account_sid and account_sid == settings.twilio_account_sid:
                return "twilio"
            if account_sid.startswith("AC"):
                return "twilio"
            if account_sid:
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


async def detect_sms_webhook_provider(request: Request) -> str | None:
    """Infer SMS CPaaS from inbound webhook headers (same signals as voice)."""
    return await detect_voice_webhook_provider(request)
