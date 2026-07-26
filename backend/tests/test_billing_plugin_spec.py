"""Specification: billing uses payment plugin — core never imports Stripe."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.models.enums import PlanTier
from app.plugins.exceptions import PaymentWebhookVerificationError
from app.plugins.interfaces import PaymentPlugin
from app.services.billing_service import BillingService


class _MockPaymentPlugin(PaymentPlugin):
    def __init__(self) -> None:
        self.customers: list[dict] = []
        self.checkout_calls: list[dict] = []

    @property
    def manifest(self):
        raise NotImplementedError

    def get_capabilities(self):
        raise NotImplementedError

    def is_configured(self) -> bool:
        return True

    def is_payment_configured(self) -> bool:
        return True

    def create_customer(self, *, email: str, name: str, metadata: dict[str, str]) -> str:
        self.customers.append({"email": email, "name": name, "metadata": metadata})
        return "cus_mock_123"

    def create_checkout_session(
        self,
        *,
        customer_id: str,
        plan_tier: str,
        success_url: str,
        cancel_url: str,
        metadata: dict[str, str],
    ) -> str:
        self.checkout_calls.append(
            {
                "customer_id": customer_id,
                "plan_tier": plan_tier,
                "success_url": success_url,
                "cancel_url": cancel_url,
                "metadata": metadata,
            }
        )
        return "https://checkout.example/session"

    def create_portal_session(self, *, customer_id: str, return_url: str) -> str:
        return f"https://portal.example/{customer_id}?return={return_url}"

    def construct_webhook_event(self, payload: bytes, signature: str) -> dict:
        if signature != "valid":
            raise PaymentWebhookVerificationError("bad signature")
        return {"type": "checkout.session.completed", "data": {"object": {"metadata": {}}}}


class BillingPluginSpecification(unittest.TestCase):
    def test_billing_service_has_no_stripe_import(self) -> None:
        import app.services.billing_service as billing_module

        source = open(billing_module.__file__, encoding="utf-8").read()
        self.assertNotIn("import stripe", source)

    def test_billing_api_has_no_stripe_import(self) -> None:
        import app.api.billing as billing_api

        source = open(billing_api.__file__, encoding="utf-8").read()
        self.assertNotIn("import stripe", source)

    @patch("app.services.billing_service.get_payment_plugin")
    @patch("app.services.billing_service.get_settings")
    def test_checkout_delegates_to_payment_plugin(self, settings_mock, plugin_mock) -> None:
        payment = _MockPaymentPlugin()
        plugin_mock.return_value = payment
        settings_mock.return_value = MagicMock(frontend_url="https://app.example")

        business = MagicMock(id="biz-1", stripe_customer_id=None, name="Acme")
        user = MagicMock(email="owner@acme.com", id="user-1")
        db = MagicMock()

        url = BillingService.create_checkout_session(db, business, user, PlanTier.STARTER)

        self.assertEqual(url, "https://checkout.example/session")
        self.assertEqual(len(payment.checkout_calls), 1)
        self.assertEqual(payment.checkout_calls[0]["plan_tier"], "starter")
        db.commit.assert_called()

    @patch("app.services.billing_service.get_payment_plugin")
    def test_webhook_uses_plugin_signature_verification(self, plugin_mock) -> None:
        payment = _MockPaymentPlugin()
        plugin_mock.return_value = payment
        db = MagicMock()

        with self.assertRaises(PaymentWebhookVerificationError):
            BillingService.handle_webhook_event(db, b"{}", "invalid")

        BillingService.handle_webhook_event(db, b"{}", "valid")
        db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
