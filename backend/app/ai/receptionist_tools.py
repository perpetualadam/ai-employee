"""Concrete AI receptionist tools backed by CRM and calendar services."""

import logging
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.ai.tools import ToolResult
from app.models import Business
from app.schemas import AppointmentCreate, CustomerCreate
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

    async def book_appointment(
        self,
        customer_id: str,
        service_type: str,
        start_time: datetime,
        end_time: datetime,
        notes: str | None = None,
    ) -> ToolResult:
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
        try:
            parsed_date = date.fromisoformat(target_date)
        except ValueError:
            return ToolResult(success=False, data={}, message="Invalid date format. Use YYYY-MM-DD.")

        duration = 60
        if service_type:
            from app.services.business_service import BusinessServiceManager

            for svc in BusinessServiceManager.list_services(self.db, self.business_id):
                if svc.name.lower() == service_type.lower():
                    duration = svc.duration_minutes
                    break

        slots = AppointmentService.get_availability(self.db, self.business, parsed_date, duration)
        tz = ZoneInfo(self.business.timezone)

        formatted_slots = [
            {
                "start_time": s["start_time"].astimezone(tz).isoformat(),
                "end_time": s["end_time"].astimezone(tz).isoformat(),
                "start_time_utc": s["start_time"].isoformat(),
                "end_time_utc": s["end_time"].isoformat(),
            }
            for s in slots
        ]

        return ToolResult(
            success=True,
            data={"date": target_date, "slots": formatted_slots, "count": len(formatted_slots)},
            message=f"Found {len(formatted_slots)} available slots on {target_date}",
        )

    async def create_customer(
        self,
        name: str,
        phone: str,
        email: str | None = None,
        address: str | None = None,
    ) -> ToolResult:
        existing = CustomerService.lookup_by_phone(self.db, self.business_id, phone)
        if existing:
            return ToolResult(
                success=True,
                data={
                    "customer_id": existing.id,
                    "name": existing.name,
                    "phone": existing.phone,
                    "already_exists": True,
                },
                message=f"Customer already exists: {existing.name}",
            )

        try:
            customer = CustomerService.create_customer(
                self.db,
                self.business_id,
                CustomerCreate(name=name, phone=phone, email=email, address=address),
            )
            return ToolResult(
                success=True,
                data={
                    "customer_id": customer.id,
                    "name": customer.name,
                    "phone": customer.phone,
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
                    from app.voice.twilio_provider import TwilioVoiceProvider

                    settings = get_settings()
                    escalation = self.business.escalation_phone or self.business.phone_number
                    if escalation and settings.twilio_account_sid:
                        provider = TwilioVoiceProvider()
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
