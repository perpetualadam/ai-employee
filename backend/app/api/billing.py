"""Billing and subscription endpoints."""

import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.deps import get_current_user, get_user_primary_business
from app.database import get_db
from app.models import Business, User
from app.models.enums import PlanTier
from app.services.billing_service import BillingService
from app.services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    plan: PlanTier = Field(default=PlanTier.STARTER)


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


@router.get("/status")
def get_billing_status(
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
) -> dict:
    return SubscriptionService.get_billing_status(db, business)


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(
    data: CheckoutRequest,
    business: Business = Depends(get_user_primary_business),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CheckoutResponse:
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured",
        )
    try:
        url = BillingService.create_checkout_session(db, business, user, data.plan)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return CheckoutResponse(checkout_url=url)


@router.post("/portal", response_model=PortalResponse)
def create_portal(
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
) -> PortalResponse:
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured",
        )
    try:
        url = BillingService.create_portal_session(db, business)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return PortalResponse(portal_url=url)


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    """Stripe webhook — no JWT auth, verified by signature."""
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    try:
        BillingService.handle_webhook_event(db, payload, signature)
    except stripe.SignatureVerificationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature") from exc
    except Exception as exc:
        logger.exception("Stripe webhook failed")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {"status": "ok"}
