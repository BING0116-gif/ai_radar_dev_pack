"""Tests for the send_notification tool (CARD-014) and the email push (default)."""

from app.agent.registry import ToolRegistry
from app.core.config import Settings, get_settings
from app.tools.notify import (
    ConsoleNotifier,
    EmailNotifier,
    NotifyError,
    register_notification_tool,
)


def test_console_notifier_registered_and_sends():
    registry = ToolRegistry()
    register_notification_tool(registry, notifiers={"console": ConsoleNotifier()})
    result = registry.execute("send_notification", {"channel": "console", "message": "hi"})
    assert result.success is True
    assert result.data["sent"] is True


def test_unknown_channel_structured_failure():
    registry = ToolRegistry()
    register_notification_tool(registry, notifiers={"console": ConsoleNotifier()})
    result = registry.execute("send_notification",
                              {"channel": "slack", "message": "hi"})
    assert result.success is False
    assert "not available" in (result.error or "")


def test_email_unconfigured_writes_demo_email(tmp_path):
    """无 EMAIL_* 时邮件走 DEMO：完整邮件落盘 .eml，而不是抛错。"""
    settings = Settings(_env_file=None).model_copy(update={"WORKSPACE_ROOT": tmp_path})
    notifier = EmailNotifier(settings)
    assert notifier.is_configured() is False

    notifier.send("brief markdown 正文", subject="AI 新闻简报 2026-09-21（5 条）")

    files = list((tmp_path / "emails").glob("*.eml"))
    assert len(files) == 1
    content = files[0].read_text(encoding="utf-8")
    assert "Subject: AI 新闻简报 2026-09-21（5 条）" in content
    assert "brief markdown 正文" in content


def test_email_default_notifiers_include_email(tmp_path):
    """build_default_notifiers 恒含 email —— 邮件推送默认可用、可运行。"""
    from app.tools.notify import build_default_notifiers

    notifiers = build_default_notifiers()
    assert set(notifiers) == {"console", "email"}


def test_email_credentials_stay_secret(monkeypatch):
    monkeypatch.setenv("EMAIL_PASSWORD", "smtp-password-secret")
    get_settings.cache_clear()  # env changed after the cached singleton was built
    try:
        settings = get_settings()
        assert settings.EMAIL_PASSWORD.get_secret_value() == "smtp-password-secret"
        assert "smtp-password-secret" not in str(settings)
        assert "smtp-password-secret" not in repr(settings)
    finally:
        get_settings.cache_clear()