"""Specification: unified inbox, address recovery, SMS recovery, booking email."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.domain.conversation import channel_label, infer_channel
from app.models.enums import CallDirection, CallStatus, ConversationChannel
from app.services.address_confirmation_service import AddressConfirmationService
from app.schemas import ConversationLeadCard
from app.services.conversation_service import ConversationService
from app.services.conversation_summary_service import ConversationSummaryService
from app.services.notification_service import NotificationService
from app.services.sms_service import SmsService
from app.voice.messaging_webhook import parse_inbound_sms_event


def _sample_call(**kwargs):
    call = MagicMock()
    call.id = kwargs.get("id", str(uuid4()))
    call.business_id = kwargs.get("business_id", "biz-1")
    call.customer_id = kwargs.get("customer_id")
    call.external_call_id = kwargs.get("external_call_id", "CA123")
    call.channel = kwargs.get("channel", ConversationChannel.VOICE)
    call.caller_phone = kwargs.get("caller_phone", "+15551234567")
    call.status = kwargs.get("status", CallStatus.COMPLETED)
    call.duration_seconds = kwargs.get("duration_seconds", 120)
    call.summary = kwargs.get("summary", "Appointment booked on voice call")
    call.ai_summary = kwargs.get("ai_summary")
    call.escalated = kwargs.get("escalated", False)
    call.conversation_history = kwargs.get(
        "conversation_history",
        [
            {"role": "user", "content": "I have a kitchen leak"},
            {"role": "assistant", "content": "May I have your name?"},
            {"role": "user", "content": "John Smith"},
        ],
    )
    call.created_at = kwargs.get("created_at", datetime.now(UTC))
    call.recording_status = kwargs.get("recording_status")
    call.recording_storage_key = kwargs.get("recording_storage_key")
    call.recording_content_type = kwargs.get("recording_content_type")
    call.recording_duration_seconds = kwargs.get("recording_duration_seconds")
    return call


class BusinessLookupSpecification(unittest.TestCase):
    def test_finds_business_by_configured_phone(self) -> None:
        from app.voice.call_service import find_business_by_phone

        db = MagicMock()
        biz = MagicMock()
        biz.id = "047694b9-6e63-4bbf-b186-280e0e23e968"
        biz.phone_number = "+13802738396"
        db.query.return_value.filter.return_value.all.return_value = [biz]

        found = find_business_by_phone(db, "+13802738396")
        self.assertIsNotNone(found)
        self.assertEqual(found.id, biz.id)


class ConversationChannelSpecification(unittest.TestCase):
    def test_voice_call_infers_voice_channel(self) -> None:
        call = _sample_call(channel=ConversationChannel.VOICE, external_call_id="CA1")
        self.assertEqual(infer_channel(call), ConversationChannel.VOICE)
        self.assertEqual(channel_label(infer_channel(call)), "Phone call")

    def test_dashboard_preview_infers_web_chat(self) -> None:
        call = _sample_call(
            channel=ConversationChannel.WEB_CHAT,
            external_call_id=None,
            caller_phone="text-chat",
        )
        self.assertEqual(infer_channel(call), ConversationChannel.WEB_CHAT)


class ConversationSummarySpecification(unittest.TestCase):
    def test_should_summarize_after_two_user_turns(self) -> None:
        call = _sample_call()
        self.assertTrue(ConversationSummaryService.should_summarize(call))

    def test_should_not_summarize_when_already_done(self) -> None:
        call = _sample_call(ai_summary="Already summarized.")
        self.assertFalse(ConversationSummaryService.should_summarize(call))


class AddressConfirmationSpecification(unittest.IsolatedAsyncioTestCase):
    async def test_send_address_link_requires_valid_caller_phone(self) -> None:
        db = MagicMock()
        business = MagicMock()
        business.id = "biz-1"
        business.name = "ABC Plumbing"
        call = _sample_call(caller_phone="unknown")

        result = AddressConfirmationService.create_and_send_link(db, business, call)
        self.assertFalse(result["sent"])
        self.assertFalse(result["link_created"])
        self.assertIn("email", result["error"].lower())

    async def test_send_address_link_via_email_only(self) -> None:
        db = MagicMock()
        business = MagicMock()
        business.id = "biz-1"
        business.name = "ABC Plumbing"
        call = _sample_call(caller_phone="unknown")

        notifications = MagicMock()
        notifications.send_email.return_value = {"sent": True, "provider": "dev_log"}

        with patch(
            "app.services.address_confirmation_service.NotificationService",
            return_value=notifications,
        ):
            result = AddressConfirmationService.create_and_send_link(
                db,
                business,
                call,
                customer_name="John Smith",
                email="john@example.com",
            )

        self.assertTrue(result["sent"])
        self.assertTrue(result["email_sent"])
        self.assertFalse(result.get("sms_sent"))
        notifications.send_email.assert_called_once()

    async def test_confirm_address_updates_customer_and_call(self) -> None:
        db = MagicMock()
        token = MagicMock()
        token.business_id = "biz-1"
        token.call_log_id = "call-1"
        token.customer_id = "cust-1"
        token.customer_name = "John Smith"
        token.confirmed_at = None
        token.expires_at = datetime.now(UTC) + timedelta(hours=1)
        token.token = "tok-abc"

        business = MagicMock()
        business.id = "biz-1"
        call = _sample_call(id="call-1", caller_phone="+15551234567")
        customer = MagicMock()
        customer.id = "cust-1"

        with patch.object(
            AddressConfirmationService,
            "get_public_token",
            return_value=token,
        ):
            with patch(
                "app.services.address_confirmation_service.CustomerService.get_customer",
                return_value=customer,
            ):
                with patch(
                    "app.services.address_confirmation_service.CustomerService.update_customer",
                    return_value=customer,
                ) as update_mock:
                    ok, msg = AddressConfirmationService.confirm_address(
                        db,
                        "tok-abc",
                        "124 Wood Street, Columbus, OH 43215",
                    )

        self.assertTrue(ok)
        self.assertIn("43215", msg)
        update_mock.assert_called_once()
        self.assertIsNotNone(token.confirmed_at)


class BookingEmailSpecification(unittest.TestCase):
    def test_skips_email_when_customer_has_no_email(self) -> None:
        db = MagicMock()
        business = MagicMock()
        business.name = "ABC Plumbing"
        business.timezone = "America/New_York"
        customer = MagicMock()
        customer.email = None
        appt = MagicMock()

        svc = NotificationService(db, business)
        result = svc.send_booking_confirmation_email(customer, appt)
        self.assertFalse(result["sent"])
        self.assertTrue(result.get("skipped"))

    def test_sends_email_when_smtp_not_configured_logs_dev_mode(self) -> None:
        db = MagicMock()
        business = MagicMock()
        business.name = "ABC Plumbing"
        business.timezone = "America/New_York"
        customer = MagicMock()
        customer.name = "John"
        customer.email = "john@example.com"
        customer.address = "124 Main St"
        appt = MagicMock()
        appt.service_type = "Leak repair"
        appt.start_time = datetime(2026, 7, 2, 14, 0, tzinfo=UTC)

        svc = NotificationService(db, business)
        dev_provider = MagicMock()
        dev_provider.provider_name = "dev_log"
        dev_provider.is_configured.return_value = False
        dev_provider.send_email.return_value = {"sent": True, "provider": "dev_log"}
        with patch(
            "app.services.notification_service.get_email_provider",
            return_value=dev_provider,
        ):
            result = svc.send_booking_confirmation_email(customer, appt)
        self.assertTrue(result["sent"])
        self.assertEqual(result["provider"], "dev_log")


class SmsRecoverySpecification(unittest.IsolatedAsyncioTestCase):
    async def test_inbound_sms_continues_active_voice_session(self) -> None:
        db = MagicMock()
        business = MagicMock()
        business.id = "biz-1"
        business.name = "ABC Plumbing"
        call = _sample_call(status=CallStatus.IN_PROGRESS)

        with patch(
            "app.services.sms_service.find_business_by_phone",
            return_value=business,
        ):
            with patch(
                "app.services.sms_service.SubscriptionService.get_access_denial_reason",
                return_value=None,
            ):
                with patch.object(SmsService, "_find_active_session", return_value=call):
                    with patch(
                        "app.services.sms_service.get_ai_provider",
                    ):
                        with patch(
                            "app.services.sms_service.ReceptionistAgent"
                        ) as agent_cls:
                            agent = agent_cls.return_value
                            agent.chat = AsyncMock(
                                return_value={
                                    "reply": "Thanks, got your address.",
                                    "tools_used": [],
                                    "escalated": False,
                                }
                            )
                            with patch(
                                "app.services.sms_service.get_settings"
                            ) as settings_mock:
                                settings_mock.return_value.groq_api_key = "test-key"
                                with patch(
                                    "app.services.sms_service.NotificationService"
                                ) as notify_cls:
                                    notify = notify_cls.return_value
                                    await SmsService.handle_inbound(
                                        db,
                                        "+15551234567",
                                        "+15559876543",
                                        "124 Wood Street, Columbus, OH 43215",
                                    )
                                    agent.chat.assert_awaited_once()
                                    notify.send_sms.assert_called()

    async def test_cold_inbound_sms_directs_caller_to_phone(self) -> None:
        db = MagicMock()
        business = MagicMock()
        business.id = "biz-1"
        business.name = "ABC Plumbing"

        with patch(
            "app.services.sms_service.find_business_by_phone",
            return_value=business,
        ):
            with patch(
                "app.services.sms_service.SubscriptionService.get_access_denial_reason",
                return_value=None,
            ):
                with patch.object(SmsService, "_find_active_session", return_value=None):
                    with patch.object(
                        SmsService, "_try_confirm_address_via_text", return_value=False
                    ):
                        with patch(
                            "app.services.sms_service.NotificationService"
                        ) as notify_cls:
                            notify = notify_cls.return_value
                            await SmsService.handle_inbound(
                                db,
                                "+15551234567",
                                "+15559876543",
                                "I need a plumber",
                            )
                            notify.send_sms.assert_called_once()
                            args = notify.send_sms.call_args[0]
                            self.assertIn("call us", args[1].lower())


class MessagingWebhookSpecification(unittest.IsolatedAsyncioTestCase):
    async def test_ignores_non_message_events(self) -> None:
        request = MagicMock()
        request.body = AsyncMock(
            return_value=b'{"data":{"event_type":"message.sent","payload":{}}}'
        )
        request.headers = {}

        with patch("app.voice.messaging_webhook.get_settings") as settings_mock:
            settings_mock.return_value.telnyx_public_key = ""
            settings_mock.return_value.debug = True
            result = await parse_inbound_sms_event(request)
        self.assertIsNone(result)


class ConversationDetailSpecification(unittest.TestCase):
    def test_get_conversation_exposes_messages_and_transcript(self) -> None:
        db = MagicMock()
        call = _sample_call(
            conversation_history=[
                {"role": "user", "content": "No hot water"},
                {"role": "assistant", "content": "May I have your name?"},
            ],
        )
        call.transcript = "USER: No hot water\nASSISTANT: May I have your name?"

        db.query.return_value.filter.return_value.first.return_value = call
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

        with (
            patch.object(
                ConversationService,
                "_build_lead_card",
                return_value=ConversationLeadCard(),
            ),
            patch.object(
                ConversationService,
                "_sms_messages_for_call",
                return_value=[],
            ),
            patch("app.services.conversation_service.get_settings") as settings_mock,
        ):
            settings_mock.return_value = MagicMock(public_api_url="https://api.example.com")
            detail = ConversationService.get_conversation(db, "biz-1", call.id)

        self.assertIsNotNone(detail)
        assert detail is not None
        self.assertEqual(len(detail.messages), 2)
        self.assertEqual(detail.messages[0].content, "No hot water")
        self.assertEqual(detail.transcript, call.transcript)
        self.assertFalse(detail.recording.available)


class OwnerEscalationEmailSpecification(unittest.TestCase):
    def test_notify_owner_falls_back_to_email_when_sms_fails(self) -> None:
        db = MagicMock()
        business = MagicMock()
        business.id = "biz-1"
        business.name = "ABC Plumbing"
        business.owner_id = "owner-1"
        business.escalation_phone = "+15559876543"
        business.phone_number = None

        owner = MagicMock()
        owner.email = "owner@example.com"
        db.query.return_value.filter.return_value.first.return_value = owner

        svc = NotificationService(db, business)
        with patch.object(svc, "send_sms", return_value={"sent": False, "provider": "telnyx"}):
            with patch.object(
                svc,
                "send_email",
                return_value={"sent": True, "provider": "smtp"},
            ) as email_mock:
                notified = svc.notify_owner_escalation("Customer wants a person", "+15551234567")

        self.assertTrue(notified)
        email_mock.assert_called_once()
        self.assertEqual(email_mock.call_args[0][0], "owner@example.com")


class SmtpEmailSpecification(unittest.TestCase):
    def test_send_email_uses_smtp_when_configured(self) -> None:
        db = MagicMock()
        business = MagicMock()
        svc = NotificationService(db, business)

        smtp_provider = MagicMock()
        smtp_provider.provider_name = "smtp"
        smtp_provider.is_configured.return_value = True
        smtp_provider.send_email.return_value = {
            "sent": True,
            "provider": "smtp",
            "email": "john@example.com",
            "subject": "Hello",
        }
        with patch(
            "app.services.notification_service.get_email_provider",
            return_value=smtp_provider,
        ):
            result = svc.send_email("john@example.com", "Hello", "Body text")

        self.assertTrue(result["sent"])
        self.assertEqual(result["provider"], "smtp")
        smtp_provider.send_email.assert_called_once_with(
            "john@example.com", "Hello", "Body text"
        )
