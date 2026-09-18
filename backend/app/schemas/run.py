"""Pydantic schemas for run / trace / brief API responses."""

from datetime import date, datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, Field


class RunSummary(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    status: str
    step_count: int = 0
    started_at: datetime
    finished_at: datetime | None = None
    error_message: str | None = None


class StepResponse(BaseModel):
    model_config = {"from_attributes": True}

    step_no: int
    event_type: str
    tool_name: str | None = None
    tool_input: dict[str, Any] = Field(
        validation_alias=AliasChoices("tool_input_json", "tool_input"), default_factory=dict
    )
    tool_output_preview: str | None = None
    duration_ms: int = 0
    success: bool = True


class RunCreated(BaseModel):
    run_id: int
    stop_reason: str
    brief_id: int | None = None


class BriefSummary(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    brief_date: date
    title: str = ""
    item_count: int = 0
    run_id: int
    created_at: datetime


class BriefDetail(BriefSummary):
    content_markdown: str = ""
    items: list[Any] = Field(
        default_factory=list, validation_alias=AliasChoices("items_json", "items")
    )