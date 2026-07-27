"""Plivo Compliance API adapter."""

from __future__ import annotations

from typing import Any

from app.providers.base import ProviderResult
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import runtime_caps, plivo_regulatory
from app.providers.exceptions import ProviderUnavailableError
from app.providers.regulatory import RegulatoryProvider
from app.voice import plivo_client


class PlivoRegulatoryProvider(RegulatoryProvider):
    @property
    def provider_name(self) -> str:
        return "plivo"

    def is_configured(self) -> bool:
        return plivo_client.is_plivo_configured()

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(plivo_regulatory(), self, service="regulatory")

    def _require(self) -> None:
        if not self.is_configured():
            raise ProviderUnavailableError(provider=self.provider_name)

    def create_end_user(self, *, business_id: str, payload: dict[str, Any]) -> ProviderResult:
        self._require()
        end_user_type = str(payload.get("type") or payload.get("end_user_type") or "business")
        attributes = {
            key: value
            for key, value in payload.items()
            if key not in {"type", "end_user_type"}
        }
        attributes.setdefault("business_id", business_id)
        record = plivo_client.create_end_user(end_user_type=end_user_type, attributes=attributes)
        return ProviderResult(
            provider=self.provider_name,
            external_id=record.get("end_user_id") or record.get("id"),
            data=record,
        )

    def upload_document(self, *, file_bytes: bytes, filename: str, content_type: str) -> ProviderResult:
        self._require()
        record = plivo_client.upload_compliance_document(
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
        )
        return ProviderResult(
            provider=self.provider_name,
            external_id=record.get("document_id") or record.get("id") or filename,
            data=record,
        )

    def create_regulatory_bundle(self, *, country_code: str, end_user_id: str) -> ProviderResult:
        self._require()
        record = plivo_client.create_compliance_application(
            end_user_type="business",
            country_iso=country_code.upper(),
            number_type="local",
        )
        return ProviderResult(
            provider=self.provider_name,
            external_id=record.get("compliance_application_uuid") or record.get("id"),
            data={**record, "end_user_id": end_user_id},
        )

    def attach_document(self, *, bundle_id: str, document_id: str) -> ProviderResult:
        self._require()
        return ProviderResult(
            provider=self.provider_name,
            external_id=bundle_id,
            data={"bundle_id": bundle_id, "document_id": document_id, "attached": True},
        )

    def submit_bundle(self, bundle_id: str) -> ProviderResult:
        self._require()
        record = plivo_client.submit_compliance_application(bundle_id)
        return ProviderResult(provider=self.provider_name, external_id=bundle_id, data=record)

    def get_bundle_status(self, bundle_id: str) -> ProviderResult:
        self._require()
        record = plivo_client.get_compliance_application(bundle_id)
        return ProviderResult(provider=self.provider_name, external_id=bundle_id, data=record)

    def get_end_user_status(self, end_user_id: str) -> ProviderResult:
        self._require()
        return ProviderResult(
            provider=self.provider_name,
            external_id=end_user_id,
            data={"end_user_id": end_user_id, "status": "pending"},
        )
