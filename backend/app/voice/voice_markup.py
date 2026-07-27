"""Provider-native voice markup builders — TeXML, TwiML, and NCCO."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from html import escape
from urllib.parse import urlencode

from app.config import get_settings
from app.domain.telecom import resolve_voice_locale
from app.domain.trades.registry import resolve_trade_context
from app.models import Business
from app.voice import telnyx_client, twilio_client, vonage_client
from app.voice.texml_builder import (
    build_outbound_answer_texml,
    media_stream_url,
    public_ws_url,
)


class VoiceMarkupBuilder(ABC):
    content_type: str = "application/xml"

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        ...

    def supports_streaming(self) -> bool:
        return self.is_configured()

    @abstractmethod
    def build_greeting(
        self,
        business: Business,
        base_url: str,
        call_log_id: str,
        *,
        call_sid: str | None = None,
    ) -> str:
        ...

    @abstractmethod
    def build_say_and_gather(
        self,
        message: str,
        base_url: str,
        call_log_id: str,
        *,
        call_sid: str | None = None,
        country: str | None = None,
    ) -> str:
        ...

    @abstractmethod
    def build_hangup(self, message: str, *, country: str | None = None) -> str:
        ...

    @abstractmethod
    def build_transfer(
        self,
        escalation_phone: str,
        message: str | None = None,
        *,
        country: str | None = None,
    ) -> str:
        ...

    @abstractmethod
    def build_empty(self) -> str:
        ...

    def build_outbound_answer(
        self,
        business_name: str,
        escalation_phone: str | None,
        *,
        reason: str | None = None,
        country: str | None = None,
    ) -> str:
        return build_outbound_answer_texml(
            business_name,
            escalation_phone,
            reason=reason,
            country=country,
        )


def _voice_urls(base_url: str, call_log_id: str) -> dict[str, str]:
    prefix = f"{base_url.rstrip('/')}/api/v1/voice"
    params = urlencode({"call_log_id": call_log_id})
    return {
        "gather": f"{prefix}/gather?{params}",
        "status": f"{prefix}/status?{params}",
        "beep": f"{prefix}/beep.wav",
    }


def _say_xml(message: str, country: str | None) -> str:
    locale = resolve_voice_locale(country)
    text = escape(message, quote=False)
    return f'<Say voice="{locale.voice}" language="{locale.language}">{text}</Say>'


class TelnyxVoiceMarkup(VoiceMarkupBuilder):
    content_type = "application/xml"

    @property
    def provider_name(self) -> str:
        return "telnyx"

    def is_configured(self) -> bool:
        settings = get_settings()
        return bool(
            telnyx_client.is_telnyx_configured()
            and settings.telnyx_account_sid
            and settings.telnyx_texml_connection_id
        )

    def build_greeting(
        self,
        business: Business,
        base_url: str,
        call_log_id: str,
        *,
        call_sid: str | None = None,
    ) -> str:
        from app.voice.texml_builder import build_greeting

        return build_greeting(business, base_url, call_log_id, call_sid=call_sid)

    def build_say_and_gather(
        self,
        message: str,
        base_url: str,
        call_log_id: str,
        *,
        call_sid: str | None = None,
        country: str | None = None,
    ) -> str:
        from app.voice.texml_builder import build_say_and_gather

        return build_say_and_gather(
            message,
            base_url,
            call_log_id,
            call_sid=call_sid,
            country=country,
        )

    def build_hangup(self, message: str, *, country: str | None = None) -> str:
        from app.voice.texml_builder import build_hangup

        return build_hangup(message, country=country)

    def build_transfer(
        self,
        escalation_phone: str,
        message: str | None = None,
        *,
        country: str | None = None,
    ) -> str:
        from app.voice.texml_builder import build_transfer_texml

        return build_transfer_texml(escalation_phone, message, country=country)

    def build_empty(self) -> str:
        from app.voice.texml_builder import build_empty_response

        return build_empty_response()


class TwilioVoiceMarkup(VoiceMarkupBuilder):
    content_type = "application/xml"

    @property
    def provider_name(self) -> str:
        return "twilio"

    def is_configured(self) -> bool:
        return twilio_client.is_twilio_configured()

    def build_greeting(
        self,
        business: Business,
        base_url: str,
        call_log_id: str,
        *,
        call_sid: str | None = None,
    ) -> str:
        trade = resolve_trade_context(business)
        greeting = (
            f"Thank you for calling {business.name}. "
            "I'm the AI receptionist. "
            f"After the tone, tell me what's going on — for example {trade.voice_greeting_example}."
        )
        return self.build_say_and_gather(
            greeting,
            base_url,
            call_log_id,
            call_sid=call_sid,
            country=business.country,
        )

    def build_say_and_gather(
        self,
        message: str,
        base_url: str,
        call_log_id: str,
        *,
        call_sid: str | None = None,
        country: str | None = None,
    ) -> str:
        from app.services.voice_mode_service import VoiceModeService

        if call_sid and VoiceModeService.effective_mode() == "duplex":
            return self._build_say_and_duplex(message, base_url, call_log_id, call_sid, country=country)
        if call_sid and VoiceModeService.effective_mode() == "stream":
            return self._build_say_and_stream(message, base_url, call_log_id, call_sid, country=country)

        settings = get_settings()
        urls = _voice_urls(base_url, call_log_id)
        gather_url = escape(urls["gather"], quote=True)
        beep_url = escape(urls["beep"], quote=True)
        locale = resolve_voice_locale(country)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f"{_say_xml(message, country)}"
            f'<Play loop="1">{beep_url}</Play>'
            f'<Gather input="speech" action="{gather_url}" method="POST" '
            f'timeout="{settings.voice_gather_timeout}" '
            f'speechTimeout="{settings.voice_gather_speech_timeout}" '
            f'language="{locale.language}"/>'
            f"{_say_xml('I did not catch that. Goodbye!', country)}"
            "<Hangup/>"
            "</Response>"
        )

    def _build_say_and_duplex(
        self,
        message: str,
        base_url: str,
        call_log_id: str,
        call_sid: str,
        *,
        country: str | None,
    ) -> str:
        from app.voice.texml_builder import duplex_stream_url

        stream_url = escape(duplex_stream_url(call_log_id, call_sid), quote=True)
        beep_url = escape(_voice_urls(base_url, call_log_id)["beep"], quote=True)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f"{_say_xml(message, country)}"
            f'<Play loop="1">{beep_url}</Play>'
            f'<Connect><Stream url="{stream_url}" /></Connect>'
            '<Pause length="3600"/>'
            f"{_say_xml('Sorry, I did not hear anything. Goodbye!', country)}"
            "<Hangup/>"
            "</Response>"
        )

    def build_outbound_answer(
        self,
        business_name: str,
        escalation_phone: str | None,
        *,
        reason: str | None = None,
        country: str | None = None,
    ) -> str:
        intro = reason or f"Hi, this is {business_name} calling about your recent service request."
        if escalation_phone:
            return (
                '<?xml version="1.0" encoding="UTF-8"?>'
                "<Response>"
                f"{_say_xml(intro, country)}"
                f"{_say_xml('Connecting you now.', country)}"
                f'<Dial timeout="30"><Number>{escape(escalation_phone.strip(), quote=False)}</Number></Dial>'
                f"{_say_xml('Sorry, we could not connect you. We will try again soon.', country)}"
                "<Hangup/>"
                "</Response>"
            )
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f"{_say_xml(intro, country)}"
            f"{_say_xml('Please call us back at your convenience. Thank you.', country)}"
            "<Hangup/>"
            "</Response>"
        )

    def _build_say_and_stream(
        self,
        message: str,
        base_url: str,
        call_log_id: str,
        call_sid: str,
        *,
        country: str | None,
    ) -> str:
        stream_params = urlencode({"call_log_id": call_log_id, "call_sid": call_sid})
        stream_url = escape(public_ws_url(f"/api/v1/voice/stream?{stream_params}"), quote=True)
        beep_url = escape(_voice_urls(base_url, call_log_id)["beep"], quote=True)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f"{_say_xml(message, country)}"
            f'<Play loop="1">{beep_url}</Play>'
            f'<Connect><Stream url="{stream_url}" /></Connect>'
            "<Pause length=\"45\"/>"
            f"{_say_xml('Sorry, I did not hear anything. Goodbye!', country)}"
            "<Hangup/>"
            "</Response>"
        )

    def build_hangup(self, message: str, *, country: str | None = None) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f"<Response>{_say_xml(message, country)}<Hangup/></Response>"
        )

    def build_transfer(
        self,
        escalation_phone: str,
        message: str | None = None,
        *,
        country: str | None = None,
    ) -> str:
        msg = message or "Please hold while I connect you with a team member."
        phone = escape(escalation_phone.strip(), quote=False)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f"{_say_xml(msg, country)}"
            f'<Dial timeout="30"><Number>{phone}</Number></Dial>'
            f"{_say_xml('Sorry, no one is available right now. We will call you back shortly.', country)}"
            "<Hangup/>"
            "</Response>"
        )

    def build_empty(self) -> str:
        return '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'


class VonageVoiceMarkup(VoiceMarkupBuilder):
    content_type = "application/json"

    @property
    def provider_name(self) -> str:
        return "vonage"

    def is_configured(self) -> bool:
        return vonage_client.is_vonage_configured()

    def build_greeting(
        self,
        business: Business,
        base_url: str,
        call_log_id: str,
        *,
        call_sid: str | None = None,
    ) -> str:
        trade = resolve_trade_context(business)
        greeting = (
            f"Thank you for calling {business.name}. "
            "I'm the AI receptionist. "
            f"Tell me what's going on — for example {trade.voice_greeting_example}."
        )
        return self.build_say_and_gather(
            greeting,
            base_url,
            call_log_id,
            call_sid=call_sid,
            country=business.country,
        )

    def build_say_and_gather(
        self,
        message: str,
        base_url: str,
        call_log_id: str,
        *,
        call_sid: str | None = None,
        country: str | None = None,
    ) -> str:
        from app.services.voice_mode_service import VoiceModeService
        from app.voice.texml_builder import duplex_stream_url

        if call_sid and VoiceModeService.effective_mode() == "duplex":
            stream_url = duplex_stream_url(call_log_id, call_sid)
            return json.dumps(
                [
                    {"action": "talk", "text": message},
                    {
                        "action": "connect",
                        "endpoint": [
                            {
                                "type": "websocket",
                                "uri": stream_url,
                                "content-type": "audio/l16;rate=16000",
                            }
                        ],
                    },
                ]
            )
        if call_sid and VoiceModeService.effective_mode() == "stream":
            stream_url = media_stream_url(call_log_id, call_sid)
            return json.dumps(
                [
                    {"action": "talk", "text": message},
                    {
                        "action": "connect",
                        "endpoint": [
                            {
                                "type": "websocket",
                                "uri": stream_url,
                                "content-type": "audio/l16;rate=16000",
                            }
                        ],
                    },
                ]
            )

        gather_url = _voice_urls(base_url, call_log_id)["gather"]
        locale = resolve_voice_locale(country)
        return json.dumps(
            [
                {"action": "talk", "text": message},
                {
                    "action": "input",
                    "type": ["speech"],
                    "eventUrl": [gather_url],
                    "speech": {
                        "endOnSilence": get_settings().voice_gather_speech_timeout,
                        "language": locale.language,
                    },
                },
                {"action": "talk", "text": "I didn't catch that. Goodbye!"},
                {"action": "hangup"},
            ]
        )

    def build_hangup(self, message: str, *, country: str | None = None) -> str:
        del country
        return json.dumps([{"action": "talk", "text": message}, {"action": "hangup"}])

    def build_transfer(
        self,
        escalation_phone: str,
        message: str | None = None,
        *,
        country: str | None = None,
    ) -> str:
        del country
        msg = message or "Please hold while I connect you with a team member."
        return json.dumps(
            [
                {"action": "talk", "text": msg},
                {
                    "action": "connect",
                    "endpoint": [{"type": "phone", "number": escalation_phone.strip()}],
                },
            ]
        )

    def build_empty(self) -> str:
        return json.dumps([])

    def build_outbound_answer(
        self,
        business_name: str,
        escalation_phone: str | None,
        *,
        reason: str | None = None,
        country: str | None = None,
    ) -> str:
        del country
        intro = reason or f"Hi, this is {business_name} calling about your recent service request."
        actions: list[dict] = [{"action": "talk", "text": intro}]
        if escalation_phone:
            actions.append({"action": "talk", "text": "Connecting you now."})
            actions.append(
                {
                    "action": "connect",
                    "endpoint": [{"type": "phone", "number": escalation_phone.strip()}],
                }
            )
            actions.append(
                {"action": "talk", "text": "Sorry, we could not connect you. We will try again soon."}
            )
        else:
            actions.append(
                {"action": "talk", "text": "Please call us back at your convenience. Thank you."}
            )
        actions.append({"action": "hangup"})
        return json.dumps(actions)


class PlivoVoiceMarkup(VoiceMarkupBuilder):
    content_type = "application/xml"

    @property
    def provider_name(self) -> str:
        return "plivo"

    def is_configured(self) -> bool:
        from app.voice import plivo_client

        return plivo_client.is_plivo_configured()

    def build_greeting(
        self,
        business: Business,
        base_url: str,
        call_log_id: str,
        *,
        call_sid: str | None = None,
    ) -> str:
        trade = resolve_trade_context(business)
        greeting = (
            f"Thank you for calling {business.name}. "
            "I'm the AI receptionist. "
            f"After the tone, tell me what's going on — for example {trade.voice_greeting_example}."
        )
        return self.build_say_and_gather(
            greeting,
            base_url,
            call_log_id,
            call_sid=call_sid,
            country=business.country,
        )

    def build_say_and_gather(
        self,
        message: str,
        base_url: str,
        call_log_id: str,
        *,
        call_sid: str | None = None,
        country: str | None = None,
    ) -> str:
        from app.services.voice_mode_service import VoiceModeService
        from app.voice.texml_builder import duplex_stream_url

        settings = get_settings()
        urls = _voice_urls(base_url, call_log_id)
        gather_url = escape(urls["gather"], quote=True)
        locale = resolve_voice_locale(country)
        if call_sid and VoiceModeService.effective_mode() == "duplex":
            stream_url = escape(duplex_stream_url(call_log_id, call_sid), quote=True)
            return (
                '<?xml version="1.0" encoding="UTF-8"?>'
                "<Response>"
                f'<Speak language="{locale.language}">{escape(message, quote=False)}</Speak>'
                f'<Stream bidirection="true" contentType="audio/x-l16;rate=16000">{stream_url}</Stream>'
                "</Response>"
            )
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f'<Speak language="{locale.language}">{escape(message, quote=False)}</Speak>'
            f'<GetInput action="{gather_url}" method="POST" inputType="speech" '
            f'speechEndTimeout="{settings.voice_gather_speech_timeout}" '
            f'executionTimeout="{settings.voice_gather_timeout}" '
            f'language="{locale.language}"/>'
            f'<Speak language="{locale.language}">I did not catch that. Goodbye!</Speak>'
            "<Hangup/>"
            "</Response>"
        )

    def build_hangup(self, message: str, *, country: str | None = None) -> str:
        locale = resolve_voice_locale(country)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f'<Speak language="{locale.language}">{escape(message, quote=False)}</Speak>'
            "<Hangup/>"
            "</Response>"
        )

    def build_transfer(
        self,
        escalation_phone: str,
        message: str | None = None,
        *,
        country: str | None = None,
    ) -> str:
        locale = resolve_voice_locale(country)
        msg = message or "Please hold while I connect you with a team member."
        phone = escape(escalation_phone.strip(), quote=False)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f'<Speak language="{locale.language}">{escape(msg, quote=False)}</Speak>'
            f"<Dial><Number>{phone}</Number></Dial>"
            f'<Speak language="{locale.language}">Sorry, no one is available right now.</Speak>'
            "<Hangup/>"
            "</Response>"
        )

    def build_empty(self) -> str:
        return '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'

    def build_outbound_answer(
        self,
        business_name: str,
        escalation_phone: str | None,
        *,
        reason: str | None = None,
        country: str | None = None,
    ) -> str:
        locale = resolve_voice_locale(country)
        intro = reason or f"Hi, this is {business_name} calling about your recent service request."
        parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            "<Response>",
            f'<Speak language="{locale.language}">{escape(intro, quote=False)}</Speak>',
        ]
        if escalation_phone:
            parts.append(f'<Speak language="{locale.language}">Connecting you now.</Speak>')
            parts.append(
                f"<Dial><Number>{escape(escalation_phone.strip(), quote=False)}</Number></Dial>"
            )
        else:
            parts.append(
                f'<Speak language="{locale.language}">Please call us back at your convenience.</Speak>'
            )
        parts.append("<Hangup/></Response>")
        return "".join(parts)


class SignalWireVoiceMarkup(TwilioVoiceMarkup):
    """cXML is TwiML-compatible — reuse Twilio gather/stream/transfer builders."""

    @property
    def provider_name(self) -> str:
        return "signalwire"

    def is_configured(self) -> bool:
        from app.voice import signalwire_client

        return signalwire_client.is_signalwire_configured()


class VoipMsVoiceMarkup(VoiceMarkupBuilder):
    """
    VoIP.ms does not consume TeXML/TwiML for inbound AI gather.

    Markup helpers return plain-text acknowledgements for SMS URL callbacks
    and SIP-routing oriented messages for voice status endpoints.
    """

    content_type = "text/plain"

    @property
    def provider_name(self) -> str:
        return "voipms"

    def is_configured(self) -> bool:
        from app.voice import voipms_client

        return voipms_client.is_voipms_configured()

    def supports_streaming(self) -> bool:
        return False

    def build_greeting(
        self,
        business: Business,
        base_url: str,
        call_log_id: str,
        *,
        call_sid: str | None = None,
    ) -> str:
        del business, base_url, call_log_id, call_sid
        return "ok"

    def build_say_and_gather(
        self,
        message: str,
        base_url: str,
        call_log_id: str,
        *,
        call_sid: str | None = None,
        country: str | None = None,
    ) -> str:
        del message, base_url, call_log_id, call_sid, country
        return "ok"

    def build_hangup(self, message: str, *, country: str | None = None) -> str:
        del message, country
        return "ok"

    def build_transfer(
        self,
        escalation_phone: str,
        message: str | None = None,
        *,
        country: str | None = None,
    ) -> str:
        del escalation_phone, message, country
        return "ok"

    def build_empty(self) -> str:
        return "ok"

    def build_outbound_answer(
        self,
        business_name: str,
        escalation_phone: str | None,
        *,
        reason: str | None = None,
        country: str | None = None,
    ) -> str:
        del business_name, escalation_phone, reason, country
        return "ok"


_BUILDERS: dict[str, type[VoiceMarkupBuilder]] = {
    "telnyx": TelnyxVoiceMarkup,
    "twilio": TwilioVoiceMarkup,
    "vonage": VonageVoiceMarkup,
    "plivo": PlivoVoiceMarkup,
    "signalwire": SignalWireVoiceMarkup,
    "voipms": VoipMsVoiceMarkup,
}


def get_voice_markup(provider_name: str) -> VoiceMarkupBuilder:
    cls = _BUILDERS.get(provider_name.lower(), TelnyxVoiceMarkup)
    return cls()


def resolve_voice_markup(*, business: Business | None = None, db=None) -> VoiceMarkupBuilder:
    from app.integrations.provider_resolution import resolve_telephony_adapter_name

    name = resolve_telephony_adapter_name(business=business, db=db)
    return get_voice_markup(name)
