"""Centralized, typed application settings.

Values are resolved from environment variables first, then from the root
`.env` file (path is anchored to the repository root on purpose, so the
behavior does not depend on the current working directory).

Sensitive fields (``LLM_API_KEY``) use ``SecretStr`` so that ``repr()`` and
any logging of the settings object never expose the real value.
"""

from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repository root: <repo>/backend/app/core/config.py
BASE_DIR = Path(__file__).resolve().parents[3]


class AppEnv(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Typed configuration for the whole backend."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- runtime mode ---
    APP_ENV: AppEnv = AppEnv.DEVELOPMENT

    # --- database ---
    DATABASE_URL: str = "sqlite:///./ai_radar.db"

    # --- LLM (optional until the Agent actually runs) ---
    LLM_BASE_URL: str = ""
    LLM_API_KEY: SecretStr = SecretStr("")
    LLM_MODEL: str = ""

    # --- agent / tools ---
    WORKSPACE_ROOT: Path = Path("workspace")
    AGENT_MAX_STEPS: int = Field(default=12, ge=1, le=50)
    TOOL_TIMEOUT_SECONDS: float = Field(default=10.0, gt=0)

    # --- scheduler ---
    SCHEDULER_ENABLED: bool = False
    SCHEDULER_DAILY_HOUR: int = Field(default=9, ge=0, le=23)
    SCHEDULER_DAILY_MINUTE: int = Field(default=0, ge=0, le=59)

    # --- notifications (credentials come from env only, never the DB) ---
    EMAIL_HOST: str = ""
    EMAIL_PORT: int = 465
    EMAIL_USER: str = ""
    EMAIL_PASSWORD: SecretStr = SecretStr("")
    EMAIL_FROM: str = ""
    EMAIL_TO: str = ""

    @field_validator("WORKSPACE_ROOT", mode="after")
    @classmethod
    def make_workspace_root_absolute(cls, value: Path) -> Path:
        """Resolve WORKSPACE_ROOT against the repo root to an absolute path."""
        if not value.is_absolute():
            value = BASE_DIR / value
        return value.resolve()


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide Settings singleton."""
    return Settings()