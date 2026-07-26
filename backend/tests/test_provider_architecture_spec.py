"""Specification: provider architecture and services without Telnyx."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.models.enums import RegulatoryStatus
from app.providers.exceptions import MissingDocumentsError
from app.services.communication_service import CommunicationService
from app.services.phone_number_service import PhoneNumberService
from app.services.verification_service import VerificationService
from tests.fakes.fake_providers import (
    FakeMessagingProvider,
    FakeNumberProvisioningProvider,
    FakeRegulatoryProvider,
    FakeStorageProvider,
)


class ProviderArchitectureSpecification(unittest.TestCase):
    def test_phone_number_service_provisions_with_fake_provider(self) -> None:
        db = MagicMock()
        business = MagicMock()
        business.id = "biz-1"
        business.country = "US"
        business.phone_provisioned = False
        business.phone_number = None

        fake = FakeNumberProvisioningProvider()
        service = PhoneNumberService(db, fake)

        with patch.object(service._phone_repo, "get_active_for_business", return_value=None):
            with patch.object(service._regulation_repo, "get_by_code", return_value=None):
                with patch.object(service._phone_repo, "assert_not_assigned_elsewhere"):
                    with patch.object(service._phone_repo, "create_pending") as create_pending:
                        record = MagicMock()
                        record.id = "rec-1"
                        create_pending.return_value = record
                        with patch.object(service._phone_repo, "activate") as activate:
                            result = service.provision(business, "+15551234567")

        self.assertTrue(result["provisioned"])
        activate.assert_called_once()

    def test_verification_requires_documents_for_gb(self) -> None:
        db = MagicMock()
        fake_reg = FakeRegulatoryProvider()
        fake_storage = FakeStorageProvider()
        service = VerificationService(db, fake_reg, fake_storage)

        regulation = MagicMock()
        regulation.requires_end_user = True
        regulation.requires_regulatory_bundle = True
        regulation.country_code = "GB"
        regulation.country_name = "United Kingdom"
        regulation.metadata_ = {}

        profile = MagicMock()
        profile.id = "prof-1"
        profile.country_code = "GB"
        profile.status = RegulatoryStatus.PENDING

        with patch.object(service._regulation_repo, "get_by_code", return_value=regulation):
            with patch.object(service._profile_repo, "get_or_create", return_value=profile):
                with patch.object(service._document_repo, "list_for_profile", return_value=[]):
                    with self.assertRaises(MissingDocumentsError):
                        service.submit_verification(
                            business_id="biz-1",
                            country_code="GB",
                            end_user_payload={"name": "Test Ltd"},
                        )

    def test_communication_service_uses_messaging_provider(self) -> None:
        messaging = FakeMessagingProvider()
        service = CommunicationService(messaging)
        result = service.send_sms(from_number="+1", to_number="+2", text="hello")
        self.assertTrue(result["sent"])
        self.assertEqual(result["provider"], "mock")


class ProviderRegistrySpecification(unittest.TestCase):
    def test_registry_lists_providers(self) -> None:
        from app.providers.factory import list_provider_registry

        registry = list_provider_registry()
        self.assertIn("telnyx", registry["telephony"])
        self.assertIn("openai", registry["voice"])
