"""Pydantic request/response schemas."""

from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import (
    AppointmentStatus,
    CallDirection,
    CallStatus,
    ConversationChannel,
    EmergencyAction,
    Industry,
    JobStatus,
)


# ── Auth ──────────────────────────────────────────────────────────────────────


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    is_active: bool
    created_at: datetime


# ── Business ──────────────────────────────────────────────────────────────────


class WorkingHoursDay(BaseModel):
    open: str = Field(description="HH:MM format")
    close: str = Field(description="HH:MM format")
    closed: bool = False


class BusinessCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    industry: Industry = Industry.PLUMBING
    country: str = Field(default="US", min_length=2, max_length=2)
    timezone: str = "America/New_York"
    currency: str = Field(default="USD", min_length=3, max_length=3)
    working_hours: dict[str, WorkingHoursDay | dict[str, Any]] = Field(default_factory=dict)
    ai_instructions: Optional[str] = None
    phone_number: Optional[str] = None
    escalation_phone: Optional[str] = None


class BusinessUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    industry: Optional[Industry] = None
    country: Optional[str] = Field(default=None, min_length=2, max_length=2)
    timezone: Optional[str] = None
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    working_hours: Optional[dict[str, Any]] = None
    ai_instructions: Optional[str] = None
    phone_number: Optional[str] = None
    escalation_phone: Optional[str] = None
    reminders_enabled: Optional[bool] = None


class BusinessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    name: str
    industry: Industry
    country: str
    timezone: str
    currency: str
    working_hours: dict
    ai_instructions: Optional[str]
    phone_number: Optional[str]
    phone_provisioned: bool = False
    escalation_phone: Optional[str]
    reminders_enabled: bool = True
    public_slug: Optional[str]
    onboarding_completed: bool
    created_at: datetime
    updated_at: datetime


class AvailablePhoneNumber(BaseModel):
    phone_number: str
    region: Optional[str] = None
    cost: Optional[str] = None


class PhoneProvisioningStatusResponse(BaseModel):
    phone_number: Optional[str] = None
    provisioned: bool = False
    platform_configured: bool = False
    can_search: bool = False
    manual_fallback_allowed: bool = True
    country: str = "US"


class PhoneSearchResponse(BaseModel):
    numbers: list[AvailablePhoneNumber]
    country: str


class PhoneProvisionRequest(BaseModel):
    phone_number: str = Field(min_length=8, max_length=32)


class PhoneProvisionResponse(BaseModel):
    phone_number: str
    provisioned: bool
    telnyx_phone_number_id: Optional[str] = None
    message: str


class OutboundCallRequest(BaseModel):
    customer_id: Optional[str] = None
    phone: Optional[str] = Field(default=None, max_length=32)
    reason: Optional[str] = Field(default=None, max_length=500)


class OutboundCallResponse(BaseModel):
    call_log_id: str
    status: str
    external_call_id: Optional[str] = None
    message: str


class ReminderRunResponse(BaseModel):
    checked: int
    sent: int
    results: list[dict]


class BusinessServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    duration_minutes: int = Field(default=60, ge=15, le=480)
    price_cents: Optional[int] = Field(default=None, ge=0)
    is_emergency: bool = False


class BusinessServiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    business_id: str
    name: str
    description: Optional[str]
    duration_minutes: int
    price_cents: Optional[int]
    is_emergency: bool


class EmergencyRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    keywords: list[str] = Field(default_factory=list)
    action: EmergencyAction
    instructions: Optional[str] = None
    is_active: bool = True


class EmergencyRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    business_id: str
    name: str
    keywords: list
    action: EmergencyAction
    instructions: Optional[str]
    is_active: bool


# ── CRM ───────────────────────────────────────────────────────────────────────


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    phone: str = Field(min_length=7, max_length=32)
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    phone: Optional[str] = Field(default=None, min_length=7, max_length=32)
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    business_id: str
    name: str
    phone: str
    email: Optional[str]
    address: Optional[str]
    notes: Optional[str]
    created_at: datetime


# ── Jobs ──────────────────────────────────────────────────────────────────────


class JobCreate(BaseModel):
    customer_id: str
    service_type: str = Field(min_length=1, max_length=255)
    notes: Optional[str] = None
    status: JobStatus = JobStatus.LEAD
    appointment_time: Optional[datetime] = None
    appointment_id: Optional[str] = None


class JobUpdate(BaseModel):
    service_type: Optional[str] = Field(default=None, min_length=1, max_length=255)
    notes: Optional[str] = None
    status: Optional[JobStatus] = None
    appointment_time: Optional[datetime] = None
    appointment_id: Optional[str] = None


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    business_id: str
    customer_id: str
    appointment_id: Optional[str]
    service_type: str
    notes: Optional[str]
    status: JobStatus
    appointment_time: Optional[datetime]
    created_at: datetime


# ── Appointments ──────────────────────────────────────────────────────────────


