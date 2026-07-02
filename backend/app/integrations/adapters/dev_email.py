"""Development email adapter — logs when SMTP is unset."""

from __future__ import annotations

import logging

from app.integrations.contracts import EmailProvider

logger = logging.getLogger(__name__)


class DevEmailProvider(EmailProvider):
    @property
    def provider_name(self) -> str:
        return "dev_log"

    def is_configured(self) -> bool:
        return True

    def send_email(self, to: str, subject: str, body: str) -> dict:
        logger.info("Email logged (dev mode)", extra={"to": to, "subject": subject})
        return {"sent": True, "provider": self.provider_name, "email": to, "subject": subject}
