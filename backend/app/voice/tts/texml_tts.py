"""TeXML TTS via <Say> — formats text for spoken delivery."""

from app.domain.telecom import resolve_voice_locale


class TeXMLSayTTS:
    """Telnyx renders speech server-side via TeXML <Say>."""

    @staticmethod
    def prepare_for_speech(text: str, max_length: int = 1200) -> str:
        cleaned = text.replace("*", "").replace("#", "").replace("`", "")
        cleaned = " ".join(cleaned.split())
        if len(cleaned) > max_length:
            cleaned = cleaned[: max_length - 3] + "..."
        return cleaned

    @staticmethod
    def voice_settings(country: str | None = None) -> dict[str, str]:
        locale = resolve_voice_locale(country)
        return {"voice": locale.voice, "language": locale.language}
