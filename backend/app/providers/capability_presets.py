"""Reusable capability presets for vendor adapters."""

from __future__ import annotations

from app.providers.capabilities import Capability, ProviderCapabilities

_NORTH_AMERICA = frozenset({"US", "CA", "*"})
_EU_UK = frozenset({"GB", "EU", "DE", "FR", "IE", "NL", "*"})
_OCEANIA = frozenset({"AU", "NZ", "*"})
_GLOBAL = frozenset({"*"})

_STANDARD_NUMBER_TYPES = frozenset({"local", "mobile", "toll_free"})


def telnyx_telephony() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name="telnyx",
        voice=True,
        sms=True,
        mms=True,
        call_transfer=True,
        voice_webhooks=True,
        sms_webhooks=True,
        texml=True,
        realtime_media_streams=True,
        duplex_voice=True,
        barge_in=True,
        recordings=True,
        transcriptions=True,
        local_numbers=True,
        mobile_numbers=True,
        toll_free_numbers=True,
        international_numbers=True,
        country_support=_NORTH_AMERICA | _EU_UK | _OCEANIA,
        supported_number_types=_STANDARD_NUMBER_TYPES,
    )


def telnyx_numbers() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name="telnyx",
        local_numbers=True,
        mobile_numbers=True,
        toll_free_numbers=True,
        international_numbers=True,
        number_porting=True,
        country_support=_NORTH_AMERICA | _EU_UK | _OCEANIA,
        supported_number_types=_STANDARD_NUMBER_TYPES,
    )


def telnyx_regulatory() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name="telnyx",
        regulatory_end_users=True,
        regulatory_bundles=True,
        document_upload=True,
        country_support=_EU_UK | frozenset({"US", "CA", "AU"}),
    )


def twilio_telephony() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name="twilio",
        voice=True,
        sms=True,
        mms=True,
        whatsapp=True,
        call_transfer=True,
        conference=True,
        voice_webhooks=True,
        sms_webhooks=True,
        sip=True,
        realtime_media_streams=True,
        duplex_voice=True,
        barge_in=True,
        recordings=True,
        transcriptions=True,
        call_insights=True,
        local_numbers=True,
        mobile_numbers=True,
        toll_free_numbers=True,
        international_numbers=True,
        country_support=_GLOBAL,
        supported_number_types=_STANDARD_NUMBER_TYPES,
    )


def twilio_numbers() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name="twilio",
        local_numbers=True,
        mobile_numbers=True,
        toll_free_numbers=True,
        international_numbers=True,
        number_porting=True,
        country_support=_GLOBAL,
        supported_number_types=_STANDARD_NUMBER_TYPES,
    )


def twilio_regulatory() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name="twilio",
        regulatory_end_users=True,
        regulatory_bundles=True,
        document_upload=True,
        country_support=_GLOBAL,
    )


def vonage_telephony() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name="vonage",
        voice=True,
        sms=True,
        mms=True,
        whatsapp=True,
        call_transfer=True,
        voice_webhooks=True,
        sms_webhooks=True,
        sip=True,
        realtime_media_streams=True,
        duplex_voice=True,
        barge_in=True,
        local_numbers=True,
        mobile_numbers=True,
        toll_free_numbers=True,
        international_numbers=True,
        country_support=_GLOBAL,
        supported_number_types=_STANDARD_NUMBER_TYPES,
    )


def vonage_numbers() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name="vonage",
        local_numbers=True,
        mobile_numbers=True,
        toll_free_numbers=True,
        international_numbers=True,
        number_porting=True,
        country_support=_GLOBAL,
        supported_number_types=_STANDARD_NUMBER_TYPES,
    )


def vonage_regulatory() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name="vonage",
        regulatory_end_users=True,
        regulatory_bundles=True,
        document_upload=True,
        country_support=_GLOBAL,
    )


def plivo_telephony() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name="plivo",
        voice=True,
        sms=True,
        mms=True,
        call_transfer=True,
        conference=True,
        voice_webhooks=True,
        sms_webhooks=True,
        sip=True,
        realtime_media_streams=True,
        duplex_voice=True,
        barge_in=True,
        recordings=True,
        local_numbers=True,
        mobile_numbers=True,
        toll_free_numbers=True,
        international_numbers=True,
        country_support=_GLOBAL,
        supported_number_types=_STANDARD_NUMBER_TYPES,
    )


