"""Telnyx SMS adapter."""

from app.config import get_settings
from app.providers.capability_presets import runtime_caps, telnyx_telephony
from app.services.messaging.provider import SmsProvider
from app.voice import telnyx_client


class TelnyxSmsProvider(SmsProvider):
    @property
    def provider_name(self) -> str:
        return "telnyx"

    def is_configured(self) -> bool:
        settings = get_settings()
        return telnyx_client.is_telnyx_configured() and bool(settings.telnyx_messaging_profile_id)

    def get_capabilities(self):
        return runtime_caps(telnyx_telephony(), self, service="messaging")

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
