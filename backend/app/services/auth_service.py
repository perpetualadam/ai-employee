"""Authentication service."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.billing.plans import TRIAL_DAYS
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Business, User
from app.models.enums import PlanTier, SubscriptionStatus
from app.schemas import BusinessCreate, UserRegister

logger = logging.getLogger(__name__)

DEFAULT_WORKING_HOURS = {
    "monday": {"open": "08:00", "close": "17:00", "closed": False},
    "tuesday": {"open": "08:00", "close": "17:00", "closed": False},
    "wednesday": {"open": "08:00", "close": "17:00", "closed": False},
    "thursday": {"open": "08:00", "close": "17:00", "closed": False},
    "friday": {"open": "08:00", "close": "17:00", "closed": False},
    "saturday": {"open": "09:00", "close": "13:00", "closed": False},
    "sunday": {"open": "00:00", "close": "00:00", "closed": True},
}


class AuthService:
    @staticmethod
    def register_user(db: Session, data: UserRegister, business: BusinessCreate | None = None) -> User:
        existing = db.query(User).filter(User.email == data.email).first()
        if existing:
            raise ValueError("Email already registered")

        user = User(
            email=data.email.lower(),
            password_hash=hash_password(data.password),
            full_name=data.full_name,
        )
        db.add(user)
        db.flush()

        # Create default business profile on signup
        biz_data = business or BusinessCreate(name=f"{data.full_name}'s Business")
        biz = Business(
            owner_id=user.id,
            name=biz_data.name,
            industry=biz_data.industry,
            country=biz_data.country,
            timezone=biz_data.timezone,
            currency=biz_data.currency,
            working_hours=biz_data.working_hours or DEFAULT_WORKING_HOURS,
            ai_instructions=biz_data.ai_instructions,
            phone_number=biz_data.phone_number,
            subscription_status=SubscriptionStatus.TRIALING,
            plan_tier=PlanTier.STARTER,
            trial_ends_at=datetime.now(UTC) + timedelta(days=TRIAL_DAYS),
        )
        db.add(biz)
        db.flush()
        from app.services.business_slug_service import BusinessSlugService

        BusinessSlugService.ensure_unique_slug(db, biz)
        db.commit()
        db.refresh(user)

        logger.info("User registered", extra={"user_id": user.id, "business_id": biz.id})
        return user

    @staticmethod
    def authenticate(db: Session, email: str, password: str) -> User | None:
        user = db.query(User).filter(User.email == email.lower(), User.is_active.is_(True)).first()
        if user is None or not verify_password(password, user.password_hash):
            return None
        return user

    @staticmethod
    def create_token(user: User) -> str:
        return create_access_token(subject=user.id)
