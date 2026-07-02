"""Telnyx SMS adapter."""

from app.services.messaging.provider import SmsProvider
from app.voice import telnyx_client


class TelnyxSmsProvider(SmsProvider):
    @property
    def provider_name(self) -> str:
        return "telnyx"

    def is_configured(self) -> bool:
        return telnyx_client.is_telnyx_configured()

    def send_sms(self, from_number: str, to_number: str, text: str) -> dict:
        try:
            result = telnyx_client.send_sms(from_number, to_number, text)
            return {
                "sent": True,
                "provider": self.provider_name,
                "phone": to_number,
                "message": text,
                "id": result.get("id"),
            }
        except Exception as exc:
            return {
                "sent": False,
                "provider": self.provider_name,
                "phone": to_number,
                "error": str(exc),
            }
