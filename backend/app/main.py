"""AI Radar backend entrypoint.

FastAPI application exposing a minimal health check endpoint.
Settings and structured logging are initialized here so that startup
validation happens as early as possible.
"""

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging

settings = get_settings()
setup_logging()
logger = get_logger("main")

app = FastAPI(title="AI Radar API", version="0.1.0")

logger.info("startup app_env=%s version=%s ws=%s", settings.APP_ENV.value, app.version, settings.WORKSPACE_ROOT)


@app.get("/health")
def health() -> dict[str, str]:
    """Return service liveness status."""
    return {"status": "ok"}