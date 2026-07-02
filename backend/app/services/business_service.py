"""Business profile management."""

import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Business, BusinessEmergencyRule, BusinessService
from app.schemas import (
    BusinessServiceCreate,
    BusinessUpdate,
    EmergencyRuleCreate,
)
from app.services.phone_provisioning_service import PhoneProvisioningService

logger = logging.getLogger(__name__)


class BusinessServiceManager:
    @staticmethod
    def update_business(db: Session, business: Business, data: BusinessUpdate) -> Business:
        update_data = data.model_dump(exclude_unset=True)
        phone_number = update_data.pop("phone_number", None)
        escalation_phone = update_data.pop("escalation_phone", None)

        if phone_number is not None:
            if business.phone_provisioned:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Provisioned phone numbers cannot be changed here.",
                )
            PhoneProvisioningService.save_manual_phone(db, business, phone_number)

        if escalation_phone is not None:
            if escalation_phone.strip():
                from app.domain.phone import is_plausible_phone, normalize_phone

                normalized = normalize_phone(escalation_phone.strip(), business.country)
                if not is_plausible_phone(normalized, business.country):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Enter a valid escalation phone number.",
                    )
                business.escalation_phone = normalized
            else:
                business.escalation_phone = None

        for field, value in update_data.items():
            setattr(business, field, value)
        db.commit()
        db.refresh(business)
        logger.info("Business updated", extra={"business_id": business.id})
        return business

    @staticmethod
    def add_service(
        db: Session, business: Business, data: BusinessServiceCreate
    ) -> BusinessService:
        service = BusinessService(business_id=business.id, **data.model_dump())
        db.add(service)
        db.commit()
        db.refresh(service)
        return service

    @staticmethod
    def add_emergency_rule(
        db: Session, business: Business, data: EmergencyRuleCreate
    ) -> BusinessEmergencyRule:
        rule = BusinessEmergencyRule(business_id=business.id, **data.model_dump())
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return rule

    @staticmethod
    def list_services(db: Session, business_id: str) -> list[BusinessService]:
        return db.query(BusinessService).filter(BusinessService.business_id == business_id).all()

    @staticmethod
    def list_emergency_rules(db: Session, business_id: str) -> list[BusinessEmergencyRule]:
        return (
            db.query(BusinessEmergencyRule)
            .filter(BusinessEmergencyRule.business_id == business_id)
            .all()
        )
