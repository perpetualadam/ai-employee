"""FastAPI dependency injection for providers and services."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.deps import get_user_primary_business
from app.database import get_db
from app.models import Business
from app.providers.factory import (
    get_call_service,
    get_messaging_provider,
    get_number_provisioning_provider,
    get_regulatory_provider,
    get_storage_provider,
    get_voice_ai_provider,
)
from app.providers.messaging import MessagingProvider
from app.providers.number_provisioning import NumberProvisioningProvider
from app.providers.regulatory import RegulatoryProvider
from app.providers.storage import StorageProvider
from app.providers.voice import VoiceProvider
from app.services.call_service import CallService
from app.services.communication_service import CommunicationService
from app.services.phone_number_service import PhoneNumberService
from app.services.verification_service import VerificationService
from app.services.voice_service import VoiceService


def get_phone_number_service(
    db: Session = Depends(get_db),
    business: Business = Depends(get_user_primary_business),
) -> PhoneNumberService:
    number_provider = get_number_provisioning_provider(business=business, db=db)
    return PhoneNumberService(db, number_provider)


def get_verification_service(
    db: Session = Depends(get_db),
    business: Business = Depends(get_user_primary_business),
) -> VerificationService:
    regulatory_provider = get_regulatory_provider(business=business, db=db)
    storage_provider = get_storage_provider()
    return VerificationService(db, regulatory_provider, storage_provider)


def get_communication_service(
    db: Session = Depends(get_db),
    business: Business = Depends(get_user_primary_business),
) -> CommunicationService:
    messaging_provider = get_messaging_provider(business=business, db=db)
    return CommunicationService(messaging_provider, db=db, business_id=business.id)


def get_voice_service(
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
) -> VoiceService:
    voice_provider = get_voice_ai_provider(business=business, db=db)
    return VoiceService(voice_provider)


def get_call_service_dep(
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
) -> CallService:
    return get_call_service(business=business, db=db)
