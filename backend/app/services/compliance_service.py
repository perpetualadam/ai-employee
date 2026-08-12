"""GDPR-style account data export and deletion."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import (
    Appointment,
    Business,
    CallLog,
    Customer,
    Job,
    SmsLog,
    User,
)
from app.providers.storage import StorageProvider
from app.services.call_recording_service import CallRecordingService


class ComplianceService:
    @staticmethod
    def export_account_data(db: Session, user: User, business: Business) -> dict:
        customers = (
            db.query(Customer)
            .filter(Customer.business_id == business.id)
            .order_by(Customer.created_at.desc())
            .all()
        )
        jobs = (
            db.query(Job)
            .filter(Job.business_id == business.id)
            .order_by(Job.created_at.desc())
            .limit(500)
            .all()
        )
        appointments = (
            db.query(Appointment)
            .filter(Appointment.business_id == business.id)
            .order_by(Appointment.start_time.desc())
            .limit(500)
            .all()
        )
        calls = (
            db.query(CallLog)
            .filter(CallLog.business_id == business.id)
            .order_by(CallLog.created_at.desc())
            .limit(500)
            .all()
        )
        sms_logs = (
            db.query(SmsLog)
            .filter(SmsLog.business_id == business.id)
            .order_by(SmsLog.created_at.desc())
            .limit(500)
            .all()
        )

        return {
            "exported_at": datetime.now(UTC).isoformat(),
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
            "business": {
                "id": business.id,
                "name": business.name,
                "industry": business.industry.value if hasattr(business.industry, "value") else str(business.industry),
                "country": business.country,
                "timezone": business.timezone,
                "phone_number": business.phone_number,
                "public_slug": business.public_slug,
                "subscription_status": business.subscription_status.value
                if hasattr(business.subscription_status, "value")
                else str(business.subscription_status),
                "created_at": business.created_at.isoformat() if business.created_at else None,
            },
            "customers": [
                {
                    "id": c.id,
                    "name": c.name,
                    "phone": c.phone,
                    "email": c.email,
                    "address": c.address,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in customers
            ],
            "jobs": [
                {
                    "id": j.id,
                    "customer_id": j.customer_id,
                    "service_type": j.service_type,
                    "status": j.status.value if hasattr(j.status, "value") else str(j.status),
                    "created_at": j.created_at.isoformat() if j.created_at else None,
                }
                for j in jobs
            ],
            "appointments": [
                {
                    "id": a.id,
                    "customer_id": a.customer_id,
                    "service_type": a.service_type,
                    "start_time": a.start_time.isoformat() if a.start_time else None,
                    "status": a.status.value if hasattr(a.status, "value") else str(a.status),
                }
                for a in appointments
            ],
            "call_logs": [
                {
                    "id": call.id,
                    "caller_phone": call.caller_phone,
                    "status": call.status.value if hasattr(call.status, "value") else str(call.status),
                    "summary": call.summary,
                    "recording_status": call.recording_status,
                    "recording_storage_key": call.recording_storage_key,
                    "created_at": call.created_at.isoformat() if call.created_at else None,
                }
                for call in calls
            ],
            "sms_logs": [
                {
                    "id": sms.id,
                    "direction": sms.direction.value if hasattr(sms.direction, "value") else str(sms.direction),
                    "from_number": sms.from_number,
                    "to_number": sms.to_number,
                    "body": sms.body,
                    "call_log_id": sms.call_log_id,
                    "created_at": sms.created_at.isoformat() if sms.created_at else None,
                }
                for sms in sms_logs
            ],
        }

    @staticmethod
    def delete_account(
        db: Session,
        user: User,
        *,
        storage: StorageProvider | None = None,
    ) -> None:
        """
        Delete the user and cascaded tenant rows.

        Object-storage artifacts (call recordings) are removed first — cascading
        CallLog deletes would otherwise drop recording_storage_key while leaving
        bytes under recordings/{business_id}/...
        """
        business_ids = [
            business_id
            for (business_id,) in db.query(Business.id)
            .filter(Business.owner_id == user.id)
            .all()
        ]
        CallRecordingService.delete_stored_recordings_for_businesses(
            db,
            business_ids,
            storage=storage,
        )
        db.delete(user)
        db.commit()
