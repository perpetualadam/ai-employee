"""Rate limit backend selection — no slowapi import so unit tests stay lightweight."""


def rate_limit_storage_uri(redis_url: str = "") -> str:
    """Use Redis when REDIS_URL is configured; otherwise in-memory."""
    cleaned = redis_url.strip()
    return cleaned if cleaned else "memory://"
