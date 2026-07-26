"""Internal plugin event bus — publish/subscribe, plugins never call each other directly."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable

logger = logging.getLogger(__name__)

EventHandler = Callable[["PluginEvent"], None]


@dataclass(frozen=True)
class PluginEvent:
    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    business_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


# Canonical domain events
class Events:
    CALL_STARTED = "CallStarted"
    CALL_ENDED = "CallEnded"
    SMS_RECEIVED = "SMSReceived"
    SMS_SENT = "SMSSent"
    BOOKING_CREATED = "BookingCreated"
    BOOKING_UPDATED = "BookingUpdated"
    INVOICE_CREATED = "InvoiceCreated"
    CUSTOMER_CREATED = "CustomerCreated"
    CUSTOMER_UPDATED = "CustomerUpdated"
    PAYMENT_RECEIVED = "PaymentReceived"
    WEBHOOK_RECEIVED = "WebhookReceived"


class PluginEventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[tuple[str, EventHandler]]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: EventHandler, *, subscriber_id: str) -> None:
        self._subscribers[event_name].append((subscriber_id, handler))

    def unsubscribe(self, event_name: str, subscriber_id: str) -> None:
        self._subscribers[event_name] = [
            (sid, handler) for sid, handler in self._subscribers[event_name] if sid != subscriber_id
        ]

    def publish(self, event: PluginEvent) -> None:
        handlers = list(self._subscribers.get(event.name, []))
        handlers.extend(self._subscribers.get("*", []))
        for subscriber_id, handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception(
                    "Plugin event handler failed",
                    extra={"event": event.name, "subscriber": subscriber_id},
                )


_bus = PluginEventBus()


def get_event_bus() -> PluginEventBus:
    return _bus
