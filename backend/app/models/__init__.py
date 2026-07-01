"""SQLAlchemy ORM models — all tenant-scoped tables include business_id."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import (
    AppointmentStatus,
    CallDirection,
    CallStatus,
    ConversationChannel,
    EmergencyAction,
    Industry,
    JobStatus,
    PlanTier,
    SubscriptionStatus,
)

if TYPE_CHECKING:
    pass


def _enum_values(enum_class: type[enum.Enum]) -> list[str]:
    """Persist Python enum values (e.g. plumbing) not names (PLUMBING)."""
    return [member.value for member in enum_class]


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(Base, TimestampMixin):
    """Business owner or team member account."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    businesses: Mapped[list["Business"]] = relationship(
        "Business", back_populates="owner", cascade="all, delete-orphan"
    )


class Business(Base, TimestampMixin):
    """
    Tenant root entity. Every business has isolated data via business_id
    on all related tables.
    """

    __tablename__ = "businesses"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    owner_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[Industry] = mapped_column(
        Enum(Industry, name="industry", values_callable=_enum_values), default=Industry.PLUMBING, nullable=False
    )
    country: Mapped[str] = mapped_column(String(2), default="US", nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="America/New_York", nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    # Weekly schedule: {"monday": {"open": "08:00", "close": "17:00"}, ...}
    working_hours: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    ai_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    escalation_phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    public_slug: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True, index=True)

    # Billing (Stripe)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    subscription_status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status", values_callable=_enum_values),
        default=SubscriptionStatus.TRIALING,
        nullable=False,
    )
    plan_tier: Mapped[PlanTier] = mapped_column(
        Enum(PlanTier, name="plan_tier", values_callable=_enum_values),
        default=PlanTier.STARTER,
        nullable=False,
    )
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    subscription_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    owner: Mapped["User"] = relationship("User", back_populates="businesses")
    services: Mapped[list["BusinessService"]] = relationship(
        "BusinessService", back_populates="business", cascade="all, delete-orphan"
    )
    emergency_rules: Mapped[list["BusinessEmergencyRule"]] = relationship(
        "BusinessEmergencyRule", back_populates="business", cascade="all, delete-orphan"
    )
    customers: Mapped[list["Customer"]] = relationship(
        "Customer", back_populates="business", cascade="all, delete-orphan"
    )
    jobs: Mapped[list["Job"]] = relationship(
        "Job", back_populates="business", cascade="all, delete-orphan"
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="business", cascade="all, delete-orphan"
    )
    call_logs: Mapped[list["CallLog"]] = relationship(
        "CallLog", back_populates="business", cascade="all, delete-orphan"
    )


class BusinessService(Base, TimestampMixin):
    """Services offered by a business (e.g. drain cleaning, water heater install)."""

    __tablename__ = "business_services"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    business_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    price_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_emergency: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    business: Mapped["Business"] = relationship("Business", back_populates="services")


class BusinessEmergencyRule(Base, TimestampMixin):
    """Rules for handling urgent calls (burst pipe, gas leak, etc.)."""

    __tablename__ = "business_emergency_rules"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    business_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    keywords: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    action: Mapped[EmergencyAction] = mapped_column(
        Enum(EmergencyAction, name="emergency_action", values_callable=_enum_values), nullable=False
    )
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    business: Mapped["Business"] = relationship("Business", back_populates="emergency_rules")


class Customer(Base, TimestampMixin):
    """CRM customer record — scoped to a single business."""

    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("business_id", "phone", name="uq_customers_business_phone"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    business_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    business: Mapped["Business"] = relationship("Business", back_populates="customers")
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="customer")
    appointments: Mapped[list["Appointment"]] = relationship("Appointment", back_populates="customer")
    call_logs: Mapped[list["CallLog"]] = relationship("CallLog", back_populates="customer")


class Job(Base, TimestampMixin):
    """Work order / job linked to a customer."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    business_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    appointment_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    service_type: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", values_callable=_enum_values), default=JobStatus.LEAD, nullable=False
    )
    appointment_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    business: Mapped["Business"] = relationship("Business", back_populates="jobs")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="jobs")
    appointment: Mapped[Optional["Appointment"]] = relationship(
        "Appointment", back_populates="job"
    )


class Appointment(Base, TimestampMixin):
    """Calendar appointment — internal scheduling system."""

    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    business_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_type: Mapped[str] = mapped_column(String(255), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus, name="appointment_status", values_callable=_enum_values),
        default=AppointmentStatus.SCHEDULED,
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confirmation_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    business: Mapped["Business"] = relationship("Business", back_populates="appointments")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="appointments")
    job: Mapped[Optional["Job"]] = relationship("Job", back_populates="appointment", uselist=False)


class CallLog(Base, TimestampMixin):
    """Phone call record for dashboard and AI training."""

    __tablename__ = "call_logs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    business_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    external_call_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    channel: Mapped[ConversationChannel] = mapped_column(
        Enum(ConversationChannel, name="conversation_channel", values_callable=_enum_values),
        default=ConversationChannel.VOICE,
        nullable=False,
    )
    parent_call_log_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("call_logs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    direction: Mapped[CallDirection] = mapped_column(
        Enum(CallDirection, name="call_direction", values_callable=_enum_values), nullable=False
    )
    status: Mapped[CallStatus] = mapped_column(
        Enum(CallStatus, name="call_status", values_callable=_enum_values), default=CallStatus.RINGING, nullable=False
    )
    caller_phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    conversation_history: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    business: Mapped["Business"] = relationship("Business", back_populates="call_logs")
    customer: Mapped[Optional["Customer"]] = relationship("Customer", back_populates="call_logs")
    ai_activities: Mapped[list["AIActivityLog"]] = relationship(
        "AIActivityLog", back_populates="call_log", cascade="all, delete-orphan"
    )


class AIActivityLog(Base):
    """Audit log of AI tool calls and decisions during conversations."""

    __tablename__ = "ai_activity_logs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    business_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    call_log_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("call_logs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    tool_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    input_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    output_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    call_log: Mapped[Optional["CallLog"]] = relationship("CallLog", back_populates="ai_activities")


class AddressConfirmationToken(Base, TimestampMixin):
    """Signed link for customers to confirm service address after voice STT issues."""

    __tablename__ = "address_confirmation_tokens"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    business_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    call_log_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("call_logs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    customer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class WebContinuationToken(Base, TimestampMixin):
    """Token for customers to continue a voice call on the public web chat."""

    __tablename__ = "web_continuation_tokens"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    business_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    call_log_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("call_logs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
