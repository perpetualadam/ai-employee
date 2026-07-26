"""Per-tenant phone number search and provisioning — delegates to PhoneNumberService."""

from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.domain.phone import is_plausible_phone, normalize_phone
from app.domain.telecom import get_example_phone_number, get_number_search_profile
from app.models import Business
from app.providers.exceptions import DuplicateProvisioningError, ProviderError
from app.providers.factory import get_number_provisioning_provider
from app.services.phone_number_service import PhoneNumberService
from app.utils.errors import http_exception_from_provider

logger = logging.getLogger(__name__)


class PhoneProvisioningService:
    """Backward-compatible facade — prefer PhoneNumberService via DI in new code."""

    @staticmethod
    def _service(db: Session, business: Business | None = None) -> PhoneNumberService:
        return PhoneNumberService(
            db,
            get_number_provisioning_provider(business=business, db=db),
        )

    @staticmethod
    def status(business: Business, db: Session | None = None) -> dict:
        if db is not None:
            return PhoneProvisioningService._service(db).status(business)

        provider = get_number_provisioning_provider()
        configured = provider.is_configured()
        already_provisioned = bool(business.phone_provisioned)
        profile = get_number_search_profile(business.country)
        return {
            "phone_number": business.phone_number,
            "provisioned": already_provisioned,
            "platform_configured": configured,
            "can_search": configured and not already_provisioned,
            "manual_fallback_allowed": not already_provisioned,
            "country": business.country,
            "prefix_label": profile.prefix_label,
            "prefix_example": profile.prefix_example,
            "prefix_supported": profile.prefix_param is not None,
            "example_phone": get_example_phone_number(business.country),
            "default_number_type": profile.default_phone_number_type,
            "number_type_options": [
                {"value": value, "label": label}
                for value, label in profile.available_phone_number_types
            ],
            "verification_required": False,
            "verification_status": None,
            "verification_approved": True,
        }

    @staticmethod
    def search_available(
        business: Business,
        *,
        prefix: str | None = None,
        limit: int = 10,
        number_type: str | None = None,
    ) -> list[dict]:
        provider = get_number_provisioning_provider()
        if not provider.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Phone provisioning is not configured on this platform.",
            )
        try:
            return provider.search_numbers(
                business.country,
                prefix=prefix,
                limit=limit,
                number_type=number_type,
            )
        except ProviderError as exc:
            raise http_exception_from_provider(exc) from exc

    @staticmethod
    def _assert_number_available(
        db: Session,
        phone_number: str,
        business_id: str,
        country: str,
    ) -> None:
        from app.repositories.phone_number_repository import PhoneNumberRepository

        try:
            PhoneNumberRepository(db).assert_not_assigned_elsewhere(
                phone_number, business_id, country
            )
        except DuplicateProvisioningError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @staticmethod
    def provision(db: Session, business: Business, phone_number: str) -> dict:
        try:
            return PhoneProvisioningService._service(db, business).provision(business, phone_number)
        except ProviderError as exc:
            raise http_exception_from_provider(exc) from exc

    @staticmethod
    def save_manual_phone(db: Session, business: Business, phone_number: str) -> Business:
        """Fallback when platform provisioning is unavailable."""
        if business.phone_provisioned:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Provisioned numbers cannot be edited manually. Contact support.",
            )

        normalized = normalize_phone(phone_number.strip(), business.country)
        if not is_plausible_phone(normalized, business.country):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Enter a valid phone number in E.164 format.",
            )

        PhoneProvisioningService._assert_number_available(db, normalized, business.id, business.country)
        business.phone_number = normalized
        db.commit()
        db.refresh(business)
        return business
