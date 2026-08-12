"""Persist provider call recordings for owner review in the inbox."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.integrations.registry import get_call_recording_adapter
from app.models import CallLog
from app.providers.factory import get_storage_provider
from app.providers.storage import StorageProvider
from app.services.tenant import is_valid_uuid

logger = logging.getLogger(__name__)

_PLAYBACK_TTL = timedelta(hours=1)


class CallRecordingService:
    @staticmethod
    def mark_recording_started(db: Session, call_log: CallLog) -> None:
        if call_log.recording_status in ("completed", "stored"):
            return
        call_log.recording_status = "started"
        db.commit()

    @staticmethod
    def handle_recording_status(
        db: Session,
        *,
        call_log_id: str,
        params: dict[str, str],
        provider: str | None = None,
        storage: StorageProvider | None = None,
    ) -> CallLog | None:
        """
        Handle provider recording-ready webhook.
        Normalizes via CallRecordingAdapter, then stores audio durably.
        """
        if not is_valid_uuid(call_log_id):
            return None

        call = db.query(CallLog).filter(CallLog.id == call_log_id).first()
        if call is None:
            logger.warning("Recording status for unknown call", extra={"call_log_id": call_log_id})
            return None

        adapter = get_call_recording_adapter(provider or call.provider)
        event = adapter.normalize_webhook(params)
        status = (event.status or "").lower()

        if event.recording_id:
            call.external_recording_id = event.recording_id
        if event.duration_seconds is not None:
            call.recording_duration_seconds = event.duration_seconds
        if event.recording_url:
            call.provider_recording_url = event.recording_url

        if status and status not in ("completed", "available", "ok"):
            call.recording_status = status or call.recording_status
            db.commit()
            return call

        if not event.recording_url:
            call.recording_status = status or "absent"
            db.commit()
            return call

        storage = storage or get_storage_provider()
        try:
            audio_bytes, content_type = adapter.download_recording(event.recording_url)
            ext = "wav" if "wav" in content_type else "mp3"
            key = (
                f"recordings/{call.business_id}/{call.id}/"
                f"{event.recording_id or 'audio'}.{ext}"
            )
            stored = storage.upload(key=key, data=audio_bytes, content_type=content_type)
            call.recording_storage_key = stored.key
            call.recording_content_type = content_type
            call.recording_status = "stored"
            db.commit()
            logger.info(
                "Call recording stored",
                extra={
                    "call_log_id": call.id,
                    "provider": adapter.provider_name,
                    "storage_key": stored.key,
                    "bytes": len(audio_bytes),
                },
            )
        except Exception:
            logger.exception(
                "Failed to store call recording",
                extra={"call_log_id": call.id, "provider": adapter.provider_name},
            )
            call.recording_status = "failed"
            db.commit()
        return call

    @staticmethod
    def get_playback_bytes(
        db: Session,
        *,
        business_id: str,
        call_log_id: str,
        storage: StorageProvider | None = None,
    ) -> tuple[bytes, str] | None:
        if not is_valid_uuid(call_log_id):
            return None
        call = (
            db.query(CallLog)
            .filter(CallLog.id == call_log_id, CallLog.business_id == business_id)
            .first()
        )
        if call is None or not call.recording_storage_key:
            return None
        storage = storage or get_storage_provider()
        data = storage.download(call.recording_storage_key)
        content_type = call.recording_content_type or "audio/mpeg"
        return data, content_type

    @staticmethod
    def recording_available(call: CallLog) -> bool:
        return bool(call.recording_storage_key) and call.recording_status == "stored"

    @staticmethod
    def playback_expires_at() -> datetime:
        return datetime.now(UTC) + _PLAYBACK_TTL
