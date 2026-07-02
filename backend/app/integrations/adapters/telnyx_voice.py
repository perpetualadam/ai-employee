"""Telnyx voice call control adapter."""

from __future__ import annotations

import logging

from app.integrations.contracts import VoiceCallControl
from app.voice import telnyx_client
from app.voice.texml_builder import build_transfer_texml

logger = logging.getLogger(__name__)


class TelnyxVoiceCallControl(VoiceCallControl):
    @property
    def provider_name(self) -> str:
        return "telnyx"

    def is_configured(self) -> bool:
        return telnyx_client.is_telnyx_configured()

    async def transfer_call(self, call_id: str, to_number: str) -> None:
        if not self.is_configured():
            raise RuntimeError("Telnyx voice is not configured")
        texml = build_transfer_texml(to_number)
        telnyx_client.update_call_texml(call_id, texml)
        logger.info("Call transfer initiated", extra={"call_sid": call_id, "to": to_number})
