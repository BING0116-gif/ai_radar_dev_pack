"""Validate-structured brief persistence: database row + workspace Markdown file.

``persist_brief`` consumes the schema-validated output of the agent (e.g. the
``structured`` field of ``AgentRunResult``), filters out items without usable
source URLs, enforces ``max_items``, renders Markdown, writes
``workspace/briefs/YYYY-MM-DD-<run_id>.md``, and saves a ``briefs`` row.
"""

from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Brief

BRIEFS_DIRNAME = "briefs"


def clean_and_limit_items(items: list[dict], max_items: int) -> list[dict]:
    """Drop items without a usable http(s) URL, then cap at ``max_items``."""
    kept: list[dict] = []
    for item in items:
        url = item.get("source_url")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            continue
        kept.append(item)
        if len(kept) >= max_items:
            break
    return kept


def render_markdown(brief_date: str, intro: str, items: list[dict]) -> str:
    """Render the final brief as Markdown."""
    lines = [f"# AI 新闻简报 {brief_date}", ""]
    if intro:
        lines.extend([intro, ""])
    for index, item in enumerate(items, start=1):
        title = item.get("title", "").strip()
        lines.append(f"## {index}. {title}")
        if item.get("source_name"):
            lines.append(f"**来源**: {item['source_name']}")
        if item.get("source_url"):
            lines.append(f"**链接**: {item['source_url']}")
        if item.get("published_at"):
            lines.append(f"**发布时间**: {item['published_at']}")
        if item.get("why_it_matters"):
            lines.append(f"**为什么重要**: {item['why_it_matters']}")
        lines.append(f"**摘要**: {item.get('summary', '')}")
        topics = item.get("topics") or []
        if topics:
            lines.append(f"**主题**: {', '.join(str(t) for t in topics)}")
        lines.append("")
    return "\n".join(lines)


def persist_brief(
    db: Session,
    *,
    user_id: int,
    run_id: int,
    structured: dict,
    max_items: int,
    root: Path | None = None,
) -> Brief:
    """Save a validated brief to the DB and as a workspace Markdown file."""
    items = clean_and_limit_items(structured.get("items", []), max_items=max_items)
    brief_date = structured.get("brief_date") or date.today().isoformat()

    markdown = render_markdown(brief_date, structured.get("intro", ""), items)
    brief = Brief(
        user_id=user_id,
        run_id=run_id,
        brief_date=date.fromisoformat(brief_date),
        title=f"AI 新闻简报 {brief_date}",
        content_markdown=markdown,
        item_count=len(items),
    )
    db.add(brief)
    db.commit()
    db.refresh(brief)

    workspace = (root or get_settings().WORKSPACE_ROOT).resolve()
    brief_dir = workspace / BRIEFS_DIRNAME
    brief_dir.mkdir(parents=True, exist_ok=True)
    out_file = brief_dir / f"{brief_date}-{run_id}.md"
    out_file.write_text(markdown, encoding="utf-8")
    return brief