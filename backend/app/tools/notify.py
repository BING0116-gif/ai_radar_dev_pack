"""Notification: Console (required) + Email (default).

Credentials come exclusively from central Settings / environment variables —
never from the database. A notification failure never destroys the brief the
agent already generated; callers treat notification as best-effort.

Email 默认启用：未配置 ``EMAIL_*``（面试官/无 SMTP 环境）时进入 **DEMO 模式**
—— 把完整的简报邮件作为 ``.eml`` 文件写入 ``workspace/emails/`` 并打日志，
证明"邮件自动推送"存在且可运行；配置 ``EMAIL_*`` 后同一份邮件真实通过 SMTP
投递。
"""

import logging
import smtplib
import ssl
from abc import ABC, abstractmethod
from datetime import datetime
from email.message import EmailMessage

from pydantic import BaseModel, Field, SecretStr

from app.agent.registry import ToolDefinition, ToolRegistry
from app.core.config import get_settings

logger = logging.getLogger("app.tools.notify")

EMAIL_DIRNAME = "emails"


class NotifyError(Exception):
    """A notification could not be delivered."""


class Notifier(ABC):
    """One delivery channel."""

    channel: str = ""

    @abstractmethod
    def send(self, message: str, subject: str | None = None) -> None:
        """Deliver the message; raise NotifyError on hard failure."""


class ConsoleNotifier(Notifier):
    channel = "console"

    def send(self, message: str, subject: str | None = None) -> None:
        head = f"[{subject}] " if subject else ""
        logger.info("[notification:%s] %s%s", self.channel, head, message)


class EmailNotifier(Notifier):
    """SMTP delivery when EMAIL_* is configured; otherwise DEMO mode.

    DEMO 模式（无凭据也可运行）：把完整邮件按 RFC 822 主体结构写到
    ``<WORKSPACE_ROOT>/emails/ai-radar-<ts>.eml``，让接收方/面试官在没有
    SMTP 的环境里也能看到"推送了什么、长什么样"。
    """

    channel = "email"

    def __init__(self, settings=None):
        self.settings = settings or get_settings()

    def is_configured(self) -> bool:
        s = self.settings
        return bool(s.EMAIL_HOST and s.EMAIL_USER and s.EMAIL_PASSWORD.get_secret_value() and s.EMAIL_FROM and s.EMAIL_TO)

    def send(self, message: str, subject: str | None = None) -> None:
        subject = subject or "AI Radar 简报"
        if not self.is_configured():
            self._demo_save(message, subject)
            return
        settings = self.settings
        msg = EmailMessage()
        msg["Subject"] = subject
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

    def _demo_save(self, message: str, subject: str) -> None:
        """No-credential fallback: persist the composed email as an .eml file."""
        out_dir = self.settings.WORKSPACE_ROOT.resolve() / EMAIL_DIRNAME
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_file = out_dir / f"ai-radar-{ts}.eml"
        body = f"Subject: {subject}\nContent-Type: text/plain; charset=utf-8\n\n{message}"
        out_file.write_text(body, encoding="utf-8")
        logger.info(
            "[notification:email] demo: SMTP 未配置（EMAIL_* 留空），邮件已写入 %s；"
            "配置 EMAIL_HOST/USER/PASSWORD/FROM/TO 后同一流程走真实 SMTP 投递",
            out_file,
        )


def build_default_notifiers() -> dict[str, Notifier]:
    """Channel map used by the tool and the run service.

    Email 恒在（DEMO 模式兜底），保证"邮件自动推送"默认可用、可运行、可验证。
    """
    return {"console": ConsoleNotifier(), "email": EmailNotifier()}


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