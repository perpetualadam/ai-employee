"""Regulatory compliance port — KYC bundles and document submission."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from app.providers.base import BaseProvider, ProviderResult


class RegulatoryProvider(BaseProvider):
    @abstractmethod
    def create_end_user(self, *, business_id: str, payload: dict[str, Any]) -> ProviderResult:
        ...

    @abstractmethod
    def upload_document(self, *, file_bytes: bytes, filename: str, content_type: str) -> ProviderResult:
        ...

    @abstractmethod
    def create_regulatory_bundle(self, *, country_code: str, end_user_id: str) -> ProviderResult:
        ...

    @abstractmethod
    def attach_document(self, *, bundle_id: str, document_id: str) -> ProviderResult:
        ...

    @abstractmethod
    def submit_bundle(self, bundle_id: str) -> ProviderResult:
        ...

    @abstractmethod
    def get_bundle_status(self, bundle_id: str) -> ProviderResult:
        ...

    @abstractmethod
    def get_end_user_status(self, end_user_id: str) -> ProviderResult:
        ...
