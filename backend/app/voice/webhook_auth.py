"""Twilio webhook signature validation."""

import logging

from fastapi import HTTPException, Request, status
from twilio.request_validator import RequestValidator

from app.config import get_settings

logger = logging.getLogger(__name__)


async def validate_twilio_signature(request: Request) -> dict[str, str]:
    """
    Validate X-Twilio-Signature on incoming webhooks.
    Returns form parameters as a flat dict.
    """
    settings = get_settings()

    if not settings.twilio_auth_token:
        if settings.debug:
            form = await request.form()
            return {k: str(v) for k, v in form.items()}
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Twilio is not configured",
        )

    form = await request.form()
    params = {k: str(v) for k, v in form.items()}

    signature = request.headers.get("X-Twilio-Signature", "")
    # Use public URL for validation when behind proxy/ngrok
    url = f"{settings.public_api_url.rstrip('/')}{request.url.path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"

    validator = RequestValidator(settings.twilio_auth_token)
    if not validator.validate(url, params, signature):
        logger.warning("Invalid Twilio signature", extra={"url": url})
        if not settings.debug:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Twilio signature")

    return params
