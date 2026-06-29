"""Twilio STT via Gather speech recognition — implements SpeechToTextProvider interface."""

from app.voice.provider import TranscriptChunk


class TwilioGatherSTT:
    """
    Twilio converts caller speech to text via <Gather input='speech'>.
    This adapter wraps the SpeechResult webhook field for the STT interface.
    """

    @staticmethod
    def from_speech_result(speech_result: str, confidence: float | None = None) -> TranscriptChunk:
        return TranscriptChunk(
            text=speech_result.strip(),
            is_final=True,
            speaker="caller",
        )

    @staticmethod
    def is_empty(speech_result: str | None) -> bool:
        return not speech_result or not speech_result.strip()
