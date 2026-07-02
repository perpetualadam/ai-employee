"""Onboarding wizard logic, checklist, and sample data seeding."""

import logging

from sqlalchemy.orm import Session

from app.domain.trades.registry import get_trade_template, resolve_trade_context
from app.models import Business, Customer
from app.models.enums import Industry
from app.schemas import CustomerCreate
from app.services.business_service import BusinessServiceManager
from app.services.customer_service import CustomerService

logger = logging.getLogger(__name__)


class OnboardingService:
    @staticmethod
    def get_checklist(db: Session, business: Business) -> dict:
        services = BusinessServiceManager.list_services(db, business.id)
        customers = CustomerService.list_customers(db, business.id)
        rules = BusinessServiceManager.list_emergency_rules(db, business.id)

        from app.models import AIActivityLog, CallLog

        has_tested_ai = (
            db.query(CallLog).filter(CallLog.business_id == business.id).count() > 0
            or db.query(AIActivityLog).filter(AIActivityLog.business_id == business.id).count() > 0
        )

        has_custom_name = not business.name.endswith("'s Business")

        steps = [
            {
                "id": "business_profile",
                "title": "Set up business profile",
                "description": "Add your company name and industry",
                "completed": has_custom_name and business.industry != Industry.GENERAL,
                "href": "/onboarding?step=1",
            },
            {
                "id": "services",
                "title": "Add your services",
                "description": "Tell the AI what jobs you take on",
                "completed": len(services) >= 1,
                "href": "/onboarding?step=2",
            },
            {
                "id": "phone",
                "title": "Configure phone numbers",
                "description": "Connect your Telnyx number and escalation line",
                "completed": bool(business.phone_number),
                "href": "/onboarding?step=3",
            },
            {
                "id": "emergency_rules",
                "title": "Set emergency rules",
                "description": "Define when to escalate urgent calls",
                "completed": len(rules) >= 1,
                "href": "/onboarding?step=3",
            },
            {
                "id": "test_ai",
                "title": "Test your AI receptionist",
                "description": "Run a practice conversation",
                "completed": has_tested_ai,
                "href": "/dashboard/receptionist",
            },
        ]

        completed_count = sum(1 for s in steps if s["completed"])

        return {
            "onboarding_completed": business.onboarding_completed,
            "steps": steps,
            "completed_count": completed_count,
            "total_steps": len(steps),
            "progress_percent": int((completed_count / len(steps)) * 100),
        }

    @staticmethod
    def complete_onboarding(db: Session, business: Business) -> Business:
        business.onboarding_completed = True
        db.commit()
        db.refresh(business)
        logger.info("Onboarding completed", extra={"business_id": business.id})
        return business

    @staticmethod
    def seed_defaults(db: Session, business: Business) -> dict:
        """Add default services and emergency rules from the business trade template."""
        template = get_trade_template(business.industry)
        created = {"services": 0, "emergency_rules": 0, "industry": template.industry.value}

        existing_services = BusinessServiceManager.list_services(db, business.id)
        if not existing_services:
            for svc in template.service_creates():
                BusinessServiceManager.add_service(db, business, svc)
                created["services"] += 1

        existing_rules = BusinessServiceManager.list_emergency_rules(db, business.id)
        if not existing_rules:
            for rule in template.rule_creates():
                BusinessServiceManager.add_emergency_rule(db, business, rule)
                created["emergency_rules"] += 1

        return created

    @staticmethod
    def seed_sample_data(db: Session, business: Business) -> dict:
        """Create demo customer for exploring the CRM and calendar."""
        existing = CustomerService.list_customers(db, business.id)
        if existing:
            return {"customer_id": existing[0].id, "already_exists": True}

        customer = CustomerService.create_customer(
            db,
            business.id,
            CustomerCreate(
                name="Jane Smith",
                phone="+15555550100",
                email="jane@example.com",
                address="123 Oak Street, Springfield",
                notes="Sample customer — delete anytime",
            ),
        )

        from datetime import UTC, datetime, timedelta
        from uuid import uuid4

        from app.models import Appointment
        from app.models.enums import AppointmentStatus

        trade = resolve_trade_context(business)
        tomorrow = datetime.now(UTC) + timedelta(days=1)
        start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=1)

        appointment = Appointment(
            id=str(uuid4()),
            business_id=business.id,
            customer_id=customer.id,
            service_type=trade.sample_service_name,
            start_time=start,
            end_time=end,
            status=AppointmentStatus.SCHEDULED,
            notes="Sample appointment — delete anytime",
        )
        db.add(appointment)
        db.commit()

        logger.info("Sample data seeded", extra={"business_id": business.id})
        return {"customer_id": customer.id, "appointment_id": appointment.id, "already_exists": False}
