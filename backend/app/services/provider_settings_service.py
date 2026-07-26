"""Provider settings for a business — overrides vs country defaults."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Business
from app.providers.configuration import get_provider_configuration
from app.providers.factory import list_provider_registry
from app.providers.services import ProviderService


class ProviderSettingsService:
    @staticmethod
    def get_settings(business: Business) -> dict:
        config = get_provider_configuration()
        country_map = config.countries.get(business.country.upper(), {})
        country_defaults = {
            service.value: country_map[service.value]
            for service in ProviderService
            if service.value in country_map
        }
        return {
            "provider_config": dict(business.provider_config or {}),
            "country_defaults": country_defaults,
            "global_defaults": config.defaults,
            "available": list_provider_registry(),
        }
