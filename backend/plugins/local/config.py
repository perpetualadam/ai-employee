"""Local plugin configuration."""

from __future__ import annotations

from app.config import get_settings


class LocalPluginConfig:
    @property
    def storage_path(self) -> str:
        return get_settings().storage_local_path

    def validate(self) -> list[str]:
        return []
