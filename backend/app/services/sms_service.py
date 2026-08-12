"""Inbound SMS — recovery/continuation channel for active voice sessions."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.ai.receptionist_agent import ReceptionistAgent, get_ai_provider
from app.config import get_settings
from app.domain.intake import is_valid_service_address
from app.domain.phone import normalize_phone
from app.domain.recording import is_retention_enabled
from app.models import Business, CallLog
from app.models.enums import CallStatus
from app.services.address_confirmation_service import AddressConfirmationService
from app.services.notification_service import NotificationService
from app.services.subscription_service import SubscriptionService
from app.voice.call_service import find_business_by_phone

logger = logging.getLogger(__name__)

SESSION_WINDOW = timedelta(hours=4)


class SmsService:
    @staticmethod
    async def handle_inbound(
        db: Session,
        from_number: str,
        to_number: str,
        body: str,
        *,
        provider: str = "unknown",
        external_id: str | None = None,
        raw_payload: dict | None = None,
    ) -> None:
        business = find_business_by_phone(db, to_number)
        from app.plugins.publishers import publish_sms_received

        publish_sms_received(
            business_id=business.id if business else None,
            from_number=from_number,
            to_number=to_number,
            text=body,
        )
        if business is None:
            logger.warning("Inbound SMS with no matching business", extra={"to": to_number})
            return

        text = (body or "").strip()
        caller = normalize_phone(from_number, business.country) if text else None
        call_log = (
            SmsService._find_active_session(db, business.id, caller)
            if caller
            else None
        )
        if text and is_retention_enabled(getattr(business, "recording_enabled", False)):
            SmsService._audit_inbound(
                db,
                business=business,
                from_number=from_number,
                to_number=to_number,
                body=text,
                call_log_id=call_log.id if call_log else None,
                provider=provider,
                external_id=external_id,
                raw_payload=raw_payload,
            )

        denial = SubscriptionService.get_access_denial_reason(business)
        if denial:
            NotificationService(db, business).send_sms(
                from_number,
                f"Sorry, {business.name} is unavailable right now. Please call back later.",
            )
            return

        if not text or caller is None:
            return

        if call_log is None:
            confirmed = SmsService._try_confirm_address_via_text(db, business, caller, text)
            if confirmed:
                NotificationService(db, business).send_sms(
                    caller,
                    f"Thanks! We saved your address. {business.name} will follow up shortly.",
                )
                return
            NotificationService(db, business).send_sms(
                caller,
                (
                    f"Thanks for contacting {business.name}. "
                    "Please call us to schedule service, or use the address link we texted you."
                ),
            )
            return

        history = list(call_log.conversation_history or [])
        settings = get_settings()
        if not settings.groq_api_key:
            NotificationService(db, business).send_sms(
                caller,
                "Sorry, our system is temporarily unavailable. Please call us instead.",
            )
            return

        try:
            agent = ReceptionistAgent(db, business, get_ai_provider(), call_log_id=call_log.id)
            result = await agent.chat(text, history, voice_mode=False)
            reply = result["reply"]
        except Exception:
            logger.exception("SMS recovery agent failed", extra={"call_log_id": call_log.id})
            NotificationService(db, business).send_sms(
                caller,
                "Sorry, we hit a snag. Please call us to finish scheduling.",
            )
            return

        # Tag SMS turns in history for unified timeline display
        db.refresh(call_log)
        updated = list(call_log.conversation_history or [])
        for entry in reversed(updated):
            if entry.get("role") == "user" and entry.get("content") == text:
                entry["channel"] = "sms"
                break
        for entry in reversed(updated):
            if entry.get("role") == "assistant" and entry.get("content") == reply:
                entry["channel"] = "sms"
                break
        call_log.conversation_history = updated
        db.commit()

        sms_result = NotificationService(db, business).send_sms(caller, reply)
        if not sms_result.get("sent"):
            logger.warning(
                "SMS reply failed but conversation was saved",
                extra={"call_log_id": call_log.id, "error": sms_result.get("error")},
            )

    @staticmethod
    def _audit_inbound(
        db: Session,
        *,
        business: Business,
        from_number: str,
        to_number: str,
        body: str,
        call_log_id: str | None,
        provider: str,
        external_id: str | None,
        raw_payload: dict | None,
    ) -> None:
        from app.services.sms_log_service import SmsLogService

        try:
            SmsLogService(db).record_inbound(
                business_id=business.id,
                provider=provider or "unknown",
                from_number=from_number,
                to_number=to_number,
                body=body,
                external_id=external_id,
                call_log_id=call_log_id,
                raw_payload=raw_payload,
            )
        except Exception:
            logger.exception(
                "Failed to persist inbound SMS audit log",
                extra={"business_id": business.id, "from": from_number},
            )

    @staticmethod
    def _find_active_session(db: Session, business_id: str, caller_phone: str) -> CallLog | None:
        cutoff = datetime.now(UTC) - SESSION_WINDOW
        return (
            db.query(CallLog)
            .filter(
                CallLog.business_id == business_id,
                CallLog.caller_phone == caller_phone,
                CallLog.status == CallStatus.IN_PROGRESS,
                CallLog.created_at >= cutoff,
            )
            .order_by(CallLog.created_at.desc())
            .first()
        )

    @staticmethod
    def _try_confirm_address_via_text(
        db: Session,
        business: Business,
        caller_phone: str,
        text: str,
    ) -> bool:
        if not is_valid_service_address(text):
            return False

        from app.models import AddressConfirmationToken

        token = (
            db.query(AddressConfirmationToken)
            .filter(
                AddressConfirmationToken.business_id == business.id,
                AddressConfirmationToken.confirmed_at.is_(None),
                AddressConfirmationToken.expires_at >= datetime.now(UTC),
            )
            .join(CallLog, CallLog.id == AddressConfirmationToken.call_log_id)
            .filter(CallLog.caller_phone == caller_phone)
            .order_by(AddressConfirmationToken.created_at.desc())
            .first()
        )
        if token is None:
            return False

        ok, _ = AddressConfirmationService.confirm_address(db, token.token, text)
        return ok
