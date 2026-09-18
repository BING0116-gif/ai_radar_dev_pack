"""Subscription request/response schemas with CARD-004 validation rules."""

from typing import Any

from pydantic import BaseModel, Field, field_validator


def _clean_string_list(values: list[str] | None) -> list[str]:
    """Strip whitespace, drop empties, and deduplicate while keeping order."""
    if not values:
        return []
    cleaned: list[str] = []
    for item in values:
        stripped = item.strip()
        if stripped and stripped not in cleaned:
            cleaned.append(stripped)
    return cleaned


class SubscriptionUpdate(BaseModel):
    """PUT /api/subscription request body."""

    max_items: int = Field(default=5, ge=1, le=20)
    topics: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    excluded_keywords: list[str] = Field(default_factory=list)
    language: str = "zh-CN"
    notification_channel: str = "none"
    enabled: bool = True
    timezone: str = "Asia/Shanghai"
    role: str | None = None  # optional identity change on the demo user

    @field_validator("topics", "keywords", "excluded_keywords")
    @classmethod
    def clean_lists(cls, value: list[str] | None) -> list[str]:
        return _clean_string_list(value)


class SubscriptionResponse(BaseModel):
    """GET/PUT /api/subscription response body: user identity + preferences."""

    id: int | None = None
    user_id: int
    name: str
    role: str = ""
    email: str = ""
    timezone: str

    max_items: int
    topics: list[Any]
    keywords: list[Any]
    excluded_keywords: list[Any]
    language: str
    notification_channel: str
    enabled: bool