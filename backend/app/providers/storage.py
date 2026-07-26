"""Object storage port — files never stored in PostgreSQL."""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.providers.base import BaseProvider


@dataclass(frozen=True)
class StoredObject:
    key: str
    size_bytes: int
    content_type: str


class StorageProvider(BaseProvider):
    @abstractmethod
    def upload(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
    ) -> StoredObject:
        ...

    @abstractmethod
    def download(self, key: str) -> bytes:
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        ...

    @abstractmethod
    def signed_url(self, key: str, *, expires_at: datetime) -> str:
        ...
