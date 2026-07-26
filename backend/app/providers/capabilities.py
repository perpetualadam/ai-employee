"""Provider capability model — self-describing features, never compare vendor names in services."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any


class Capability:
    """Canonical capability identifiers used for routing and validation."""

    VOICE = "voice"
    SMS = "sms"
    MMS = "mms"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    RECORDING = "recording"
    CALL_TRANSFER = "call_transfer"
    CONFERENCE = "conference"
    LOCAL_NUMBERS = "local_numbers"
    MOBILE_NUMBERS = "mobile_numbers"
    TOLL_FREE_NUMBERS = "toll_free_numbers"
    INTERNATIONAL_NUMBERS = "international_numbers"
    NUMBER_PORTING = "number_porting"
    REGULATORY_END_USERS = "regulatory_end_users"
    REGULATORY_BUNDLES = "regulatory_bundles"
    DOCUMENT_UPLOAD = "document_upload"
    VOICE_WEBHOOKS = "voice_webhooks"
    SMS_WEBHOOKS = "sms_webhooks"
    TEXML = "texml"
    SIP = "sip"
    REALTIME_MEDIA_STREAMS = "realtime_media_streams"
    DUPLEX_VOICE = "duplex_voice"
    BARGE_IN = "barge_in"
    RECORDINGS = "recordings"
    TRANSCRIPTIONS = "transcriptions"
    CALL_INSIGHTS = "call_insights"
    AI_VOICE = "ai_voice"
    STORAGE = "storage"
    SIMULATED = "simulated"


# Maps capability id -> dataclass field name
_CAPABILITY_FIELDS: dict[str, str] = {
    Capability.VOICE: "voice",
    Capability.SMS: "sms",
    Capability.MMS: "mms",
    Capability.WHATSAPP: "whatsapp",
    Capability.EMAIL: "email",
    Capability.RECORDING: "recording",
    Capability.CALL_TRANSFER: "call_transfer",
    Capability.CONFERENCE: "conference",
    Capability.LOCAL_NUMBERS: "local_numbers",
    Capability.MOBILE_NUMBERS: "mobile_numbers",
    Capability.TOLL_FREE_NUMBERS: "toll_free_numbers",
    Capability.INTERNATIONAL_NUMBERS: "international_numbers",
    Capability.NUMBER_PORTING: "number_porting",
    Capability.REGULATORY_END_USERS: "regulatory_end_users",
    Capability.REGULATORY_BUNDLES: "regulatory_bundles",
    Capability.DOCUMENT_UPLOAD: "document_upload",
    Capability.VOICE_WEBHOOKS: "voice_webhooks",
    Capability.SMS_WEBHOOKS: "sms_webhooks",
    Capability.TEXML: "texml",
    Capability.SIP: "sip",
    Capability.REALTIME_MEDIA_STREAMS: "realtime_media_streams",
    Capability.DUPLEX_VOICE: "duplex_voice",
    Capability.BARGE_IN: "barge_in",
    Capability.RECORDINGS: "recordings",
    Capability.TRANSCRIPTIONS: "transcriptions",
    Capability.CALL_INSIGHTS: "call_insights",
    Capability.AI_VOICE: "ai_voice",
    Capability.STORAGE: "storage",
    Capability.SIMULATED: "simulated",
}


@dataclass(frozen=True)
class ProviderCapabilities:
    """Advertised capabilities for a provider implementation."""

    provider_name: str
    provider_version: str = "1.0.0"
    provider_priority: int = 100
    provider_weight: int = 100
    health_status: str = "unknown"

    voice: bool = False
    sms: bool = False
    mms: bool = False
    whatsapp: bool = False
    email: bool = False
    recording: bool = False
    call_transfer: bool = False
    conference: bool = False
    local_numbers: bool = False
    mobile_numbers: bool = False
    toll_free_numbers: bool = False
    international_numbers: bool = False
    number_porting: bool = False
    regulatory_end_users: bool = False
    regulatory_bundles: bool = False
    document_upload: bool = False
    voice_webhooks: bool = False
    sms_webhooks: bool = False
    texml: bool = False
    sip: bool = False
    realtime_media_streams: bool = False
    duplex_voice: bool = False
    barge_in: bool = False
    recordings: bool = False
    transcriptions: bool = False
    call_insights: bool = False
    ai_voice: bool = False
    storage: bool = False
    simulated: bool = False

    country_support: frozenset[str] = field(default_factory=frozenset)
    supported_number_types: frozenset[str] = field(default_factory=frozenset)
    metadata: dict[str, Any] = field(default_factory=dict)

    def supports(self, *features: str) -> bool:
        for feature in features:
            field_name = _CAPABILITY_FIELDS.get(feature, feature)
            if not getattr(self, field_name, False):
                return False
        return True

    def supports_country(self, country: str | None) -> bool:
        if not country:
            return True
        code = country.strip().upper()
        if not self.country_support:
            return True
        if "*" in self.country_support:
            return True
        if code in self.country_support:
            return True
        if code == "UK" and "GB" in self.country_support:
            return True
        return False

    def supports_number_type(self, number_type: str | None) -> bool:
        if not number_type or not self.supported_number_types:
            return True
        return number_type.lower() in {t.lower() for t in self.supported_number_types}

    def supported_features(self) -> frozenset[str]:
        enabled: set[str] = set()
        for cap_id, field_name in _CAPABILITY_FIELDS.items():
            if getattr(self, field_name, False):
                enabled.add(cap_id)
        return frozenset(enabled)

    def with_runtime(
        self,
        *,
        health_status: str | None = None,
        provider_priority: int | None = None,
        provider_weight: int | None = None,
        provider_version: str | None = None,
    ) -> ProviderCapabilities:
        updates: dict[str, Any] = {}
        if health_status is not None:
            updates["health_status"] = health_status
        if provider_priority is not None:
            updates["provider_priority"] = provider_priority
        if provider_weight is not None:
            updates["provider_weight"] = provider_weight
        if provider_version is not None:
            updates["provider_version"] = provider_version
        return replace(self, **updates)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "provider_priority": self.provider_priority,
            "provider_weight": self.provider_weight,
            "health_status": self.health_status,
            "country_support": sorted(self.country_support),
            "supported_number_types": sorted(self.supported_number_types),
            "supported_features": sorted(self.supported_features()),
            **{field_name: getattr(self, field_name) for field_name in _CAPABILITY_FIELDS.values()},
            "metadata": dict(self.metadata),
        }
