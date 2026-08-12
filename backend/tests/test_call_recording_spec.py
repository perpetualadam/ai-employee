"""Specification: hybrid call recording + inbound SMS audit for owner review."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.domain.recording import (
    RECORDING_DISCLOSURE,
    greeting_with_recording_notice,
    supports_xml_call_recording,
)
from app.models.enums import CallDirection, CallStatus, ConversationChannel
from app.services.call_recording_service import CallRecordingService
from app.services.conversation_service import ConversationService
from app.voice.recording_markup import with_call_recording


class RecordingDomainSpecification(unittest.TestCase):
    def test_greeting_prefaces_disclosure_when_enabled(self) -> None:
        text = greeting_with_recording_notice(
            "Thank you for calling Acme.",
            recording_enabled=True,
        )
        self.assertTrue(text.startswith(RECORDING_DISCLOSURE))
        self.assertIn("Acme", text)

    def test_greeting_unchanged_when_disabled(self) -> None:
        text = greeting_with_recording_notice(
            "Thank you for calling Acme.",
            recording_enabled=False,
        )
        self.assertEqual(text, "Thank you for calling Acme.")

    def test_xml_providers_support_recording(self) -> None:
        self.assertTrue(supports_xml_call_recording("telnyx"))
        self.assertTrue(supports_xml_call_recording("twilio"))
        self.assertFalse(supports_xml_call_recording("vonage"))


class RecordingMarkupSpecification(unittest.TestCase):
    def test_injects_start_recording_into_texml(self) -> None:
        markup = '<?xml version="1.0"?><Response><Say>Hi</Say></Response>'
        result = with_call_recording(
            markup,
            base_url="https://example.com",
            call_log_id="11111111-1111-1111-1111-111111111111",
            provider="telnyx",
            enabled=True,
        )
        self.assertIn("<Start>", result)
        self.assertIn("<Recording", result)
        self.assertIn("recording-status?", result)
        self.assertIn("channels=\"dual\"", result)

    def test_skips_injection_when_disabled_or_unsupported(self) -> None:
        markup = '<?xml version="1.0"?><Response><Say>Hi</Say></Response>'
        self.assertEqual(
            with_call_recording(
                markup,
                base_url="https://example.com",
                call_log_id="11111111-1111-1111-1111-111111111111",
                provider="telnyx",
                enabled=False,
            ),
            markup,
        )
        self.assertEqual(
            with_call_recording(
                markup,
                base_url="https://example.com",
                call_log_id="11111111-1111-1111-1111-111111111111",
                provider="vonage",
                enabled=True,
            ),
            markup,
        )


class CallRecordingServiceSpecification(unittest.TestCase):
    def test_stores_provider_recording_on_completed_callback(self) -> None:
        call_id = str(uuid4())
        call = MagicMock()
        call.id = call_id
        call.business_id = str(uuid4())
        call.recording_status = "started"
        call.recording_storage_key = None

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = call

        storage = MagicMock()
        storage.upload.return_value = MagicMock(key=f"recordings/{call.business_id}/{call_id}/r1.mp3")

        with patch.object(
            CallRecordingService,
            "_download_recording",
            return_value=(b"ID3fake", "audio/mpeg"),
        ):
            result = CallRecordingService.handle_recording_status(
                db,
                call_log_id=call_id,
                params={
                    "RecordingStatus": "completed",
                    "RecordingUrl": "https://provider.example/rec.mp3",
                    "RecordingSid": "r1",
                    "RecordingDuration": "42",
                },
                storage=storage,
            )

        self.assertIs(result, call)
        self.assertEqual(call.recording_status, "stored")
        self.assertEqual(call.recording_duration_seconds, 42)
        storage.upload.assert_called_once()
        db.commit.assert_called()


class ConversationRecordingSurfaceSpecification(unittest.TestCase):
    def test_detail_includes_recording_and_sms_audit(self) -> None:
        call_id = str(uuid4())
        biz_id = str(uuid4())
        call = MagicMock()
        call.id = call_id
        call.business_id = biz_id
        call.customer_id = None
        call.channel = ConversationChannel.VOICE
        call.status = CallStatus.COMPLETED
        call.caller_phone = "+15551234567"
        call.duration_seconds = 90
        call.summary = "Leak reported"
        call.ai_summary = "Customer reported a kitchen leak"
        call.escalated = False
        call.transcript = None
        call.conversation_history = [
            {"role": "user", "content": "I have a leak"},
            {"role": "assistant", "content": "I can help"},
        ]
        call.created_at = datetime.now(UTC)
        call.recording_status = "stored"
        call.recording_storage_key = f"recordings/{biz_id}/{call_id}/r1.mp3"
        call.recording_content_type = "audio/mpeg"
        call.recording_duration_seconds = 90

        sms = MagicMock()
        sms.id = str(uuid4())
        sms.direction = CallDirection.INBOUND
        sms.from_number = "+15551234567"
        sms.to_number = "+15557654321"
        sms.body = "123 Main St"
        sms.provider = "telnyx"
        sms.sent = True
        sms.created_at = call.created_at

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = call
        activities_query = MagicMock()
        activities_query.filter.return_value.order_by.return_value.all.return_value = []
        sms_query = MagicMock()
        sms_query.filter.return_value.filter.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            sms
        ]

        def query_side_effect(model):
            if model.__name__ == "CallLog":
                q = MagicMock()
                q.filter.return_value.first.return_value = call
                return q
            if model.__name__ == "AIActivityLog":
                return activities_query
            if model.__name__ == "SmsLog":
                return sms_query
            if model.__name__ == "Customer":
                q = MagicMock()
                q.filter.return_value.first.return_value = None
                return q
            if model.__name__ == "Appointment":
                q = MagicMock()
                q.filter.return_value.order_by.return_value.first.return_value = None
                return q
            if model.__name__ == "Business":
                q = MagicMock()
                q.filter.return_value.first.return_value = None
                return q
            return MagicMock()

        db.query.side_effect = query_side_effect

        with patch("app.services.conversation_service.get_settings") as settings_mock:
            settings_mock.return_value = MagicMock(public_api_url="https://api.example.com")
            detail = ConversationService.get_conversation(db, biz_id, call_id)

        self.assertIsNotNone(detail)
        assert detail is not None
        self.assertTrue(detail.recording.available)
        self.assertIn("/recording", detail.recording.playback_url or "")
        self.assertEqual(len(detail.sms_messages), 1)
        self.assertEqual(detail.sms_messages[0].body, "123 Main St")


class InboundSmsAuditSpecification(unittest.TestCase):
    def test_handle_inbound_persists_sms_log(self) -> None:
        import asyncio

        from app.services.sms_service import SmsService

        db = MagicMock()
        business = MagicMock()
        business.id = str(uuid4())
        business.name = "Acme Plumbing"
        business.country = "US"
        business.phone_number = "+15557654321"

        with (
            patch("app.services.sms_service.find_business_by_phone", return_value=business),
            patch("app.plugins.publishers.publish_sms_received"),
            patch("app.services.sms_service.SubscriptionService.get_access_denial_reason", return_value=None),
            patch.object(SmsService, "_find_active_session", return_value=None),
            patch.object(SmsService, "_try_confirm_address_via_text", return_value=False),
            patch("app.services.sms_service.NotificationService") as notify_cls,
            patch("app.services.sms_log_service.SmsLogService") as log_cls,
        ):
            notify_cls.return_value.send_sms.return_value = {"sent": True}
            log_service = MagicMock()
            log_cls.return_value = log_service

            asyncio.run(
                SmsService.handle_inbound(
                    db,
                    "+15551234567",
                    "+15557654321",
                    "Hello",
                    provider="telnyx",
                    external_id="msg-1",
                    raw_payload={"from": "+15551234567", "text": "Hello"},
                )
            )

        log_service.record_inbound.assert_called_once()
        kwargs = log_service.record_inbound.call_args.kwargs
        self.assertEqual(kwargs["provider"], "telnyx")
        self.assertEqual(kwargs["body"], "Hello")
        self.assertEqual(kwargs["business_id"], business.id)


if __name__ == "__main__":
    unittest.main()
