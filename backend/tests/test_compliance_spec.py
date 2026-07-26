"""Compliance export/delete and audit logging tests."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from app.schemas import AccountDeleteRequest
from app.services.audit_service import AuditService
from app.services.compliance_service import ComplianceService


class ComplianceServiceSpecification(unittest.TestCase):
    def test_export_account_data_includes_core_sections(self) -> None:
        db = MagicMock()
        user = MagicMock()
        user.id = "user-1"
        user.email = "owner@example.com"
        user.full_name = "Owner"
        user.created_at = datetime.now(UTC)

        business = MagicMock()
        business.id = "biz-1"
        business.name = "Test Co"
        business.industry.value = "plumbing"
        business.country = "US"
        business.timezone = "America/New_York"
        business.phone_number = "+15551234567"
        business.public_slug = "test-co"
        business.subscription_status.value = "trialing"
        business.created_at = datetime.now(UTC)

        customer = MagicMock()
        customer.id = "cust-1"
        customer.name = "Jane"
        customer.phone = "+15559876543"
        customer.email = None
        customer.address = "123 Main"
        customer.created_at = datetime.now(UTC)

        def _query(model):
            chain = MagicMock()
            if getattr(model, "__name__", "") == "Customer":
                chain.filter.return_value.order_by.return_value.all.return_value = [customer]
            else:
                chain.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
            return chain

        db.query.side_effect = _query

        payload = ComplianceService.export_account_data(db, user, business)

        self.assertIn("user", payload)
        self.assertIn("business", payload)
        self.assertIn("customers", payload)
        self.assertEqual(payload["user"]["email"], "owner@example.com")
        self.assertEqual(payload["customers"][0]["name"], "Jane")

    def test_delete_account_removes_user(self) -> None:
        db = MagicMock()
        user = MagicMock()
        ComplianceService.delete_account(db, user)
        db.delete.assert_called_once_with(user)
        db.commit.assert_called_once()


class AuditServiceSpecification(unittest.TestCase):
    def test_log_event_persists_audit_row(self) -> None:
        db = MagicMock()
        with patch("app.services.audit_service.AuditLog") as audit_model:
            instance = MagicMock()
            audit_model.return_value = instance
            AuditService.log_event(
                db,
                action="data.export",
                resource="account",
                user_id="user-1",
                business_id="biz-1",
                ip_address="127.0.0.1",
                metadata={"count": 1},
            )
            db.add.assert_called_once_with(instance)
            db.commit.assert_called_once()


class AccountDeleteRequestSpecification(unittest.TestCase):
    def test_requires_delete_confirmation_string(self) -> None:
        request = AccountDeleteRequest(confirmation="DELETE")
        self.assertEqual(request.confirmation, "DELETE")


if __name__ == "__main__":
    unittest.main()
