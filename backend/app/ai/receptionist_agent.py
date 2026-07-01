"""AI receptionist agent — tool-calling conversation loop."""

import json
import logging
from dataclasses import asdict
from uuid import uuid4

from sqlalchemy.orm import Session

from app.ai.groq_provider import GroqProvider, serialize_tool_result, tool_definitions_from_schemas
from app.ai.prompts import build_receptionist_prompt
from app.ai.provider import AIMessage, AIProvider
from app.ai.receptionist_tools import ReceptionistToolsImpl
from app.ai.tools import RECEPTIONIST_TOOL_DEFINITIONS, ToolResult
from app.models import AIActivityLog, Business, CallLog
from app.models.enums import CallDirection, CallStatus, ConversationChannel
from app.services.business_service import BusinessServiceManager
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 8


class ReceptionistAgent:
    """Orchestrates AI conversation with tool execution and activity logging."""

    def __init__(
        self,
        db: Session,
        business: Business,
        provider: AIProvider,
        call_log_id: str | None = None,
    ):
        self.db = db
        self.business = business
        self.provider = provider
        self.call_log_id = call_log_id
        self.tools_impl = ReceptionistToolsImpl(
            db,
            business,
            NotificationService(db, business),
            call_log_id,
        )
        self.tool_defs = tool_definitions_from_schemas(RECEPTIONIST_TOOL_DEFINITIONS)

    def _build_system_message(self, *, caller_phone: str | None = None, voice_mode: bool = False) -> AIMessage:
        services = BusinessServiceManager.list_services(self.db, self.business.id)
        rules = BusinessServiceManager.list_emergency_rules(self.db, self.business.id)
        if caller_phone is None and self.call_log_id:
            call = self.db.query(CallLog).filter(CallLog.id == self.call_log_id).first()
            if call and call.caller_phone:
                caller_phone = call.caller_phone
        prompt = build_receptionist_prompt(
            self.business,
            services,
            rules,
            caller_phone=caller_phone,
            voice_mode=voice_mode,
        )
        return AIMessage(role="system", content=prompt)

    def _log_activity(
        self,
        action: str,
        tool_name: str | None = None,
        input_data: dict | None = None,
        output_data: dict | None = None,
    ) -> None:
        log = AIActivityLog(
            id=str(uuid4()),
            business_id=self.business.id,
            call_log_id=self.call_log_id,
            action=action,
            tool_name=tool_name,
            input_data=input_data,
            output_data=output_data,
        )
        self.db.add(log)
        self.db.commit()

    async def chat(
        self,
        user_message: str,
        history: list[dict[str, str]],
        *,
        voice_mode: bool = False,
    ) -> dict:
        self._voice_mode = voice_mode
        self.tools_impl.voice_mode = voice_mode
        self.tools_impl.user_turn_count = sum(
            1 for entry in history if entry.get("role") == "user"
        ) + 1
        self.tools_impl.current_user_message = user_message
        messages: list[AIMessage] = [self._build_system_message(voice_mode=voice_mode)]

        for entry in history:
            if entry["role"] in ("user", "assistant"):
                messages.append(AIMessage(role=entry["role"], content=entry["content"]))

        messages.append(AIMessage(role="user", content=user_message))

        tools_used: list[str] = []

        for _ in range(MAX_TOOL_ROUNDS):
            response = await self.provider.chat(messages, tools=self.tool_defs)

            if not response.tool_calls:
                reply = response.content or "I'm sorry, I didn't catch that. Could you repeat that?"
                self._save_conversation_turn(user_message, history, reply, voice_mode=voice_mode)
                return {
                    "reply": reply,
                    "tools_used": tools_used,
                    "escalated": self.tools_impl.escalated,
                    "owner_notified": self.tools_impl.owner_notified,
                }

            # Assistant message requesting tool calls
            messages.append(
                AIMessage(
                    role="assistant",
                    content=response.content or "",
                    tool_calls=response.tool_calls,
                )
            )

            for tool_call in response.tool_calls:
                fn = tool_call.get("function", {})
                tool_name = fn.get("name", "")
                tool_id = tool_call.get("id", "")

                try:
                    arguments = json.loads(fn.get("arguments", "{}"))
                except json.JSONDecodeError:
                    arguments = {}

                logger.info(
                    "Executing tool",
                    extra={"tool": tool_name, "business_id": self.business.id},
                )

                try:
                    result = await self.tools_impl.dispatch(tool_name, arguments)
                except Exception:
                    self.db.rollback()
                    logger.exception(
                        "Tool execution failed",
                        extra={"tool": tool_name, "business_id": self.business.id},
                    )
                    result = ToolResult(
                        success=False,
                        data={},
                        message="That action failed. Try again or ask the caller for more details.",
                    )

                tools_used.append(tool_name)

                try:
                    self._log_activity(
                        action="tool_call",
                        tool_name=tool_name,
                        input_data=arguments,
                        output_data=asdict(result),
                    )
                except Exception:
                    self.db.rollback()
                    logger.exception(
                        "Failed to log tool activity",
                        extra={"tool": tool_name, "business_id": self.business.id},
                    )

                messages.append(
                    AIMessage(
                        role="tool",
                        content=serialize_tool_result(result),
                        tool_call_id=tool_id,
                        name=tool_name,
                    )
                )

        caller_phone = None
        if self.call_log_id:
            call = self.db.query(CallLog).filter(CallLog.id == self.call_log_id).first()
            if call:
                caller_phone = call.caller_phone

        if not self.tools_impl.escalated:
            self.tools_impl.escalated = True
            if not self._voice_mode:
                self.tools_impl.owner_notified = self.tools_impl.notifications.notify_owner_escalation(
                    "The AI could not finish handling this request automatically.",
                    caller_phone,
                )

        if self._voice_mode:
            reply = "Please hold — I'm connecting you with someone who can help."
        else:
            reply = (
                "Thanks for your patience. I've passed this to our team — "
                "someone will call you back shortly."
            )

        return {
            "reply": reply,
            "tools_used": tools_used,
            "escalated": True,
            "owner_notified": self.tools_impl.owner_notified,
        }

    def _save_conversation_turn(
        self,
        user_message: str,
        history: list[dict[str, str]],
        reply: str,
        *,
        voice_mode: bool = False,
    ) -> None:
        if not self.call_log_id:
            return

        call = self.db.query(CallLog).filter(CallLog.id == self.call_log_id).first()
        if not call:
            return

        updated_history = list(history) + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": reply},
        ]
        call.conversation_history = updated_history
        call.transcript = "\n".join(f"{h['role'].upper()}: {h['content']}" for h in updated_history)

        if not voice_mode:
            call.status = CallStatus.COMPLETED

        self.db.commit()


def create_text_session(
    db: Session,
    business_id: str,
    caller_phone: str | None = None,
) -> CallLog:
    """Create a call log entry for a text chat session."""
    call = CallLog(
        id=str(uuid4()),
        business_id=business_id,
        channel=ConversationChannel.WEB_CHAT,
        direction=CallDirection.INBOUND,
        status=CallStatus.IN_PROGRESS,
        caller_phone=caller_phone or "text-chat",
        summary="Text receptionist session",
    )
    db.add(call)
    db.commit()
    db.refresh(call)
    return call


def get_ai_provider() -> AIProvider:
    from app.config import get_settings

    settings = get_settings()
    return GroqProvider(api_key=settings.groq_api_key, model=settings.groq_model)
