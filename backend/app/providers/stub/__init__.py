"""Shared helpers for vendor stub providers (Twilio, Vonage, etc.)."""

from __future__ import annotations

from typing import Any, AsyncIterator

from app.providers.base import ProviderResult
from app.providers.exceptions import ProviderUnavailableError
from app.providers.voice import TranscriptSegment


class StubProviderMixin:
    """Mixin for stub CPaaS providers — configured via env credentials."""

    _credential_fields: tuple[str, ...] = ()

    def _has_credentials(self) -> bool:
        from app.config import get_settings

        settings = get_settings()
        return all(bool(getattr(settings, field, "")) for field in self._credential_fields)

    def is_configured(self) -> bool:
        return self._has_credentials()

    def _require_configured(self) -> None:
        if not self.is_configured():
            raise ProviderUnavailableError(
                f"{self.provider_name} is not configured — set required environment credentials",
            )


def stub_result(provider: str, external_id: str = "stub-1", **data: Any) -> ProviderResult:
    return ProviderResult(provider=provider, external_id=external_id, data=dict(data))


async def stub_transcript_stream() -> AsyncIterator[TranscriptSegment]:
    yield TranscriptSegment(text="stub", is_final=True)
