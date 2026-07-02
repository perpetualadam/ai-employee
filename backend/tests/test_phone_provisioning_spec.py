"""Specification: per-tenant phone provisioning."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.services.phone_provisioning_service import PhoneProvisioningService


class PhoneProvisioningSpecification(unittest.TestCase):
    def test_status_when_not_provisioned(self) -> None:
        business = MagicMock()
        business.phone_number = None
        business.phone_provisioned = False
        business.country = "US"

        with patch(
            "app.services.phone_provisioning_service.telnyx_client.is_phone_provisioning_configured",
            return_value=True,
        ):
            status = PhoneProvisioningService.status(business)

        self.assertFalse(status["provisioned"])
        self.assertTrue(status["can_search"])

    @patch("app.services.phone_provisioning_service.telnyx_client.configure_phone_number")
    @patch("app.services.phone_provisioning_service.telnyx_client.find_phone_number_record")
    @patch("app.services.phone_provisioning_service.telnyx_client.wait_for_number_order")
    @patch("app.services.phone_provisioning_service.telnyx_client.create_number_order")
    @patch(
        "app.services.phone_provisioning_service.telnyx_client.is_phone_provisioning_configured",
        return_value=True,
    )
    def test_provision_assigns_number_to_business(
        self,
        _mock_configured,
        mock_order,
        _mock_wait,
        mock_find,
        mock_configure,
    ) -> None:
        db = MagicMock()
        business = MagicMock()
        business.id = "biz-1"
        business.country = "US"
        business.phone_provisioned = False
        business.phone_number = None

        db.query.return_value.filter.return_value.all.return_value = []

        mock_order.return_value = {"id": "order-1"}
        mock_find.return_value = {"id": "pn-123", "phone_number": "+16145551234"}

        with patch("app.services.phone_provisioning_service.get_settings") as settings_mock:
            settings_mock.return_value.telnyx_texml_connection_id = "conn-1"
            settings_mock.return_value.telnyx_messaging_profile_id = "mp-1"
            result = PhoneProvisioningService.provision(db, business, "+16145551234")

        self.assertTrue(result["provisioned"])
        self.assertEqual(result["phone_number"], "+16145551234")
        self.assertEqual(business.telnyx_phone_number_id, "pn-123")
        mock_configure.assert_called_once()


if __name__ == "__main__":
    unittest.main()
