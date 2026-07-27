"""SignalWire regulatory adapter — project/account scoped compliance records."""

from __future__ import annotations

from typing import Any

from app.providers.base import ProviderResult
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import runtime_caps, signalwire_regulatory
from app.providers.exceptions import ProviderUnavailableError
from app.providers.regulatory import RegulatoryProvider
from app.voice import signalwire_client


class SignalWireRegulatoryProvider(RegulatoryProvider):
    """
    SignalWire Compatibility API does not expose Twilio Trust Hub.

    End-user / bundle IDs are projected onto the SignalWire project account so
    operators can track verification state alongside DID provisioning.
    """

    @property
    def provider_name(self) -> str:
        return "signalwire"

    def is_configured(self) -> bool:
        return signalwire_client.is_signalwire_configured()

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(signalwire_regulatory(), self, service="regulatory")

    def _require(self) -> None:
        if not self.is_configured():
            raise ProviderUnavailableError(provider=self.provider_name)

    def create_end_user(self, *, business_id: str, payload: dict[str, Any]) -> ProviderResult:
        self._require()
        account = signalwire_client.get_account()
        external_id = f"{account.get('sid') or 'sw'}:eu:{business_id}"
        return ProviderResult(
            provider=self.provider_name,
            external_id=external_id,
            data={"business_id": business_id, "account": account, **payload},
        )

    def upload_document(self, *, file_bytes: bytes, filename: str, content_type: str) -> ProviderResult:
        self._require()
        return ProviderResult(
            provider=self.provider_name,
            external_id=f"doc-{filename}",
            data={
                "filename": filename,
                "content_type": content_type,
                "byte_length": len(file_bytes),
            },
        )

    def create_regulatory_bundle(self, *, country_code: str, end_user_id: str) -> ProviderResult:
        self._require()
        bundle_id = f"{end_user_id}:{country_code.upper()}"
        return ProviderResult(
            provider=self.provider_name,
            external_id=bundle_id,
            data={"bundle_id": bundle_id, "country_code": country_code.upper()},
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
        account = signalwire_client.get_account()
        return ProviderResult(
            provider=self.provider_name,
            external_id=bundle_id,
            data={"bundle_id": bundle_id, "status": "pending-review", "account": account},
        )

    def get_end_user_status(self, end_user_id: str) -> ProviderResult:
        self._require()
        account = signalwire_client.get_account()
        return ProviderResult(
            provider=self.provider_name,
            external_id=end_user_id,
            data={"end_user_id": end_user_id, "account": account, "status": "pending"},
        )
