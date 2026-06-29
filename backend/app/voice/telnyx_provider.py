"""Telnyx voice provider — SMS and call control via TeXML REST API."""

import logging

from app.voice import telnyx_client
from app.voice.texml_builder import build_transfer_texml

logger = logging.getLogger(__name__)


class TelnyxVoiceProvider:
    """Telnyx implementation for SMS and call transfers."""

    async def send_sms(self, from_number: str, to_number: str, body: str) -> str:
        if not telnyx_client.is_telnyx_configured():
            raise RuntimeError("Telnyx is not configured")

        result = telnyx_client.send_sms(from_number, to_number, body)
        return result.get("id", "")

    async def transfer_call(self, call_id: str, to_number: str, from_number: str | None = None) -> None:
        """Redirect an active call to dial another number via TeXML update."""
        if not telnyx_client.is_telnyx_configured():
            raise RuntimeError("Telnyx is not configured")

        texml = build_transfer_texml(to_number)
        telnyx_client.update_call_texml(call_id, texml)
        logger.info("Call transfer initiated", extra={"call_sid": call_id, "to": to_number})
