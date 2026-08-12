"""Provider-agnostic call recording injection into answer markup."""

from __future__ import annotations

from app.domain.recording import supports_call_recording
from app.integrations.adapters.call_recording import recording_status_callback_url


def with_call_recording(
    markup: str,
    *,
    base_url: str,
    call_log_id: str,
    provider: str | None,
    enabled: bool,
) -> str:
    """
    Inject provider-native recording instructions when supported.
    Safe no-op when disabled or the CPaaS cannot record from answer markup.
    """
    if not enabled or not supports_call_recording(provider):
        return markup
    from app.integrations.registry import get_call_recording_adapter

    adapter = get_call_recording_adapter(provider)
    if not adapter.supports_inline_recording():
        return markup
    return adapter.inject_recording(markup, base_url=base_url, call_log_id=call_log_id)


__all__ = ["recording_status_callback_url", "with_call_recording"]
