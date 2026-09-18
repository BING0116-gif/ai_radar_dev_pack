"""Tests for the send_notification tool (CARD-014)."""

import pytest

from app.agent.registry import ToolRegistry
from app.core.config import get_settings
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


def test_email_notifier_requires_configuration():
    settings = get_settings()
    notifier = EmailNotifier(settings)
    assert notifier.is_configured() is False
    with pytest.raises(NotifyError):
        notifier.send("x")


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