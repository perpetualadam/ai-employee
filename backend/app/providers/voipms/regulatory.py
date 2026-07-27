"""VoIP.ms regulatory adapter — portal-driven; API exposes DID ownership only."""

from __future__ import annotations

from typing import Any

from app.providers.base import ProviderResult
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import runtime_caps, voipms_regulatory
from app.providers.exceptions import ProviderUnavailableError
from app.providers.regulatory import RegulatoryProvider
from app.voice import voipms_client


class VoipMsRegulatoryProvider(RegulatoryProvider):
    @property
    def provider_name(self) -> str:
        return "voipms"

    def is_configured(self) -> bool:
        return voipms_client.is_voipms_configured()

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(voipms_regulatory(), self, service="regulatory")

    def _require(self) -> None:
        if not self.is_configured():
            raise ProviderUnavailableError(provider=self.provider_name)

    def create_end_user(self, *, business_id: str, payload: dict[str, Any]) -> ProviderResult:
        self._require()
        return ProviderResult(
            provider=self.provider_name,
            external_id=f"voipms-eu-{business_id}",
            data={"business_id": business_id, **payload, "status": "portal"},
        )

    def upload_document(self, *, file_bytes: bytes, filename: str, content_type: str) -> ProviderResult:
        self._require()
        return ProviderResult(
            provider=self.provider_name,
            external_id=f"voipms-doc-{filename}",
            data={
                "filename": filename,
                "content_type": content_type,
                "byte_length": len(file_bytes),
                "status": "portal",
            },
        )

    def create_regulatory_bundle(self, *, country_code: str, end_user_id: str) -> ProviderResult:
        self._require()
        bundle_id = f"{end_user_id}:{country_code.upper()}"
        return ProviderResult(
            provider=self.provider_name,
            external_id=bundle_id,
            data={"bundle_id": bundle_id, "status": "portal"},
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
        return ProviderResult(
            provider=self.provider_name,
            external_id=bundle_id,
            data={"bundle_id": bundle_id, "status": "portal"},
        )

    def get_end_user_status(self, end_user_id: str) -> ProviderResult:
        self._require()
        return ProviderResult(
            provider=self.provider_name,
            external_id=end_user_id,
            data={"end_user_id": end_user_id, "status": "portal"},
        )
