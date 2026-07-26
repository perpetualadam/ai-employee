"""Telnyx plugin isolated configuration."""

from __future__ import annotations

from app.config import get_settings
from plugins.telnyx.manifest import MANIFEST
from app.plugins.configuration import PluginConfigurationService


class TelnyxPluginConfig:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._scoped = PluginConfigurationService(MANIFEST)

    @property
    def api_key(self) -> str:
        return self._settings.telnyx_api_key or self._scoped.get("api_key")

    @property
    def messaging_profile_id(self) -> str:
        return self._settings.telnyx_messaging_profile_id or self._scoped.get("messaging_profile_id")

    @property
    def texml_connection_id(self) -> str:
        return self._settings.telnyx_texml_connection_id or self._scoped.get("texml_connection_id")
