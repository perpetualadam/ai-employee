"""SMS and email notification service."""

import logging
import smtplib
from datetime import UTC, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Appointment, Business, Customer
from app.voice import telnyx_client

logger = logging.getLogger(__name__)


class NotificationService:
    """Sends customer notifications via Telnyx SMS and optional SMTP email."""

    def __init__(self, db: Session, business: Business):
        self.db = db
        self.business = business

    def _from_number(self) -> str | None:
        settings = get_settings()
        return self.business.phone_number or settings.telnyx_phone_number or None

    def _smtp_configured(self) -> bool:
        settings = get_settings()
        return bool(settings.smtp_host and settings.smtp_from_email)

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
        if not self._smtp_configured():
            logger.info(
                "Email logged (dev mode)",
                extra={"to": email, "subject": subject, "business_id": self.business.id},
            )
            return {"sent": True, "provider": "dev_log", "email": email, "subject": subject}

        settings = get_settings()
        msg = MIMEMultipart()
        msg["From"] = settings.smtp_from_email
        msg["To"] = email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
                if settings.smtp_use_tls:
                    server.starttls()
                if settings.smtp_user:
                    server.login(settings.smtp_user, settings.smtp_password)
                server.sendmail(settings.smtp_from_email, [email], msg.as_string())
            return {"sent": True, "provider": "smtp", "email": email, "subject": subject}
        except Exception as exc:
            logger.exception("SMTP email failed", extra={"to": email})
            return {"sent": False, "provider": "smtp", "error": str(exc)}

    def send_booking_confirmation_email(
        self,
        customer: Customer,
        appointment: Appointment,
    ) -> dict:
        if not customer.email:
            return {"sent": False, "skipped": True, "reason": "No customer email"}

        tz = ZoneInfo(self.business.timezone)
        local_start = appointment.start_time.astimezone(tz)
        when_label = local_start.strftime("%A, %B %d at %I:%M %p").replace("  ", " ")

        subject = f"Your appointment with {self.business.name}"
        body = (
            f"Hi {customer.name},\n\n"
            f"Your appointment is confirmed:\n\n"
            f"Service: {appointment.service_type}\n"
            f"Date/Time: {when_label} ({self.business.timezone})\n"
            f"Address: {customer.address or 'On file'}\n\n"
            f"Reply to this email if anything changes.\n\n"
            f"— {self.business.name}"
        )
        result = self.send_email(customer.email, subject, body)
        if result.get("sent"):
            appointment.confirmation_sent_at = datetime.now(UTC)
            self.db.commit()
        return result

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
