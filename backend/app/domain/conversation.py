"""Conversation channel helpers — pure business rules."""

from app.models import CallLog
from app.models.enums import ConversationChannel


def infer_channel(call: CallLog) -> ConversationChannel:
    """Infer channel for legacy rows missing explicit channel."""
    if call.channel:
        return call.channel
    if call.external_call_id:
        return ConversationChannel.VOICE
    if call.caller_phone in (None, "text-chat", "unknown", ""):
        return ConversationChannel.WEB_CHAT
    return ConversationChannel.SMS


def channel_label(channel: ConversationChannel) -> str:
    labels = {
        ConversationChannel.VOICE: "Phone call",
        ConversationChannel.SMS: "SMS",
        ConversationChannel.WEB_CHAT: "Web chat",
    }
    return labels.get(channel, channel.value)


def conversation_has_sms_continuation(call: CallLog) -> bool:
    """True when a voice session also has SMS turns in history metadata."""
    history = call.conversation_history or []
    return any(entry.get("channel") == "sms" for entry in history)
