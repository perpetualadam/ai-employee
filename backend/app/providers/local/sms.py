"""Local SMS provider for development and testing."""

from __future__ import annotations

import logging
import uuid

from app.providers.base import ProviderResult
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import local_sms, runtime_caps
from app.providers.messaging import MessagingProvider

logger = logging.getLogger(__name__)


class LocalSMSProvider(MessagingProvider):
    @property
    def provider_name(self) -> str:
        return "local_sms"

    def is_configured(self) -> bool:
        return True

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(local_sms(), self, service="messaging")

    def send_sms(self, *, from_number: str, to_number: str, text: str) -> ProviderResult:
        message_id = str(uuid.uuid4())
        logger.info(
            "Local SMS (dev)",
            extra={"from": from_number, "to": to_number, "text": text[:120], "id": message_id},
        )
        return ProviderResult(
            provider=self.provider_name,
            external_id=message_id,
            data={"sent": True, "to": to_number},
        )

    def send_email(self, *, to: str, subject: str, body: str) -> ProviderResult:
        message_id = str(uuid.uuid4())
        logger.info(
            "Local email (dev)",
            extra={"to": to, "subject": subject, "body_preview": body[:120], "id": message_id},
        )
        return ProviderResult(
            provider=self.provider_name,
            external_id=message_id,
            data={"sent": True, "to": to},
        )

    def send_whatsapp(self, *, from_number: str, to_number: str, text: str) -> ProviderResult:
        return self.send_sms(from_number=from_number, to_number=to_number, text=text)
