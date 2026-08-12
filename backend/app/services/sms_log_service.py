"""Record inbound and outbound SMS with provider attribution."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import SmsLog
from app.repositories.sms_log_repository import SmsLogRepository


class SmsLogService:
    def __init__(self, db: Session) -> None:
        self._repo = SmsLogRepository(db)

    def record_outbound(
        self,
        *,
        business_id: str,
        provider: str,
        from_number: str | None,
        to_number: str,
        body: str,
        sent: bool,
        external_id: str | None = None,
        error: str | None = None,
        call_log_id: str | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> SmsLog:
        return self._repo.record_outbound(
            business_id=business_id,
            provider=provider,
            from_number=from_number,
            to_number=to_number,
            body=body,
            sent=sent,
            external_id=external_id,
            error=error,
            call_log_id=call_log_id,
            raw_payload=raw_payload,
        )

    def record_inbound(
        self,
        *,
        business_id: str,
        provider: str,
        from_number: str | None,
        to_number: str,
        body: str,
        external_id: str | None = None,
        call_log_id: str | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> SmsLog:
        return self._repo.record_inbound(
            business_id=business_id,
            provider=provider,
            from_number=from_number,
            to_number=to_number,
            body=body,
            external_id=external_id,
            call_log_id=call_log_id,
            raw_payload=raw_payload,
        )
