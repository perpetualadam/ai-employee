"""Persistence for SMS audit records."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import SmsLog
from app.models.enums import CallDirection


class SmsLogRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

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
        record = SmsLog(
            business_id=business_id,
            provider=provider,
            direction=CallDirection.OUTBOUND,
            from_number=from_number,
            to_number=to_number,
            body=body,
            external_id=external_id,
            sent=sent,
            error=error,
            call_log_id=call_log_id,
            raw_payload=raw_payload,
        )
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        return record

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
        record = SmsLog(
            business_id=business_id,
            provider=provider,
            direction=CallDirection.INBOUND,
            from_number=from_number,
            to_number=to_number,
            body=body,
            external_id=external_id,
            sent=True,
            call_log_id=call_log_id,
            raw_payload=raw_payload,
        )
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        return record
