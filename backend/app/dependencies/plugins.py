"""FastAPI dependency injection for plugins."""

from __future__ import annotations

from app.plugins.interfaces import (
    CalendarPlugin,
    CRMPlugin,
    EmailPlugin,
    MessagingPlugin,
    PaymentPlugin,
    SpeechToTextPlugin,
    StoragePlugin,
    TelephonyPlugin,
    VoicePlugin,
)
from app.plugins.manager import get_plugin_manager
from app.providers.factory import get_telephony_provider
from app.providers.telephony import TelephonyProvider


def get_telephony_plugin() -> TelephonyPlugin | None:
    return get_plugin_manager().get_telephony_plugin()


def get_ai_plugin() -> VoicePlugin | None:
    return get_plugin_manager().get_voice_plugin()


def get_messaging_plugin() -> MessagingPlugin | None:
    return get_plugin_manager().get_messaging_plugin()


def get_payment_plugin() -> PaymentPlugin | None:
    return get_plugin_manager().get_payment_plugin()


def get_storage_plugin_dep() -> StoragePlugin | None:
    return get_plugin_manager().get_storage_plugin()


def get_speech_to_text_plugin() -> SpeechToTextPlugin | None:
    return get_plugin_manager().get_speech_to_text_plugin()


def get_email_plugin() -> EmailPlugin | None:
    return get_plugin_manager().get_email_plugin()


def get_crm_plugin() -> CRMPlugin | None:
    return get_plugin_manager().get_crm_plugin()


def get_calendar_plugin() -> CalendarPlugin | None:
    return get_plugin_manager().get_calendar_plugin()


def get_telephony_provider_dep() -> TelephonyProvider:
    """Capability-routed telephony port — business services use this, not plugin names."""
    return get_telephony_provider()  # type: ignore[return-value]
