"""Telnyx plugin health probes."""

from plugins.telnyx.plugin import TelnyxPlugin


def check_health() -> dict:
    return TelnyxPlugin().health()
