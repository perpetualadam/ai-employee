"""Phone number inventory data access."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Business
from app.models.enums import PhoneNumberStatus
from app.models.telecom import PhoneNumber


class PhoneNumberRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_active_for_business(self, business_id: str) -> PhoneNumber | None:
        return (
            self._db.query(PhoneNumber)
            .filter(
                PhoneNumber.business_id == business_id,
                PhoneNumber.status == PhoneNumberStatus.ACTIVE,
            )
            .first()
        )

    def get_by_number(self, phone_number: str) -> PhoneNumber | None:
        return self._db.query(PhoneNumber).filter(PhoneNumber.phone_number == phone_number).first()

    def create_pending(
        self,
        *,
        business_id: str,
        phone_number: str,
        country: str,
        provider: str,
    ) -> PhoneNumber:
        record = PhoneNumber(
            business_id=business_id,
            phone_number=phone_number,
            country=country.upper(),
            provider=provider,
            status=PhoneNumberStatus.PROVISIONING,
        )
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        return record

    def activate(
        self,
        record: PhoneNumber,
        *,
        provider_number_id: str,
        voice_enabled: bool = True,
        sms_enabled: bool = True,
    ) -> PhoneNumber:
        record.provider_number_id = provider_number_id
        record.status = PhoneNumberStatus.ACTIVE
        record.voice_enabled = voice_enabled
        record.sms_enabled = sms_enabled
        self._db.commit()
        self._db.refresh(record)
        return record

    def mark_failed(self, record: PhoneNumber) -> PhoneNumber:
        record.status = PhoneNumberStatus.FAILED
        self._db.commit()
        self._db.refresh(record)
        return record

    def list_failed(self) -> list[PhoneNumber]:
        return (
            self._db.query(PhoneNumber)
            .filter(PhoneNumber.status == PhoneNumberStatus.FAILED)
            .order_by(PhoneNumber.updated_at.desc())
            .all()
        )

    def list_for_business(self, business_id: str) -> list[PhoneNumber]:
        return (
            self._db.query(PhoneNumber)
            .filter(PhoneNumber.business_id == business_id)
            .order_by(PhoneNumber.created_at.desc())
            .all()
        )

    def assert_not_assigned_elsewhere(
        self,
        phone_number: str,
        business_id: str,
        country: str,
    ) -> None:
        from app.domain.phone import normalize_phone

        normalized = normalize_phone(phone_number, country)
        existing_businesses = (
            self._db.query(Business)
            .filter(Business.phone_number.isnot(None), Business.id != business_id)
            .all()
        )
        for other in existing_businesses:
            if other.phone_number and normalize_phone(other.phone_number, other.country) == normalized:
                from app.providers.exceptions import DuplicateProvisioningError

                raise DuplicateProvisioningError(
                    "That phone number is already assigned to another business."
                )
        other_record = self.get_by_number(normalized)
        if other_record and other_record.business_id != business_id:
            from app.providers.exceptions import DuplicateProvisioningError

            raise DuplicateProvisioningError(
                "That phone number is already assigned to another business."
            )
