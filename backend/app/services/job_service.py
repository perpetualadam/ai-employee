"""Job/work order service — scoped by business_id."""

import logging

from sqlalchemy.orm import Session

from app.models import Job
from app.models.enums import JobStatus
from app.schemas import JobCreate, JobUpdate
from app.services.tenant import get_customer_for_business

logger = logging.getLogger(__name__)


class JobService:
    @staticmethod
    def list_jobs(
        db: Session,
        business_id: str,
        status: JobStatus | None = None,
        customer_id: str | None = None,
    ) -> list[Job]:
        query = db.query(Job).filter(Job.business_id == business_id)
        if status:
            query = query.filter(Job.status == status)
        if customer_id:
            query = query.filter(Job.customer_id == customer_id)
        return query.order_by(Job.created_at.desc()).all()

    @staticmethod
    def get_job(db: Session, business_id: str, job_id: str) -> Job | None:
        return db.query(Job).filter(Job.id == job_id, Job.business_id == business_id).first()

    @staticmethod
    def create_job(db: Session, business_id: str, data: JobCreate) -> Job:
        customer = get_customer_for_business(db, business_id, data.customer_id)
        if customer is None:
            raise ValueError("Customer not found")

        job = Job(
            business_id=business_id,
            customer_id=data.customer_id,
            service_type=data.service_type.strip(),
            notes=data.notes,
            status=data.status,
            appointment_time=data.appointment_time,
            appointment_id=data.appointment_id,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        logger.info("Job created", extra={"business_id": business_id, "job_id": job.id})
        return job

    @staticmethod
    def update_job(db: Session, job: Job, data: JobUpdate) -> Job:
        update_data = data.model_dump(exclude_unset=True)
        if "appointment_id" in update_data and update_data["appointment_id"]:
            from app.models import Appointment

            appt = (
                db.query(Appointment)
                .filter(
                    Appointment.id == update_data["appointment_id"],
                    Appointment.business_id == job.business_id,
                )
                .first()
            )
            if appt is None:
                raise ValueError("Appointment not found")

        for field, value in update_data.items():
            if field == "service_type" and isinstance(value, str):
                value = value.strip()
            setattr(job, field, value)
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def delete_job(db: Session, job: Job) -> None:
        db.delete(job)
        db.commit()
