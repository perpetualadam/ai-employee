"""Plugin-layer exceptions — core never imports vendor SDK error types."""


class PaymentWebhookVerificationError(Exception):
    """Raised when a payment provider webhook signature is invalid."""
