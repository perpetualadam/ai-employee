"""Shared conversation state for receptionist tool calls (voice and text)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.ai.tools import ToolResult
from app.domain.call import call_has_booking
from app.domain.intake import is_valid_customer_name, is_valid_service_address
from app.domain.phone import normalize_phone


@dataclass
class ConversationState:
    """Customer and booking progress for a single call or chat session."""

    verified_customer_id: str | None = None
    name_collected: bool = False
    address_collected: bool = False
    availability_checked: bool = False
    booking_complete: bool = False
    caller_phone: str | None = None

    def note_customer(
        self,
        customer_id: str,
        address: str | None,
        name: str | None = None,
    ) -> None:
        self.verified_customer_id = customer_id
        if is_valid_service_address(address):
            self.address_collected = True
        if is_valid_customer_name(name):
            self.name_collected = True

    def require_customer_intake(self, action: str) -> ToolResult | None:
        if self.verified_customer_id is None:
            return ToolResult(
                success=False,
                data={},
                message=f"Cannot {action} yet. Call lookup_customer or create_customer first.",
            )
        if not self.name_collected:
            return ToolResult(
                success=False,
                data={},
                message=(
                    f"Cannot {action} yet. Ask for the caller's full name and save it "
                    "via create_customer before continuing."
                ),
            )
        if not self.address_collected:
            return ToolResult(
                success=False,
                data={},
                message=(
                    f"Cannot {action} yet. Ask for the service address and save it "
                    "via create_customer before checking availability or booking."
                ),
            )
        return None

    @classmethod
    def load_from_call(
        cls,
        db: Session,
        business_id: str,
        call_log_id: str | None,
    ) -> ConversationState:
        state = cls()
        if not call_log_id:
            return state

        from app.models import AIActivityLog, CallLog

        call = (
            db.query(CallLog)
            .filter(CallLog.id == call_log_id, CallLog.business_id == business_id)
            .first()
        )
        if not call:
            return state

        if call.caller_phone and call.caller_phone not in ("text-chat", "unknown", ""):
            state.caller_phone = normalize_phone(call.caller_phone)
        if call_has_booking(call.summary):
            state.booking_complete = True

        logs = (
            db.query(AIActivityLog)
            .filter(AIActivityLog.call_log_id == call_log_id)
            .order_by(AIActivityLog.created_at)
            .all()
        )
        for log in logs:
            state.apply_activity_log(log)
        return state

    def apply_activity_log(self, log) -> None:
        output = log.output_data or {}
        if not output.get("success"):
            return
        if log.tool_name == "create_customer":
            data = output.get("data") or {}
            customer_id = data.get("customer_id")
            if customer_id:
                self.note_customer(customer_id, data.get("address"), data.get("name"))
        elif log.tool_name == "check_availability":
            self.availability_checked = True
        elif log.tool_name == "book_appointment":
            self.booking_complete = True
