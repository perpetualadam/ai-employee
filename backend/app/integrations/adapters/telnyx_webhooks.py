"""Telnyx voice webhook adapter."""

from __future__ import annotations

from fastapi import Request

from app.integrations.contracts import VoiceWebhookAdapter
from app.voice.webhook_auth import validate_telnyx_webhook


class TelnyxVoiceWebhookAdapter(VoiceWebhookAdapter):
    @property
    def provider_name(self) -> str:
        return "telnyx"

    async def parse_request(self, request: Request) -> dict[str, str]:
        return await validate_telnyx_webhook(request)
