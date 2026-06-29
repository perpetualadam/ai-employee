"""Groq API provider — OpenAI-compatible chat completions with tool calling."""

import json
import logging
from typing import Any

import httpx

from app.ai.provider import AIMessage, AIProvider, AIResponse, ToolDefinition

logger = logging.getLogger(__name__)

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider(AIProvider):
    """Groq API implementation using OpenAI-compatible endpoints."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        if not api_key:
            raise ValueError("GROQ_API_KEY is not configured")
        self.api_key = api_key
        self.model = model

    def _format_messages(self, messages: list[AIMessage]) -> list[dict[str, Any]]:
        formatted: list[dict[str, Any]] = []
        for msg in messages:
            entry: dict[str, Any] = {"role": msg.role, "content": msg.content or ""}
            if msg.role == "tool":
                entry["tool_call_id"] = msg.tool_call_id
            if msg.role == "assistant" and msg.tool_calls:
                entry["tool_calls"] = msg.tool_calls
            formatted.append(entry)
        return formatted

    def _format_tools(self, tools: list[ToolDefinition] | None) -> list[dict[str, Any]] | None:
        if not tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]

    async def chat(
        self,
        messages: list[AIMessage],
        tools: list[ToolDefinition] | None = None,
    ) -> AIResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": self._format_messages(messages),
            "temperature": 0.4,
        }

        formatted_tools = self._format_tools(tools)
        if formatted_tools:
            payload["tools"] = formatted_tools
            payload["tool_choice"] = "auto"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                GROQ_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        if response.status_code != 200:
            logger.error(
                "Groq API error",
                extra={"status": response.status_code, "body": response.text[:500]},
            )
            response.raise_for_status()

        data = response.json()
        choice = data["choices"][0]
        message = choice["message"]
        tool_calls = message.get("tool_calls") or []

        return AIResponse(
            content=message.get("content"),
            tool_calls=tool_calls,
            finish_reason=choice.get("finish_reason", "stop"),
        )


def tool_definitions_from_schemas(schemas: list[dict[str, Any]]) -> list[ToolDefinition]:
    """Convert OpenAI-format tool schemas to ToolDefinition objects."""
    result = []
    for schema in schemas:
        fn = schema["function"]
        result.append(
            ToolDefinition(
                name=fn["name"],
                description=fn["description"],
                parameters=fn["parameters"],
            )
        )
    return result


def serialize_tool_result(result: Any) -> str:
    """JSON-serialize a tool result for the model."""
    if hasattr(result, "__dict__"):
        from dataclasses import asdict

        if hasattr(result, "success"):
            return json.dumps(asdict(result))
    return json.dumps(result)
