"""Business profile management."""

import logging

from sqlalchemy.orm import Session

from app.models import Business, BusinessEmergencyRule, BusinessService
from app.schemas import (
    BusinessUpdate,
    EmergencyRuleCreate,
    BusinessServiceCreate,
)

logger = logging.getLogger(__name__)


class BusinessServiceManager:
    @staticmethod
    def update_business(db: Session, business: Business, data: BusinessUpdate) -> Business:
        update_data = data.model_dump(exclude_unset=True)
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
