"""Provider service identifiers — used by registry and factory."""

from __future__ import annotations

import enum


class ProviderService(str, enum.Enum):
    TELEPHONY = "telephony"
    NUMBERS = "numbers"
    REGULATORY = "regulatory"
    VOICE = "voice"
    MESSAGING = "messaging"
    STORAGE = "storage"
