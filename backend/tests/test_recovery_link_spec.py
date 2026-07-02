"""Specification: recovery link delivery — SMS first when functional."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.ai.receptionist_tools import ReceptionistToolsImpl
from app.services.recovery_delivery_service import RecoveryDeliveryService
from app.voice.session_state import VoiceSessionState
from tests.helpers import fresh_voice_session, sample_business


def _voice_tools(state: VoiceSessionState) -> ReceptionistToolsImpl:
    db = MagicMock()
    notifications = MagicMock()
    business = sample_business()
    with patch.object(VoiceSessionState, "load", return_value=state):
        tools = ReceptionistToolsImpl(
            db,
            business,
            notifications,
            call_log_id="call-recovery-1",
            voice_mode=True,
        )
    return tools


class RecoveryDeliverySpecification(unittest.TestCase):
    def test_sms_first_agent_message_when_text_sent(self) -> None:
        message = RecoveryDeliveryService.agent_message_for_web_chat(
            continue_url="http://localhost:3000/continue/tok",
            standalone_url="http://localhost:3000/chat/plumber",
            delivery={
                "sms_sent": True,
                "email_sent": False,
                "sms_functional": True,
            },
        )
        self.assertIn("text message", message.lower())

    def test_web_fallback_message_when_sms_not_configured(self) -> None:
        message = RecoveryDeliveryService.agent_message_for_web_chat(
            continue_url="http://localhost:3000/continue/tok",
            standalone_url="http://localhost:3000/chat/plumber",
            delivery={
                "sms_sent": False,
                "email_sent": False,
                "sms_functional": False,
            },
        )
        self.assertIn("web chat", message.lower())


class RecoveryLinkSmsFirstSpecification(unittest.IsolatedAsyncioTestCase):
    async def test_blocks_duplicate_recovery_link(self) -> None:
        state = fresh_voice_session()
        state.recovery_link_sent_this_call = True
        tools = _voice_tools(state)

        result = await tools.send_web_chat_link(email="caller@example.com")
        self.assertFalse(result.success)
        self.assertIn("already sent", result.message.lower())

    @patch("app.services.business_slug_service.BusinessSlugService.ensure_unique_slug")
    @patch("app.services.web_continuation_service.WebContinuationService.create_for_call")
    @patch("app.services.recovery_delivery_service.RecoveryDeliveryService.deliver_web_chat_link")
    async def test_web_chat_link_uses_recovery_delivery(
        self,
        mock_deliver,
        mock_create,
        _mock_slug,
    ) -> None:
        state = fresh_voice_session()
        tools = _voice_tools(state)
        call = MagicMock()
        call.id = "call-recovery-1"
        tools.db.query.return_value.filter.return_value.first.return_value = call
        tools.business.public_slug = "joes-plumbing"
        tools.notifications.is_sms_functional.return_value = True

        mock_create.return_value = {
            "continue_url": "http://localhost:3000/continue/tok-1",
            "standalone_chat_url": "http://localhost:3000/chat/plumber",
            "link_created": True,
        }
        mock_deliver.return_value = {
            "sms_sent": True,
            "email_sent": False,
            "sms_functional": True,
            "delivery_strategy": "sms_first",
        }

        result = await tools.send_web_chat_link(email="caller@example.com")

        self.assertTrue(result.success)
        self.assertTrue(result.data.get("sms_sent"))
        mock_deliver.assert_called_once()
        self.assertIn("text message", result.message.lower())

    @patch("app.services.address_confirmation_service.AddressConfirmationService.create_and_send_link")
    async def test_address_link_accepts_email(self, mock_send) -> None:
        state = fresh_voice_session()
        tools = _voice_tools(state)
        call = MagicMock()
        call.id = "call-recovery-1"
        tools.db.query.return_value.filter.return_value.first.return_value = call

        mock_send.return_value = {
            "sent": True,
            "link_created": True,
            "url": "http://localhost:3000/confirm-address/tok",
            "email_sent": True,
            "sms_sent": False,
        }

        result = await tools.send_address_confirmation_link(
            customer_name="Jane Doe",
            email="jane@example.com",
        )

        self.assertTrue(result.success)
        self.assertTrue(state.recovery_link_sent_this_call)
        mock_send.assert_called_once()
        self.assertEqual(mock_send.call_args.kwargs.get("email"), "jane@example.com")


if __name__ == "__main__":
    unittest.main()
