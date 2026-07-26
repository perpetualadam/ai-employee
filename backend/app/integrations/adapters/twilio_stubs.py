"""Twilio integration adapter stubs."""

from __future__ import annotations

import logging

from fastapi import Request

from app.integrations.contracts import SmsInboundAdapter, VoiceCallControl, VoiceWebhookAdapter
from app.config import get_settings

logger = logging.getLogger(__name__)


class TwilioVoiceCallControl(VoiceCallControl):
    @property
    def provider_name(self) -> str:
        return "twilio"

    def is_configured(self) -> bool:
        settings = get_settings()
        return bool(settings.twilio_account_sid and settings.twilio_auth_token)

    async def transfer_call(self, call_id: str, to_number: str) -> None:
        if not self.is_configured():
            raise RuntimeError("Twilio voice is not configured")
        logger.info("Twilio stub transfer", extra={"call_id": call_id, "to": to_number})


class TwilioVoiceWebhookAdapter(VoiceWebhookAdapter):
    @property
    def provider_name(self) -> str:
        return "twilio"

    async def parse_request(self, request: Request) -> dict[str, str]:
        form = await request.form()
        return {k: str(v) for k, v in form.items()}


class TwilioSmsInboundAdapter(SmsInboundAdapter):
    @property
    def provider_name(self) -> str:
        return "twilio"

    async def parse_inbound(self, request: Request) -> dict[str, str] | None:
        form = await request.form()
        if not form:
            return None
        return {
            "from": str(form.get("From", "")),
            "to": str(form.get("To", "")),
            "text": str(form.get("Body", "")),
        }
