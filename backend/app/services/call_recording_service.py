"""Persist provider call recordings for owner review in the inbox."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy.orm import Session

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
        storage: StorageProvider | None = None,
    ) -> CallLog | None:
        """
        Handle provider recordingStatusCallback (completed).
        Downloads the temporary provider URL into durable storage.
        """
        if not is_valid_uuid(call_log_id):
            return None

        call = db.query(CallLog).filter(CallLog.id == call_log_id).first()
        if call is None:
            logger.warning("Recording status for unknown call", extra={"call_log_id": call_log_id})
            return None

        status = (params.get("RecordingStatus") or params.get("recording_status") or "").lower()
        recording_url = (
            params.get("RecordingUrl")
            or params.get("recording_url")
            or params.get("RecordingUrl0")
            or ""
        ).strip()
        recording_sid = (
            params.get("RecordingSid")
            or params.get("recording_sid")
            or params.get("RecordingId")
            or ""
        ).strip() or None
        duration_raw = params.get("RecordingDuration") or params.get("recording_duration")
        try:
            duration = int(float(duration_raw)) if duration_raw not in (None, "") else None
        except (TypeError, ValueError):
            duration = None

        if recording_sid:
            call.external_recording_id = recording_sid
        if duration is not None:
            call.recording_duration_seconds = duration
        if recording_url:
            call.provider_recording_url = recording_url

        if status and status not in ("completed", "available"):
            call.recording_status = status or call.recording_status
            db.commit()
            return call

        if not recording_url:
            call.recording_status = status or "absent"
            db.commit()
            return call

        storage = storage or get_storage_provider()
        try:
            audio_bytes, content_type = CallRecordingService._download_recording(recording_url)
            ext = "wav" if "wav" in content_type else "mp3"
            key = f"recordings/{call.business_id}/{call.id}/{recording_sid or 'audio'}.{ext}"
            stored = storage.upload(key=key, data=audio_bytes, content_type=content_type)
            call.recording_storage_key = stored.key
            call.recording_content_type = content_type
            call.recording_status = "stored"
            db.commit()
            logger.info(
                "Call recording stored",
                extra={"call_log_id": call.id, "storage_key": stored.key, "bytes": len(audio_bytes)},
            )
        except Exception:
            logger.exception("Failed to store call recording", extra={"call_log_id": call.id})
            call.recording_status = "failed"
            db.commit()
        return call

    @staticmethod
    def _download_recording(url: str) -> tuple[bytes, str]:
        # Provider URLs are short-lived; fetch immediately.
        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "audio/mpeg").split(";")[0].strip()
            if not content_type.startswith("audio/"):
                content_type = "audio/mpeg"
            return response.content, content_type

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
