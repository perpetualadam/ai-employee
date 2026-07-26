"""Specification: verification document upload and submit flow."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.models.enums import DocumentType, DocumentVerificationStatus, RegulatoryStatus
from app.services.verification_service import VerificationService
from tests.fakes.fake_providers import FakeRegulatoryProvider, FakeStorageProvider


class VerificationUploadSpecification(unittest.TestCase):
    def _service(self) -> VerificationService:
        return VerificationService(MagicMock(), FakeRegulatoryProvider(), FakeStorageProvider())

    def test_upload_stores_file_and_creates_document_record(self) -> None:
        service = self._service()
        profile = MagicMock()
        profile.id = "prof-1"

        doc = MagicMock()
        doc.id = "doc-1"
        doc.document_type = DocumentType.BUSINESS_REGISTRATION
        doc.verification_status = DocumentVerificationStatus.SUBMITTED
        doc.storage_key = "regulatory/biz-1/business_registration/cert.pdf"
        doc.provider_document_id = "doc-cert.pdf"
        doc.created_at = MagicMock()

        with patch.object(service, "get_profile", return_value=profile):
            with patch.object(service._document_repo, "create", return_value=doc) as create:
                with patch.object(service._document_repo, "update_provider_id", return_value=doc):
                    result = service.upload_document(
                        business_id="biz-1",
                        country_code="GB",
                        document_type=DocumentType.BUSINESS_REGISTRATION,
                        file_bytes=b"%PDF-1.4",
                        filename="cert.pdf",
                        content_type="application/pdf",
                    )

        self.assertEqual(result.id, "doc-1")
        create.assert_called_once()
        stored = service._storage._store
        self.assertTrue(any(k.startswith("regulatory/biz-1/") for k in stored))

    def test_list_documents_delegates_to_repository(self) -> None:
        service = self._service()
        doc = MagicMock()
        with patch.object(service._document_repo, "list_for_business", return_value=[doc]) as list_fn:
            docs = service.list_documents("biz-1")
        list_fn.assert_called_once_with("biz-1")
        self.assertEqual(docs, [doc])

    def test_submit_auto_approves_when_regulatory_provider_not_configured(self) -> None:
        service = self._service()
        profile = MagicMock()
        profile.id = "prof-1"
        profile.country_code = "GB"
        profile.status = RegulatoryStatus.PENDING

        reg_doc = MagicMock()
        reg_doc.document_type = DocumentType.BUSINESS_REGISTRATION
        reg_doc.provider_document_id = "p1"
        addr_doc = MagicMock()
        addr_doc.document_type = DocumentType.PROOF_OF_ADDRESS
        addr_doc.provider_document_id = "p2"

        updated = MagicMock()
        updated.status = RegulatoryStatus.APPROVED

        with patch.object(service, "get_profile", return_value=profile):
            with patch.object(
                service._document_repo,
                "list_for_profile",
                return_value=[reg_doc, addr_doc],
            ):
                with patch.object(service._regulatory, "is_configured", return_value=False):
                    with patch.object(service._profile_repo, "update_status", return_value=updated) as upd:
                        result = service.submit_verification(
                            business_id="biz-1",
                            country_code="GB",
                            end_user_payload={"business_name": "Test Ltd"},
                        )

        upd.assert_called_once_with(profile, RegulatoryStatus.APPROVED)
        self.assertEqual(result.status, RegulatoryStatus.APPROVED)

    def test_submit_requires_all_documents_for_gb(self) -> None:
        service = self._service()
        profile = MagicMock()
        profile.id = "prof-1"
        profile.country_code = "GB"
        profile.status = RegulatoryStatus.PENDING

        with patch.object(service, "get_profile", return_value=profile):
            with patch.object(service._document_repo, "list_for_profile", return_value=[]):
                from app.providers.exceptions import MissingDocumentsError

                with self.assertRaises(MissingDocumentsError):
                    service.submit_verification(
                        business_id="biz-1",
                        country_code="GB",
                        end_user_payload={"business_name": "Test Ltd"},
                    )


if __name__ == "__main__":
    unittest.main()
