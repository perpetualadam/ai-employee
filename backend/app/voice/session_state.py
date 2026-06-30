"""Voice-call session state — intake guards and slot booking rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from app.ai.conversation_state import ConversationState
from app.ai.tools import ToolResult
from app.voice.slots import format_slots_for_voice, resolve_offered_slot, voice_availability_message


@dataclass
class VoiceSessionState(ConversationState):
    """Extends shared state with phone-call-specific booking rules."""

    intake_saved_this_call: bool = False
    offered_slots: list[dict] = field(default_factory=list)
    availability_checked_this_turn: bool = False
    prior_availability_check: bool = False
    sms_sent_this_call: bool = False

    @classmethod
    def load(
        cls,
        db: Session,
        business_id: str,
        call_log_id: str | None,
    ) -> VoiceSessionState:
        base = ConversationState.load_from_call(db, business_id, call_log_id)
        state = cls(
            verified_customer_id=base.verified_customer_id,
            name_collected=base.name_collected,
            address_collected=base.address_collected,
            availability_checked=base.availability_checked,
            booking_complete=base.booking_complete,
            caller_phone=base.caller_phone,
        )
        if not call_log_id:
            return state

        from app.models import AIActivityLog

        logs = (
            db.query(AIActivityLog)
            .filter(AIActivityLog.call_log_id == call_log_id)
            .order_by(AIActivityLog.created_at)
            .all()
        )
        for log in logs:
            state.apply_voice_activity_log(log)
        return state

    def apply_activity_log(self, log) -> None:
        super().apply_activity_log(log)
        self.apply_voice_activity_log(log)

    def apply_voice_activity_log(self, log) -> None:
        output = log.output_data or {}
        if not output.get("success"):
            return
        if log.tool_name == "create_customer":
            self.intake_saved_this_call = True
        elif log.tool_name == "check_availability":
            self.prior_availability_check = True
            data = output.get("data") or {}
            slots = data.get("slots") or data.get("next_slots") or []
            if slots:
                self.offered_slots = slots
        elif log.tool_name == "send_sms" and output.get("success"):
            self.sms_sent_this_call = True

    def require_intake(self, action: str) -> ToolResult | None:
        if not self.intake_saved_this_call:
            return ToolResult(
                success=False,
                data={},
                message=(
                    f"Cannot {action} yet. Ask for the customer's full name "
                    "and service address, then call create_customer with those details."
                ),
            )
        return self.require_customer_intake(action)

    def block_same_turn_booking(self) -> ToolResult | None:
        if self.availability_checked_this_turn and not self.prior_availability_check:
            return ToolResult(
                success=False,
                data={},
                message=(
                    "Tell the caller the available times and wait for them to pick one. "
                    "Do not book in the same turn you first checked availability."
                ),
            )
        return None

    def validate_and_resolve_slot(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> tuple[datetime, datetime] | ToolResult:
        resolved = resolve_offered_slot(start_time, end_time, self.offered_slots)
        if resolved is not None:
            return resolved
        if self.offered_slots:
            offered = ", ".join(s.get("spoken_time", "?") for s in self.offered_slots[:5])
            return ToolResult(
                success=False,
                data={"offered_slots": self.offered_slots[:5]},
                message=(
                    "start_time and end_time must exactly match one offered slot. "
                    f"Offered times were: {offered}. "
                    "Copy start_time_utc and end_time_utc from that slot — do not round or guess."
                ),
            )
        return start_time, end_time

    def record_availability(self, formatted_slots: list[dict], *, voice: bool = True) -> str:
        self.offered_slots = formatted_slots
        self.availability_checked = True
        self.availability_checked_this_turn = True
        if voice:
            return voice_availability_message(formatted_slots)
        return ""

    def mark_intake_saved(
        self,
        customer_id: str,
        address: str | None,
        name: str | None,
    ) -> None:
        self.intake_saved_this_call = True
        self.note_customer(customer_id, address, name)

    @staticmethod
    def format_slots(raw_slots: list[dict], tz) -> list[dict]:
        return format_slots_for_voice(raw_slots, tz)
