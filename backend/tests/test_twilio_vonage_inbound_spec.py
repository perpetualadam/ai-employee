"""Twilio and Vonage inbound gather/stream markup and webhook normalization."""

from __future__ import annotations

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.integrations.adapters.vonage_stubs import VonageVoiceWebhookAdapter
from app.providers.twilio.telephony import TwilioTelephonyProvider
from app.providers.vonage.telephony import VonageTelephonyProvider
from app.voice.stt.gather_stt import GatherSpeechSTT
from app.voice.voice_markup import TwilioVoiceMarkup, VonageVoiceMarkup


class TwilioVonageInboundSpecification(unittest.TestCase):
    def test_twilio_builds_gather_twiml(self) -> None:
        markup = TwilioVoiceMarkup()
        twiml = markup.build_say_and_gather(
            "How can I help?",
            "https://api.example.com",
            "call-log-1",
            call_sid="CA123",
            country="US",
        )
        self.assertIn("<Gather", twiml)
        self.assertIn('input="speech"', twiml)
        self.assertIn("/api/v1/voice/gather", twiml)
        self.assertIn("How can I help?", twiml)

    def test_vonage_builds_input_ncco(self) -> None:
        markup = VonageVoiceMarkup()
        ncco = json.loads(
            markup.build_say_and_gather(
                "How can I help?",
                "https://api.example.com",
                "call-log-1",
                call_sid="uuid-1",
                country="US",
            )
        )
        self.assertEqual(ncco[0]["action"], "talk")
        self.assertEqual(ncco[1]["action"], "input")
        self.assertIn("speech", ncco[1]["type"])
        self.assertIn("/api/v1/voice/gather", ncco[1]["eventUrl"][0])

    def test_vonage_webhook_normalizes_call_and_speech(self) -> None:
        adapter = VonageVoiceWebhookAdapter()
        request = MagicMock()
        request.headers = {"content-type": "application/json"}
        request.json = AsyncMock(
            return_value={
                "uuid": "uuid-77",
                "from": "+15551112222",
                "to": "+15553334444",
                "speech": {
                    "results": [{"text": "I need a plumber", "confidence": "0.91"}],
                },
            }
        )

        async def _run() -> dict[str, str]:
            return await adapter.parse_request(request)

        params = asyncio.run(_run())
        self.assertEqual(params["CallSid"], "uuid-77")
        self.assertEqual(params["From"], "+15551112222")
        self.assertEqual(params["To"], "+15553334444")
        self.assertEqual(params["SpeechResult"], "I need a plumber")
        self.assertEqual(params["Confidence"], "0.91")

    def test_gather_stt_reads_vonage_speech_params(self) -> None:
        speech, confidence = GatherSpeechSTT.extract_from_params(
            {"SpeechResult": "book an appointment", "Confidence": "0.88"}
        )
        self.assertEqual(speech, "book an appointment")
        self.assertEqual(confidence, "0.88")

    def test_twilio_telephony_answer_call_pushes_twiml(self) -> None:
        provider = TwilioTelephonyProvider()
        with patch.object(provider, "_require_configured"):
            with patch("app.voice.twilio_client.update_call_twiml") as update:
                asyncio.run(
                    provider.answer_call("CA999", {"texml": "<Response><Hangup/></Response>"})
                )
                update.assert_called_once_with("CA999", "<Response><Hangup/></Response>")

    def test_vonage_telephony_answer_call_pushes_ncco(self) -> None:
        provider = VonageTelephonyProvider()
        ncco = '[{"action":"talk","text":"Hello"},{"action":"hangup"}]'
        with patch.object(provider, "_require_configured"):
            with patch("app.voice.vonage_client.update_call_ncco") as update:
                asyncio.run(provider.answer_call("uuid-9", {"texml": ncco}))
                update.assert_called_once_with("uuid-9", ncco)

    def test_streaming_available_when_twilio_markup_configured(self) -> None:
        from app.services.voice_mode_service import VoiceModeService

        stt = MagicMock()
        stt.is_configured.return_value = True
        markup = MagicMock()
        markup.supports_streaming.return_value = True
        markup.is_configured.return_value = True
        with patch("app.services.voice_mode_service.get_settings") as settings_mock:
            settings_mock.return_value.voice_mode = "stream"
            with patch(
                "app.services.voice_mode_service.get_speech_to_text_plugin",
                return_value=stt,
            ):
                with patch(
                    "app.services.voice_mode_service.resolve_voice_markup",
                    return_value=markup,
                ):
                    self.assertTrue(VoiceModeService.streaming_available())
                    self.assertEqual(VoiceModeService.effective_mode(), "stream")


if __name__ == "__main__":
    unittest.main()
