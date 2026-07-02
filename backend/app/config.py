"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_name: str = "AI Employee API"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = "postgresql://aiemployee:aiemployee@localhost:5432/aiemployee"

    # Auth
    secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    algorithm: str = "HS256"

    # CORS (comma-separated origins)
    cors_origins: str = "http://localhost:3000"

    # Future integrations (Phase 3+)
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    ai_provider: str = "groq"  # groq — add openai/anthropic adapters in integrations/registry
    telnyx_api_key: str = ""
    telnyx_public_key: str = ""
    telnyx_account_sid: str = ""
    telnyx_phone_number: str = ""
    telnyx_messaging_profile_id: str = ""
    telnyx_texml_connection_id: str = ""
    sms_provider: str = "telnyx"  # telnyx | dev | auto (country-based pick)
    voice_provider: str = "telnyx"  # telnyx | auto — swap voice CPaaS via integrations/adapters
    email_provider: str = "auto"  # auto | smtp | dev
    public_api_url: str = "http://localhost:8000"
    deepgram_api_key: str = ""
    voice_mode: str = "gather"  # gather | stream
    voice_gather_speech_timeout: int = 3  # seconds of silence after speech before Telnyx submits
    voice_gather_timeout: int = 20  # max seconds to wait for caller to start speaking
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_starter: str = ""
    stripe_price_pro: str = ""
    frontend_url: str = "http://localhost:3000"

    # P4 — reminders, monitoring, internal jobs
    reminders_enabled: bool = True
    reminder_hours_before: int = 24
    cron_secret: str = ""
    sentry_dsn: str = ""
    sentry_environment: str = "development"
    sentry_traces_sample_rate: float = 0.1

    # Email (SMTP) — optional; logs only when unset
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_use_tls: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
