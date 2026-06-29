"""Onboarding wizard and checklist endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_user_primary_business
from app.database import get_db
from app.models import Business
from app.schemas import BusinessResponse
from app.services.onboarding_service import OnboardingService

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.get("/status")
def get_onboarding_status(
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
) -> dict:
    return OnboardingService.get_checklist(db, business)


@router.post("/complete", response_model=BusinessResponse)
def complete_onboarding(
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
) -> Business:
    return OnboardingService.complete_onboarding(db, business)


@router.post("/seed-defaults")
def seed_defaults(
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
) -> dict:
    """Add default plumbing services and emergency rules."""
    return OnboardingService.seed_defaults(db, business)


@router.post("/sample-data")
def seed_sample_data(
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
) -> dict:
    """Add a demo customer and appointment."""
    return OnboardingService.seed_sample_data(db, business)
