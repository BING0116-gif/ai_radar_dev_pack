"""Structured (JSON-lines) logging for the backend.

Logs are emitted as single-line JSON objects on stdout, which keeps them
machine-parseable while staying dependency-free (stdlib only).
"""

import json
import logging
import sys
from datetime import datetime, timezone

APP_LOGGER_NAME = "app"


class JsonFormatter(logging.Formatter):
    """Format log records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: int = logging.INFO, stream=None) -> logging.Logger:
    """Configure the ``app`` logger with a JSON formatter on stdout.

    Call once at startup; returns the app logger.
    """
    logger = logging.getLogger(APP_LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False
    logger.handlers.clear()

    handler = logging.StreamHandler(stream if stream is not None else sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the app namespace, e.g. ``get_logger("main")``."""
    return logging.getLogger(f"{APP_LOGGER_NAME}.{name}")