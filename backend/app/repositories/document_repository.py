"""Uploaded document metadata access."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.enums import DocumentType, DocumentVerificationStatus
from app.models.telecom import UploadedDocument


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        *,
        business_id: str,
        document_type: DocumentType,
        storage_key: str,
        regulatory_profile_id: str | None = None,
    ) -> UploadedDocument:
        doc = UploadedDocument(
            business_id=business_id,
            regulatory_profile_id=regulatory_profile_id,
            document_type=document_type,
            storage_key=storage_key,
            verification_status=DocumentVerificationStatus.UPLOADED,
        )
        self._db.add(doc)
        self._db.commit()
        self._db.refresh(doc)
        return doc

    def list_for_business(self, business_id: str) -> list[UploadedDocument]:
        return (
            self._db.query(UploadedDocument)
            .filter(UploadedDocument.business_id == business_id)
            .order_by(UploadedDocument.created_at.desc())
            .all()
        )

    def list_for_profile(self, profile_id: str) -> list[UploadedDocument]:
        return (
            self._db.query(UploadedDocument)
            .filter(UploadedDocument.regulatory_profile_id == profile_id)
            .all()
        )

    def update_provider_id(self, doc: UploadedDocument, provider_document_id: str) -> UploadedDocument:
        doc.provider_document_id = provider_document_id
        doc.verification_status = DocumentVerificationStatus.SUBMITTED
        self._db.commit()
        self._db.refresh(doc)
        return doc