def plivo_numbers() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name="plivo",
        local_numbers=True,
        mobile_numbers=True,
        toll_free_numbers=True,
        international_numbers=True,
        number_porting=True,
        country_support=_GLOBAL,
        supported_number_types=_STANDARD_NUMBER_TYPES,
    )


def plivo_regulatory() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name="plivo",
        regulatory_end_users=True,
        regulatory_bundles=True,
        document_upload=True,
        country_support=_GLOBAL,
    )


def signalwire_telephony() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name="signalwire",
        voice=True,
        sms=True,
        mms=True,
        call_transfer=True,
        conference=True,
        voice_webhooks=True,
        sms_webhooks=True,
        sip=True,
        realtime_media_streams=True,
        duplex_voice=True,
        barge_in=True,
        recordings=True,
        local_numbers=True,
        toll_free_numbers=True,
        international_numbers=True,
        country_support=_GLOBAL,
        supported_number_types=_STANDARD_NUMBER_TYPES,
    )


def signalwire_numbers() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name="signalwire",
        local_numbers=True,
        toll_free_numbers=True,
        international_numbers=True,
        number_porting=True,
        country_support=_GLOBAL,
        supported_number_types=_STANDARD_NUMBER_TYPES,
    )


def signalwire_regulatory() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name="signalwire",
        regulatory_end_users=True,
        regulatory_bundles=True,
        document_upload=True,
        country_support=_GLOBAL,
    )


def voipms_telephony() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name="voipms",
        voice=True,
        sms=True,
        mms=True,
        call_transfer=True,
        voice_webhooks=True,
        sms_webhooks=True,
        sip=True,
        local_numbers=True,
        toll_free_numbers=True,
        country_support=frozenset({"US", "CA"}),
        supported_number_types=frozenset({"local", "tollfree"}),
    )


def voipms_numbers() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name="voipms",
        local_numbers=True,
        toll_free_numbers=True,
        number_porting=True,
        country_support=frozenset({"US", "CA"}),
        supported_number_types=frozenset({"local", "tollfree"}),
    )


def voipms_regulatory() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name="voipms",
        regulatory_end_users=False,
        regulatory_bundles=False,
        document_upload=False,
        country_support=frozenset({"US", "CA"}),
    )


def openai_voice() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name="openai",
        ai_voice=True,
        transcriptions=True,
        country_support=_GLOBAL,
    )


def composite_messaging() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name="composite",
        sms=True,
        email=True,
        whatsapp=False,
        country_support=_GLOBAL,
    )


def local_sms() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name="local_sms",
        sms=True,
        email=True,
        simulated=True,
        country_support=_GLOBAL,
    )


def local_storage() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name="local",
        storage=True,
        document_upload=True,
        country_support=_GLOBAL,
    )


def resend_email() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name="resend",
        email=True,
        country_support=_GLOBAL,
    )


def dev_sms() -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name="dev_log",
        sms=True,
        simulated=True,
        country_support=_GLOBAL,
    )


def mock_all(name: str = "mock") -> ProviderCapabilities:
    return ProviderCapabilities(
        provider_name=name,
        voice=True,
        sms=True,
        email=True,
        whatsapp=True,
        call_transfer=True,
        local_numbers=True,
        mobile_numbers=True,
        regulatory_end_users=True,
        regulatory_bundles=True,
        document_upload=True,
        ai_voice=True,
        storage=True,
        simulated=True,
        country_support=_GLOBAL,
        supported_number_types=_STANDARD_NUMBER_TYPES,
    )


def runtime_caps(base: ProviderCapabilities, provider: object, *, service: str) -> ProviderCapabilities:
    from app.plugins.interfaces import BasePlugin

    health_status = "unconfigured"
    if isinstance(provider, BasePlugin):
        health_status = "ok" if provider.is_configured() else "unconfigured"
    elif hasattr(provider, "health"):
        try:
            health = provider.health(service=service)  # type: ignore[attr-defined]
        except TypeError:
            health = provider.health()  # type: ignore[misc]
        if isinstance(health, dict):
            health_status = str(health.get("status", "unknown"))
        elif hasattr(health, "status"):
            health_status = health.status if getattr(health, "healthy", True) else health.status
    elif hasattr(provider, "is_configured") and provider.is_configured():  # type: ignore[attr-defined]
        health_status = "ok"
    version = getattr(provider, "version", lambda: base.provider_version)()
    return base.with_runtime(
        health_status=health_status,
        provider_version=version,
    )
