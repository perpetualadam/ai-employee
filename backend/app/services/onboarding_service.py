"""Onboarding wizard logic, checklist, and sample data seeding."""

import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import Business, BusinessEmergencyRule, BusinessService, Customer
from app.models.enums import EmergencyAction, Industry
from app.schemas import BusinessServiceCreate, CustomerCreate, EmergencyRuleCreate
from app.services.business_service import BusinessServiceManager
from app.services.customer_service import CustomerService

logger = logging.getLogger(__name__)

DEFAULT_PLUMBING_SERVICES = [
    BusinessServiceCreate(
        name="Drain cleaning",
        description="Clear clogged drains and pipes",
        duration_minutes=60,
        is_emergency=False,
    ),
    BusinessServiceCreate(
        name="Water heater repair",
        description="Diagnose and repair water heater issues",
        duration_minutes=90,
        is_emergency=False,
    ),
    BusinessServiceCreate(
        name="Emergency leak repair",
        description="Urgent burst pipe or active leak",
        duration_minutes=60,
        is_emergency=True,
    ),
]

DEFAULT_EMERGENCY_RULES = [
    EmergencyRuleCreate(
        name="Burst pipe / flooding",
        keywords=["burst", "flood", "water everywhere", "pipe broke"],
        action=EmergencyAction.ESCALATE,
        instructions="Treat as emergency. Collect address immediately and transfer to owner.",
    ),
    EmergencyRuleCreate(
        name="Gas smell",
        keywords=["gas smell", "gas leak", "smell gas"],
        action=EmergencyAction.ESCALATE,
        instructions="Tell caller to leave the building and call 911. Transfer to owner.",
    ),
]


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
        """Add default plumbing services and emergency rules if missing."""
        created = {"services": 0, "emergency_rules": 0}

        existing_services = BusinessServiceManager.list_services(db, business.id)
        if not existing_services:
            for svc in DEFAULT_PLUMBING_SERVICES:
                BusinessServiceManager.add_service(db, business, svc)
                created["services"] += 1

        existing_rules = BusinessServiceManager.list_emergency_rules(db, business.id)
        if not existing_rules:
            for rule in DEFAULT_EMERGENCY_RULES:
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

        from app.models import Appointment
        from app.models.enums import AppointmentStatus

        tomorrow = datetime.now(UTC) + timedelta(days=1)
        start = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=1)

        appointment = Appointment(
            id=str(uuid4()),
            business_id=business.id,
            customer_id=customer.id,
            service_type="Drain cleaning",
            start_time=start,
            end_time=end,
            status=AppointmentStatus.SCHEDULED,
            notes="Sample appointment — delete anytime",
        )
        db.add(appointment)
        db.commit()

        logger.info("Sample data seeded", extra={"business_id": business.id})
        return {"customer_id": customer.id, "appointment_id": appointment.id, "already_exists": False}
