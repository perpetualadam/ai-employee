"""Twilio Regulatory Compliance adapter — parity with TelnyxRegulatoryProvider."""

from __future__ import annotations

import logging
from typing import Any

from app.providers.base import ProviderResult
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import runtime_caps, twilio_regulatory
from app.providers.exceptions import ProviderUnavailableError
from app.providers.regulatory import RegulatoryProvider
from app.voice import twilio_client

logger = logging.getLogger(__name__)


class TwilioRegulatoryProvider(RegulatoryProvider):
    @property
    def provider_name(self) -> str:
        return "twilio"

    def is_configured(self) -> bool:
        return twilio_client.is_twilio_configured()

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(twilio_regulatory(), self, service="regulatory")

    def _require(self) -> None:
        if not self.is_configured():
            raise ProviderUnavailableError(provider=self.provider_name)

    def create_end_user(self, *, business_id: str, payload: dict[str, Any]) -> ProviderResult:
        self._require()
        end_user_type = str(payload.get("type") or payload.get("end_user_type") or "business")
        friendly_name = str(payload.get("friendly_name") or f"business-{business_id}")
        attributes = {
            key: value
            for key, value in payload.items()
            if key not in {"type", "end_user_type", "friendly_name"}
        }
        attributes.setdefault("business_id", business_id)
        record = twilio_client.create_end_user(
            friendly_name=friendly_name,
            end_user_type=end_user_type,
            attributes=attributes,
        )
        return ProviderResult(
            provider=self.provider_name,
            external_id=record.get("sid"),
            data=record,
        )

    def upload_document(self, *, file_bytes: bytes, filename: str, content_type: str) -> ProviderResult:
        """
        Create a Supporting Document metadata record.

        Twilio file attachment is a separate multi-step upload; this creates the
        compliance document object so callers can proceed with bundle assignment.
        """
        self._require()
        record = twilio_client.upload_supporting_document(
            friendly_name=filename,
            document_type="business_registration",
            attributes={
                "filename": filename,
                "content_type": content_type,
                "byte_length": len(file_bytes),
            },
        )
        return ProviderResult(
            provider=self.provider_name,
            external_id=record.get("sid"),
            data=record,
        )

    def create_regulatory_bundle(self, *, country_code: str, end_user_id: str) -> ProviderResult:
        self._require()
        record = twilio_client.create_regulatory_bundle(
            friendly_name=f"bundle-{country_code}-{end_user_id}",
            email="compliance@example.com",
            iso_country=country_code.upper(),
            end_user_type="business",
            number_type="local",
        )
        bundle_sid = record.get("sid")
        if bundle_sid and end_user_id:
            twilio_client.assign_bundle_item(bundle_sid=bundle_sid, object_sid=end_user_id)
        return ProviderResult(
            provider=self.provider_name,
            external_id=bundle_sid,
            data=record,
        )

    def attach_document(self, *, bundle_id: str, document_id: str) -> ProviderResult:
        self._require()
        record = twilio_client.assign_bundle_item(bundle_sid=bundle_id, object_sid=document_id)
        return ProviderResult(
            provider=self.provider_name,
            external_id=bundle_id,
            data=record,
        )

    def submit_bundle(self, bundle_id: str) -> ProviderResult:
        self._require()
        record = twilio_client.submit_regulatory_bundle(bundle_id)
        return ProviderResult(
            provider=self.provider_name,
            external_id=bundle_id,
            data=record,
        )

    def get_bundle_status(self, bundle_id: str) -> ProviderResult:
        self._require()
        record = twilio_client.get_regulatory_bundle(bundle_id)
        return ProviderResult(
            provider=self.provider_name,
            external_id=bundle_id,
            data=record,
        )

    def get_end_user_status(self, end_user_id: str) -> ProviderResult:
        self._require()
        record = twilio_client.get_end_user(end_user_id)
        return ProviderResult(
            provider=self.provider_name,
            external_id=end_user_id,
            data=record,
        )
