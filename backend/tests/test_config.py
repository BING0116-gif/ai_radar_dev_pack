"""Tests for the central settings object (CARD-002 key defaults)."""

import pytest

from app.core.config import BASE_DIR, AppEnv, Settings


def test_defaults():
    settings = Settings(_env_file=None)
    assert settings.AGENT_MAX_STEPS == 12
    assert settings.TOOL_TIMEOUT_SECONDS == 10.0
    assert settings.APP_ENV == AppEnv.DEVELOPMENT


def test_workspace_root_resolves_to_absolute():
    settings = Settings(_env_file=None)
    assert settings.WORKSPACE_ROOT.is_absolute()
    assert settings.WORKSPACE_ROOT == (BASE_DIR / "workspace").resolve()


def test_dev_env_starts_without_optional_keys():
    # No LLM_* values provided -> defaults are used, construction must not raise.
    settings = Settings(_env_file=None)
    assert settings.LLM_MODEL == ""
    assert settings.LLM_BASE_URL == ""


def test_sensitive_value_is_masked():
    settings = Settings(LLM_API_KEY="sk-secret-value-123", _env_file=None)
    # value is accessible explicitly ...
    assert settings.LLM_API_KEY.get_secret_value() == "sk-secret-value-123"
    # ... but never printed in full by repr/str.
    assert "sk-secret-value-123" not in str(settings)
    assert "sk-secret-value-123" not in repr(settings)


def test_env_var_override(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    settings = Settings(_env_file=None)
    assert settings.APP_ENV == AppEnv.PRODUCTION


def test_invalid_max_steps_rejected():
    with pytest.raises(ValueError):
        Settings(AGENT_MAX_STEPS=0, _env_file=None)