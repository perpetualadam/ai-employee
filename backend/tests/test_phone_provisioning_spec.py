"""Specification: per-tenant phone provisioning."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.services.phone_number_service import PhoneNumberService
from app.services.phone_provisioning_service import PhoneProvisioningService


class PhoneProvisioningSpecification(unittest.TestCase):
    def test_status_when_not_provisioned(self) -> None:
        business = MagicMock()
        business.phone_number = None
        business.phone_provisioned = False
        business.country = "US"

        provider = MagicMock()
        provider.is_configured.return_value = True
        with patch(
            "app.services.phone_provisioning_service.get_number_provisioning_provider",
            return_value=provider,
        ):
            status = PhoneProvisioningService.status(business)

        self.assertFalse(status["provisioned"])
        self.assertTrue(status["can_search"])

    @patch("app.services.phone_provisioning_service.get_number_provisioning_provider")
    def test_provision_assigns_number_to_business(self, mock_get_provider) -> None:
        from tests.fakes.fake_providers import FakeNumberProvisioningProvider

        mock_get_provider.return_value = FakeNumberProvisioningProvider()
        db = MagicMock()
        business = MagicMock()
        business.id = "biz-1"
        business.country = "US"
        business.phone_provisioned = False
        business.phone_number = None

        mock_get_provider.return_value = FakeNumberProvisioningProvider()

        with patch.object(PhoneNumberService, "provision", return_value={
            "phone_number": "+16145551234",
            "provisioned": True,
            "telnyx_phone_number_id": "pn-123",
            "provider_number_id": "pn-123",
            "message": "ok",
        }) as mock_provision:
            result = PhoneProvisioningService.provision(db, business, "+16145551234")

        self.assertTrue(result["provisioned"])
        self.assertEqual(result["phone_number"], "+16145551234")
        mock_provision.assert_called_once_with(business, "+16145551234")

    def test_duplicate_check_normalizes_with_each_business_country(self) -> None:
        from fastapi import HTTPException

        db = MagicMock()
        other = MagicMock()
        other.id = "biz-other"
        other.country = "GB"
        other.phone_number = "07949046947"

        db.query.return_value.filter.return_value.all.return_value = [other]
        db.query.return_value.filter.return_value.first.return_value = None

        with self.assertRaises(HTTPException) as ctx:
            PhoneProvisioningService._assert_number_available(
                db,
                "+447949046947",
                "biz-new",
                "GB",
            )
        self.assertEqual(ctx.exception.status_code, 409)
