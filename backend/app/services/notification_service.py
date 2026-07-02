"""SMS and email notification service."""

import logging
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.config import get_settings
from app.integrations.registry import get_email_provider
from app.models import Appointment, Business, Customer, User
from app.services.messaging.factory import get_sms_provider_for_business
from app.voice.slots import spoken_local_time

logger = logging.getLogger(__name__)


class NotificationService:
    """Sends customer notifications via configurable SMS and email providers."""

    def __init__(self, db: Session, business: Business):
        self.db = db
        self.business = business

    def _from_number(self) -> str | None:
        settings = get_settings()
        return self.business.phone_number or settings.telnyx_phone_number or None

    def is_sms_functional(self) -> bool:
        """True when outbound SMS can be sent for this business (provider + sender configured)."""
        provider = get_sms_provider_for_business(self.business)
        if provider.provider_name == "dev_log":
            return False
        if not provider.is_configured():
            return False
        if not self._from_number():
            return False
        settings = get_settings()
        if provider.provider_name == "telnyx" and not settings.telnyx_messaging_profile_id:
            return False
        return True

    def send_sms(self, phone: str, message: str) -> dict:
        provider = get_sms_provider_for_business(self.business)
        if not provider.is_configured():
            provider = get_sms_provider_for_business(None)
        if provider.provider_name == "dev_log" or not provider.is_configured():
            logger.info(
                "SMS logged (dev mode)",
                extra={"to": phone, "message": message, "business_id": self.business.id},
            )
            return {"sent": True, "provider": "dev_log", "phone": phone, "message": message}

        from_number = self._from_number()
        if not from_number:
            logger.error("No from number for SMS", extra={"business_id": self.business.id})
            return {
                "sent": False,
                "provider": provider.provider_name,
                "error": "No sender phone configured",
            }

        result = provider.send_sms(from_number, phone, message)
        if not result.get("sent"):
            logger.error(
                "SMS delivery failed",
                extra={
                    "to": phone,
                    "provider": provider.provider_name,
                    "error": result.get("error"),
                },
            )
        return result

    def send_email(self, email: str, subject: str, body: str) -> dict:
        provider = get_email_provider()
        if provider.provider_name == "dev_log" or not provider.is_configured():
            logger.info(
                "Email logged (dev mode)",
                extra={"to": email, "subject": subject, "business_id": self.business.id},
            )
            return {"sent": True, "provider": "dev_log", "email": email, "subject": subject}

        result = provider.send_email(email, subject, body)
        if not result.get("sent"):
            logger.error(
                "Email delivery failed",
                extra={
                    "to": email,
                    "provider": provider.provider_name,
                    "error": result.get("error"),
                },
            )
        return result

    def send_booking_confirmation_email(
        self,
        customer: Customer,
        appointment: Appointment,
    ) -> dict:
        if not customer.email:
            return {"sent": False, "skipped": True, "reason": "No customer email"}

        tz = ZoneInfo(self.business.timezone)
        local_start = appointment.start_time.astimezone(tz)
        when_label = (
            f"{local_start.strftime('%A, %B')} {local_start.day} "
            f"at {spoken_local_time(local_start)}"
        )

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
        """Alert the business owner when the AI escalates (SMS first, then owner email)."""
        caller = (caller_phone or "").strip()
        if not caller or caller in ("text-chat", "unknown"):
            caller_label = "a customer (no number on file)"
        else:
            caller_label = caller

        owner_phone = self.business.escalation_phone or self.business.phone_number
        if owner_phone:
            message = (
                f"AI Employee ({self.business.name}): {reason} "
                f"Caller: {caller_label}. Please call them back as soon as you can."
            )
            sms_result = self.send_sms(owner_phone, message)
            if sms_result.get("sent"):
                return True

        owner = self.db.query(User).filter(User.id == self.business.owner_id).first()
        if owner and owner.email:
            subject = f"AI Employee escalation — {self.business.name}"
            body = (
                f"Your AI receptionist escalated a conversation.\n\n"
                f"Reason: {reason}\n"
                f"Caller: {caller_label}\n\n"
                f"Please call them back as soon as you can.\n\n"
                f"— AI Employee"
            )
            email_result = self.send_email(owner.email, subject, body)
            if email_result.get("sent"):
                return True

        logger.warning(
            "Escalation with no owner notification delivered",
            extra={"business_id": self.business.id, "reason": reason},
        )
        return False
