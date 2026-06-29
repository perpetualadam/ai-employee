"""Twilio voice provider — REST API for SMS and call control."""

import logging

from twilio.rest import Client

from app.voice.twilio_client import get_twilio_client

logger = logging.getLogger(__name__)


class TwilioVoiceProvider:
    """Twilio implementation for SMS and call transfers."""

    def __init__(self, account_sid: str | None = None, auth_token: str | None = None):
        self._client = get_twilio_client()
        if account_sid and auth_token:
            self._client = Client(account_sid, auth_token)

    async def send_sms(self, from_number: str, to_number: str, body: str) -> str:
        if self._client is None:
            raise RuntimeError("Twilio is not configured")

        message = self._client.messages.create(
            body=body,
            from_=from_number,
            to=to_number,
        )
        logger.info("SMS sent", extra={"sid": message.sid, "to": to_number})
        return message.sid

    async def transfer_call(self, call_id: str, to_number: str, from_number: str | None = None) -> None:
        """Redirect an active call to dial another number via TwiML update."""
        if self._client is None:
            raise RuntimeError("Twilio is not configured")

        from app.voice.twiml_builder import build_transfer_twiml

        twiml = build_transfer_twiml(to_number)
        self._client.calls(call_id).update(twiml=twiml)
        logger.info("Call transfer initiated", extra={"call_sid": call_id, "to": to_number})
