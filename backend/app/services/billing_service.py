"""Billing integration — checkout, portal, webhooks via payment plugin."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.config import get_settings
from app.dependencies.plugins import get_payment_plugin
from app.models import Business, User
from app.models.enums import PlanTier, SubscriptionStatus
from app.plugins.interfaces import PaymentPlugin

logger = logging.getLogger(__name__)


def _require_payment_plugin() -> PaymentPlugin:
    plugin = get_payment_plugin()
    if plugin is None or not plugin.is_payment_configured():
        raise RuntimeError("Payment plugin is not configured")
    return plugin


class BillingService:
    @staticmethod
    def get_or_create_customer(db: Session, business: Business, user: User) -> str:
        payment = _require_payment_plugin()

        if business.stripe_customer_id:
            return business.stripe_customer_id

        customer_id = payment.create_customer(
            email=user.email,
            name=business.name,
            metadata={"business_id": business.id, "user_id": user.id},
        )
        business.stripe_customer_id = customer_id
        db.commit()
        logger.info("Payment customer created", extra={"business_id": business.id})
        return customer_id

    @staticmethod
    def create_checkout_session(
        db: Session,
        business: Business,
        user: User,
        plan: PlanTier,
    ) -> str:
        payment = _require_payment_plugin()
        settings = get_settings()

        customer_id = BillingService.get_or_create_customer(db, business, user)

        return payment.create_checkout_session(
            customer_id=customer_id,
            plan_tier=plan.value,
            success_url=f"{settings.frontend_url}/dashboard/billing?success=true",
            cancel_url=f"{settings.frontend_url}/dashboard/billing?canceled=true",
            metadata={"business_id": business.id, "plan_tier": plan.value},
        )

    @staticmethod
    def create_portal_session(db: Session, business: Business) -> str:
        payment = _require_payment_plugin()
        settings = get_settings()

        if not business.stripe_customer_id:
            raise ValueError("No billing account found. Subscribe first.")

        return payment.create_portal_session(
            customer_id=business.stripe_customer_id,
            return_url=f"{settings.frontend_url}/dashboard/billing",
        )

    @staticmethod
    def handle_webhook_event(db: Session, payload: bytes, signature: str) -> None:
        payment = _require_payment_plugin()
        event = payment.construct_webhook_event(payload, signature)

        event_type = event["type"]
        data = event["data"]["object"]

        logger.info("Payment webhook received", extra={"type": event_type})

        if event_type == "checkout.session.completed":
            BillingService._handle_checkout_completed(db, data)
        elif event_type in ("customer.subscription.updated", "customer.subscription.created"):
            BillingService._handle_subscription_updated(db, data)
        elif event_type == "customer.subscription.deleted":
            BillingService._handle_subscription_deleted(db, data)
        elif event_type == "invoice.payment_failed":
            BillingService._handle_payment_failed(db, data)

    @staticmethod
    def _get_business_by_stripe(
        db: Session,
        customer_id: str | None,
        metadata: dict | None,
    ) -> Business | None:
        if metadata and metadata.get("business_id"):
            return db.query(Business).filter(Business.id == metadata["business_id"]).first()
        if customer_id:
            return db.query(Business).filter(Business.stripe_customer_id == customer_id).first()
        return None

    @staticmethod
    def _map_stripe_status(status: str) -> SubscriptionStatus:
        mapping = {
            "trialing": SubscriptionStatus.TRIALING,
            "active": SubscriptionStatus.ACTIVE,
            "past_due": SubscriptionStatus.PAST_DUE,
            "canceled": SubscriptionStatus.CANCELED,
            "unpaid": SubscriptionStatus.UNPAID,
            "incomplete": SubscriptionStatus.NONE,
            "incomplete_expired": SubscriptionStatus.NONE,
            "paused": SubscriptionStatus.CANCELED,
        }
        return mapping.get(status, SubscriptionStatus.NONE)

    @staticmethod
    def _handle_checkout_completed(db: Session, session: dict) -> None:
        business = BillingService._get_stripe_business_from_session(db, session)
        if business is None:
            return

        business.stripe_customer_id = session.get("customer") or business.stripe_customer_id
        business.stripe_subscription_id = session.get("subscription")
        business.subscription_status = SubscriptionStatus.ACTIVE

        metadata = session.get("metadata") or {}
        plan = metadata.get("plan_tier")
        if plan in ("starter", "pro"):
            business.plan_tier = PlanTier(plan)

        db.commit()
        logger.info("Checkout completed", extra={"business_id": business.id})
        from app.plugins.publishers import publish_payment_received

        publish_payment_received(
            business_id=business.id,
            customer_id=business.stripe_customer_id,
            plan_tier=plan if plan in ("starter", "pro") else None,
        )

    @staticmethod
    def _get_stripe_business_from_session(db: Session, session: dict) -> Business | None:
        return BillingService._get_business_by_stripe(
            db, session.get("customer"), session.get("metadata")
        )

    @staticmethod
    def _handle_subscription_updated(db: Session, subscription: dict) -> None:
        business = BillingService._get_business_by_stripe(
            db, subscription.get("customer"), subscription.get("metadata")
        )
        if business is None:
            return

        business.stripe_subscription_id = subscription.get("id")
        business.subscription_status = BillingService._map_stripe_status(subscription.get("status", ""))

        metadata = subscription.get("metadata") or {}
        plan = metadata.get("plan_tier")
        if plan in ("starter", "pro"):
            business.plan_tier = PlanTier(plan)

        period_end = subscription.get("current_period_end")
        if period_end:
            business.subscription_period_end = datetime.fromtimestamp(period_end, tz=UTC)

        db.commit()

    @staticmethod
    def _handle_subscription_deleted(db: Session, subscription: dict) -> None:
        business = BillingService._get_business_by_stripe(
            db, subscription.get("customer"), subscription.get("metadata")
        )
        if business is None:
            return

        business.subscription_status = SubscriptionStatus.CANCELED
        business.stripe_subscription_id = None
        db.commit()

    @staticmethod
    def _handle_payment_failed(db: Session, invoice: dict) -> None:
        business = BillingService._get_business_by_stripe(db, invoice.get("customer"), None)
        if business is None:
            return

        business.subscription_status = SubscriptionStatus.PAST_DUE
        db.commit()
