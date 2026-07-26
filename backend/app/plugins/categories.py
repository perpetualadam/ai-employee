"""Plugin category taxonomy."""

from __future__ import annotations

import enum


class PluginCategory(str, enum.Enum):
    TELEPHONY = "telephony"
    VOICE_AI = "voice_ai"
    SPEECH_TO_TEXT = "speech_to_text"
    TEXT_TO_SPEECH = "text_to_speech"
    MESSAGING = "messaging"
    EMAIL = "email"
    CRM = "crm"
    CALENDAR = "calendar"
    PAYMENTS = "payments"
    STORAGE = "storage"
    ANALYTICS = "analytics"
    MONITORING = "monitoring"
    AUTHENTICATION = "authentication"
    DOCUMENT_STORAGE = "document_storage"
    REGULATORY = "regulatory"
    WEBHOOK = "webhook"
    NOTIFICATION = "notification"
    AI_MODELS = "ai_models"
