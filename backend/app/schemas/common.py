"""Unified API response envelope and error convention.

Every endpoint returns the same shape: ``{"code": 0, "message": "ok", "data": ...}``.
Errors are raised as ``ApiError`` (business errors) or surface through the
``RequestValidationError`` handler, both producing the same envelope.
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Uniform success/error envelope returned by all endpoints."""

    code: int = 0
    message: str = "ok"
    data: T | None = None


def ok(data: Any = None) -> ApiResponse[Any]:
    """Build a success response envelope."""
    return ApiResponse(data=data)


def error_response(code: int, message: str, data: Any = None) -> dict[str, Any]:
    """Build the error envelope payload (used by exception handlers)."""
    return {"code": code, "message": message, "data": data}


class ApiError(Exception):
    """Business error carrying its own HTTP status and envelope code."""

    def __init__(self, message: str, code: int = 1, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code