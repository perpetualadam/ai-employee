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
        logger.info("Vonage stub transfer", extra={"call_id": call_id, "to": to_number})


class VonageVoiceWebhookAdapter(VoiceWebhookAdapter):
    @property
    def provider_name(self) -> str:
        return "vonage"

    async def parse_request(self, request: Request) -> dict[str, str]:
        payload = await request.json()
        return {k: str(v) for k, v in payload.items() if isinstance(v, (str, int, float))}


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
