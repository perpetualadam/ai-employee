"""Web continuation tokens — voice call handoff to public chat."""

import logging
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Business, CallLog, WebContinuationToken

logger = logging.getLogger(__name__)

TOKEN_TTL_HOURS = 24


class WebContinuationService:
    @staticmethod
    def create_for_call(
        db: Session,
        business: Business,
        call_log: CallLog,
        *,
        reuse_existing: bool = True,
    ) -> dict:
        existing = None
        if reuse_existing:
            existing = (
                db.query(WebContinuationToken)
                .filter(
                    WebContinuationToken.call_log_id == call_log.id,
                    WebContinuationToken.expires_at > datetime.now(UTC),
                )
                .order_by(WebContinuationToken.created_at.desc())
                .first()
            )

        if existing:
            token_value = existing.token
            link_created = False
        else:
            token_value = secrets.token_urlsafe(24)
            record = WebContinuationToken(
                id=str(uuid4()),
                business_id=business.id,
                call_log_id=call_log.id,
                token=token_value,
                expires_at=datetime.now(UTC) + timedelta(hours=TOKEN_TTL_HOURS),
            )
            db.add(record)
            db.commit()
            link_created = True

        settings = get_settings()
        chat_url = f"{settings.frontend_url.rstrip('/')}/continue/{token_value}"
        slug_url = None
        if business.public_slug:
            slug_url = f"{settings.frontend_url.rstrip('/')}/chat/{business.public_slug}"

        logger.info(
            "Web continuation link created",
            extra={
                "call_log_id": call_log.id,
                "business_id": business.id,
                "link_created": link_created,
            },
        )
        return {
            "continue_url": chat_url,
            "standalone_chat_url": slug_url,
            "token": token_value,
            "expires_hours": TOKEN_TTL_HOURS,
            "link_created": link_created,
        }

    @staticmethod
    def resolve_token(db: Session, token_value: str) -> WebContinuationToken | None:
        record = (
            db.query(WebContinuationToken)
            .filter(WebContinuationToken.token == token_value)
            .first()
        )
        if record is None:
            return None
        if record.expires_at < datetime.now(UTC):
            return None
        return record
