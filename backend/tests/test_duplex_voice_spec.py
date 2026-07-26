"""Specification: provider-agnostic duplex voice (Telnyx, Twilio, Vonage)."""

from __future__ import annotations

import asyncio
import base64
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.integrations.adapters.telnyx_duplex import TelnyxDuplexMediaAdapter
from app.integrations.adapters.twilio_duplex import TwilioDuplexMediaAdapter
from app.integrations.adapters.vonage_duplex import VonageDuplexMediaAdapter
from app.integrations.registry import get_duplex_media_adapter, register_duplex_adapter
from app.voice.duplex.contracts import MediaEventType
from app.voice.duplex.media_utils import parse_json_media_message
from app.voice.duplex.session import DuplexVoiceSession, SessionState
from app.voice.provider import TranscriptChunk


class DuplexVoiceSpecification(unittest.TestCase):
    def test_media_parser_normalizes_telnyx_twilio_vonage_frames(self) -> None:
        payload = base64.b64encode(b"\xff\xfe").decode()
        raw = json.dumps({"event": "media", "media": {"payload": payload}, "callSid": "CA123"})
        for provider in ("telnyx", "twilio", "vonage"):
            event = parse_json_media_message(raw, provider_name=provider)
            self.assertIsNotNone(event)
            assert event is not None
            self.assertEqual(event.event_type, MediaEventType.MEDIA)
            self.assertEqual(event.call_id, "CA123")
            self.assertEqual(event.audio_payload, b"\xff\xfe")

    def test_duplex_adapters_registered_for_all_cpaas_providers(self) -> None:
        from app.integrations import registry as reg

        self.assertIn("telnyx", reg._DUPLEX_ADAPTERS)
        self.assertIn("twilio", reg._DUPLEX_ADAPTERS)
        self.assertIn("vonage", reg._DUPLEX_ADAPTERS)

    def test_telnyx_adapter_builds_texml_stream_markup(self) -> None:
        adapter = TelnyxDuplexMediaAdapter()
        markup = adapter.build_session_start_response(
            greeting="Hello",
            stream_url="wss://example.com/stream",
            country="US",
        )
        self.assertIn("<Stream", markup)
        self.assertIn('bidirectionalMode="mp3"', markup)
        self.assertIn("Hello", markup)
        self.assertTrue(markup.startswith('<?xml version="1.0"'))

    def test_telnyx_delivers_mp3_over_websocket(self) -> None:
        adapter = TelnyxDuplexMediaAdapter()
        websocket = AsyncMock()

        async def _run() -> bool:
            await adapter.bind_media_websocket(
                websocket,
                context=__import__(
                    "app.voice.duplex.contracts",
                    fromlist=["MediaStreamBindContext"],
                ).MediaStreamBindContext(call_control_id="v2:test"),
            )
            return await adapter.deliver_audio("sid", b"\xff\xfb", content_type="audio/mpeg")

        delivered = asyncio.run(_run())
        self.assertTrue(delivered)
        websocket.send_text.assert_called_once()
        sent = websocket.send_text.call_args[0][0]
        self.assertIn('"event": "media"', sent)

    def test_telnyx_barge_in_sends_clear_frame(self) -> None:
        adapter = TelnyxDuplexMediaAdapter()
        websocket = AsyncMock()

        async def _run() -> None:
            await adapter.bind_media_websocket(
                websocket,
                context=__import__(
                    "app.voice.duplex.contracts",
                    fromlist=["MediaStreamBindContext"],
                ).MediaStreamBindContext(call_control_id="v2:test"),
            )
            with patch("app.integrations.adapters.telnyx_duplex.telnyx_client.playback_stop") as stop_mock:
                await adapter.stop_playback("sid")
                stop_mock.assert_called_once_with("v2:test")

        asyncio.run(_run())
        websocket.send_text.assert_called_once()
        self.assertIn('"event": "clear"', websocket.send_text.call_args[0][0])

    def test_start_event_extracts_call_control_id(self) -> None:
        raw = json.dumps(
            {
                "event": "start",
                "stream_id": "stream-1",
                "start": {"call_control_id": "v2:abc123", "media_format": {"encoding": "PCMU"}},
            }
        )
        event = parse_json_media_message(raw, provider_name="telnyx")
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.call_id, "v2:abc123")
        self.assertEqual(event.stream_id, "stream-1")

    def test_twilio_delivers_mulaw_over_websocket(self) -> None:
        adapter = TwilioDuplexMediaAdapter()
        websocket = AsyncMock()

        async def _run() -> bool:
            await adapter.bind_media_websocket(
                websocket,
                context=__import__(
                    "app.voice.duplex.contracts",
                    fromlist=["MediaStreamBindContext"],
                ).MediaStreamBindContext(stream_id="MZ123"),
            )
            mulaw = b"\xff" * 160
            return await adapter.deliver_audio("CA123", mulaw, content_type="audio/mulaw")

        delivered = asyncio.run(_run())
        self.assertTrue(delivered)
        websocket.send_text.assert_called()
        sent = websocket.send_text.call_args[0][0]
        self.assertIn('"streamSid": "MZ123"', sent)
        self.assertIn('"event": "media"', sent)

    def test_twilio_barge_in_sends_clear_with_stream_sid(self) -> None:
        adapter = TwilioDuplexMediaAdapter()
        websocket = AsyncMock()

        async def _run() -> None:
            await adapter.bind_media_websocket(
                websocket,
                context=__import__(
                    "app.voice.duplex.contracts",
                    fromlist=["MediaStreamBindContext"],
                ).MediaStreamBindContext(stream_id="MZ456"),
            )
            await adapter.stop_playback("CA123")

        asyncio.run(_run())
        websocket.send_text.assert_called_once()
        self.assertIn('"event": "clear"', websocket.send_text.call_args[0][0])
        self.assertIn('"streamSid": "MZ456"', websocket.send_text.call_args[0][0])

    def test_twilio_prefers_mulaw_tts_format(self) -> None:
        adapter = TwilioDuplexMediaAdapter()
        self.assertEqual(adapter.preferred_playback_content_type(), "audio/mulaw")
        self.assertTrue(adapter.supports_websocket_playback())

    def test_twilio_adapter_builds_twiml_connect_stream(self) -> None:
        adapter = TwilioDuplexMediaAdapter()
        markup = adapter.build_session_start_response(
            greeting="Hello",
            stream_url="wss://example.com/stream",
        )
        self.assertIn("<Connect>", markup)
        self.assertIn("<Stream", markup)

    def test_vonage_adapter_builds_ncco_websocket(self) -> None:
        adapter = VonageDuplexMediaAdapter()
        markup = adapter.build_session_start_response(
            greeting="Hello",
            stream_url="wss://example.com/stream",
        )
        data = json.loads(markup)
        self.assertEqual(data[0]["action"], "talk")
        endpoint = data[1]["endpoint"][0]
        self.assertEqual(endpoint["type"], "websocket")
        self.assertIn("rate=16000", endpoint["content-type"])

    def test_vonage_delivers_l16_binary_frames(self) -> None:
        adapter = VonageDuplexMediaAdapter()
        websocket = AsyncMock()

        async def _run() -> bool:
            await adapter.bind_media_websocket(
                websocket,
                context=__import__(
                    "app.voice.duplex.contracts",
                    fromlist=["MediaStreamBindContext"],
                ).MediaStreamBindContext(call_control_id="uuid-1"),
            )
            pcm = b"\x00\x01" * 320
            return await adapter.deliver_audio("uuid-1", pcm, content_type="audio/l16")

        delivered = asyncio.run(_run())
        self.assertTrue(delivered)
        websocket.send_bytes.assert_called()

    def test_vonage_barge_in_sends_clear_command(self) -> None:
        adapter = VonageDuplexMediaAdapter()
        websocket = AsyncMock()

        async def _run() -> None:
            await adapter.bind_media_websocket(
                websocket,
                context=__import__(
                    "app.voice.duplex.contracts",
                    fromlist=["MediaStreamBindContext"],
                ).MediaStreamBindContext(call_control_id="uuid-2"),
            )
            await adapter.stop_playback("uuid-2")

        asyncio.run(_run())
        websocket.send_text.assert_called_once()
        self.assertIn('"action": "clear"', websocket.send_text.call_args[0][0])

    def test_vonage_binary_media_parsing(self) -> None:
        from app.voice.duplex.vonage_media_utils import parse_vonage_binary_media, parse_vonage_text_message

        binary = parse_vonage_binary_media(b"\x00\x01" * 10)
        assert binary is not None
        self.assertEqual(binary.event_type, MediaEventType.MEDIA)
        self.assertEqual(len(binary.audio_payload or b""), 20)

        connected = parse_vonage_text_message(
            json.dumps({"event": "websocket:connected", "content-type": "audio/l16;rate=16000"})
        )
        assert connected is not None
        self.assertEqual(connected.event_type, MediaEventType.START)

    def test_vonage_prefers_l16_and_binary_mode(self) -> None:
        adapter = VonageDuplexMediaAdapter()
        self.assertEqual(adapter.preferred_playback_content_type(), "audio/l16")
        self.assertTrue(adapter.uses_binary_media())
        self.assertEqual(adapter.stt_audio_encoding(), ("linear16", 16000))

    def test_voice_mode_service_duplex_available_uses_adapter_not_telnyx_only(self) -> None:
        from app.services.voice_mode_service import VoiceModeService

        mock_stt = MagicMock()
        mock_stt.is_configured.return_value = True
        mock_adapter = MagicMock()
        mock_adapter.is_configured.return_value = True
        mock_adapter.supports_duplex.return_value = True
        mock_adapter.provider_name = "twilio"

        with patch("app.services.voice_mode_service.get_speech_to_text_plugin", return_value=mock_stt):
            with patch(
                "app.services.voice_mode_service.get_duplex_media_adapter",
                return_value=mock_adapter,
            ):
                self.assertTrue(VoiceModeService.duplex_available())

    def test_duplex_handler_has_no_vendor_imports(self) -> None:
        import app.voice.duplex.handler as handler_module

        source = open(handler_module.__file__, encoding="utf-8").read()
        self.assertNotIn("telnyx_client", source)
        self.assertNotIn("Deepgram", source)

    def test_session_barge_in_switches_to_listening(self) -> None:
        class _Adapter:
            provider_name = "telnyx"

            def supports_barge_in(self) -> bool:
                return True

            async def stop_playback(self, call_id: str) -> None:
                pass

            def parse_media_message(self, raw_text: str):
                return None

        adapter = _Adapter()
        stt = MagicMock()
        session = DuplexVoiceSession(
            adapter=adapter,  # type: ignore[arg-type]
            stt=stt,
            tts=None,
            call_id="sid",
            call_log_id="log",
        )
        session._state = SessionState.SPEAKING
        session._speaking = True

        async def _run() -> None:
            await session._handle_barge_in()

        asyncio.run(_run())
        self.assertEqual(session.state, SessionState.LISTENING)
        self.assertFalse(session._speaking)

    def test_get_duplex_media_adapter_resolves_by_telephony_provider(self) -> None:
        register_duplex_adapter("telnyx", TelnyxDuplexMediaAdapter)
        with patch(
            "app.integrations.registry.resolve_telephony_adapter_name",
            return_value="telnyx",
        ):
            with patch.object(TelnyxDuplexMediaAdapter, "is_configured", return_value=True):
                adapter = get_duplex_media_adapter()
                self.assertIsInstance(adapter, TelnyxDuplexMediaAdapter)


class _MockStt:
    async def transcribe_stream(self, audio_stream, *, language: str = "en-US"):
        async for _ in audio_stream:
            yield TranscriptChunk(text="book appointment", is_final=True, speaker="caller")
            break


if __name__ == "__main__":
    unittest.main()
