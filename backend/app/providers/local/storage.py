"""Local filesystem storage — S3-compatible interface for future swap."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.config import get_settings
from app.providers.capabilities import ProviderCapabilities
from app.providers.capability_presets import local_storage, runtime_caps
from app.providers.exceptions import ProviderError
from app.providers.storage import StorageProvider, StoredObject

logger = logging.getLogger(__name__)


class LocalStorageProvider(StorageProvider):
    @property
    def provider_name(self) -> str:
        return "local"

    def is_configured(self) -> bool:
        return True

    def get_capabilities(self) -> ProviderCapabilities:
        return runtime_caps(local_storage(), self, service="storage")

    def _root(self) -> Path:
        root = Path(get_settings().storage_local_path)
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _path(self, key: str) -> Path:
        safe_key = key.replace("..", "").lstrip("/")
        return self._root() / safe_key

    def upload(self, *, key: str, data: bytes, content_type: str) -> StoredObject:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        logger.info("Stored object locally", extra={"key": key, "bytes": len(data)})
        return StoredObject(key=key, size_bytes=len(data), content_type=content_type)

    def download(self, key: str) -> bytes:
        path = self._path(key)
        if not path.is_file():
            raise ProviderError(f"Object not found: {key}")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.is_file():
            path.unlink()

    def signed_url(self, key: str, *, expires_at: datetime) -> str:
        settings = get_settings()
        ttl = max(int((expires_at - datetime.now(timezone.utc)).total_seconds()), 60)
        return f"{settings.public_api_url}/api/v1/admin/storage/{key}?expires={ttl}"
