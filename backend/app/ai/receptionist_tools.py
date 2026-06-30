"""Concrete AI receptionist tools backed by CRM and calendar services."""

import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.ai.date_utils import business_now, resolve_target_date
from app.ai.tools import ToolResult
from app.domain.intake import is_valid_customer_name, is_valid_service_address
from app.domain.phone import is_plausible_phone, normalize_phone, resolve_caller_phone
from app.models import Business
from app.schemas import AppointmentCreate, CustomerCreate, CustomerUpdate
from app.services.appointment_service import AppointmentService
from app.services.customer_service import CustomerService
from app.services.notification_service import NotificationService
from app.voice.session_state import VoiceSessionState
from app.voice.slots import parse_datetime_utc

logger = logging.getLogger(__name__)


class ReceptionistToolsImpl:
    """Real tool implementations — all scoped to a single business."""

    def __init__(
        self,
        db: Session,
        business: Business,
        notification_service: NotificationService,
        call_log_id: str | None = None,
        voice_mode: bool = False,
    ):
        self.db = db
        self.business = business
        self.business_id = business.id
        self.notifications = notification_service
        self.call_log_id = call_log_id
        self.voice_mode = voice_mode
        self.escalated = False
        self.owner_notified = False
        self.user_turn_count = 0
        self._session: VoiceSessionState = VoiceSessionState.load(
            db, business.id, call_log_id
        )

    def _require_intake(self, action: str) -> ToolResult | None:
        return self._session.require_intake(action)

    def _resolve_phone(self, phone: str) -> str:
        resolved = resolve_caller_phone(phone, self._session.caller_phone)
        return resolved or normalize_phone(phone)

    async def book_appointment(
        self,
        customer_id: str,
        service_type: str,
        start_time: datetime,
        end_time: datetime,
        notes: str | None = None,
    ) -> ToolResult:
        intake_block = self._require_intake("book")
        if intake_block:
            return intake_block

        same_turn = self._session.block_same_turn_booking()
        if same_turn:
            return same_turn

        if customer_id != self._session.verified_customer_id:
            return ToolResult(
                success=False,
                data={"customer_id": self._session.verified_customer_id},
                message=(
                    f"Use customer_id {self._session.verified_customer_id} from lookup/create — "
                    "do not invent a customer_id."
                ),
            )
        if not self._session.availability_checked:
            return ToolResult(
                success=False,
                data={},
                message="Cannot book yet. Call check_availability for the requested date first.",
            )
        if self._session.booking_complete:
            return ToolResult(
                success=False,
                data={},
                message=(
                    "An appointment is already booked on this call. "
                    "Confirm the existing booking to the caller and end the conversation — do not book again."
                ),
            )

        slot_result = self._session.validate_and_resolve_slot(start_time, end_time)
        if isinstance(slot_result, ToolResult):
            return slot_result
        start_time, end_time = slot_result

        try:
            appt = AppointmentService.create_appointment(
                self.db,
                self.business,
                AppointmentCreate(
                    customer_id=customer_id,
                    service_type=service_type,
                    start_time=start_time,
                    end_time=end_time,
                    notes=notes,
                ),
            )
            self._session.booking_complete = True
            if self.call_log_id:
                from app.models import CallLog

                call = (
                    self.db.query(CallLog)
                    .filter(CallLog.id == self.call_log_id, CallLog.business_id == self.business_id)
                    .first()
                )
                if call:
                    call.summary = "Appointment booked on voice call"
                    self.db.commit()

            tz = ZoneInfo(self.business.timezone)
            local_start = appt.start_time.astimezone(tz)
            local_label = local_start.strftime("%A %B %-d at %-I:%M %p").replace("  ", " ")

            return ToolResult(
                success=True,
                data={
                    "appointment_id": appt.id,
                    "start_time": appt.start_time.isoformat(),
                    "end_time": appt.end_time.isoformat(),
                    "local_time": local_start.isoformat(),
                    "local_time_spoken": f"{local_label} {self.business.timezone}",
                    "status": appt.status.value,
                },
                message=(
                    f"Appointment booked for {service_type} at {local_label} "
                    f"({self.business.timezone}). Tell the caller this exact local time."
                ),
            )
        except ValueError as exc:
            return ToolResult(success=False, data={}, message=str(exc))

    async def check_availability(
        self,
        target_date: str,
        service_type: str | None = None,
    ) -> ToolResult:
        intake_block = self._require_intake("check availability")
        if intake_block:
            return intake_block

        parsed_date = resolve_target_date(target_date, self.business.timezone)
        if parsed_date is None:
            return ToolResult(
                success=False,
                data={},
                message="Invalid date. Use YYYY-MM-DD or relative terms like today or tomorrow.",
            )

        duration = 60
        if service_type:
            from app.services.business_service import BusinessServiceManager

            for svc in BusinessServiceManager.list_services(self.db, self.business_id):
                if svc.name.lower() == service_type.lower():
                    duration = svc.duration_minutes
                    break

        slots = AppointmentService.get_availability(self.db, self.business, parsed_date, duration)
        tz = ZoneInfo(self.business.timezone)
        now = business_now(self.business.timezone)
        resolved_date = parsed_date.isoformat()
        next_date: date | None = None
        next_slots_raw: list[dict[str, datetime]] = []

        if not slots:
            next_date, next_slots_raw = AppointmentService.find_next_available(
                self.db,
                self.business,
                parsed_date + timedelta(days=1),
                duration,
            )

        formatted_slots = VoiceSessionState.format_slots(slots, tz)
        slot_msg = f"Found {len(formatted_slots)} available slots on {resolved_date}"
        slot_msg += self._session.record_availability(formatted_slots, voice=self.voice_mode)
        next_formatted: list[dict] = []
        if not formatted_slots and next_date and next_slots_raw:
            next_formatted = VoiceSessionState.format_slots(next_slots_raw, tz)
            self._session.offered_slots = next_formatted
            self._session.availability_checked = True
            slot_msg += (
                f" No openings on {resolved_date}. "
                f"Next availability is {next_date.isoformat()} with {len(next_formatted)} slots — "
                "offer those times. Do NOT transfer_call just because the requested day is full."
            )

        data: dict = {
            "date": resolved_date,
            "requested_date": target_date,
            "timezone": self.business.timezone,
            "current_local_time": now.isoformat(),
            "slots": formatted_slots,
            "count": len(formatted_slots),
        }
        if next_date and next_slots_raw:
            data["next_available_date"] = next_date.isoformat()
            data["next_slots"] = next_formatted

        return ToolResult(
            success=True,
            data=data,
            message=slot_msg,
        )

    async def create_customer(
        self,
        name: str,
        phone: str,
        email: str | None = None,
        address: str | None = None,
    ) -> ToolResult:
        if not self.voice_mode and self.user_turn_count < 2:
            return ToolResult(
                success=False,
                data={},
                message=(
                    "Cannot save customer yet. Greet them and ask for their full name first — "
                    "one question per message."
                ),
            )
        if not is_valid_customer_name(name):
            return ToolResult(
                success=False,
                data={},
                message="Ask the caller for their full name first — do not guess or use a placeholder.",
            )
        if not is_valid_service_address(address):
            return ToolResult(
                success=False,
                data={},
                message=(
                    "Address is required. Ask for the full street address including "
                    "street number — a city or state alone is not enough."
                ),
            )

        phone = self._resolve_phone(phone)
        if not is_plausible_phone(phone):
            return ToolResult(
                success=False,
                data={},
                message="Valid phone required. Use the caller ID phone from the system prompt.",
            )

        existing = CustomerService.lookup_by_phone(self.db, self.business_id, phone)
        if existing:
            update_data: dict[str, str] = {}
            if not is_valid_service_address(existing.address):
                update_data["address"] = address.strip()
            if not is_valid_customer_name(existing.name):
                update_data["name"] = name.strip()
            if update_data:
                existing = CustomerService.update_customer(
                    self.db,
                    existing,
                    CustomerUpdate(**update_data),
                )
            if not is_valid_customer_name(existing.name) or not is_valid_service_address(existing.address):
                return ToolResult(
                    success=False,
                    data={},
                    message=(
                        "Customer record still missing a valid name or address. "
                        "Ask the caller for both, then call create_customer again."
                    ),
                )
            self._session.mark_intake_saved(existing.id, existing.address, existing.name)
            return ToolResult(
                success=True,
                data={
                    "customer_id": existing.id,
                    "name": existing.name,
                    "phone": existing.phone,
                    "address": existing.address,
                    "already_exists": True,
                },
                message=f"Customer saved: {existing.name} at {existing.address}",
            )

        try:
            customer = CustomerService.create_customer(
                self.db,
                self.business_id,
                CustomerCreate(name=name.strip(), phone=phone, email=email, address=address.strip()),
            )
            self._session.mark_intake_saved(customer.id, customer.address, customer.name)
            return ToolResult(
                success=True,
                data={
                    "customer_id": customer.id,
                    "name": customer.name,
                    "phone": customer.phone,
                    "address": customer.address,
                    "already_exists": False,
                },
                message=f"Customer {customer.name} created",
            )
        except ValueError as exc:
            return ToolResult(success=False, data={}, message=str(exc))

    async def send_sms(self, phone: str, message: str) -> ToolResult:
        from app.config import get_settings

        if self._session.sms_sent_this_call:
            return ToolResult(
                success=False,
                data={},
                message=(
                    "Confirmation SMS was already sent. Do not send again — "
                    "reply briefly and end the conversation."
                ),
            )

        settings = get_settings()
        if self.call_log_id and not settings.telnyx_messaging_profile_id:
            return ToolResult(
                success=True,
                data={"sent": False, "skipped": True, "reason": "SMS not configured for voice calls"},
                message="SMS skipped — confirm the appointment verbally to the caller instead.",
            )

        phone = self._resolve_phone(phone)
        if not is_plausible_phone(phone):
            return ToolResult(
                success=False,
                data={},
                message="Cannot send SMS — use the caller ID phone number.",
            )

        result = self.notifications.send_sms(phone, message)
        if result.get("sent"):
            self._session.sms_sent_this_call = True
        return ToolResult(
            success=result["sent"],
            data=result,
            message="SMS sent" if result["sent"] else "Failed to send SMS",
        )

    def _caller_phone_for_escalation(self) -> str | None:
        phone = self._session.caller_phone
        if phone and phone not in ("text-chat", "unknown", ""):
            return phone
        if self.call_log_id:
            from app.models import CallLog

            call = (
                self.db.query(CallLog)
                .filter(CallLog.id == self.call_log_id, CallLog.business_id == self.business_id)
                .first()
            )
            if call and call.caller_phone and call.caller_phone not in ("text-chat", "unknown"):
                return call.caller_phone
        return None

    async def transfer_call(self, call_id: str, reason: str) -> ToolResult:
        reason_lower = reason.lower()
        scheduling_only = (
            "no available slot" in reason_lower
            or "no slots" in reason_lower
            or "fully booked" in reason_lower
            or "no availability" in reason_lower
            or "no openings" in reason_lower
        )
        if scheduling_only:
            return ToolResult(
                success=False,
                data={"escalated": False},
                message=(
                    "Do not escalate because a date is full. Call check_availability for the next "
                    "business day (or use next_slots from the prior result) and offer those times. "
                    "Only transfer_call for true emergencies (active flooding, gas smell) or if the "
                    "customer explicitly insists on speaking to a person."
                ),
            )

        self.escalated = True
        caller_phone = self._caller_phone_for_escalation()
        live_transfer = False

        if self.call_log_id:
            from app.models import CallLog

            call = (
                self.db.query(CallLog)
                .filter(CallLog.id == self.call_log_id, CallLog.business_id == self.business_id)
                .first()
            )
            if call:
                call.escalated = True
                call.summary = f"Escalated: {reason}"
                self.db.commit()

                if call.external_call_id:
                    from app.config import get_settings
                    from app.voice.telnyx_provider import TelnyxVoiceProvider

                    settings = get_settings()
                    escalation = self.business.escalation_phone or self.business.phone_number
                    if escalation and settings.telnyx_api_key:
                        provider = TelnyxVoiceProvider()
                        await provider.transfer_call(call.external_call_id, escalation)
                        live_transfer = True
                else:
                    self.owner_notified = self.notifications.notify_owner_escalation(
                        reason, caller_phone
                    )

        logger.warning(
            "Call escalated to human",
            extra={
                "business_id": self.business_id,
                "reason": reason,
                "live_transfer": live_transfer,
                "owner_notified": self.owner_notified,
            },
        )
        if self.voice_mode:
            tool_message = (
                "Live transfer in progress. Tell the caller you are connecting them now and to stay on the line."
            )
        else:
            tool_message = (
                "Owner has been notified to call the customer back. "
                "Tell the customer a team member will call them back shortly at their phone number. "
                "Do NOT say they are being transferred, put on hold, or connected live."
            )
        return ToolResult(
            success=True,
            data={
                "escalated": True,
                "reason": reason,
                "owner_notified": self.owner_notified,
                "live_transfer": live_transfer,
            },
            message=tool_message,
        )

    async def lookup_customer(self, phone: str) -> ToolResult:
        phone = self._resolve_phone(phone)
        customer = CustomerService.lookup_by_phone(self.db, self.business_id, phone)
        if customer is None:
            return ToolResult(
                success=True,
                data={"found": False},
                message=(
                    "No customer found with that phone number. "
                    "Ask for their full name and service address, then call create_customer."
                ),
            )

        has_valid_name = is_valid_customer_name(customer.name)
        has_valid_address = is_valid_service_address(customer.address)

        if self.voice_mode:
            return ToolResult(
                success=True,
                data={
                    "found": True,
                    "customer_id": customer.id,
                    "name": customer.name,
                    "phone": customer.phone,
                    "email": customer.email,
                    "address": customer.address,
                    "name_on_file": has_valid_name,
                    "address_on_file": has_valid_address,
                },
                message=(
                    f"Phone matches {customer.name if has_valid_name else 'a customer on file'}. "
                    "On phone calls you must still ask for their full name and service address, "
                    "then call create_customer with what they tell you — do not skip to booking."
                ),
            )

        self._session.note_customer(customer.id, customer.address, customer.name)
        if not has_valid_address:
            return ToolResult(
                success=True,
                data={
                    "found": True,
                    "customer_id": customer.id,
                    "name": customer.name,
                    "phone": customer.phone,
                    "email": customer.email,
                    "address": customer.address,
                    "address_on_file": False,
                },
                message=(
                    f"Found customer {customer.name}, but no address on file. "
                    "Ask for their service address, then call create_customer with name, phone, and address."
                ),
            )
        return ToolResult(
            success=True,
            data={
                "found": True,
                "customer_id": customer.id,
                "name": customer.name,
                "phone": customer.phone,
                "email": customer.email,
                "address": customer.address,
            },
            message=f"Found customer: {customer.name}",
        )

    async def dispatch(self, tool_name: str, arguments: dict) -> ToolResult:
        """Route a tool call to the correct handler."""
        if tool_name == "book_appointment":
            start_raw = arguments.get("start_time_utc") or arguments.get("start_time")
            end_raw = arguments.get("end_time_utc") or arguments.get("end_time")
            return await self.book_appointment(
                customer_id=arguments["customer_id"],
                service_type=arguments["service_type"],
                start_time=parse_datetime_utc(start_raw),
                end_time=parse_datetime_utc(end_raw),
                notes=arguments.get("notes"),
            )
        if tool_name == "check_availability":
            return await self.check_availability(
                target_date=arguments["date"],
                service_type=arguments.get("service_type"),
            )
        if tool_name == "create_customer":
            return await self.create_customer(
                name=arguments["name"],
                phone=arguments["phone"],
                email=arguments.get("email"),
                address=arguments.get("address"),
            )
        if tool_name == "send_sms":
            return await self.send_sms(phone=arguments["phone"], message=arguments["message"])
        if tool_name == "transfer_call":
            return await self.transfer_call(
                call_id=arguments.get("call_id", self.call_log_id or "text-session"),
                reason=arguments["reason"],
            )
        if tool_name == "lookup_customer":
            return await self.lookup_customer(phone=arguments["phone"])

        return ToolResult(success=False, data={}, message=f"Unknown tool: {tool_name}")
