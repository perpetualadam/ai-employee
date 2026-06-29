"""SMS and email notification service."""

import logging

from sqlalchemy.orm import Session

from app.models import Business
from app.voice.twilio_client import get_twilio_client, is_twilio_configured

logger = logging.getLogger(__name__)


class NotificationService:
    """Sends customer notifications via Twilio SMS when configured."""

    def __init__(self, db: Session, business: Business):
        self.db = db
        self.business = business

    def _from_number(self) -> str | None:
        from app.config import get_settings

        settings = get_settings()
        return self.business.phone_number or settings.twilio_phone_number or None

    def send_sms(self, phone: str, message: str) -> dict:
        if not is_twilio_configured():
            logger.info(
                "SMS logged (dev mode)",
                extra={"to": phone, "message": message, "business_id": self.business.id},
            )
            return {"sent": True, "provider": "dev_log", "phone": phone, "message": message}

        from_number = self._from_number()
        if not from_number:
            logger.error("No from number for SMS", extra={"business_id": self.business.id})
            return {"sent": False, "provider": "twilio", "error": "No sender phone configured"}

        client = get_twilio_client()
        if client is None:
            return {"sent": False, "provider": "twilio", "error": "Twilio not configured"}

        try:
            msg = client.messages.create(body=message, from_=from_number, to=phone)
            logger.info("SMS sent via Twilio", extra={"sid": msg.sid, "to": phone})
            return {
                "sent": True,
                "provider": "twilio",
                "phone": phone,
                "message": message,
                "sid": msg.sid,
            }
        except Exception as exc:
            logger.exception("Twilio SMS failed", extra={"to": phone})
            return {"sent": False, "provider": "twilio", "error": str(exc)}

    def send_email(self, email: str, subject: str, body: str) -> dict:
        logger.info(
            "Email logged (dev mode)",
            extra={"to": email, "subject": subject, "business_id": self.business.id},
        )
        return {"sent": True, "provider": "dev_log", "email": email, "subject": subject}
