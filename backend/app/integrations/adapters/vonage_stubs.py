"""Vonage integration adapter stubs."""

from __future__ import annotations

import logging

from fastapi import Request

from app.config import get_settings
from app.integrations.contracts import SmsInboundAdapter, VoiceCallControl, VoiceWebhookAdapter

logger = logging.getLogger(__name__)


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
        content_type = (request.headers.get("content-type") or "").lower()
        if "json" in content_type:
            payload = await request.json()
        else:
            form = await request.form()
            payload = {k: v for k, v in form.items()}

        flat: dict[str, str] = {}
        if isinstance(payload, dict):
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


class VonageSmsInboundAdapter(SmsInboundAdapter):
    @property
    def provider_name(self) -> str:
        return "vonage"

    async def parse_inbound(self, request: Request) -> dict[str, str] | None:
        payload = await request.json()
        text = payload.get("text") or payload.get("message", {}).get("content", "")
        if not text:
            return None
        return {
            "from": str(payload.get("from", "")),
            "to": str(payload.get("to", "")),
            "text": str(text),
        }
