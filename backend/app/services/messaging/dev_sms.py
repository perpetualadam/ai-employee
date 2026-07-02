"""Development SMS adapter — logs messages when no provider is configured."""

import logging

from app.services.messaging.provider import SmsProvider

logger = logging.getLogger(__name__)


class DevSmsProvider(SmsProvider):
    @property
    def provider_name(self) -> str:
        return "dev_log"

    def is_configured(self) -> bool:
        return True

    def send_sms(self, from_number: str, to_number: str, text: str) -> dict:
        logger.info(
            "SMS logged (dev mode)",
            extra={"from": from_number, "to": to_number, "message": text},
        )
        return {
            "sent": True,
            "provider": self.provider_name,
            "phone": to_number,
            "message": text,
        }
