"""AI Radar backend entrypoint.

FastAPI application exposing the health check and API routers. Settings and
structured logging are initialized here so startup validation happens early.
The daily scheduler starts on startup only when ``SCHEDULER_ENABLED=true``
(set ``DISABLE_SCHEDULER=1`` to suppress, e.g. in test environments).
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.runs import router as runs_router
from app.api.subscriptions import router as subscriptions_router
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.schemas.common import ApiError, error_response

settings = get_settings()
setup_logging()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    scheduler = None
    if settings.SCHEDULER_ENABLED and os.environ.get("DISABLE_SCHEDULER") != "1":
        from app.services.scheduler import build_scheduler

        scheduler = build_scheduler()
        scheduler.start()
        logger.info("daily scheduler started (hour=%s minute=%s)",
                    settings.SCHEDULER_DAILY_HOUR, settings.SCHEDULER_DAILY_MINUTE)
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)


app = FastAPI(title="AI Radar API", version="0.1.0", lifespan=lifespan)

logger.info("startup app_env=%s version=%s ws=%s", settings.APP_ENV.value, app.version, settings.WORKSPACE_ROOT)


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    """Business errors -> unified error envelope with the carried status code."""
    return JSONResponse(status_code=exc.status_code, content=error_response(exc.code, exc.message))


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Pydantic 422s -> the same unified error envelope."""
    return JSONResponse(status_code=422, content=error_response(42200, "validation_error", exc.errors()))


app.include_router(subscriptions_router)
app.include_router(runs_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Return service liveness status."""
    return {"status": "ok"}