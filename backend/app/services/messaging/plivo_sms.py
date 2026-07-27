"""Plivo SMS outbound adapter."""

from __future__ import annotations

from app.config import get_settings
from app.providers.capability_presets import runtime_caps, plivo_telephony
from app.services.messaging.provider import SmsProvider
from app.voice import plivo_client


class PlivoSmsProvider(SmsProvider):
    @property
    def provider_name(self) -> str:
        return "plivo"

    def is_configured(self) -> bool:
        return plivo_client.is_plivo_configured()

    def get_capabilities(self):
        return runtime_caps(plivo_telephony(), self, service="messaging")

    def send_sms(self, from_number: str, to_number: str, text: str) -> dict:
        if not self.is_configured():
            return {
                "sent": False,
                "provider": self.provider_name,
                "phone": to_number,
                "error": "Plivo is not configured",
            }
        settings = get_settings()
        sender = from_number or settings.plivo_phone_number
        if not sender:
            return {
                "sent": False,
                "provider": self.provider_name,
                "phone": to_number,
                "error": "Plivo sender number is not configured",
            }
        try:
            result = plivo_client.send_sms(sender, to_number, text)
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
