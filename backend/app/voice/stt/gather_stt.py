"""Speech-to-text via TeXML Gather — wraps SpeechResult webhook field."""

from app.voice.provider import TranscriptChunk


class GatherSpeechSTT:
    """Telnyx TeXML converts caller speech via <Gather input='speech'>."""

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
