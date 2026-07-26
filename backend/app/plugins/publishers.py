"""Publish domain events to the plugin event bus."""

from __future__ import annotations

from typing import Any

from app.plugins.events import Events, PluginEvent, get_event_bus


def _publish(name: str, *, business_id: str | None = None, **payload: Any) -> None:
    get_event_bus().publish(
        PluginEvent(name=name, business_id=business_id, payload=dict(payload)),
    )


def publish_call_started(
    *,
    business_id: str,
    call_log_id: str,
    caller_phone: str,
    provider: str | None = None,
) -> None:
    _publish(
        Events.CALL_STARTED,
        business_id=business_id,
        call_log_id=call_log_id,
        caller_phone=caller_phone,
        provider=provider,
    )


def publish_call_ended(
    *,
    business_id: str,
    call_log_id: str,
    status: str,
    duration_seconds: int | None = None,
) -> None:
    _publish(
        Events.CALL_ENDED,
        business_id=business_id,
        call_log_id=call_log_id,
        status=status,
        duration_seconds=duration_seconds,
    )


def publish_sms_received(
    *,
    business_id: str | None,
    from_number: str,
    to_number: str,
    text: str,
) -> None:
    _publish(
        Events.SMS_RECEIVED,
        business_id=business_id,
        from_number=from_number,
        to_number=to_number,
        text=text,
    )


def publish_sms_sent(
    *,
    business_id: str,
    to_number: str,
    provider: str,
    sent: bool,
    body: str | None = None,
) -> None:
    _publish(
        Events.SMS_SENT,
        business_id=business_id,
        to_number=to_number,
        provider=provider,
        sent=sent,
        body=body,
    )


def publish_booking_created(
    *,
    business_id: str,
    appointment_id: str,
    customer_id: str,
    start_time: str,
) -> None:
    _publish(
        Events.BOOKING_CREATED,
        business_id=business_id,
        appointment_id=appointment_id,
        customer_id=customer_id,
        start_time=start_time,
    )


def publish_booking_updated(
    *,
    business_id: str,
    appointment_id: str,
    status: str | None = None,
) -> None:
    _publish(
        Events.BOOKING_UPDATED,
        business_id=business_id,
        appointment_id=appointment_id,
        status=status,
    )


def publish_payment_received(
    *,
    business_id: str,
    customer_id: str | None = None,
    plan_tier: str | None = None,
) -> None:
    _publish(
        Events.PAYMENT_RECEIVED,
        business_id=business_id,
        customer_id=customer_id,
        plan_tier=plan_tier,
    )
