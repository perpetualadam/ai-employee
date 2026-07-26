"""Outbound communication facade — SMS and email via MessagingProvider."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.providers.messaging import MessagingProvider

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class CommunicationService:
    def __init__(
        self,
        messaging_provider: MessagingProvider,
        *,
        db: Session | None = None,
        business_id: str | None = None,
    ) -> None:
        self._messaging = messaging_provider
        self._db = db
        self._business_id = business_id
        self._sms_log = None
        if db is not None:
            from app.services.sms_log_service import SmsLogService

            self._sms_log = SmsLogService(db)

    def send_sms(self, *, from_number: str, to_number: str, text: str) -> dict:
        result = self._messaging.send_sms(
            from_number=from_number,
            to_number=to_number,
            text=text,
        )
        payload = {
            "sent": True,
            "provider": result.provider,
            "id": result.external_id,
            **result.data,
        }
        if self._sms_log and self._business_id:
            self._sms_log.record_outbound(
                business_id=self._business_id,
                provider=result.provider,
                from_number=from_number,
                to_number=to_number,
                body=text,
                sent=True,
                external_id=result.external_id,
            )
        return payload

    def send_email(self, *, to: str, subject: str, body: str) -> dict:
        result = self._messaging.send_email(to=to, subject=subject, body=body)
        return {
            "sent": True,
            "provider": result.provider,
            "id": result.external_id,
            **result.data,
        }

    def send_whatsapp(self, *, from_number: str, to_number: str, text: str) -> dict:
        result = self._messaging.send_whatsapp(
            from_number=from_number,
            to_number=to_number,
            text=text,
        )
        payload = {
            "sent": True,
            "provider": result.provider,
            "id": result.external_id,
            **result.data,
        }
        if self._sms_log and self._business_id:
            self._sms_log.record_outbound(
                business_id=self._business_id,
                provider=result.provider,
                from_number=from_number,
                to_number=to_number,
                body=text,
                sent=True,
                external_id=result.external_id,
            )
        return payload

    def is_configured(self) -> bool:
        return self._messaging.is_configured()
