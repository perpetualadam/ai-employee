"""Subscription plan definitions and usage limits."""

from dataclasses import dataclass

from app.models.enums import PlanTier

TRIAL_DAYS = 14


@dataclass(frozen=True)
class PlanLimits:
    calls_per_month: int
    ai_messages_per_month: int
    price_label: str
    description: str


PLAN_LIMITS: dict[PlanTier, PlanLimits] = {
    PlanTier.STARTER: PlanLimits(
        calls_per_month=100,
        ai_messages_per_month=500,
        price_label="$49/month",
        description="For solo operators getting started",
    ),
    PlanTier.PRO: PlanLimits(
        calls_per_month=500,
        ai_messages_per_month=5000,
        price_label="$99/month",
        description="For growing teams with higher call volume",
    ),
}


def get_limits(plan: PlanTier) -> PlanLimits:
    return PLAN_LIMITS[plan]
