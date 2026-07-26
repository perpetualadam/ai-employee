"""Admin telecom dashboard — verification, provisioning, provider status."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies.providers import get_phone_number_service, get_verification_service
from app.models.enums import PhoneNumberStatus, RegulatoryStatus
from app.providers.factory import (
    get_factory,
    get_messaging_provider,
    get_number_provisioning_provider,
    get_regulatory_provider,
    get_storage_provider,
    get_telephony_provider,
    get_voice_ai_provider,
    list_provider_registry,
)
from app.repositories.phone_number_repository import PhoneNumberRepository
from app.repositories.regulatory_profile_repository import RegulatoryProfileRepository
from app.services.phone_number_service import PhoneNumberService
from app.services.verification_service import VerificationService

router = APIRouter(prefix="/admin/telecom", tags=["admin-telecom"])


def _verify_admin_secret(x_cron_secret: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not settings.cron_secret:
        if settings.debug:
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CRON_SECRET is not configured.",
        )
    if x_cron_secret != settings.cron_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin secret")


@router.get("/dashboard")
def telecom_dashboard(
    db: Session = Depends(get_db),
    _: None = Depends(_verify_admin_secret),
) -> dict:
    phone_repo = PhoneNumberRepository(db)
    profile_repo = RegulatoryProfileRepository(db)

    failed_numbers = phone_repo.list_failed()
    pending_verification = profile_repo.list_by_status(RegulatoryStatus.SUBMITTED)
    rejected = profile_repo.list_by_status(RegulatoryStatus.REJECTED)

    number_provider = get_number_provisioning_provider()
    telephony = get_telephony_provider()
    regulatory = get_regulatory_provider()
    messaging = get_messaging_provider()
    voice = get_voice_ai_provider()
    storage = get_storage_provider()

    return {
        "verification": {
            "pending_count": len(pending_verification),
            "rejected_count": len(rejected),
            "profiles": [
                {
                    "id": p.id,
                    "business_id": p.business_id,
                    "country_code": p.country_code,
                    "status": p.status.value,
                    "provider_bundle_id": p.provider_bundle_id,
                }
                for p in pending_verification[:50]
            ],
        },
        "phone_numbers": {
            "failed_count": len(failed_numbers),
            "failed": [
                {
                    "id": n.id,
                    "business_id": n.business_id,
                    "phone_number": n.phone_number,
                    "status": n.status.value,
                }
                for n in failed_numbers[:50]
            ],
        },
        "documents": {
            "note": "Use per-business document listing via verification API",
        },
        "providers": {
            "number_provisioning": {
                "name": number_provider.provider_name,
                "configured": number_provider.is_configured(),
            },
            "telephony": {
                "name": telephony.provider_name,
                "configured": telephony.is_configured(),
            },
            "regulatory": {
                "name": regulatory.provider_name,
                "configured": regulatory.is_configured(),
            },
            "messaging": {
                "name": messaging.provider_name,
                "configured": messaging.is_configured(),
            },
            "voice_ai": {
                "name": voice.provider_name,
                "configured": voice.is_configured(),
            },
            "storage": {
                "name": storage.provider_name,
                "configured": storage.is_configured(),
            },
            "registry": list_provider_registry(),
            "health": get_factory().health_check(),
        },
    }


@router.post("/provisioning/retry/{record_id}")
def retry_failed_provisioning(
    record_id: str,
    service: PhoneNumberService = Depends(get_phone_number_service),
    _: None = Depends(_verify_admin_secret),
) -> dict:
    return service.retry_failed_provisioning(record_id)


@router.post("/verification/refresh/{profile_id}")
def refresh_verification_status(
    profile_id: str,
    db: Session = Depends(get_db),
    verification: VerificationService = Depends(get_verification_service),
    _: None = Depends(_verify_admin_secret),
) -> dict:
    from app.models.telecom import BusinessRegulatoryProfile

    profile = db.get(BusinessRegulatoryProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    updated = verification.refresh_status(profile)
    return {"id": updated.id, "status": updated.status.value}
