"""Rate limiting configuration and utilities."""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Create limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/hour"],  # Global default
    storage_uri="memory://",  # Use Redis in production: "redis://localhost:6379"
)


def _rate_limit_exceeded_handler(request, exc):
    """Custom error response for rate limit exceeded."""
    return {
        "error": "rate_limit_exceeded",
        "detail": "Too many requests. Please try again later.",
        "retry_after": exc.retry_after if hasattr(exc, "retry_after") else None,
    }
