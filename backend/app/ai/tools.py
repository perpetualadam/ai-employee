"""
AI receptionist tool definitions.

These tools are invoked by the AI during phone/text conversations.
Each tool enforces business_id tenant isolation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ToolResult:
    success: bool
    data: dict[str, Any]
    message: str


class ReceptionistTools(ABC):
    """Interface for AI-callable tools — implemented in Phase 2/3."""

    business_id: str

    @abstractmethod
    async def book_appointment(
        self,
        customer_id: str,
        service_type: str,
        start_time: datetime,
        end_time: datetime,
        notes: str | None = None,
    ) -> ToolResult:
        ...

    @abstractmethod
    async def check_availability(
        self,
        date: str,
        service_type: str | None = None,
    ) -> ToolResult:
        ...

    @abstractmethod
    async def create_customer(
        self,
        name: str,
        phone: str,
        email: str | None = None,
        address: str | None = None,
    ) -> ToolResult:
        ...

    @abstractmethod
    async def send_sms(self, phone: str, message: str) -> ToolResult:
        ...

    @abstractmethod
    async def transfer_call(self, call_id: str, reason: str) -> ToolResult:
        ...

    @abstractmethod
    async def lookup_customer(self, phone: str) -> ToolResult:
        ...


# Tool schemas exposed to the AI provider (OpenAI-compatible format)
RECEPTIONIST_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": (
                "Book an appointment for a customer. "
                "Requires lookup/create customer and check_availability first. "
                "You MUST copy start_time and end_time exactly from start_time_utc "
                "and end_time_utc of the slot the caller chose — do not invent times."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "service_type": {"type": "string"},
                    "start_time": {
                        "type": "string",
                        "description": "Exact start_time_utc from the chosen check_availability slot (ISO 8601 UTC)",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Exact end_time_utc from the chosen check_availability slot (ISO 8601 UTC)",
                    },
                    "notes": {"type": "string"},
                },
                "required": ["customer_id", "service_type", "start_time", "end_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": (
                "Check available appointment slots for a given date. "
                "Use YYYY-MM-DD or relative terms: today, tomorrow."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "YYYY-MM-DD, or today, or tomorrow (business local time)",
                    },
                    "service_type": {"type": "string"},
                },
                "required": ["date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_customer",
            "description": (
                "Create a customer record after collecting name, phone, and a confirmed US service address "
                "(house number, street name, street type, optional unit, city, state, ZIP)"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "phone": {"type": "string"},
                    "email": {"type": "string"},
                    "address": {
                        "type": "string",
                        "description": (
                            "Full US service address: house number, street name, street type, "
                            "optional Apt/Suite/Unit, city, state, 5-digit ZIP"
                        ),
                    },
                },
                "required": ["name", "phone", "address"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_sms",
            "description": "Send an SMS confirmation or notification",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["phone", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_web_chat_link",
            "description": (
                "Create a web chat link so the caller can continue online — finish typing their "
                "address, book an appointment, or complete intake when voice is difficult. "
                "Prefer this over SMS when speech recognition fails. Voice calls only."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_address_confirmation_link",
            "description": (
                "Send the caller an SMS link to confirm their service address when speech "
                "recognition keeps failing or the address is unclear. Voice calls only."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {
                        "type": "string",
                        "description": "Caller name if already collected",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "transfer_call",
            "description": "Transfer the call to a human when escalation is needed",
            "parameters": {
                "type": "object",
                "properties": {
                    "call_id": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["call_id", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_customer",
            "description": "Look up an existing customer by phone number",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string"},
                },
                "required": ["phone"],
            },
        },
    },
]
