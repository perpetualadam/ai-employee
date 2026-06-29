"""Concrete AI receptionist tools backed by CRM and calendar services."""

import logging
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.ai.date_utils import business_now, resolve_target_date
from app.ai.tools import ToolResult
from app.models import Business
from app.schemas import AppointmentCreate, CustomerCreate, CustomerUpdate
from app.services.appointment_service import AppointmentService
from app.services.customer_service import CustomerService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class ReceptionistToolsImpl:
    """Real tool implementations — all scoped to a single business."""

    def __init__(
        self,
        db: Session,
        business: Business,
        notification_service: NotificationService,
        call_log_id: str | None = None,
    ):
        self.db = db
        self.business = business
        self.business_id = business.id
        self.notifications = notification_service
        self.call_log_id = call_log_id
        self.escalated = False
        self._verified_customer_id: str | None = None
        self._address_collected = False
        self._availability_checked = False

    @staticmethod
    def _has_address(address: str | None) -> bool:
        return bool(address and address.strip())

    def _note_customer(self, customer_id: str, address: str | None) -> None:
        self._verified_customer_id = customer_id
        if self._has_address(address):
            self._address_collected = True

    def _require_customer_and_address(self, action: str) -> ToolResult | None:
        if self._verified_customer_id is None:
            return ToolResult(
                success=False,
                data={},
                message=f"Cannot {action} yet. Call lookup_customer or create_customer first.",
            )
        if not self._address_collected:
            return ToolResult(
                success=False,
                data={},
                message=(
                    f"Cannot {action} yet. Ask for the service address and save it "
                    "via create_customer before checking availability or booking."
                ),
            )
        return None

    async def book_appointment(
        self,
        customer_id: str,
        service_type: str,
        start_time: datetime,
        end_time: datetime,
        notes: str | None = None,
    ) -> ToolResult:
        if self._verified_customer_id is None:
            return ToolResult(
                success=False,
                data={},
                message="Cannot book yet. Call lookup_customer or create_customer first.",
            )
        if customer_id != self._verified_customer_id:
            return ToolResult(
                success=False,
                data={"customer_id": self._verified_customer_id},
                message=(
                    f"Use customer_id {self._verified_customer_id} from lookup/create — "
                    "do not invent a customer_id."
                ),
            )
        if not self._availability_checked:
            return ToolResult(
                success=False,
                data={},
                message="Cannot book yet. Call check_availability for the requested date first.",
            )
        address_block = self._require_customer_and_address("book")
        if address_block:
            return address_block

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
            return ToolResult(
                success=True,
                data={
                    "appointment_id": appt.id,
                    "start_time": appt.start_time.isoformat(),
                    "end_time": appt.end_time.isoformat(),
                    "status": appt.status.value,
                },
                message=f"Appointment booked for {service_type}",
            )
        except ValueError as exc:
            return ToolResult(success=False, data={}, message=str(exc))

    async def check_availability(
        self,
        target_date: str,
        service_type: str | None = None,
    ) -> ToolResult:
        address_block = self._require_customer_and_address("check availability")
        if address_block:
            return address_block

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

        formatted_slots = [
            {
                "start_time": s["start_time"].astimezone(tz).isoformat(),
                "end_time": s["end_time"].astimezone(tz).isoformat(),
                "start_time_utc": s["start_time"].isoformat(),
                "end_time_utc": s["end_time"].isoformat(),
            }
            for s in slots
        ]

        self._availability_checked = True
        resolved_date = parsed_date.isoformat()

        return ToolResult(
            success=True,
            data={
                "date": resolved_date,
                "requested_date": target_date,
                "timezone": self.business.timezone,
                "current_local_time": now.isoformat(),
                "slots": formatted_slots,
                "count": len(formatted_slots),
            },
            message=f"Found {len(formatted_slots)} available slots on {resolved_date}",
        )

    async def create_customer(
        self,
        name: str,
        phone: str,
        email: str | None = None,
        address: str | None = None,
    ) -> ToolResult:
        if not self._has_address(address):
            return ToolResult(
                success=False,
                data={},
                message="Address is required. Ask the caller for their service address first.",
            )

        existing = CustomerService.lookup_by_phone(self.db, self.business_id, phone)
        if existing:
            if not self._has_address(existing.address):
                existing = CustomerService.update_customer(
                    self.db,
                    existing,
                    CustomerUpdate(address=address.strip()),
                )
            self._note_customer(existing.id, existing.address)
            return ToolResult(
                success=True,
                data={
                    "customer_id": existing.id,
                    "name": existing.name,
                    "phone": existing.phone,
                    "address": existing.address,
                    "already_exists": True,
                },
                message=f"Customer on file: {existing.name}",
            )

        try:
            customer = CustomerService.create_customer(
                self.db,
                self.business_id,
                CustomerCreate(name=name, phone=phone, email=email, address=address.strip()),
            )
            self._note_customer(customer.id, customer.address)
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
        result = self.notifications.send_sms(phone, message)
        return ToolResult(
            success=result["sent"],
            data=result,
            message="SMS sent" if result["sent"] else "Failed to send SMS",
        )

    async def transfer_call(self, call_id: str, reason: str) -> ToolResult:
        self.escalated = True

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

        logger.warning(
            "Call escalated to human",
            extra={"business_id": self.business_id, "reason": reason},
        )
        return ToolResult(
            success=True,
            data={"escalated": True, "reason": reason},
            message="Transferring to a team member. Someone will follow up shortly.",
        )

    async def lookup_customer(self, phone: str) -> ToolResult:
        customer = CustomerService.lookup_by_phone(self.db, self.business_id, phone)
        if customer is None:
            return ToolResult(
                success=True,
                data={"found": False},
                message="No customer found with that phone number",
            )
        self._note_customer(customer.id, customer.address)
        if not self._address_collected:
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
            return await self.book_appointment(
                customer_id=arguments["customer_id"],
                service_type=arguments["service_type"],
                start_time=_parse_datetime(arguments["start_time"]),
                end_time=_parse_datetime(arguments["end_time"]),
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


def _parse_datetime(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)
