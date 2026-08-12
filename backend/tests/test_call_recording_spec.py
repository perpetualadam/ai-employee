"""Specification: platform-agnostic call recording + inbound SMS audit."""

from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.domain.recording import (
    RECORDING_DISCLOSURE,
    greeting_with_recording_notice,
    supports_call_recording,
)
from app.integrations.adapters.call_recording import (
    PlivoCallRecordingAdapter,
    TexmlTwimlCallRecordingAdapter,
    UnsupportedCallRecordingAdapter,
    VonageCallRecordingAdapter,
    build_call_recording_adapter,
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

    def test_supported_providers_include_major_cpaas(self) -> None:
        for name in ("telnyx", "twilio", "signalwire", "vonage", "plivo"):
            self.assertTrue(supports_call_recording(name), name)
        self.assertFalse(supports_call_recording("voipms"))


class RecordingAdapterSpecification(unittest.TestCase):
    def test_texml_injects_start_recording(self) -> None:
        adapter = TexmlTwimlCallRecordingAdapter("telnyx")
        markup = '<?xml version="1.0"?><Response><Say>Hi</Say></Response>'
        result = adapter.inject_recording(
            markup,
            base_url="https://example.com",
            call_log_id="11111111-1111-1111-1111-111111111111",
        )
        self.assertIn("<Start>", result)
        self.assertIn("<Recording", result)
        self.assertIn("recording-status?", result)
        self.assertIn('channels="dual"', result)

    def test_vonage_injects_async_record_action(self) -> None:
        adapter = VonageCallRecordingAdapter()
        markup = json.dumps([{"action": "talk", "text": "Hi"}])
        result = json.loads(
            adapter.inject_recording(
                markup,
                base_url="https://example.com",
                call_log_id="11111111-1111-1111-1111-111111111111",
            )
        )
        self.assertEqual(result[0]["action"], "record")
        self.assertEqual(result[0]["channels"], 2)
        self.assertTrue(result[0]["eventUrl"][0].endswith("recording-status?call_log_id=11111111-1111-1111-1111-111111111111"))
        self.assertEqual(result[1]["action"], "talk")

    def test_plivo_injects_record_session(self) -> None:
        adapter = PlivoCallRecordingAdapter()
        markup = '<?xml version="1.0"?><Response><Speak>Hi</Speak></Response>'
        result = adapter.inject_recording(
            markup,
            base_url="https://example.com",
            call_log_id="11111111-1111-1111-1111-111111111111",
        )
        self.assertIn('recordSession="true"', result)
        self.assertIn("callbackUrl=", result)
        self.assertIn("<Speak>Hi</Speak>", result)

    def test_unsupported_provider_is_noop(self) -> None:
        adapter = UnsupportedCallRecordingAdapter("voipms")
        markup = "ok"
        self.assertFalse(adapter.supports_inline_recording())
        self.assertEqual(
            adapter.inject_recording(markup, base_url="https://x", call_log_id="y"),
            markup,
        )

    def test_facade_routes_to_provider_adapters(self) -> None:
        telnyx = with_call_recording(
            '<?xml version="1.0"?><Response><Say>Hi</Say></Response>',
            base_url="https://example.com",
            call_log_id="11111111-1111-1111-1111-111111111111",
            provider="twilio",
            enabled=True,
        )
        self.assertIn("<Recording", telnyx)

        vonage = with_call_recording(
            json.dumps([{"action": "talk", "text": "Hi"}]),
            base_url="https://example.com",
            call_log_id="11111111-1111-1111-1111-111111111111",
            provider="vonage",
            enabled=True,
        )
        self.assertEqual(json.loads(vonage)[0]["action"], "record")

        skipped = with_call_recording(
            "ok",
            base_url="https://example.com",
            call_log_id="11111111-1111-1111-1111-111111111111",
            provider="voipms",
            enabled=True,
        )
        self.assertEqual(skipped, "ok")

    def test_normalize_webhooks_across_providers(self) -> None:
        texml = build_call_recording_adapter("signalwire").normalize_webhook(
            {
                "RecordingStatus": "completed",
                "RecordingUrl": "https://cdn.example/a.mp3",
                "RecordingSid": "RE1",
                "RecordingDuration": "12",
            }
        )
        self.assertEqual(texml.status, "completed")
        self.assertEqual(texml.recording_url, "https://cdn.example/a.mp3")

        vonage = build_call_recording_adapter("vonage").normalize_webhook(
            {
                "recording_url": "https://api.nexmo.com/v1/files/abc",
                "recording_uuid": "rec-1",
                "status": "ok",
            }
        )
        self.assertEqual(vonage.status, "completed")
        self.assertEqual(vonage.recording_id, "rec-1")

        plivo = build_call_recording_adapter("plivo").normalize_webhook(
            {
                "RecordUrl": "https://media.plivo.com/r.mp3",
                "RecordingID": "p-1",
                "RecordingDuration": "33",
            }
        )
        self.assertEqual(plivo.recording_url, "https://media.plivo.com/r.mp3")
        self.assertEqual(plivo.duration_seconds, 33)


class CallRecordingServiceSpecification(unittest.TestCase):
    def test_stores_provider_recording_on_completed_callback(self) -> None:
        call_id = str(uuid4())
        call = MagicMock()
        call.id = call_id
        call.business_id = str(uuid4())
        call.provider = "vonage"
        call.recording_status = "started"
        call.recording_storage_key = None

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = call

        storage = MagicMock()
        storage.upload.return_value = MagicMock(key=f"recordings/{call.business_id}/{call_id}/r1.mp3")

        adapter = MagicMock()
        adapter.provider_name = "vonage"
        adapter.normalize_webhook.return_value = MagicMock(
            status="completed",
            recording_url="https://provider.example/rec.mp3",
            recording_id="r1",
            duration_seconds=42,
        )
        adapter.download_recording.return_value = (b"ID3fake", "audio/mpeg")

        with patch(
            "app.services.call_recording_service.get_call_recording_adapter",
            return_value=adapter,
        ):
            result = CallRecordingService.handle_recording_status(
                db,
                call_log_id=call_id,
                params={"recording_url": "https://provider.example/rec.mp3"},
                provider="vonage",
                storage=storage,
            )

        self.assertIs(result, call)
        self.assertEqual(call.recording_status, "stored")
        self.assertEqual(call.recording_duration_seconds, 42)
        storage.upload.assert_called_once()
        adapter.download_recording.assert_called_once_with("https://provider.example/rec.mp3")
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
            if model.__name__ in {"Customer", "Appointment", "Business"}:
                q = MagicMock()
                q.filter.return_value.first.return_value = None
                q.filter.return_value.order_by.return_value.first.return_value = None
                return q
            return MagicMock()

        db = MagicMock()
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
                    provider="plivo",
                    external_id="msg-1",
                    raw_payload={"from": "+15551234567", "text": "Hello"},
                )
            )

        log_service.record_inbound.assert_called_once()
        kwargs = log_service.record_inbound.call_args.kwargs
        self.assertEqual(kwargs["provider"], "plivo")
        self.assertEqual(kwargs["body"], "Hello")
        self.assertEqual(kwargs["business_id"], business.id)


if __name__ == "__main__":
    unittest.main()
