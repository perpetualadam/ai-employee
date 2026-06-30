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
            confidence=confidence,
        )

    @staticmethod
    def is_empty(speech_result: str | None) -> bool:
        return not speech_result or not speech_result.strip()

    @staticmethod
    def extract_from_params(params: dict[str, str]) -> tuple[str | None, str | None]:
        """Read speech or keypad input from Telnyx gather callback parameters."""
        for key in ("SpeechResult", "UnstableSpeechResult", "speech_result"):
            value = (params.get(key) or "").strip()
            if value:
                confidence = params.get("Confidence") or params.get("confidence")
                return value, confidence

        digits = (params.get("Digits") or "").strip()
        if digits:
            return f"The caller entered {digits} on the phone keypad.", None

        return None, None
