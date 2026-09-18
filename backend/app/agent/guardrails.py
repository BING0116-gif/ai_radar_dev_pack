"""Output guardrails: enforce the final-brief JSON schema with one repair pass.

The model's final text is parsed as JSON (direct, markdown-fenced, or by
extracting the outermost ``{...}``) and validated against ``BriefSchema``.
If validation fails, the caller may trigger exactly one repair turn; the
guard itself never loops.
"""

import json
import re
from dataclasses import dataclass
from typing import Any

from pydantic import AnyHttpUrl, BaseModel, Field, ValidationError

REPAIR_INSTRUCTION = (
    "你上一轮的输出不符合要求的 JSON 结构。"
    "请只输出一个 JSON 对象（不要任何解释文字），结构为："
    '{{"brief_date": "YYYY-MM-DD", "intro": 引言, "items": [{{"title": 标题, "summary": 摘要, '
    '"why_it_matters": 为什么重要, "source_name": 来源名称, "source_url": 来源链接, '
    '"published_at": 发布时间或 null, "topics": [标签数组]}}], "generated_at": ""}}。'
    "每条新闻的 source_url 必须是有效 http(s) 链接，且必须有 title 和 summary。错误信息：{error}"
)


class BriefItem(BaseModel):
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    why_it_matters: str = ""
    source_name: str = ""
    source_url: AnyHttpUrl
    published_at: str | None = None
    topics: list[str] = Field(default_factory=list)


class BriefSchema(BaseModel):
    brief_date: str
    intro: str = ""
    items: list[BriefItem] = Field(min_length=1, max_length=30)
    generated_at: str = ""


def extract_json(text: str) -> dict[str, Any] | None:
    """Best-effort recovery of a JSON object from model output."""
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            parsed = json.loads(stripped)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass
    # markdown code fence
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fence:
        try:
            parsed = json.loads(fence.group(1).strip())
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass
    # outermost braces
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass
    return None


@dataclass
class ValidationResult:
    ok: bool
    data: dict[str, Any] | None = None
    error: str | None = None


class BriefOutputGuard:
    """Validates final text against BriefSchema."""

    def validate(self, text: str) -> ValidationResult:
        parsed = extract_json(text)
        if parsed is None:
            return ValidationResult(ok=False, error="no JSON object found in output")
        try:
            brief = BriefSchema.model_validate(parsed)
        except ValidationError as exc:
            return ValidationResult(ok=False, error=f"brief schema invalid: {exc}")
        return ValidationResult(ok=True, data=brief.model_dump(mode="json"))