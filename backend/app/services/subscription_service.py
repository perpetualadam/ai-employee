"""Subscription access checks and usage metering."""

import logging
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.billing.plans import get_limits
from app.models import AIActivityLog, Business, CallLog
from app.models.enums import PlanTier, SubscriptionStatus

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = {SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING, SubscriptionStatus.PAST_DUE}


def _month_start() -> datetime:
    now = datetime.now(UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


class SubscriptionService:
    @staticmethod
    def is_subscription_active(business: Business) -> bool:
        if business.subscription_status not in ACTIVE_STATUSES:
            return False

        if business.subscription_status == SubscriptionStatus.TRIALING:
            if business.trial_ends_at and datetime.now(UTC) > business.trial_ends_at:
                return False

        return True

    @staticmethod
    def get_access_denial_reason(business: Business) -> str | None:
        if SubscriptionService.is_subscription_active(business):
            return None

        if business.subscription_status == SubscriptionStatus.TRIALING:
            return "Your free trial has ended. Subscribe to continue using your AI receptionist."

        if business.subscription_status in (
            SubscriptionStatus.CANCELED,
            SubscriptionStatus.UNPAID,
            SubscriptionStatus.NONE,
        ):
            return "An active subscription is required. Please subscribe to continue."

        return "Your subscription is inactive. Please update billing."

    @staticmethod
    def get_usage_for_business(db: Session, business: Business) -> dict:
        month_start = _month_start()
        limits = get_limits(business.plan_tier)

        calls_count = (
            db.query(func.count(CallLog.id))
            .filter(CallLog.business_id == business.id, CallLog.created_at >= month_start)
            .scalar()
            or 0
        )

        ai_tool_calls = (
            db.query(func.count(AIActivityLog.id))
            .filter(
                AIActivityLog.business_id == business.id,
                AIActivityLog.action == "tool_call",
                AIActivityLog.created_at >= month_start,
            )
            .scalar()
            or 0
        )

        return {
            "calls_this_month": calls_count,
            "calls_limit": limits.calls_per_month,
            "calls_remaining": max(0, limits.calls_per_month - calls_count),
            "ai_tool_calls_this_month": ai_tool_calls,
            "ai_tool_calls_limit": limits.ai_messages_per_month,
        }

    @staticmethod
    def is_within_call_limit(db: Session, business: Business) -> bool:
        usage = SubscriptionService.get_usage_for_business(db, business)
        return usage["calls_this_month"] < usage["calls_limit"]

    @staticmethod
    def get_billing_status(db: Session, business: Business) -> dict:
        limits = get_limits(business.plan_tier)
        usage = SubscriptionService.get_usage_for_business(db, business)
        active = SubscriptionService.is_subscription_active(business)

        return {
            "subscription_status": business.subscription_status.value,
            "plan_tier": business.plan_tier.value,
            "plan_label": limits.price_label,
            "plan_description": limits.description,
            "is_active": active,
            "trial_ends_at": business.trial_ends_at.isoformat() if business.trial_ends_at else None,
            "subscription_period_end": (
                business.subscription_period_end.isoformat()
                if business.subscription_period_end
                else None
            ),
            "has_stripe_customer": bool(business.stripe_customer_id),
            "usage": usage,
            "limits": {
                "calls_per_month": limits.calls_per_month,
                "ai_messages_per_month": limits.ai_messages_per_month,
            },
        }
