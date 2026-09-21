"""UI-driven local email configuration (single-user demo convenience).

设计说明（面试可讲）：
- **生产/正式路径**：`EMAIL_*` 环境变量（`.env` 或系统环境变量），凭据不入库、
  不入 git。
- **UI 路径**：设置页填写的 SMTP 配置写入
  ``<WORKSPACE_ROOT>/email_settings.json``（已 gitignore 的本地文件；容器里落在
  ``/data/workspace`` 命名卷，重启保留）。用户名/口令**不写入数据库**。
- **合并顺序**：环境变量作默认值，文件值覆盖（文件 = 用户在 UI 上最新配置，
  优先）；全空则 EmailNotifier 走 DEMO 落盘模式。
"""

import json
import logging
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger("app.services.email_settings")

JSON_FILENAME = "email_settings.json"
# 存的键与 EmailNotifier 用的一致
KEYS = ("host", "port", "user", "password", "from", "to")


def email_file(root: Path | None = None) -> Path:
    base = (root or get_settings().WORKSPACE_ROOT).resolve()
    return base / JSON_FILENAME


def env_defaults() -> dict:
    settings = get_settings()
    return {
        "host": (settings.EMAIL_HOST or "").strip(),
        "port": int(settings.EMAIL_PORT or 465),
        "user": (settings.EMAIL_USER or "").strip(),
        "password": settings.EMAIL_PASSWORD.get_secret_value() if settings.EMAIL_PASSWORD else "",
        "from": (settings.EMAIL_FROM or "").strip(),
        "to": (settings.EMAIL_TO or "").strip(),
    }


def load_email_config(root: Path | None = None) -> dict:
    """Effective config: env defaults, overridden by the UI-saved local file."""
    config = env_defaults()
    path = email_file(root)
    if path.exists():
        try:
            stored = json.loads(path.read_text(encoding="utf-8"))
            for key in KEYS:
                value = stored.get(key)
                if value not in (None, ""):
                    config[key] = str(value)
        except (ValueError, OSError) as exc:  # corrupt file must not break sending
            logger.warning("email_settings.json 解析失败，忽略文件: %s", exc)
    return config


def save_email_config(payload: dict, root: Path | None = None) -> dict:
    """Persist the UI-configured SMTP settings to the gitignored local file."""
    path = email_file(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


_sensitive = {"password"}


def public_email_config(config: dict) -> dict:
    """Same shape minus the secret; password is never echoed back."""
    return {key: value for key, value in config.items() if key not in _sensitive}


def is_fully_configured(config: dict) -> bool:
    required = ("host", "user", "password", "from", "to")
    return all(str(config.get(key) or "").strip() for key in required)