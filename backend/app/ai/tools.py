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
            "description": "Book an appointment for a customer",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "service_type": {"type": "string"},
                    "start_time": {"type": "string", "description": "ISO 8601 datetime"},
                    "end_time": {"type": "string", "description": "ISO 8601 datetime"},
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
            "description": "Check available appointment slots for a given date",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
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
            "description": "Create a new customer record",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "phone": {"type": "string"},
                    "email": {"type": "string"},
                    "address": {"type": "string"},
                },
                "required": ["name", "phone"],
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
