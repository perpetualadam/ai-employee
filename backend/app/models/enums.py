"""Shared enums used across models."""

import enum


class Industry(str, enum.Enum):
    PLUMBING = "plumbing"
    ELECTRICAL = "electrical"
    HVAC = "hvac"
    ROOFING = "roofing"
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
