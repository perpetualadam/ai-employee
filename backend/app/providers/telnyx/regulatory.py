"""Telnyx regulatory compliance adapter."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import get_settings
from app.providers.base import ProviderResult
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import runtime_caps, telnyx_regulatory
from app.providers.exceptions import ProviderUnavailableError
from app.providers.regulatory import RegulatoryProvider

logger = logging.getLogger(__name__)

TELNYX_API_BASE = "https://api.telnyx.com/v2"


class TelnyxRegulatoryProvider(RegulatoryProvider):
    @property
    def provider_name(self) -> str:
        return "telnyx"

    def is_configured(self) -> bool:
        return bool(get_settings().telnyx_api_key)

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(telnyx_regulatory(), self, service="regulatory")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {get_settings().telnyx_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        if not self.is_configured():
            raise ProviderUnavailableError(provider=self.provider_name)
        with httpx.Client(timeout=60.0) as client:
            response = client.request(
                method,
                f"{TELNYX_API_BASE}{path}",
                headers=self._headers(),
                **kwargs,
            )
            response.raise_for_status()
            return response.json()

    def create_end_user(self, *, business_id: str, payload: dict[str, Any]) -> ProviderResult:
        body = {"business_id": business_id, **payload}
        data = self._request("POST", "/regulatory_requirements/end_users", json=body)
        record = data.get("data") or {}
        return ProviderResult(
            provider=self.provider_name,
            external_id=record.get("id"),
            data=record,
        )

    def upload_document(self, *, file_bytes: bytes, filename: str, content_type: str) -> ProviderResult:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{TELNYX_API_BASE}/documents",
                headers={"Authorization": f"Bearer {get_settings().telnyx_api_key}"},
                files={"file": (filename, file_bytes, content_type)},
            )
            response.raise_for_status()
            record = response.json().get("data") or {}
        return ProviderResult(
            provider=self.provider_name,
            external_id=record.get("id"),
            data=record,
        )

    def create_regulatory_bundle(self, *, country_code: str, end_user_id: str) -> ProviderResult:
        payload = {
            "country_code": country_code,
            "end_user_id": end_user_id,
        }
        data = self._request("POST", "/regulatory_requirements/bundles", json=payload)
        record = data.get("data") or {}
        return ProviderResult(
            provider=self.provider_name,
            external_id=record.get("id"),
            data=record,
        )

    def attach_document(self, *, bundle_id: str, document_id: str) -> ProviderResult:
        payload = {"document_id": document_id}
        data = self._request(
            "POST",
            f"/regulatory_requirements/bundles/{bundle_id}/documents",
            json=payload,
        )
        record = data.get("data") or {}
        return ProviderResult(
            provider=self.provider_name,
            external_id=bundle_id,
            data=record,
        )

    def submit_bundle(self, bundle_id: str) -> ProviderResult:
        data = self._request(
            "POST",
            f"/regulatory_requirements/bundles/{bundle_id}/submit",
        )
        record = data.get("data") or {}
        return ProviderResult(
            provider=self.provider_name,
            external_id=bundle_id,
            data=record,
        )

    def get_bundle_status(self, bundle_id: str) -> ProviderResult:
        data = self._request("GET", f"/regulatory_requirements/bundles/{bundle_id}")
        record = data.get("data") or {}
        return ProviderResult(
            provider=self.provider_name,
            external_id=bundle_id,
            data=record,
        )

    def get_end_user_status(self, end_user_id: str) -> ProviderResult:
        data = self._request("GET", f"/regulatory_requirements/end_users/{end_user_id}")
        record = data.get("data") or {}
        return ProviderResult(
            provider=self.provider_name,
            external_id=end_user_id,
            data=record,
        )
