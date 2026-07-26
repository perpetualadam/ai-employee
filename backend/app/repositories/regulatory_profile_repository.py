"""Business regulatory profile data access."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.enums import RegulatoryStatus
from app.models.telecom import BusinessRegulatoryProfile


class RegulatoryProfileRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_for_business(self, business_id: str, country_code: str) -> BusinessRegulatoryProfile | None:
        return (
            self._db.query(BusinessRegulatoryProfile)
            .filter(
                BusinessRegulatoryProfile.business_id == business_id,
                BusinessRegulatoryProfile.country_code == country_code.upper(),
            )
            .first()
        )

    def get_or_create(
        self,
        *,
        business_id: str,
        country_code: str,
        provider: str | None = None,
    ) -> BusinessRegulatoryProfile:
        profile = self.get_for_business(business_id, country_code)
        if profile:
            return profile
        profile = BusinessRegulatoryProfile(
            business_id=business_id,
            country_code=country_code.upper(),
            provider=provider or "unknown",
            status=RegulatoryStatus.PENDING,
        )
        self._db.add(profile)
        self._db.commit()
        self._db.refresh(profile)
        return profile

    def update_status(
        self,
        profile: BusinessRegulatoryProfile,
        status: RegulatoryStatus,
        *,
        end_user_id: str | None = None,
        bundle_id: str | None = None,
    ) -> BusinessRegulatoryProfile:
        profile.status = status
        profile.last_checked = datetime.now(timezone.utc)
        if end_user_id:
            profile.provider_end_user_id = end_user_id
        if bundle_id:
            profile.provider_bundle_id = bundle_id
        self._db.commit()
        self._db.refresh(profile)
        return profile

    def list_by_status(self, status: RegulatoryStatus) -> list[BusinessRegulatoryProfile]:
        return (
            self._db.query(BusinessRegulatoryProfile)
            .filter(BusinessRegulatoryProfile.status == status)
            .order_by(BusinessRegulatoryProfile.updated_at.desc())
            .all()
        )

    def list_for_business(self, business_id: str) -> list[BusinessRegulatoryProfile]:
        return (
            self._db.query(BusinessRegulatoryProfile)
            .filter(BusinessRegulatoryProfile.business_id == business_id)
            .all()
        )
