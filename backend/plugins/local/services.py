"""Local dev messaging and filesystem storage providers."""

from __future__ import annotations

from app.providers.local.sms import LocalSMSProvider
from app.providers.local.storage import LocalStorageProvider


def messaging_provider() -> LocalSMSProvider:
    return LocalSMSProvider()


def storage_provider() -> LocalStorageProvider:
    return LocalStorageProvider()
