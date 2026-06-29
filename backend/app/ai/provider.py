"""
AI provider abstraction — swap Groq for OpenAI/Anthropic without changing business logic.

Phase 3 will implement GroqProvider with tool calling.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class AIMessage:
    role: str  # system | user | assistant | tool
    content: str
    tool_call_id: str | None = None
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]


@dataclass
class AIResponse:
    content: str | None
    tool_calls: list[dict[str, Any]]
    finish_reason: str


class AIProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[AIMessage],
        tools: list[ToolDefinition] | None = None,
    ) -> AIResponse:
        """Send messages to the AI and return response (with optional tool calls)."""
        ...
