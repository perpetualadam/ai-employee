"""Mock object storage for tests."""

from __future__ import annotations

from datetime import datetime

from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import mock_all, runtime_caps
from app.providers.storage import StorageProvider, StoredObject


class MockStorageProvider(StorageProvider):
    def __init__(self, name: str = "mock") -> None:
        self._name = name
        self._store: dict[str, bytes] = {}

    @property
    def provider_name(self) -> str:
        return self._name

    def is_configured(self) -> bool:
        return True

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(mock_all(self._name), self, service="storage")

    def upload(self, *, key: str, data: bytes, content_type: str) -> StoredObject:
        self._store[key] = data
        return StoredObject(key=key, size_bytes=len(data), content_type=content_type)

    def download(self, key: str) -> bytes:
        return self._store[key]

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def signed_url(self, key: str, *, expires_at: datetime) -> str:
        return f"https://mock.test/{key}"
