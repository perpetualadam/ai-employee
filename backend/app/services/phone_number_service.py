"""Phone number provisioning — uses NumberProvisioningProvider only."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.domain.phone import is_plausible_phone, normalize_phone
from app.domain.telecom import get_example_phone_number, get_number_search_profile
from app.models import Business
from app.models.enums import PhoneNumberStatus, RegulatoryStatus
from app.providers.exceptions import (
    DuplicateProvisioningError,
    MissingDocumentsError,
    ProviderError,
    ProviderUnavailableError,
)
from app.providers.number_provisioning import NumberProvisioningProvider
from app.repositories.country_regulation_repository import CountryRegulationRepository
from app.repositories.phone_number_repository import PhoneNumberRepository
from app.repositories.regulatory_profile_repository import RegulatoryProfileRepository
from app.utils.retry import with_retry

logger = logging.getLogger(__name__)


class PhoneNumberService:
    def __init__(
        self,
        db: Session,
        number_provider: NumberProvisioningProvider,
    ) -> None:
        self._db = db
        self._number_provider = number_provider
        self._phone_repo = PhoneNumberRepository(db)
        self._regulation_repo = CountryRegulationRepository(db)
        self._profile_repo = RegulatoryProfileRepository(db)

    def status(self, business: Business) -> dict:
        configured = self._number_provider.is_configured()
        active = self._phone_repo.get_active_for_business(business.id)
        already_provisioned = bool(business.phone_provisioned or active)
        profile = get_number_search_profile(business.country)
        regulation = self._regulation_repo.get_by_code(business.country)
        reg_profile = self._profile_repo.get_for_business(business.id, business.country)
        verification_required = bool(
            regulation
            and (regulation.requires_end_user or regulation.requires_regulatory_bundle)
        )
        verification_approved = (
            not verification_required
            or (reg_profile and reg_profile.status == RegulatoryStatus.APPROVED)
        )
        return {
            "phone_number": business.phone_number or (active.phone_number if active else None),
            "provisioned": already_provisioned,
            "platform_configured": configured,
            "can_search": configured and not already_provisioned and verification_approved,
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
            "verification_required": verification_required,
            "verification_status": reg_profile.status.value if reg_profile else None,
            "verification_approved": verification_approved,
        }

    def search_available(
        self,
        business: Business,
        *,
        prefix: str | None = None,
        limit: int = 10,
        number_type: str | None = None,
    ) -> list[dict]:
        if not self._number_provider.is_configured():
            raise ProviderUnavailableError(provider=self._number_provider.provider_name)
        return self._number_provider.search_numbers(
            business.country,
            prefix=prefix,
            limit=limit,
            number_type=number_type,
        )

    def _ensure_verification_approved(self, business: Business) -> None:
        regulation = self._regulation_repo.get_by_code(business.country)
        if not regulation:
            return
        if not regulation.requires_end_user and not regulation.requires_regulatory_bundle:
            return
        profile = self._profile_repo.get_for_business(business.id, business.country)
        if profile is None or profile.status != RegulatoryStatus.APPROVED:
            raise MissingDocumentsError(
                "Regulatory verification must be approved before provisioning a number."
            )

    def provision(self, business: Business, phone_number: str) -> dict:
        if business.phone_provisioned or self._phone_repo.get_active_for_business(business.id):
            raise DuplicateProvisioningError("This business already has a provisioned phone number.")
        if not self._number_provider.is_configured():
            raise ProviderUnavailableError(provider=self._number_provider.provider_name)

        self._ensure_verification_approved(business)

        normalized = normalize_phone(phone_number.strip(), business.country)
        if not is_plausible_phone(normalized, business.country):
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Enter a valid phone number in E.164 format.",
            )

        self._phone_repo.assert_not_assigned_elsewhere(normalized, business.id, business.country)

        record = self._phone_repo.create_pending(
            business_id=business.id,
            phone_number=normalized,
            country=business.country,
            provider=self._number_provider.provider_name,
        )

        try:
            order = with_retry(lambda: self._number_provider.purchase_number(normalized))
            order_id = order.external_id
            if order_id:
                with_retry(lambda: self._number_provider.wait_for_purchase(order_id))

            provider_record = self._number_provider.find_number_record(normalized)
            if provider_record is None:
                raise ProviderError("Purchased number not found with provider")

            provider_number_id = provider_record.get("id")
            if not provider_number_id:
                raise ProviderError("Provider number record missing id")

            self._number_provider.configure_voice(str(provider_number_id))
            self._number_provider.configure_sms(str(provider_number_id))

            self._phone_repo.activate(
                record,
                provider_number_id=str(provider_number_id),
            )

            business.phone_number = normalized
            business.telnyx_phone_number_id = str(provider_number_id)
            self._db.commit()
            self._db.refresh(business)

        except ProviderError:
            self._phone_repo.mark_failed(record)
            raise
        except Exception as exc:
            self._phone_repo.mark_failed(record)
            logger.exception(
                "Phone provisioning failed",
                extra={"business_id": business.id, "phone_number": normalized},
            )
            raise ProviderError(f"Could not provision phone number: {exc}") from exc

        logger.info(
            "Phone number provisioned",
            extra={
                "business_id": business.id,
                "phone_number": normalized,
                "provider_number_id": provider_number_id,
            },
        )
        return {
            "phone_number": normalized,
            "provisioned": True,
            "telnyx_phone_number_id": str(provider_number_id),
            "provider_number_id": str(provider_number_id),
            "message": (
                "Your business phone number is live. Customers can call it now — "
                "inbound calls route to your AI receptionist automatically."
            ),
        }

    def retry_failed_provisioning(self, record_id: str) -> dict:
        from app.models.telecom import PhoneNumber

        record = self._db.get(PhoneNumber, record_id)
        if record is None or record.status != PhoneNumberStatus.FAILED:
            raise DuplicateProvisioningError("No failed provisioning record to retry.")
        business = self._db.get(Business, record.business_id)
        if business is None:
            raise ProviderError("Business not found for failed number")
        record.status = PhoneNumberStatus.PROVISIONING
        self._db.commit()
        return self.provision(business, record.phone_number)
