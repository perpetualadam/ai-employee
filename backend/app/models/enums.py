"""Shared enums used across models."""

import enum


class Industry(str, enum.Enum):
    PLUMBING = "plumbing"
    ELECTRICAL = "electrical"
    HVAC = "hvac"
    ROOFING = "roofing"
    GAS_ENGINEER = "gas_engineer"
    MOBILE_MECHANIC = "mobile_mechanic"
    PLASTERER = "plasterer"
    CARPENTER = "carpenter"
    LOCKSMITH = "locksmith"
    PEST_CONTROL = "pest_control"
    LANDSCAPING = "landscaping"
    PAINTER = "painter"
    APPLIANCE_REPAIR = "appliance_repair"
    GENERAL = "general"


class JobStatus(str, enum.Enum):
    LEAD = "lead"
    QUOTED = "quoted"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class CallDirection(str, enum.Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class CallStatus(str, enum.Enum):
    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    MISSED = "missed"
    FAILED = "failed"
    TRANSFERRED = "transferred"


class EmergencyAction(str, enum.Enum):
    ESCALATE = "escalate"
    PRIORITY_BOOK = "priority_book"
    MESSAGE_OWNER = "message_owner"


class SubscriptionStatus(str, enum.Enum):
    NONE = "none"
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"


class PlanTier(str, enum.Enum):
    STARTER = "starter"
    PRO = "pro"


class ConversationChannel(str, enum.Enum):
    """How the customer reached the AI receptionist."""

    VOICE = "voice"
    SMS = "sms"
    WEB_CHAT = "web_chat"


class RegulatoryStatus(str, enum.Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    DOCUMENTS_REQUIRED = "documents_required"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class PhoneNumberStatus(str, enum.Enum):
    PENDING = "pending"
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    FAILED = "failed"
    RELEASED = "released"


class DocumentVerificationStatus(str, enum.Enum):
    PENDING = "pending"
    UPLOADED = "uploaded"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class DocumentType(str, enum.Enum):
    BUSINESS_REGISTRATION = "business_registration"
    PROOF_OF_ADDRESS = "proof_of_address"
    ID_DOCUMENT = "id_document"
    OTHER = "other"
