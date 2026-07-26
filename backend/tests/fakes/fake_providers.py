"""Test doubles — mock providers for unit tests."""

from __future__ import annotations

from app.providers.mocks import (
    MockMessagingProvider,
    MockNumberProvisioningProvider,
    MockRegulatoryProvider,
    MockTelephonyProvider,
    MockVoiceProvider,
)
from app.providers.mocks.storage import MockStorageProvider

FakeNumberProvisioningProvider = MockNumberProvisioningProvider
FakeRegulatoryProvider = MockRegulatoryProvider
FakeMessagingProvider = MockMessagingProvider
FakeTelephonyProvider = MockTelephonyProvider
FakeVoiceProvider = MockVoiceProvider
FakeStorageProvider = MockStorageProvider
