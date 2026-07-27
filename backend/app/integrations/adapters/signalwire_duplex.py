"""SignalWire duplex adapter — cXML Stream compatible with Twilio duplex path."""

from __future__ import annotations

from app.config import get_settings
from app.integrations.adapters.twilio_duplex import TwilioDuplexMediaAdapter


class SignalWireDuplexMediaAdapter(TwilioDuplexMediaAdapter):
    @property
    def provider_name(self) -> str:
        return "signalwire"

    def is_configured(self) -> bool:
        settings = get_settings()
        return bool(
            settings.signalwire_project_id
            and settings.signalwire_api_token
            and settings.signalwire_space_url
        )

    async def push_markup(self, call_id: str, markup: str) -> None:
        from app.voice import signalwire_client

        signalwire_client.update_call_cxml(call_id, markup)
