"""Retry helper for provider calls with transient failures."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

from app.providers.exceptions import ProviderError, ProviderRateLimitError, ProviderTimeoutError

logger = logging.getLogger(__name__)

T = TypeVar("T")

RETRYABLE = (ProviderTimeoutError, ProviderRateLimitError)


def with_retry(
    fn: Callable[[], T],
    *,
    max_attempts: int = 3,
    base_delay_seconds: float = 0.5,
) -> T:
    last_error: ProviderError | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except RETRYABLE as exc:
            last_error = exc
            if attempt >= max_attempts:
                raise
            delay = base_delay_seconds * (2 ** (attempt - 1))
            logger.warning(
                "Retrying provider call",
                extra={"attempt": attempt, "delay": delay, "error": str(exc)},
            )
            time.sleep(delay)
    if last_error:
        raise last_error
    raise RuntimeError("with_retry exhausted without result")
