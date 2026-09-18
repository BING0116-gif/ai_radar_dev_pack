"""run_agent(user_id): the single entry the scheduler (and REST API) triggers.

It assembles the registry + prompt + guarded loop + tracing + brief
persistence + best-effort notification. It has *no* opinion about tool order
— that stays inside the model-driven loop.
"""

import logging
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.agent.context import AgentContext
from app.agent.guardrails import BriefOutputGuard
from app.agent.loop import AgentLoop
from app.agent.registry import ToolRegistry
from app.agent.prompts import build_system_prompt
from app.core.config import get_settings
from app.core.llm_client import LLMClient, OpenAICompatibleClient
from app.models import Brief, Subscription, User
from app.news.dedup import extract_history_entries
from app.services.briefs import persist_brief
from app.services.tracing import DbTracer
from app.tools.bash import register_bash_tool
from app.tools.fetch_url import register_fetch_url_tool
from app.tools.filesystem import register_filesystem_tools
from app.tools.notify import Notifier, build_default_notifiers, register_notification_tool
from app.tools.web_search import register_web_search_tool

logger = logging.getLogger("app.services.runs")

SUCCESS_STOP_REASONS = {"final_response", "repaired"}


def get_default_llm() -> LLMClient:
    """LLM used by API/scheduler runs; tests monkeypatch this factory."""
    return OpenAICompatibleClient()


def build_default_registry(root: Path | None = None) -> ToolRegistry:
    """The standard tool set for one agent run."""
    registry = ToolRegistry()
    workspace = (root or get_settings().WORKSPACE_ROOT).resolve()
    register_filesystem_tools(registry, root=workspace)
    register_bash_tool(registry, cwd=workspace)
    register_web_search_tool(registry)
    register_fetch_url_tool(registry)
    register_notification_tool(registry)
    return registry


def recent_titles(db: Session, user_id: int, days: int = 7) -> list[str]:
    """Titles from the last N days of briefs (for prompt-level dedup hints)."""
    since = date.today() - timedelta(days=days)
    briefs = (
        db.query(Brief)
        .filter(Brief.user_id == user_id, Brief.brief_date >= since)
        .order_by(Brief.brief_date.desc())
        .limit(20)
        .all()
    )
    titles: list[str] = []
    for brief in briefs:
        titles.extend(title for _url, title in extract_history_entries(brief.content_markdown))
    return titles[:30]


def run_agent(
    db: Session,
    user_id: int,
    *,
    llm: LLMClient | None = None,
    registry: ToolRegistry | None = None,
    notifiers: dict[str, Notifier] | None = None,
    root: Path | None = None,
    reason: str = "manual",
) -> dict:
    """Run one full agent task for a user; persist brief; notify best-effort."""
    settings = get_settings()
    user = db.get(User, user_id)
    if user is None:
        raise ValueError(f"user not found: {user_id}")
    subscription = (
        db.query(Subscription).filter(Subscription.user_id == user_id).order_by(Subscription.id).first()
    )
    max_items = subscription.max_items if subscription else 5

    system_prompt = build_system_prompt(
        {"name": user.name, "role": user.role, "timezone": user.timezone},
        {
            "topics": subscription.topics_json if subscription else [],
            "keywords": subscription.keywords_json if subscription else [],
            "excluded_keywords": subscription.excluded_keywords_json if subscription else [],
            "max_items": max_items,
            "language": subscription.language if subscription else "zh-CN",
        },
        recent_titles=recent_titles(db, user_id),
    )

    reg = registry if registry is not None else build_default_registry(root)
    tracer = DbTracer(db, user, run_reason=reason)
    guard = BriefOutputGuard()

    # llm defaults to the real OpenAI-compatible client; tests inject mocks.
    llm = llm if llm is not None else OpenAICompatibleClient()
    result = AgentLoop(reg, llm, output_guard=guard, tracer=tracer).run(
        AgentContext(task=_task_instruction(subscription), extra={"user_id": user_id})
    )

    summary = {
        "run_id": tracer.run.id,
        "stop_reason": result.stop_reason,
        "brief_id": None,
        "item_count": 0,
        "notification_sent": False,
        "error": None,
    }

    if result.stop_reason in SUCCESS_STOP_REASONS and result.structured:
        brief = persist_brief(
            db, user_id=user_id, run_id=tracer.run.id,
            structured=result.structured, max_items=max_items, root=root,
        )
        summary["brief_id"] = brief.id
        summary["item_count"] = brief.item_count
        summary["notification_sent"] = _notify(
            (notifiers if notifiers is not None else build_default_notifiers()),
            subscription, max_items, brief.item_count,
        )
    elif result.stop_reason not in SUCCESS_STOP_REASONS:
        summary["error"] = f"run ended with {result.stop_reason}"
    return summary


def _notify(notifiers: dict[str, Notifier], subscription, max_items: int, item_count: int) -> bool:
    channel = (subscription.notification_channel if subscription else "console") or "console"
    notifier = notifiers.get(channel)
    if notifier is None:
        logger.warning("notification channel '%s' not available; brief already saved", channel)
        return False
    try:
        notifier.send(f"简报已生成：{item_count} 条新闻（上限 {max_items} 条）。")
        return True
    except Exception as exc:  # notification is best-effort; never lose the brief
        logger.warning("notification failed (brief kept): %s", exc)
        return False


def _task_instruction(subscription) -> str:
    topics = subscription.topics_json if subscription else []
    topics_text = "、".join(topics) if topics else "AI 领域"
    return (
        f"为今日生成一份个性化 AI 新闻简报：重点围绕 {topics_text}。"
        "按要求的 JSON 结构输出最终简报（每一条都必须有真实来源 URL）。"
    )