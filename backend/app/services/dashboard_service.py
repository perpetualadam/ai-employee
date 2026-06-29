"""Dashboard aggregation queries — all scoped by business_id."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import AIActivityLog, Appointment, CallLog, Customer, Job
from app.models.enums import AppointmentStatus, JobStatus
from app.schemas import DashboardSummary


class DashboardService:
    @staticmethod
    def get_summary(db: Session, business_id: str) -> DashboardSummary:
        now = datetime.now(UTC)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        today_appointments = (
            db.query(Appointment)
            .filter(
                Appointment.business_id == business_id,
                Appointment.start_time >= start_of_day,
                Appointment.start_time < end_of_day,
                Appointment.status != AppointmentStatus.CANCELLED,
            )
            .order_by(Appointment.start_time.asc())
            .limit(20)
            .all()
        )

        recent_calls = (
            db.query(CallLog)
            .filter(CallLog.business_id == business_id)
            .order_by(CallLog.created_at.desc())
            .limit(10)
            .all()
        )

        recent_customers = (
            db.query(Customer)
            .filter(Customer.business_id == business_id)
            .order_by(Customer.created_at.desc())
            .limit(10)
            .all()
        )

        recent_jobs = (
            db.query(Job)
            .filter(Job.business_id == business_id)
            .order_by(Job.created_at.desc())
            .limit(10)
            .all()
        )

        recent_ai_activity = (
            db.query(AIActivityLog)
            .filter(AIActivityLog.business_id == business_id)
            .order_by(AIActivityLog.created_at.desc())
            .limit(15)
            .all()
        )

        stats = {
            "customers_total": db.query(func.count(Customer.id))
            .filter(Customer.business_id == business_id)
            .scalar()
            or 0,
            "jobs_open": db.query(func.count(Job.id))
            .filter(
                Job.business_id == business_id,
                Job.status.notin_([JobStatus.COMPLETED, JobStatus.CANCELLED]),
            )
            .scalar()
            or 0,
            "appointments_today": len(today_appointments),
            "calls_this_week": db.query(func.count(CallLog.id))
            .filter(
                CallLog.business_id == business_id,
                CallLog.created_at >= now - timedelta(days=7),
            )
            .scalar()
            or 0,
        }

        return DashboardSummary(
            today_appointments=today_appointments,
            recent_calls=recent_calls,
            recent_customers=recent_customers,
            recent_jobs=recent_jobs,
            recent_ai_activity=recent_ai_activity,
            stats=stats,
        )