class AppointmentCreate(BaseModel):
    customer_id: str
    service_type: str = Field(min_length=1, max_length=255)
    start_time: datetime
    end_time: datetime
    notes: Optional[str] = None


class AppointmentUpdate(BaseModel):
    service_type: Optional[str] = Field(default=None, min_length=1, max_length=255)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = None


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    business_id: str
    customer_id: str
    service_type: str
    start_time: datetime
    end_time: datetime
    status: AppointmentStatus
    notes: Optional[str]
    confirmation_sent_at: Optional[datetime]
    created_at: datetime


class AppointmentBulkCancelRequest(BaseModel):
    appointment_ids: list[str] = Field(min_length=1, max_length=200)


class AppointmentBulkCancelResponse(BaseModel):
    cancelled: int
    skipped: int


class AvailabilitySlot(BaseModel):
    start_time: datetime
    end_time: datetime


class AvailabilityResponse(BaseModel):
    date: date
    duration_minutes: int
    slots: list[AvailabilitySlot]


# ── Dashboard ─────────────────────────────────────────────────────────────────


class CallLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    business_id: str
    customer_id: Optional[str]
    direction: CallDirection
    status: CallStatus
    caller_phone: Optional[str]
    duration_seconds: Optional[int]
    summary: Optional[str]
    ai_summary: Optional[str] = None
    escalated: bool
    created_at: datetime


# ── Conversations (unified inbox) ─────────────────────────────────────────────


class ConversationLeadCard(BaseModel):
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    service_address: Optional[str] = None
    service_type: Optional[str] = None
    appointment_time: Optional[datetime] = None
    is_booked: bool = False
    is_escalated: bool = False
    is_emergency: bool = False


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    channel: Optional[str] = None


class ConversationListItem(BaseModel):
    id: str
    channel: ConversationChannel
    channel_label: str
    status: CallStatus
    caller_phone: Optional[str]
    summary: Optional[str]
    ai_summary: Optional[str]
    escalated: bool
    is_booked: bool
    created_at: datetime
    lead_card: ConversationLeadCard


class AIActivityDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    action: str
    tool_name: Optional[str]
    input_data: Optional[dict[str, Any]]
    output_data: Optional[dict[str, Any]]
    created_at: datetime


class ConversationDetailResponse(BaseModel):
    id: str
    business_id: str
    customer_id: Optional[str]
    channel: ConversationChannel
    channel_label: str
    status: CallStatus
    caller_phone: Optional[str]
    duration_seconds: Optional[int]
    summary: Optional[str]
    ai_summary: Optional[str]
    escalated: bool
    created_at: datetime
    transcript: Optional[str] = None
    messages: list[ConversationMessage]
    activities: list[AIActivityDetailResponse]
    lead_card: ConversationLeadCard


class AddressConfirmInfoResponse(BaseModel):
    business_name: str
    customer_name: Optional[str] = None
    already_confirmed: bool = False
    confirmed_address: Optional[str] = None


class AddressConfirmRequest(BaseModel):
    address: str = Field(min_length=5, max_length=500)


class AddressConfirmResponse(BaseModel):
    success: bool
    address: Optional[str] = None
    message: str


class PublicChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class PublicChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[PublicChatHistoryMessage] = Field(default_factory=list, max_length=50)
    session_id: str | None = None
    customer_phone: str | None = Field(default=None, max_length=32)


class PublicChatResponse(BaseModel):
    reply: str
    session_id: str
    tools_used: list[str]
    escalated: bool
    owner_notified: bool = False


class PublicChatInfoResponse(BaseModel):
    business_name: str
    public_slug: str
    phone_number: Optional[str] = None


class PublicContinueInfoResponse(BaseModel):
    business_name: str
    session_id: str
    phone_number: Optional[str] = None
    messages: list[PublicChatHistoryMessage]
    voice_handoff: bool = True


class AIActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    business_id: str
    call_log_id: Optional[str]
    action: str
    tool_name: Optional[str]
    created_at: datetime


class DashboardSummary(BaseModel):
    today_appointments: list[AppointmentResponse]
    recent_calls: list[CallLogResponse]
    recent_customers: list[CustomerResponse]
    recent_jobs: list[JobResponse]
    recent_ai_activity: list[AIActivityResponse]
    stats: dict[str, int]


# ── AI Receptionist ───────────────────────────────────────────────────────────


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=50)
    session_id: str | None = Field(default=None, description="Call log ID for session continuity")
    caller_phone: str | None = Field(default=None, max_length=32)


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    tools_used: list[str]
    escalated: bool
    owner_notified: bool = False


# ── Onboarding ────────────────────────────────────────────────────────────────


class OnboardingStep(BaseModel):
    id: str
    title: str
    description: str
    completed: bool
    href: str


class OnboardingStatus(BaseModel):
    onboarding_completed: bool
    steps: list[OnboardingStep]
    completed_count: int
    total_steps: int
    progress_percent: int
