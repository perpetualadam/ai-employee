"""SMS and email notification service."""

import logging

from sqlalchemy.orm import Session

from app.models import Business
from app.voice import telnyx_client

logger = logging.getLogger(__name__)


class NotificationService:
    """Sends customer notifications via Telnyx SMS when configured."""

    def __init__(self, db: Session, business: Business):
        self.db = db
        self.business = business

    def _from_number(self) -> str | None:
        from app.config import get_settings

        settings = get_settings()
        return self.business.phone_number or settings.telnyx_phone_number or None

    def send_sms(self, phone: str, message: str) -> dict:
        if not telnyx_client.is_telnyx_configured():
            logger.info(
                "SMS logged (dev mode)",
                extra={"to": phone, "message": message, "business_id": self.business.id},
            )
            return {"sent": True, "provider": "dev_log", "phone": phone, "message": message}

        from_number = self._from_number()
        if not from_number:
            logger.error("No from number for SMS", extra={"business_id": self.business.id})
            return {"sent": False, "provider": "telnyx", "error": "No sender phone configured"}

        try:
            result = telnyx_client.send_sms(from_number, phone, message)
            return {
                "sent": True,
                "provider": "telnyx",
                "phone": phone,
                "message": message,
                "id": result.get("id"),
            }
        except Exception as exc:
            logger.exception("Telnyx SMS failed", extra={"to": phone})
            return {"sent": False, "provider": "telnyx", "error": str(exc)}

    def send_email(self, email: str, subject: str, body: str) -> dict:
        logger.info(
            "Email logged (dev mode)",
            extra={"to": email, "subject": subject, "business_id": self.business.id},
        )
        return {"sent": True, "provider": "dev_log", "email": email, "subject": subject}

    def notify_owner_escalation(self, reason: str, caller_phone: str | None) -> bool:
        """Text the business owner when the AI escalates (chat or failed auto-handling)."""
        owner_phone = self.business.escalation_phone or self.business.phone_number
        if not owner_phone:
            logger.warning(
                "Escalation with no owner phone configured",
                extra={"business_id": self.business.id, "reason": reason},
            )
            return False

        caller = (caller_phone or "").strip()
        if not caller or caller in ("text-chat", "unknown"):
            caller_label = "a customer (no number on file)"
        else:
            caller_label = caller

        message = (
            f"AI Employee ({self.business.name}): {reason} "
            f"Caller: {caller_label}. Please call them back as soon as you can."
        )
        result = self.send_sms(owner_phone, message)
        return bool(result.get("sent"))
