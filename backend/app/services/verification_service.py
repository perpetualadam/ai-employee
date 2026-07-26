"""Regulatory verification — uses RegulatoryProvider and StorageProvider."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.enums import DocumentType, RegulatoryStatus
from app.models.telecom import BusinessRegulatoryProfile, UploadedDocument
from app.providers.exceptions import MissingDocumentsError, ProviderError, VerificationRejectedError
from app.providers.regulatory import RegulatoryProvider
from app.providers.storage import StorageProvider
from app.repositories.country_regulation_repository import CountryRegulationRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.regulatory_profile_repository import RegulatoryProfileRepository
from app.utils.retry import with_retry

logger = logging.getLogger(__name__)

REQUIRED_DOCUMENTS: dict[str, list[DocumentType]] = {
    "GB": [DocumentType.BUSINESS_REGISTRATION, DocumentType.PROOF_OF_ADDRESS],
    "DE": [DocumentType.BUSINESS_REGISTRATION, DocumentType.PROOF_OF_ADDRESS],
    "AU": [DocumentType.BUSINESS_REGISTRATION],
    "FR": [DocumentType.BUSINESS_REGISTRATION],
    "IE": [DocumentType.BUSINESS_REGISTRATION],
}


class VerificationService:
    def __init__(
        self,
        db: Session,
        regulatory_provider: RegulatoryProvider,
        storage_provider: StorageProvider,
    ) -> None:
        self._db = db
        self._regulatory = regulatory_provider
        self._storage = storage_provider
        self._regulation_repo = CountryRegulationRepository(db)
        self._profile_repo = RegulatoryProfileRepository(db)
        self._document_repo = DocumentRepository(db)

    def get_requirements(self, country_code: str) -> dict:
        regulation = self._regulation_repo.get_by_code(country_code)
        if regulation is None:
            return {
                "country_code": country_code.upper(),
                "verification_required": False,
                "required_documents": [],
            }
        required = REQUIRED_DOCUMENTS.get(country_code.upper(), [])
        return {
            "country_code": regulation.country_code,
            "country_name": regulation.country_name,
            "verification_required": regulation.requires_end_user or regulation.requires_regulatory_bundle,
            "requires_end_user": regulation.requires_end_user,
            "requires_regulatory_bundle": regulation.requires_regulatory_bundle,
            "required_documents": [doc.value for doc in required],
            "metadata": regulation.metadata_,
        }

    def get_profile(self, business_id: str, country_code: str) -> BusinessRegulatoryProfile:
        regulation = self._regulation_repo.get_by_code(country_code)
        if regulation is None or (
            not regulation.requires_end_user and not regulation.requires_regulatory_bundle
        ):
            profile = self._profile_repo.get_or_create(
                business_id=business_id,
                country_code=country_code,
                provider=self._regulatory.provider_name,
            )
            return self._profile_repo.update_status(profile, RegulatoryStatus.NOT_REQUIRED)

        return self._profile_repo.get_or_create(
            business_id=business_id,
            country_code=country_code,
            provider=self._regulatory.provider_name,
        )

    def upload_document(
        self,
        *,
        business_id: str,
        country_code: str,
        document_type: DocumentType,
        file_bytes: bytes,
        filename: str,
        content_type: str,
    ) -> UploadedDocument:
        profile = self.get_profile(business_id, country_code)
        storage_key = f"regulatory/{business_id}/{document_type.value}/{filename}"
        self._storage.upload(key=storage_key, data=file_bytes, content_type=content_type)
        doc = self._document_repo.create(
            business_id=business_id,
            document_type=document_type,
            storage_key=storage_key,
            regulatory_profile_id=profile.id,
        )
        if self._regulatory.is_configured():
            result = with_retry(
                lambda: self._regulatory.upload_document(
                    file_bytes=file_bytes,
                    filename=filename,
                    content_type=content_type,
                )
            )
            if result.external_id:
                self._document_repo.update_provider_id(doc, result.external_id)
        return doc

    def _assert_required_documents(self, profile: BusinessRegulatoryProfile) -> None:
        required = REQUIRED_DOCUMENTS.get(profile.country_code, [])
        if not required:
            return
        uploaded = {doc.document_type for doc in self._document_repo.list_for_profile(profile.id)}
        missing = [doc.value for doc in required if doc not in uploaded]
        if missing:
            raise MissingDocumentsError(f"Missing required documents: {', '.join(missing)}")

    def submit_verification(
        self,
        *,
        business_id: str,
        country_code: str,
        end_user_payload: dict,
    ) -> BusinessRegulatoryProfile:
        profile = self.get_profile(business_id, country_code)
        if profile.status == RegulatoryStatus.APPROVED:
            return profile

        self._assert_required_documents(profile)

        if not self._regulatory.is_configured():
            return self._profile_repo.update_status(profile, RegulatoryStatus.APPROVED)

        end_user = with_retry(
            lambda: self._regulatory.create_end_user(
                business_id=business_id,
                payload=end_user_payload,
            )
        )
        end_user_id = end_user.external_id
        if not end_user_id:
            raise ProviderError("Provider did not return end user id")

        bundle = with_retry(
            lambda: self._regulatory.create_regulatory_bundle(
                country_code=country_code.upper(),
                end_user_id=end_user_id,
            )
        )
        bundle_id = bundle.external_id
        if not bundle_id:
            raise ProviderError("Provider did not return bundle id")

        for doc in self._document_repo.list_for_profile(profile.id):
            if doc.provider_document_id:
                with_retry(
                    lambda d=doc: self._regulatory.attach_document(
                        bundle_id=bundle_id,
                        document_id=d.provider_document_id,
                    )
                )

        with_retry(lambda: self._regulatory.submit_bundle(bundle_id))
        return self._profile_repo.update_status(
            profile,
            RegulatoryStatus.SUBMITTED,
            end_user_id=end_user_id,
            bundle_id=bundle_id,
        )

    def refresh_status(self, profile: BusinessRegulatoryProfile) -> BusinessRegulatoryProfile:
        if not profile.provider_bundle_id or not self._regulatory.is_configured():
            return profile

        result = with_retry(
            lambda: self._regulatory.get_bundle_status(profile.provider_bundle_id)
        )
        raw_status = (result.data.get("status") or "").lower()
        profile.last_checked = datetime.now(timezone.utc)

        if raw_status in ("approved", "active", "verified"):
            return self._profile_repo.update_status(profile, RegulatoryStatus.APPROVED)
        if raw_status in ("rejected", "failed"):
            raise VerificationRejectedError(f"Bundle rejected: {raw_status}")

        self._db.commit()
        self._db.refresh(profile)
        return profile

    def list_pending_profiles(self) -> list[BusinessRegulatoryProfile]:
        return self._profile_repo.list_by_status(RegulatoryStatus.SUBMITTED)

    def list_documents(self, business_id: str) -> list[UploadedDocument]:
        return self._document_repo.list_for_business(business_id)
