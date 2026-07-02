"""SMTP email adapter."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import get_settings
from app.integrations.contracts import EmailProvider

logger = logging.getLogger(__name__)


class SmtpEmailProvider(EmailProvider):
    @property
    def provider_name(self) -> str:
        return "smtp"

    def is_configured(self) -> bool:
        settings = get_settings()
        return bool(settings.smtp_host and settings.smtp_from_email)

    def send_email(self, to: str, subject: str, body: str) -> dict:
        settings = get_settings()
        msg = MIMEMultipart()
        msg["From"] = settings.smtp_from_email
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
                if settings.smtp_use_tls:
                    server.starttls()
                if settings.smtp_user:
                    server.login(settings.smtp_user, settings.smtp_password)
                server.sendmail(settings.smtp_from_email, [to], msg.as_string())
            return {"sent": True, "provider": self.provider_name, "email": to, "subject": subject}
        except Exception as exc:
            logger.exception("SMTP email failed", extra={"to": to})
            return {"sent": False, "provider": self.provider_name, "error": str(exc)}
