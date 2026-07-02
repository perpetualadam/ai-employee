"""Conversation list/detail queries and lead-card enrichment."""

from sqlalchemy.orm import Session

from app.domain.call import call_has_booking
from app.domain.conversation import channel_label, infer_channel
from app.models import AIActivityLog, Appointment, CallLog, Customer
from app.models.enums import AppointmentStatus, ConversationChannel
from app.schemas import (
    AIActivityDetailResponse,
    ConversationDetailResponse,
    ConversationLeadCard,
    ConversationListItem,
    ConversationMessage,
)


class ConversationService:
    @staticmethod
    def list_conversations(
        db: Session,
        business_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ConversationListItem]:
        rows = (
            db.query(CallLog)
            .filter(CallLog.business_id == business_id)
            .order_by(CallLog.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [ConversationService._to_list_item(db, row) for row in rows]

    @staticmethod
    def get_conversation(
        db: Session,
        business_id: str,
        conversation_id: str,
    ) -> ConversationDetailResponse | None:
        call = (
            db.query(CallLog)
            .filter(CallLog.id == conversation_id, CallLog.business_id == business_id)
            .first()
        )
        if call is None:
            return None

        activities = (
            db.query(AIActivityLog)
            .filter(
                AIActivityLog.business_id == business_id,
                AIActivityLog.call_log_id == call.id,
            )
            .order_by(AIActivityLog.created_at.asc())
            .all()
        )

        return ConversationDetailResponse(
            id=call.id,
            business_id=call.business_id,
            customer_id=call.customer_id,
            channel=infer_channel(call),
            channel_label=channel_label(infer_channel(call)),
            status=call.status,
            caller_phone=call.caller_phone,
            duration_seconds=call.duration_seconds,
            summary=call.summary,
            ai_summary=call.ai_summary,
            escalated=call.escalated,
            created_at=call.created_at,
            transcript=call.transcript,
            messages=ConversationService._history_to_messages(call),
            activities=[AIActivityDetailResponse.model_validate(a) for a in activities],
            lead_card=ConversationService._build_lead_card(db, call),
        )

    @staticmethod
    def _to_list_item(db: Session, call: CallLog) -> ConversationListItem:
        channel = infer_channel(call)
        return ConversationListItem(
            id=call.id,
            channel=channel,
            channel_label=channel_label(channel),
            status=call.status,
            caller_phone=call.caller_phone,
            summary=call.summary,
            ai_summary=call.ai_summary,
            escalated=call.escalated,
            is_booked=call_has_booking(call.summary),
            created_at=call.created_at,
            lead_card=ConversationService._build_lead_card(db, call),
        )

    @staticmethod
    def _history_to_messages(call: CallLog) -> list[ConversationMessage]:
        messages: list[ConversationMessage] = []
        for entry in call.conversation_history or []:
            role = entry.get("role")
            content = entry.get("content")
            if role not in ("user", "assistant") or not content:
                continue
            messages.append(
                ConversationMessage(
                    role=role,
                    content=content,
                    channel=entry.get("channel"),
                )
            )
        return messages

    @staticmethod
    def _build_lead_card(db: Session, call: CallLog) -> ConversationLeadCard:
        customer: Customer | None = None
        if call.customer_id:
            customer = (
                db.query(Customer)
                .filter(Customer.id == call.customer_id, Customer.business_id == call.business_id)
                .first()
            )

        appointment: Appointment | None = None
        if customer:
            appointment = (
                db.query(Appointment)
                .filter(
                    Appointment.business_id == call.business_id,
                    Appointment.customer_id == customer.id,
                    Appointment.status != AppointmentStatus.CANCELLED,
                )
                .order_by(Appointment.start_time.desc())
                .first()
            )

        service_type = appointment.service_type if appointment else None
        if not service_type:
            service_type = ConversationService._infer_service_from_history(call)

        emergency = call.escalated or ConversationService._looks_emergency(call)

        return ConversationLeadCard(
            customer_name=customer.name if customer else ConversationService._name_from_activity(db, call),
            customer_phone=customer.phone if customer else call.caller_phone,
            service_address=customer.address if customer else None,
            service_type=service_type,
            appointment_time=appointment.start_time if appointment else None,
            is_booked=call_has_booking(call.summary) or appointment is not None,
            is_escalated=call.escalated,
            is_emergency=emergency,
        )

    @staticmethod
    def _infer_service_from_history(call: CallLog) -> str | None:
        for entry in reversed(call.conversation_history or []):
            if entry.get("role") != "user":
                continue
            text = (entry.get("content") or "").lower()
            if any(k in text for k in ("leak", "hot water", "boiler", "drain", "pipe", "hvac", "heat")):
                return entry.get("content", "")[:120]
        return None

    @staticmethod
    def _name_from_activity(db: Session, call: CallLog) -> str | None:
        activity = (
            db.query(AIActivityLog)
            .filter(
                AIActivityLog.call_log_id == call.id,
                AIActivityLog.tool_name == "create_customer",
            )
            .order_by(AIActivityLog.created_at.desc())
            .first()
        )
        if activity and activity.input_data:
            name = activity.input_data.get("name")
            if name:
                return str(name)
        return None

    @staticmethod
    def _looks_emergency(call: CallLog) -> bool:
        blob = " ".join(
            entry.get("content", "")
            for entry in (call.conversation_history or [])
            if entry.get("role") == "user"
        ).lower()
        return any(k in blob for k in ("emergency", "flooding", "gas smell", "burst", "urgent"))
