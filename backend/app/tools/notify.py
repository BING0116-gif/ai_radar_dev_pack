"""Notification: Console (required) + Email (when configured).

Credentials come exclusively from central Settings / environment variables —
never from the database. A notification failure never destroys the brief the
agent already generated; callers treat notification as best-effort.
"""

import logging
import smtplib
import ssl
from abc import ABC, abstractmethod
from email.message import EmailMessage

from pydantic import BaseModel, Field, SecretStr

from app.agent.registry import ToolDefinition, ToolRegistry
from app.core.config import get_settings

logger = logging.getLogger("app.tools.notify")


class NotifyError(Exception):
    """A notification could not be delivered."""


class Notifier(ABC):
    """One delivery channel."""

    channel: str = ""

    @abstractmethod
    def send(self, message: str) -> None:
        """Deliver the message; raise NotifyError on failure."""


class ConsoleNotifier(Notifier):
    channel = "console"

    def send(self, message: str) -> None:
        logger.info("[notification:%s] %s", self.channel, message)


class EmailNotifier(Notifier):
    """SMTP delivery; only usable when EMAIL_* settings are fully configured."""

    channel = "email"

    def __init__(self, settings=None):
        self.settings = settings or get_settings()

    def is_configured(self) -> bool:
        s = self.settings
        return bool(s.EMAIL_HOST and s.EMAIL_USER and s.EMAIL_PASSWORD.get_secret_value() and s.EMAIL_FROM and s.EMAIL_TO)

    def send(self, message: str) -> None:
        settings = self.settings
        if not self.is_configured():
            raise NotifyError("email not configured (missing EMAIL_* env settings)")
        msg = EmailMessage()
        msg["Subject"] = "AI Radar 简报"
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = settings.EMAIL_TO
        msg.set_content(message)
        context = ssl.create_default_context()
        try:
            if settings.EMAIL_PORT == 465:
                with smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT, context=context, timeout=20) as smtp:
                    smtp.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD.get_secret_value())
                    smtp.send_message(msg)
            else:
                with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=20) as smtp:
                    smtp.starttls(context=context)
                    smtp.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD.get_secret_value())
                    smtp.send_message(msg)
        except (smtplib.SMTPException, OSError) as exc:
            raise NotifyError(f"email send failed: {exc}") from exc


def build_default_notifiers() -> dict[str, Notifier]:
    """Channel map used by the tool and the run service."""
    notifiers: dict[str, Notifier] = {"console": ConsoleNotifier()}
    email = EmailNotifier()
    if email.is_configured():
        notifiers["email"] = email
    return notifiers


# --- agent tool ---------------------------------------------------------------

class SendNotificationParams(BaseModel):
    channel: str = Field(default="console", description="console | email")
    message: str = Field(description="notification text")


class NotificationTool:
    def __init__(self, notifiers: dict[str, Notifier]):
        self._notifiers = notifiers

    def send_notification(self, channel: str, message: str) -> dict:
        notifier = self._notifiers.get(channel)
        if notifier is None:
            raise NotifyError(f"notification channel not available: {channel}")
        notifier.send(message)
        return {"channel": channel, "sent": True}


def register_notification_tool(registry: ToolRegistry, notifiers: dict[str, Notifier] | None = None) -> None:
    """Register send_notification; ``notifiers`` injectable for tests."""
    tool = NotificationTool(notifiers if notifiers is not None else build_default_notifiers())
    registry.register(ToolDefinition(
        name="send_notification",
        description="Deliver a message via a notification channel (console or configured email).",
        parameters_model=SendNotificationParams,
        func=tool.send_notification,
        timeout_seconds=30,
    ))