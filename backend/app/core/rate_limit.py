"""Rate limiting configuration and utilities."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings
from app.core.rate_limit_storage import rate_limit_storage_uri

_settings = get_settings()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/hour"],
    storage_uri=rate_limit_storage_uri(_settings.redis_url),
)


def _rate_limit_exceeded_handler(request, exc):
    """Custom error response for rate limit exceeded."""
    return {
        "error": "rate_limit_exceeded",
        "detail": "Too many requests. Please try again later.",
        "retry_after": exc.retry_after if hasattr(exc, "retry_after") else None,
    }
