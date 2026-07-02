"""Appointment reminder SMS/email delivery."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.config import get_settings
from app.domain.phone import is_plausible_phone
from app.models import Appointment, Business, Customer
from app.models.enums import AppointmentStatus
from app.services.notification_service import NotificationService
from app.voice.slots import spoken_local_time

logger = logging.getLogger(__name__)


class ReminderService:
    @staticmethod
    def due_appointments(db: Session, *, hours_before: int | None = None) -> list[Appointment]:
        settings = get_settings()
        lead = hours_before if hours_before is not None else settings.reminder_hours_before
        now = datetime.now(UTC)
        window_start = now + timedelta(hours=max(lead - 1, 0))
        window_end = now + timedelta(hours=lead + 1)

        return (
            db.query(Appointment)
            .join(Business, Appointment.business_id == Business.id)
            .filter(
                Appointment.status == AppointmentStatus.SCHEDULED,
                Appointment.reminder_sent_at.is_(None),
                Appointment.start_time >= window_start,
                Appointment.start_time <= window_end,
                Business.reminders_enabled.is_(True),
            )
            .order_by(Appointment.start_time.asc())
            .all()
        )

    @staticmethod
    def send_reminder(db: Session, appointment: Appointment) -> dict:
        business = db.query(Business).filter(Business.id == appointment.business_id).first()
        customer = db.query(Customer).filter(Customer.id == appointment.customer_id).first()
        if business is None or customer is None:
            return {"sent": False, "skipped": True, "reason": "Missing business or customer"}

        tz = ZoneInfo(business.timezone)
        local_start = appointment.start_time.astimezone(tz)
        when_label = (
            f"{local_start.strftime('%A, %B')} {local_start.day} "
            f"at {spoken_local_time(local_start)}"
        )

        notifications = NotificationService(db, business)
        sms_sent = False
        email_sent = False

        if customer.phone and is_plausible_phone(customer.phone, business.country):
            message = (
                f"Reminder from {business.name}: your {appointment.service_type} appointment "
                f"is tomorrow at {spoken_local_time(local_start)} ({business.timezone}). "
                f"Reply or call us if you need to reschedule."
            )
            sms_result = notifications.send_sms(customer.phone, message)
            sms_sent = bool(sms_result.get("sent"))

        if customer.email:
            subject = f"Appointment reminder — {business.name}"
            body = (
                f"Hi {customer.name},\n\n"
                f"This is a friendly reminder about your upcoming appointment:\n\n"
                f"Service: {appointment.service_type}\n"
                f"When: {when_label} ({business.timezone})\n"
                f"Address: {customer.address or 'On file'}\n\n"
                f"Reply to this email or call us if you need to reschedule.\n\n"
                f"— {business.name}"
            )
            email_result = notifications.send_email(customer.email, subject, body)
            email_sent = bool(email_result.get("sent"))

        if sms_sent or email_sent:
            appointment.reminder_sent_at = datetime.now(UTC)
            db.commit()
            logger.info(
                "Appointment reminder sent",
                extra={
                    "appointment_id": appointment.id,
                    "business_id": business.id,
                    "sms_sent": sms_sent,
                    "email_sent": email_sent,
                },
            )
            return {
                "sent": True,
                "appointment_id": appointment.id,
                "sms_sent": sms_sent,
                "email_sent": email_sent,
            }

        return {
            "sent": False,
            "appointment_id": appointment.id,
            "skipped": True,
            "reason": "No deliverable SMS or email for customer",
        }

    @staticmethod
    def run_due_reminders(db: Session) -> dict:
        appointments = ReminderService.due_appointments(db)
        results = []
        sent_count = 0
        for appointment in appointments:
            result = ReminderService.send_reminder(db, appointment)
            results.append(result)
            if result.get("sent"):
                sent_count += 1
        return {
            "checked": len(appointments),
            "sent": sent_count,
            "results": results,
        }
