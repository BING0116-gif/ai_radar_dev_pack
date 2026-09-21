"""Tests for the UI-driven email config (store + API + demo/real switching)."""

import json

import pytest

from app.core.config import Settings
from app.services import email_settings as store
from app.tools.notify import EmailNotifier


@pytest.fixture
def tmp_settings(tmp_path):
    return Settings(_env_file=None).model_copy(update={"WORKSPACE_ROOT": tmp_path})


def test_load_defaults_from_env_and_empty_is_unconfigured(tmp_settings, monkeypatch):
    for key in ("EMAIL_HOST", "EMAIL_USER", "EMAIL_FROM", "EMAIL_TO"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("EMAIL_PASSWORD", raising=False)
    monkeypatch.setattr(store, "get_settings", lambda: tmp_settings)

    root = tmp_settings.WORKSPACE_ROOT
    cfg = store.load_email_config(root)
    assert cfg["host"] == ""
    assert store.is_fully_configured(cfg) is False


def test_save_and_reload_roundtrip_with_file_override(tmp_settings, monkeypatch):
    monkeypatch.setattr(store, "get_settings", lambda: tmp_settings)
    root = tmp_settings.WORKSPACE_ROOT
    store.save_email_config({
        "host": "smtp.qq.com", "port": 465, "user": "u@qq.com",
        "password": "smtp-code", "from": "u@qq.com", "to": "me@qq.com",
    }, root=root)

    cfg = store.load_email_config(root)
    assert cfg["host"] == "smtp.qq.com"
    assert cfg["password"] == "smtp-code"
    assert store.is_fully_configured(cfg) is True

    # 公开视图绝不回显密码
    public = store.public_email_config(cfg)
    assert "password" not in public


def test_file_overrides_env(tmp_settings, monkeypatch):
    monkeypatch.setenv("EMAIL_HOST", "env.example.com")
    monkeypatch.setattr(store, "get_settings", lambda: tmp_settings)
    store.save_email_config({"host": "ui.example.com"}, root=tmp_settings.WORKSPACE_ROOT)

    cfg = store.load_email_config(tmp_settings.WORKSPACE_ROOT)
    assert cfg["host"] == "ui.example.com"  # UI 最新配置优先


def test_email_notifier_demo_mode_from_settings(tmp_settings):
    notifier = EmailNotifier(tmp_settings)  # 无 env、无文件 -> 未配置
    assert notifier.is_configured() is False
    notifier.send("hi there", subject="AI Radar 邮件推送测试")
    files = list((tmp_settings.WORKSPACE_ROOT / "emails").glob("*.eml"))
    assert len(files) == 1
    assert "Subject: AI Radar 邮件推送测试" in files[0].read_text(encoding="utf-8")


def test_email_notifier_uses_saved_config(tmp_settings):
    store.save_email_config({
        "host": "smtp.qq.com", "port": 465, "user": "u@qq.com",
        "password": "code", "from": "u@qq.com", "to": "me@qq.com",
    }, root=tmp_settings.WORKSPACE_ROOT)
    notifier = EmailNotifier(tmp_settings)
    assert notifier.is_configured() is True


def test_api_get_put_and_masking(client, tmp_settings, monkeypatch):
    from app.tools import notify as notify_module

    monkeypatch.setattr(store, "get_settings", lambda: tmp_settings)
    monkeypatch.setattr(notify_module, "get_settings", lambda: tmp_settings)

    got = client.get("/api/email-config")
    assert got.status_code == 200
    assert got.json()["data"]["configured"] is False

    put = client.put("/api/email-config", json={
        "host": "smtp.qq.com", "port": 465, "user": "u@qq.com",
        "password": "smtp-code", "sender": "u@qq.com", "recipient": "me@qq.com",
    })
    assert put.status_code == 200
    data = put.json()["data"]
    assert data["configured"] is True
    assert data["recipient"] == "me@qq.com"
    assert "password" not in data  # 不回显
    assert (tmp_settings.WORKSPACE_ROOT / "email_settings.json").exists()


def test_api_test_email_unconfigured_returns_demo(client, tmp_settings, monkeypatch):
    from app.tools import notify as notify_module

    monkeypatch.setattr(store, "get_settings", lambda: tmp_settings)
    monkeypatch.setattr(notify_module, "get_settings", lambda: tmp_settings)
    resp = client.post("/api/email-config/test", json={"host": "", "port": 465,
                                                       "user": "", "password": "",
                                                       "sender": "", "recipient": ""})
    assert resp.status_code == 200
    result = resp.json()["data"]
    assert result["mode"] == "demo"
    assert result["sent"] is True