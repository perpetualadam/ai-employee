"""Per-tenant phone number provisioning endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_user_primary_business
from app.database import get_db
from app.models import Business
from app.schemas import (
    PhoneProvisionRequest,
    PhoneProvisionResponse,
    PhoneProvisioningStatusResponse,
    PhoneSearchResponse,
)
from app.services.phone_provisioning_service import PhoneProvisioningService

router = APIRouter(prefix="/business/phone", tags=["phone"])


@router.get("/status", response_model=PhoneProvisioningStatusResponse)
def phone_status(
    business: Business = Depends(get_user_primary_business),
) -> PhoneProvisioningStatusResponse:
    return PhoneProvisioningService.status(business)


@router.get("/available", response_model=PhoneSearchResponse)
def search_phone_numbers(
    area_code: str | None = Query(default=None, max_length=10),
    limit: int = Query(default=10, ge=1, le=25),
    business: Business = Depends(get_user_primary_business),
) -> PhoneSearchResponse:
    numbers = PhoneProvisioningService.search_available(
        business,
        area_code=area_code,
        limit=limit,
    )
    return PhoneSearchResponse(country=business.country, numbers=numbers)


@router.post("/provision", response_model=PhoneProvisionResponse)
def provision_phone_number(
    body: PhoneProvisionRequest,
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
) -> PhoneProvisionResponse:
    result = PhoneProvisioningService.provision(db, business, body.phone_number)
    return PhoneProvisionResponse(**result)
