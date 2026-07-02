"""Telnyx voice provider — backward-compatible shim; prefer integrations.registry."""

from app.integrations.adapters.telnyx_voice import TelnyxVoiceCallControl


class TelnyxVoiceProvider(TelnyxVoiceCallControl):
    """Deprecated alias — use get_voice_call_control() from integrations.registry."""

    async def send_sms(self, from_number: str, to_number: str, body: str) -> str:
        from app.services.messaging.telnyx_sms import TelnyxSmsProvider

        result = TelnyxSmsProvider().send_sms(from_number, to_number, body)
        if not result.get("sent"):
            raise RuntimeError(result.get("error") or "SMS failed")
        return result.get("id", "")
