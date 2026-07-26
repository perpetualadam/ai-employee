"""Twilio and Vonage in-call REST control — hangup/transfer markup push."""

from __future__ import annotations

import asyncio
import json
import unittest
from unittest.mock import MagicMock, patch

from app.integrations.adapters.twilio_duplex import TwilioDuplexMediaAdapter
from app.integrations.adapters.twilio_stubs import TwilioVoiceCallControl
from app.integrations.adapters.vonage_duplex import VonageDuplexMediaAdapter
from app.integrations.adapters.vonage_stubs import VonageVoiceCallControl
from app.voice.duplex.contracts import MediaStreamBindContext


class TwilioVonageCallControlSpecification(unittest.TestCase):
    def test_twilio_push_markup_updates_call_via_rest(self) -> None:
        adapter = TwilioDuplexMediaAdapter()

        async def _run() -> None:
            with patch("app.voice.twilio_client.update_call_twiml") as update:
                await adapter.push_markup("CA123", "<Response><Hangup/></Response>")
                update.assert_called_once_with("CA123", "<Response><Hangup/></Response>")

        asyncio.run(_run())

    def test_vonage_push_markup_updates_call_via_rest(self) -> None:
        adapter = VonageDuplexMediaAdapter()

        async def _run() -> None:
            await adapter.bind_media_websocket(
                MagicMock(),
                context=MediaStreamBindContext(call_control_id="uuid-99"),
            )
            ncco = adapter.build_hangup_response("Goodbye")
            with patch("app.voice.vonage_client.update_call_ncco") as update:
                await adapter.push_markup("uuid-99", ncco)
                update.assert_called_once_with("uuid-99", ncco)

        asyncio.run(_run())

    def test_twilio_builds_twiml_hangup_and_transfer(self) -> None:
        adapter = TwilioDuplexMediaAdapter()
        hangup = adapter.build_hangup_response("Thanks for calling", country="US")
        self.assertIn("<Hangup/>", hangup)
        self.assertIn("Thanks for calling", hangup)

        transfer = adapter.build_transfer_response("+15551234567", "Connecting you", country="US")
        self.assertIn("<Dial", transfer)
        self.assertIn("+15551234567", transfer)

    def test_vonage_builds_ncco_hangup_and_transfer(self) -> None:
        adapter = VonageDuplexMediaAdapter()
        hangup = json.loads(adapter.build_hangup_response("Goodbye"))
        self.assertEqual(hangup[-1]["action"], "hangup")

        transfer = json.loads(adapter.build_transfer_response("+15551234567", "Hold please"))
        self.assertEqual(transfer[0]["action"], "talk")
        self.assertEqual(transfer[1]["action"], "connect")

    def test_twilio_voice_control_transfer_uses_rest(self) -> None:
        control = TwilioVoiceCallControl()
        with patch.object(control, "is_configured", return_value=True):
            with patch("app.voice.twilio_client.update_call_twiml") as update:
                asyncio.run(control.transfer_call("CA555", "+15551234567"))
                update.assert_called_once()
                self.assertIn("<Dial", update.call_args[0][1])

    def test_vonage_voice_control_transfer_uses_rest(self) -> None:
        control = VonageVoiceCallControl()
        with patch.object(control, "is_configured", return_value=True):
            with patch("app.voice.vonage_client.update_call_ncco") as update:
                asyncio.run(control.transfer_call("uuid-55", "+15551234567"))
                update.assert_called_once_with("uuid-55", unittest.mock.ANY)
                payload = json.loads(update.call_args[0][1])
                self.assertEqual(payload[1]["action"], "connect")


if __name__ == "__main__":
    unittest.main()
