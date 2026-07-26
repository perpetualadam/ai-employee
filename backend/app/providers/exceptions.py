"""Provider-layer exceptions — mapped to HTTP responses in API boundaries."""

from __future__ import annotations


class ProviderError(Exception):
    """Base error for external provider failures."""

    def __init__(self, message: str, *, provider: str | None = None, retryable: bool = False) -> None:
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable


class CapabilityNotSupportedError(ProviderError):
    def __init__(
        self,
        message: str = "Required capability is not supported",
        *,
        service: str | None = None,
        required: list[str] | None = None,
        country: str | None = None,
        provider: str | None = None,
        **kwargs,
    ) -> None:
        detail = message
        if service and required:
            detail = (
                f"No provider for service '{service}' supports "
                f"{', '.join(required)}"
                + (f" in {country}" if country else "")
            )
        super().__init__(detail, provider=provider, retryable=False, **kwargs)
        self.service = service
        self.required = required or []
        self.country = country


class ProviderUnavailableError(ProviderError):
    def __init__(self, message: str = "Provider is unavailable", **kwargs) -> None:
        super().__init__(message, retryable=True, **kwargs)


class ProviderTimeoutError(ProviderError):
    def __init__(self, message: str = "Provider request timed out", **kwargs) -> None:
        super().__init__(message, retryable=True, **kwargs)


class ProviderRateLimitError(ProviderError):
    def __init__(self, message: str = "Provider rate limit exceeded", **kwargs) -> None:
        super().__init__(message, retryable=True, **kwargs)


class DuplicateProvisioningError(ProviderError):
    def __init__(self, message: str = "Number already provisioned", **kwargs) -> None:
        super().__init__(message, retryable=False, **kwargs)


class VerificationRejectedError(ProviderError):
    def __init__(self, message: str = "Verification was rejected", **kwargs) -> None:
        super().__init__(message, retryable=False, **kwargs)


class MissingDocumentsError(ProviderError):
    def __init__(self, message: str = "Required documents are missing", **kwargs) -> None:
        super().__init__(message, retryable=False, **kwargs)
