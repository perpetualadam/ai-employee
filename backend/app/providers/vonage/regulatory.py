"""Vonage regulatory stub."""

from __future__ import annotations

from typing import Any

from app.providers.base import ProviderResult
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import runtime_caps, vonage_regulatory
from app.providers.regulatory import RegulatoryProvider
from app.providers.stub import StubProviderMixin, stub_result


class VonageRegulatoryProvider(StubProviderMixin, RegulatoryProvider):
    _credential_fields = ("vonage_api_key", "vonage_api_secret")

    @property
    def provider_name(self) -> str:
        return "vonage"

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(vonage_regulatory(), self, service="regulatory")

    def create_end_user(self, *, business_id: str, payload: dict[str, Any]) -> ProviderResult:
        self._require_configured()
        return stub_result(self.provider_name, f"eu-{business_id}")

    def upload_document(self, *, file_bytes: bytes, filename: str, content_type: str) -> ProviderResult:
        self._require_configured()
        return stub_result(self.provider_name, f"doc-{filename}")

    def create_regulatory_bundle(self, *, country_code: str, end_user_id: str) -> ProviderResult:
        return stub_result(self.provider_name, f"bundle-{country_code}")

    def attach_document(self, *, bundle_id: str, document_id: str) -> ProviderResult:
        return stub_result(self.provider_name, bundle_id)

    def submit_bundle(self, bundle_id: str) -> ProviderResult:
        return stub_result(self.provider_name, bundle_id, status="pending")

    def get_bundle_status(self, bundle_id: str) -> ProviderResult:
        return stub_result(self.provider_name, bundle_id, status="pending")

    def get_end_user_status(self, end_user_id: str) -> ProviderResult:
        return stub_result(self.provider_name, end_user_id, status="pending")
