"""Vonage integration adapter stubs."""

from __future__ import annotations

import json
import logging

from fastapi import HTTPException, Request, status

from app.config import get_settings
from app.integrations.contracts import SmsInboundAdapter, VoiceCallControl, VoiceWebhookAdapter
from app.voice.vonage_webhook_auth import validate_vonage_signed_webhook

logger = logging.getLogger(__name__)


def _vonage_signature_secret() -> str:
    settings = get_settings()
    return (settings.vonage_signature_secret or settings.vonage_api_secret or "").strip()


def _require_vonage_webhook_signature(request: Request, body: bytes) -> None:
    settings = get_settings()
    secret = _vonage_signature_secret()
    if secret:
        authorization = request.headers.get("authorization") or request.headers.get("Authorization")
        query_params = {k: v for k, v in request.query_params.items()}
        if not validate_vonage_signed_webhook(
            authorization=authorization,
            signature_secret=secret,
            body=body,
            method=request.method,
            query_params=query_params,
        ):
            logger.warning("Invalid Vonage webhook signature", extra={"path": request.url.path})
            if not settings.debug:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid webhook signature",
                )
    elif not settings.debug:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vonage is not configured",
        )


def _parse_vonage_payload(body: bytes, content_type: str) -> dict:
    if "json" in content_type and body:
        parsed = json.loads(body.decode("utf-8"))
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _flatten_vonage_voice_payload(payload: dict) -> dict[str, str]:
    flat: dict[str, str] = {}
    for key, value in payload.items():
        if isinstance(value, (str, int, float)):
            flat[str(key)] = str(value)

    speech = payload.get("speech")
    if isinstance(speech, dict):
        results = speech.get("results") or []
        if results and isinstance(results[0], dict):
            best = results[0]
            text = str(best.get("text") or "").strip()
            if text:
                flat["SpeechResult"] = text
            if best.get("confidence") is not None:
                flat["Confidence"] = str(best.get("confidence"))

    if flat.get("uuid") and not flat.get("CallSid"):
        flat["CallSid"] = flat["uuid"]
    if flat.get("conversation_uuid") and not flat.get("CallSid"):
        flat["CallSid"] = flat["conversation_uuid"]
    if flat.get("from") and not flat.get("From"):
        flat["From"] = flat["from"]
    if flat.get("to") and not flat.get("To"):
        flat["To"] = flat["to"]
    return flat


class VonageVoiceCallControl(VoiceCallControl):
    @property
    def provider_name(self) -> str:
        return "vonage"

    def is_configured(self) -> bool:
        settings = get_settings()
        return bool(settings.vonage_api_key and settings.vonage_api_secret)

    async def transfer_call(self, call_id: str, to_number: str) -> None:
        if not self.is_configured():
            raise RuntimeError("Vonage voice is not configured")
        from app.integrations.adapters.vonage_duplex import VonageDuplexMediaAdapter

        adapter = VonageDuplexMediaAdapter()
        ncco = adapter.build_transfer_response(to_number)
        from app.voice import vonage_client

        vonage_client.update_call_ncco(call_id, ncco)
        logger.info("Vonage transfer initiated", extra={"call_id": call_id, "to": to_number})


class VonageVoiceWebhookAdapter(VoiceWebhookAdapter):
    @property
    def provider_name(self) -> str:
        return "vonage"

    async def parse_request(self, request: Request) -> dict[str, str]:
        body = await request.body()
        _require_vonage_webhook_signature(request, body)
        content_type = (request.headers.get("content-type") or "").lower()
        payload = _parse_vonage_payload(body, content_type)
        return _flatten_vonage_voice_payload(payload)


class VonageSmsInboundAdapter(SmsInboundAdapter):
    @property
    def provider_name(self) -> str:
        return "vonage"

    async def parse_inbound(self, request: Request) -> dict[str, str] | None:
        body = await request.body()
        _require_vonage_webhook_signature(request, body)
        payload = _parse_vonage_payload(body, (request.headers.get("content-type") or "").lower())
        text = payload.get("text") or payload.get("message", {}).get("content", "")
        if not text:
            return None
        return {
            "from": str(payload.get("from", "")),
            "to": str(payload.get("to", "")),
            "text": str(text),
        }
