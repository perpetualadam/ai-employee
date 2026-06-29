"""Stripe billing integration — checkout, portal, webhooks."""

import logging
from datetime import UTC, datetime

import stripe
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Business, User
from app.models.enums import PlanTier, SubscriptionStatus

logger = logging.getLogger(__name__)


def _configure_stripe() -> None:
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")
    stripe.api_key = settings.stripe_secret_key


def _price_id_for_plan(plan: PlanTier) -> str:
    settings = get_settings()
    if plan == PlanTier.PRO:
        if not settings.stripe_price_pro:
            raise ValueError("STRIPE_PRICE_PRO is not configured")
        return settings.stripe_price_pro
    if not settings.stripe_price_starter:
        raise ValueError("STRIPE_PRICE_STARTER is not configured")
    return settings.stripe_price_starter


class BillingService:
    @staticmethod
    def get_or_create_stripe_customer(db: Session, business: Business, user: User) -> str:
        _configure_stripe()

        if business.stripe_customer_id:
            return business.stripe_customer_id

        customer = stripe.Customer.create(
            email=user.email,
            name=business.name,
            metadata={"business_id": business.id, "user_id": user.id},
        )
        business.stripe_customer_id = customer.id
        db.commit()
        logger.info("Stripe customer created", extra={"business_id": business.id})
        return customer.id

    @staticmethod
    def create_checkout_session(
        db: Session,
        business: Business,
        user: User,
        plan: PlanTier,
    ) -> str:
        _configure_stripe()
        settings = get_settings()

        customer_id = BillingService.get_or_create_stripe_customer(db, business, user)
        price_id = _price_id_for_plan(plan)

        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{settings.frontend_url}/dashboard/billing?success=true",
            cancel_url=f"{settings.frontend_url}/dashboard/billing?canceled=true",
            metadata={"business_id": business.id, "plan_tier": plan.value},
            subscription_data={"metadata": {"business_id": business.id, "plan_tier": plan.value}},
        )
        return session.url

    @staticmethod
    def create_portal_session(db: Session, business: Business) -> str:
        _configure_stripe()
        settings = get_settings()

        if not business.stripe_customer_id:
            raise ValueError("No billing account found. Subscribe first.")

        session = stripe.billing_portal.Session.create(
            customer=business.stripe_customer_id,
            return_url=f"{settings.frontend_url}/dashboard/billing",
        )
        return session.url

    @staticmethod
    def handle_webhook_event(db: Session, payload: bytes, signature: str) -> None:
        _configure_stripe()
        settings = get_settings()
        if not settings.stripe_webhook_secret:
            raise RuntimeError("STRIPE_WEBHOOK_SECRET is not configured")

        event = stripe.Webhook.construct_event(
            payload, signature, settings.stripe_webhook_secret
        )

        event_type = event["type"]
        data = event["data"]["object"]

        logger.info("Stripe webhook received", extra={"type": event_type})

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

    @staticmethod
    def _get_stripe_business_from_session(db: Session, session: dict) -> Business | None:
        return BillingService._get_business_by_stripe(
            db, session.get("customer"), session.get("metadata")
        )

    # Fix typo in method name above - I used _get_bripe_business - need to fix

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
