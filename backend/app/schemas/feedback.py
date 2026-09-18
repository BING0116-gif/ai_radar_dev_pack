"""Feedback request/response schemas (per-item personalization signals)."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class FeedbackPayload(BaseModel):
    """POST /api/feedback body: the user's stance on one news item."""

    item_key: str = Field(description="stable item identity (e.g. source URL)")
    item_title: str = ""
    verdict: str

    @field_validator("item_key")
    @classmethod
    def strip_key(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("item_key is required")
        return value[:256]

    @field_validator("item_title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        return value.strip()[:200]

    @field_validator("verdict")
    @classmethod
    def check_verdict(cls, value: str) -> str:
        if value not in ("like", "dislike", "read"):
            raise ValueError("verdict must be one of: like, dislike, read")
        return value


class FeedbackResponse(BaseModel):
    model_config = {"from_attributes": True}

    item_key: str
    item_title: str = ""
    verdict: str
    updated_at: datetime