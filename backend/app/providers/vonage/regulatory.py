"""Vonage regulatory / compliance adapter — Applications + media as end-user/docs."""

from __future__ import annotations

import logging
from typing import Any

from app.config import get_settings
from app.providers.base import ProviderResult
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import runtime_caps, vonage_regulatory
from app.providers.exceptions import ProviderUnavailableError
from app.providers.regulatory import RegulatoryProvider
from app.voice import vonage_client

logger = logging.getLogger(__name__)


class VonageRegulatoryProvider(RegulatoryProvider):
    """
    Maps Telnyx-style regulatory ports onto Vonage Applications + media uploads.

    Vonage country compliance is often dashboard-driven; these methods create
    durable external IDs operators can attach to number registration workflows.
    """

    @property
    def provider_name(self) -> str:
        return "vonage"

    def is_configured(self) -> bool:
        return vonage_client.is_vonage_configured()

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(vonage_regulatory(), self, service="regulatory")

    def _require(self) -> None:
        if not self.is_configured():
            raise ProviderUnavailableError(provider=self.provider_name)

    def create_end_user(self, *, business_id: str, payload: dict[str, Any]) -> ProviderResult:
        self._require()
        settings = get_settings()
        name = str(payload.get("friendly_name") or payload.get("business_name") or f"business-{business_id}")
        answer_url = f"{settings.public_api_url.rstrip('/')}/api/v1/voice/inbound"
        event_url = f"{settings.public_api_url.rstrip('/')}/api/v1/voice/status"
        record = vonage_client.create_application(
            name=name,
            answer_url=answer_url,
            event_url=event_url,
        )
        return ProviderResult(
            provider=self.provider_name,
            external_id=record.get("id"),
            data={**record, "business_id": business_id},
        )

    def upload_document(self, *, file_bytes: bytes, filename: str, content_type: str) -> ProviderResult:
        self._require()
        record = vonage_client.upload_media(
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
        )
        return ProviderResult(
            provider=self.provider_name,
            external_id=record.get("id") or filename,
            data=record,
        )

    def create_regulatory_bundle(self, *, country_code: str, end_user_id: str) -> ProviderResult:
        self._require()
        # Bundle identity is the application + country registration intent.
        bundle_id = f"{end_user_id}:{country_code.upper()}"
        record = vonage_client.get_application(end_user_id) if end_user_id else {}
        return ProviderResult(
            provider=self.provider_name,
            external_id=bundle_id,
            data={"bundle_id": bundle_id, "country_code": country_code.upper(), "application": record},
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
        return ProviderResult(
            provider=self.provider_name,
            external_id=bundle_id,
            data={"bundle_id": bundle_id, "status": "pending-review"},
        )

    def get_bundle_status(self, bundle_id: str) -> ProviderResult:
        self._require()
        end_user_id = bundle_id.split(":", 1)[0]
        record: dict[str, Any] = {"bundle_id": bundle_id, "status": "pending-review"}
        try:
            record["application"] = vonage_client.get_application(end_user_id)
            record["status"] = "active"
        except Exception as exc:  # noqa: BLE001 — surface provider status without crashing callers
            logger.info("Vonage bundle status probe failed", extra={"bundle_id": bundle_id, "error": str(exc)})
            record["status"] = "pending-review"
        return ProviderResult(provider=self.provider_name, external_id=bundle_id, data=record)

    def get_end_user_status(self, end_user_id: str) -> ProviderResult:
        self._require()
        record = vonage_client.get_application(end_user_id)
        return ProviderResult(
            provider=self.provider_name,
            external_id=end_user_id,
            data=record,
        )
