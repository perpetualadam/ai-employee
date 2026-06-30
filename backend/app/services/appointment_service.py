"""Calendar and appointment scheduling service."""

import logging
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models import Appointment, Business, Job
from app.models.enums import AppointmentStatus, JobStatus
from app.schemas import AppointmentCreate, AppointmentUpdate
from app.services.tenant import get_customer_for_business

logger = logging.getLogger(__name__)

DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _parse_time(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class AppointmentService:
    @staticmethod
    def list_appointments(
        db: Session,
        business_id: str,
        start: datetime | None = None,
        end: datetime | None = None,
        status: AppointmentStatus | None = None,
    ) -> list[Appointment]:
        query = db.query(Appointment).filter(Appointment.business_id == business_id)
        if start:
            query = query.filter(Appointment.start_time >= _ensure_utc(start))
        if end:
            query = query.filter(Appointment.start_time <= _ensure_utc(end))
        if status:
            query = query.filter(Appointment.status == status)
        return query.order_by(Appointment.start_time.asc()).all()

    @staticmethod
    def get_appointment(db: Session, business_id: str, appointment_id: str) -> Appointment | None:
        return (
            db.query(Appointment)
            .filter(Appointment.id == appointment_id, Appointment.business_id == business_id)
            .first()
        )

    @staticmethod
    def get_availability(
        db: Session,
        business: Business,
        target_date: date,
        duration_minutes: int = 60,
        exclude_appointment_id: str | None = None,
    ) -> list[dict[str, datetime]]:
        tz = ZoneInfo(business.timezone)
        day_key = DAY_NAMES[target_date.weekday()]
        hours = business.working_hours.get(day_key, {})

        if hours.get("closed"):
            return []

        open_time = _parse_time(hours.get("open", "08:00"))
        close_time = _parse_time(hours.get("close", "17:00"))
        day_start = datetime.combine(target_date, open_time, tzinfo=tz)
        day_end = datetime.combine(target_date, close_time, tzinfo=tz)

        if day_end <= day_start:
            return []

        candidate_slots: list[tuple[datetime, datetime]] = []
        current = day_start
        delta = timedelta(minutes=duration_minutes)
        while current + delta <= day_end:
            candidate_slots.append((current, current + delta))
            current += delta

        day_start_utc = day_start.astimezone(UTC)
        day_end_utc = day_end.astimezone(UTC)

        query = db.query(Appointment).filter(
            Appointment.business_id == business.id,
            Appointment.status != AppointmentStatus.CANCELLED,
            Appointment.start_time < day_end_utc,
            Appointment.end_time > day_start_utc,
        )
        if exclude_appointment_id:
            query = query.filter(Appointment.id != exclude_appointment_id)
        existing = query.all()

        available: list[dict[str, datetime]] = []
        for slot_start, slot_end in candidate_slots:
            slot_start_utc = slot_start.astimezone(UTC)
            slot_end_utc = slot_end.astimezone(UTC)
            overlaps = any(
                slot_start_utc < _ensure_utc(appt.end_time)
                and slot_end_utc > _ensure_utc(appt.start_time)
                for appt in existing
            )
            if not overlaps:
                available.append({"start_time": slot_start_utc, "end_time": slot_end_utc})

        return available

    @staticmethod
    def find_next_available(
        db: Session,
        business: Business,
        start_date: date,
        duration_minutes: int = 60,
        *,
        max_days: int = 14,
    ) -> tuple[date | None, list[dict[str, datetime]]]:
        """First date on or after start_date with at least one open slot."""
        for offset in range(max_days):
            candidate = start_date + timedelta(days=offset)
            slots = AppointmentService.get_availability(db, business, candidate, duration_minutes)
            if slots:
                return candidate, slots
        return None, []

    @staticmethod
    def _validate_slot_available(
        db: Session,
        business: Business,
        start_time: datetime,
        end_time: datetime,
        exclude_appointment_id: str | None = None,
    ) -> None:
        start_utc = _ensure_utc(start_time)
        end_utc = _ensure_utc(end_time)

        if end_utc <= start_utc:
            raise ValueError("End time must be after start time")

        tz = ZoneInfo(business.timezone)
        local_start = start_utc.astimezone(tz)
        local_date = local_start.date()
        duration = int((end_utc - start_utc).total_seconds() // 60)

        slots = AppointmentService.get_availability(
            db, business, local_date, duration, exclude_appointment_id
        )
        if not any(
            _ensure_utc(s["start_time"]) == start_utc and _ensure_utc(s["end_time"]) == end_utc
            for s in slots
        ):
            raise ValueError("Selected time slot is not available")

    @staticmethod
    def create_appointment(
        db: Session,
        business: Business,
        data: AppointmentCreate,
        create_job: bool = True,
    ) -> Appointment:
        customer = get_customer_for_business(db, business.id, data.customer_id)
        if customer is None:
            raise ValueError("Customer not found")

        AppointmentService._validate_slot_available(
            db, business, data.start_time, data.end_time
        )

        appointment = Appointment(
            business_id=business.id,
            customer_id=data.customer_id,
            service_type=data.service_type.strip(),
            start_time=_ensure_utc(data.start_time),
            end_time=_ensure_utc(data.end_time),
            notes=data.notes,
            status=AppointmentStatus.SCHEDULED,
        )
        db.add(appointment)
        db.flush()

        if create_job:
            job = Job(
                business_id=business.id,
                customer_id=data.customer_id,
                appointment_id=appointment.id,
                service_type=appointment.service_type,
                notes=data.notes,
                status=JobStatus.SCHEDULED,
                appointment_time=appointment.start_time,
            )
            db.add(job)

        db.commit()
        db.refresh(appointment)
        logger.info(
            "Appointment booked",
            extra={"business_id": business.id, "appointment_id": appointment.id},
        )
        return appointment

    @staticmethod
    def update_appointment(
        db: Session,
        business: Business,
        appointment: Appointment,
        data: AppointmentUpdate,
    ) -> Appointment:
        update_data = data.model_dump(exclude_unset=True)

        new_start = update_data.get("start_time", appointment.start_time)
        new_end = update_data.get("end_time", appointment.end_time)

        if "start_time" in update_data or "end_time" in update_data:
            if appointment.status == AppointmentStatus.CANCELLED:
                raise ValueError("Cannot reschedule a cancelled appointment")
            AppointmentService._validate_slot_available(
                db,
                business,
                new_start,
                new_end,
                exclude_appointment_id=appointment.id,
            )
            update_data["start_time"] = _ensure_utc(new_start)
            update_data["end_time"] = _ensure_utc(new_end)

        for field, value in update_data.items():
            if field == "service_type" and isinstance(value, str):
                value = value.strip()
            setattr(appointment, field, value)

        # Sync linked job if times changed
        if "start_time" in update_data:
            linked_job = (
                db.query(Job)
                .filter(Job.appointment_id == appointment.id, Job.business_id == business.id)
                .first()
            )
            if linked_job:
                linked_job.appointment_time = appointment.start_time
                if linked_job.status == JobStatus.SCHEDULED:
                    linked_job.service_type = appointment.service_type

        db.commit()
        db.refresh(appointment)
        return appointment

    @staticmethod
    def cancel_appointment(db: Session, business_id: str, appointment: Appointment) -> Appointment:
        if appointment.status == AppointmentStatus.CANCELLED:
            raise ValueError("Appointment is already cancelled")

        appointment.status = AppointmentStatus.CANCELLED
        linked_job = (
            db.query(Job)
            .filter(Job.appointment_id == appointment.id, Job.business_id == business_id)
            .first()
        )
        if linked_job and linked_job.status not in (JobStatus.COMPLETED, JobStatus.CANCELLED):
            linked_job.status = JobStatus.CANCELLED

        db.commit()
        db.refresh(appointment)
        logger.info(
            "Appointment cancelled",
            extra={"business_id": business_id, "appointment_id": appointment.id},
        )
        return appointment
