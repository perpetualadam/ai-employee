"""Business profile endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_user_primary_business
from app.database import get_db
from app.models import Business
from app.schemas import (
    BusinessResponse,
    BusinessServiceCreate,
    BusinessServiceResponse,
    BusinessUpdate,
    EmergencyRuleCreate,
    EmergencyRuleResponse,
)
from app.services.business_service import BusinessServiceManager

router = APIRouter(prefix="/business", tags=["business"])


@router.get("", response_model=BusinessResponse)
def get_business(business: Business = Depends(get_user_primary_business)) -> Business:
    return business


@router.patch("", response_model=BusinessResponse)
def update_business(
    data: BusinessUpdate,
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
) -> Business:
    return BusinessServiceManager.update_business(db, business, data)


@router.get("/services", response_model=list[BusinessServiceResponse])
def list_services(
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
) -> list:
    return BusinessServiceManager.list_services(db, business.id)


@router.post("/services", response_model=BusinessServiceResponse, status_code=status.HTTP_201_CREATED)
def create_service(
    data: BusinessServiceCreate,
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
):
    return BusinessServiceManager.add_service(db, business, data)


@router.get("/emergency-rules", response_model=list[EmergencyRuleResponse])
def list_emergency_rules(
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
) -> list:
    return BusinessServiceManager.list_emergency_rules(db, business.id)


@router.post(
    "/emergency-rules",
    response_model=EmergencyRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_emergency_rule(
    data: EmergencyRuleCreate,
    business: Business = Depends(get_user_primary_business),
    db: Session = Depends(get_db),
):
    return BusinessServiceManager.add_emergency_rule(db, business, data)
