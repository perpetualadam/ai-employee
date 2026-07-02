"""Telnyx inbound SMS webhook adapter."""

from __future__ import annotations

from fastapi import Request

from app.integrations.contracts import SmsInboundAdapter
from app.voice.messaging_webhook import parse_inbound_sms_event


class TelnyxSmsInboundAdapter(SmsInboundAdapter):
    @property
    def provider_name(self) -> str:
        return "telnyx"

    async def parse_inbound(self, request: Request) -> dict[str, str] | None:
        return await parse_inbound_sms_event(request)
