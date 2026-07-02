"""Recovery link delivery — SMS first when functional, email optional, web chat fallback."""

from __future__ import annotations

from app.domain.phone import is_plausible_phone, normalize_phone
from app.models import Business, CallLog
from app.services.notification_service import NotificationService


class RecoveryDeliveryService:
    @staticmethod
    def deliver_web_chat_link(
        notifications: NotificationService,
        business: Business,
        call: CallLog,
        *,
        continue_url: str,
        standalone_url: str,
        email: str | None = None,
    ) -> dict:
        country = business.country
        phone = call.caller_phone
        sms_functional = notifications.is_sms_functional()
        sms_sent = False
        email_sent = False
        sms_error = None

        if sms_functional and phone and is_plausible_phone(phone, country):
            message = (
                f"{business.name}: Continue online — tap to type your name, address, "
                f"email, and finish booking: {continue_url}"
            )
            sms_result = notifications.send_sms(normalize_phone(phone, country), message)
            sms_sent = bool(sms_result.get("sent"))
            sms_error = sms_result.get("error")

        if email:
            subject = f"{business.name} — continue online"
            body = (
                f"Hi,\n\n"
                f"Continue your request and type your details (name, address, email) here:\n\n"
                f"{continue_url}\n\n"
                f"You can also use our chat page anytime: {standalone_url}\n\n"
                f"— {business.name}"
            )
            email_result = notifications.send_email(email, subject, body)
            email_sent = bool(email_result.get("sent"))

        strategy = "sms_first" if sms_functional else "web_first"
        return {
            "sms_sent": sms_sent,
            "email_sent": email_sent,
            "sms_functional": sms_functional,
            "delivery_strategy": strategy,
            "sms_error": sms_error,
            "email": email,
        }

    @staticmethod
    def agent_message_for_web_chat(
        *,
        continue_url: str,
        standalone_url: str,
        delivery: dict,
    ) -> str:
        sms_sent = delivery.get("sms_sent")
        email_sent = delivery.get("email_sent")
        sms_functional = delivery.get("sms_functional")
        email = delivery.get("email")

        if sms_sent:
            msg = (
                "Recovery link sent by text message — SMS is the primary path. "
                "Tell the caller to check their phone and tap the link to type their "
                "name, address, email, and finish booking. "
                "Stay on the line briefly in case the text is delayed."
            )
            if email_sent and email:
                msg += f" A copy was also emailed to {email}."
            msg += (
                f" Continue link for this call: {continue_url} "
                f"Standalone chat page: {standalone_url}."
            )
            return msg

        if sms_functional and not sms_sent:
            msg = (
                "SMS is configured but could not be delivered to this caller. "
                "Read the web chat link clearly on the call and ask them to open it "
                "in their phone browser NOW to type their details."
            )
        else:
            msg = (
                "SMS is not configured — web chat link is the primary path. "
                "Tell the caller to open this link on their phone browser NOW and type "
                "their details: name, address, email, and finish booking."
            )

        if email_sent and email:
            msg += f" A copy was also emailed to {email}."
        msg += (
            f" For this call: {continue_url} "
            f"Or anytime: {standalone_url}. "
            "Do not spell the full URL unless they ask."
        )
        return msg
