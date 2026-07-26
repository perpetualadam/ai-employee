"""Telnyx duplex media adapter — Phase 2 bidirectional WebSocket playback."""

from __future__ import annotations

import asyncio
import logging
from html import escape
from typing import Any

from app.integrations.adapters._duplex_markup_base import MarkupDuplexAdapter
from app.voice import telnyx_client
from app.voice.duplex.contracts import MediaEvent, MediaStreamBindContext
from app.voice.duplex.media_utils import parse_json_media_message
from app.voice.telnyx_media_stream import (
    build_clear_playback_frame,
    build_outbound_mp3_frame,
    build_outbound_rtp_frame,
    chunk_mulaw_frames,
    is_mp3_audio,
)

logger = logging.getLogger(__name__)


class TelnyxDuplexMediaAdapter(MarkupDuplexAdapter):
    def __init__(self) -> None:
        self._websocket: Any | None = None
        self._bind_context: MediaStreamBindContext | None = None

    @property
    def provider_name(self) -> str:
        return "telnyx"

    def is_configured(self) -> bool:
        from app.config import get_settings

        settings = get_settings()
        return bool(
            telnyx_client.is_telnyx_configured()
            and settings.telnyx_account_sid
            and settings.telnyx_texml_connection_id
        )

    def supports_duplex(self) -> bool:
        return self.is_configured()

    def supports_barge_in(self) -> bool:
        return True

    def supports_websocket_playback(self) -> bool:
        return True

    def preferred_playback_content_type(self) -> str:
        return "audio/mpeg"

    def parse_media_message(self, raw_text: str) -> MediaEvent | None:
        return parse_json_media_message(raw_text, provider_name=self.provider_name)

    def _stream_block(self, stream_url: str, *, codec: str = "PCMU") -> str:
        url = escape(stream_url, quote=True)
        return (
            "<Start>"
            f'<Stream url="{url}" track="inbound_track" codec="{codec}" '
            'bidirectionalMode="mp3" enableReconnect="true" />'
            "</Start>"
        )

    def _wrap_response(self, inner: str) -> str:
        return f'<?xml version="1.0" encoding="UTF-8"?><Response>{inner}</Response>'

    async def bind_media_websocket(
        self,
        websocket: Any,
        *,
        context: MediaStreamBindContext,
    ) -> None:
        self._websocket = websocket
        self._bind_context = context
        logger.info(
            "Telnyx duplex WebSocket bound",
            extra={
                "call_control_id": context.call_control_id,
                "stream_id": context.stream_id,
            },
        )

    async def unbind_media_websocket(self) -> None:
        self._websocket = None
        self._bind_context = None

    async def stop_playback(self, call_id: str) -> None:
        if self._websocket is not None:
            try:
                await self._websocket.send_text(build_clear_playback_frame())
            except Exception:
                logger.exception("Telnyx duplex clear frame failed", extra={"call_id": call_id})

        call_control_id = (self._bind_context.call_control_id if self._bind_context else None) or call_id
        if call_control_id:
            try:
                await asyncio.to_thread(telnyx_client.playback_stop, call_control_id)
            except Exception:
                logger.exception(
                    "Telnyx playback_stop failed",
                    extra={"call_control_id": call_control_id},
                )

    async def deliver_audio(
        self,
        call_id: str,
        audio: bytes,
        *,
        content_type: str = "audio/mulaw",
    ) -> bool:
        del call_id
        if not audio or self._websocket is None:
            return False

        try:
            if is_mp3_audio(audio, content_type):
                await self._websocket.send_text(build_outbound_mp3_frame(audio))
                return True

            for frame in chunk_mulaw_frames(audio):
                await self._websocket.send_text(build_outbound_rtp_frame(frame))
            return True
        except Exception:
            logger.exception("Telnyx duplex outbound audio failed")
            return False

    async def _push_call_markup(self, call_id: str, markup: str) -> None:
        telnyx_client.update_call_texml(call_id, markup)
