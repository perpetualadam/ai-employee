"""Shared Twilio REST client factory."""

from functools import lru_cache

from twilio.rest import Client

from app.config import get_settings


@lru_cache
def get_twilio_client() -> Client | None:
    settings = get_settings()
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        return None
    return Client(settings.twilio_account_sid, settings.twilio_auth_token)


def is_twilio_configured() -> bool:
    return get_twilio_client() is not None
