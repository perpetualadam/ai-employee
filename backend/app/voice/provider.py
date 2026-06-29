"""
Voice provider abstraction — swap Twilio/Telnyx without changing call flow logic.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass
class IncomingCall:
    call_id: str
    from_number: str
    to_number: str
    business_id: str


@dataclass
class TranscriptChunk:
    text: str
    is_final: bool
    speaker: str  # caller | assistant


class SpeechToTextProvider(ABC):
    @abstractmethod
    async def transcribe_stream(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[TranscriptChunk]:
        ...


class TextToSpeechProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """Return audio bytes (e.g. mulaw/wav) for playback to caller."""
        ...


class VoiceProvider(ABC):
    """Handles inbound/outbound calls, media streams, and transfers."""

    @abstractmethod
    async def handle_inbound_webhook(self, payload: dict) -> dict:
        """Process provider webhook (Twilio/Telnyx) and return response TwiML/teXML."""
        ...

    @abstractmethod
    async def transfer_call(self, call_id: str, to_number: str) -> None:
        ...

    @abstractmethod
    async def send_sms(self, from_number: str, to_number: str, body: str) -> str:
        """Returns message SID."""
        ...


# Concrete implementation: app.voice.twilio_provider.TwilioVoiceProvider
