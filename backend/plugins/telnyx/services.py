"""Telnyx plugin service bindings — vendor code isolated to this plugin."""

from __future__ import annotations

from app.providers.telnyx.number_provisioning import TelnyxNumberProvisioningProvider
from app.providers.telnyx.regulatory import TelnyxRegulatoryProvider
from app.providers.telnyx.telephony import TelnyxTelephonyProvider


def telephony_provider() -> TelnyxTelephonyProvider:
    return TelnyxTelephonyProvider()


def number_provider() -> TelnyxNumberProvisioningProvider:
    return TelnyxNumberProvisioningProvider()


def regulatory_provider() -> TelnyxRegulatoryProvider:
    return TelnyxRegulatoryProvider()
