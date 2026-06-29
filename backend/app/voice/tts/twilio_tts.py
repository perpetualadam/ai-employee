"""Twilio TTS via <Say> — implements TextToSpeechProvider for TwiML responses."""

from app.voice.twiml_builder import VOICE, LANGUAGE


class TwilioSayTTS:
    """
    Twilio Polly TTS is rendered server-side via TwiML <Say>.
    This class formats text for voice-friendly output.
    """

    @staticmethod
    def prepare_for_speech(text: str, max_length: int = 1200) -> str:
        """Trim and clean AI response for spoken delivery."""
        cleaned = text.replace("*", "").replace("#", "").replace("`", "")
        cleaned = " ".join(cleaned.split())
        if len(cleaned) > max_length:
            cleaned = cleaned[: max_length - 3] + "..."
        return cleaned

    @staticmethod
    def voice_settings() -> dict[str, str]:
        return {"voice": VOICE, "language": LANGUAGE}
