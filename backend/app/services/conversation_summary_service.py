"""Generate owner-facing AI summaries when conversations end."""

import logging

from sqlalchemy.orm import Session

from app.ai.groq_provider import GroqProvider
from app.ai.provider import AIMessage
from app.config import get_settings
from app.models import AIActivityLog, CallLog

logger = logging.getLogger(__name__)

SUMMARY_PROMPT = """Summarize this customer conversation for a trade business owner in 2-3 short sentences.
Focus on: who called/texted, what they need, whether it was booked, and any urgency.
Be factual. Do not invent details not in the transcript.

Transcript:
{transcript}

Tool outcomes:
{tools}
"""


class ConversationSummaryService:
    @staticmethod
    def should_summarize(call: CallLog) -> bool:
        if call.ai_summary:
            return False
        user_turns = sum(
            1 for entry in (call.conversation_history or []) if entry.get("role") == "user"
        )
        return user_turns >= 2

    @staticmethod
    async def maybe_summarize(db: Session, call_log_id: str) -> None:
        call = db.query(CallLog).filter(CallLog.id == call_log_id).first()
        if call is None or not ConversationSummaryService.should_summarize(call):
            return
        await ConversationSummaryService.summarize_call_log(db, call_log_id)

    @staticmethod
    async def summarize_call_log(db: Session, call_log_id: str) -> str | None:
        settings = get_settings()
        if not settings.groq_api_key:
            return None

        call = db.query(CallLog).filter(CallLog.id == call_log_id).first()
        if call is None:
            return None

        if call.ai_summary:
            return call.ai_summary

        history = call.conversation_history or []
        if not history:
            return None

        transcript_lines = [
            f"{entry.get('role', '').upper()}: {entry.get('content', '')}"
            for entry in history
            if entry.get("content")
        ]
        if not transcript_lines:
            return None

        activities = (
            db.query(AIActivityLog)
            .filter(AIActivityLog.call_log_id == call_log_id)
            .order_by(AIActivityLog.created_at.asc())
            .all()
        )
        tool_lines = []
        for act in activities:
            if act.tool_name:
                outcome = (act.output_data or {}).get("message", "")
                tool_lines.append(f"- {act.tool_name}: {outcome[:200]}")

        prompt = SUMMARY_PROMPT.format(
            transcript="\n".join(transcript_lines[-40:]),
            tools="\n".join(tool_lines[-15:]) or "None",
        )

        try:
            provider = GroqProvider(api_key=settings.groq_api_key, model=settings.groq_model)
            response = await provider.chat([AIMessage(role="user", content=prompt)])
            summary = (response.content or "").strip()
            if not summary:
                return None
            call.ai_summary = summary
            db.commit()
            return summary
        except Exception:
            logger.exception("Failed to generate AI summary", extra={"call_log_id": call_log_id})
            return None
