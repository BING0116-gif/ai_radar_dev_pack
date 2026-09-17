"""AI Radar backend entrypoint.

FastAPI application exposing a minimal health check endpoint.
Settings and structured logging are initialized here so that startup
validation happens as early as possible.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.subscriptions import router as subscriptions_router
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.schemas.common import ApiError, error_response

settings = get_settings()
setup_logging()
logger = get_logger("main")

app = FastAPI(title="AI Radar API", version="0.1.0")

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


@app.get("/health")
def health() -> dict[str, str]:
    """Return service liveness status."""
    return {"status": "ok"}