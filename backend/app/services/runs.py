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
from app.agent.prompts import build_chat_system_prompt, build_system_prompt
from app.core.config import get_settings
from app.core.llm_client import LLMClient, OpenAICompatibleClient
from app.models import Brief, Feedback, Subscription, User
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


def recent_feedback(db: Session, user_id: int, limit: int = 40) -> dict[str, list[str]]:
    """Group the user's latest feedback titles by verdict (personalization signals).

    Only like/dislike are fed to generation; "read" is kept out of the prompt
    (it means "seen", not "dislike") but exposed to the UI.
    """
    signals: dict[str, list[str]] = {"like": [], "dislike": [], "read": []}
    rows = (
        db.query(Feedback)
        .filter(Feedback.user_id == user_id)
        .order_by(Feedback.updated_at.desc())
        .limit(limit)
        .all()
    )
    for row in rows:
        bucket = signals.get(row.verdict)
        if bucket is not None and row.item_title and row.item_title not in bucket:
            bucket.append(row.item_title)
    return signals


def run_agent(
    db: Session,
    user_id: int,
    *,
    llm: LLMClient | None = None,
    registry: ToolRegistry | None = None,
    notifiers: dict[str, Notifier] | None = None,
    root: Path | None = None,
    reason: str = "manual",
    task: str | None = None,
    mode: str = "brief",
) -> dict:
    """Run one full agent task for a user.

    mode="brief": the standard daily-brief flow (schema-guarded, persisted,
    notified). mode="chat": free-form task answered by the same model-driven
    loop (no JSON guard, no brief persistence).
    """
    settings = get_settings()
    user = db.get(User, user_id)
    if user is None:
        raise ValueError(f"user not found: {user_id}")
    subscription = (
        db.query(Subscription).filter(Subscription.user_id == user_id).order_by(Subscription.id).first()
    )
    max_items = subscription.max_items if subscription else 5
    user_info = {"name": user.name, "role": user.role, "timezone": user.timezone}
    sub_info = {
        "topics": subscription.topics_json if subscription else [],
        "keywords": subscription.keywords_json if subscription else [],
        "excluded_keywords": subscription.excluded_keywords_json if subscription else [],
        "max_items": max_items,
        "language": subscription.language if subscription else "zh-CN",
    }

    if mode == "chat":
        system_prompt = build_chat_system_prompt(user_info, sub_info)
        guard = None
        agent_task = task or ""
    else:
        system_prompt = build_system_prompt(
            user_info,
            sub_info,
            recent_titles=recent_titles(db, user_id),
            feedback_signals=recent_feedback(db, user_id),
        )
        guard = BriefOutputGuard()
        agent_task = task or _task_instruction(subscription)

    reg = registry if registry is not None else build_default_registry(root)
    tracer = DbTracer(db, user, run_reason=reason)

    # llm defaults to the real OpenAI-compatible client; tests inject mocks.
    llm = llm if llm is not None else OpenAICompatibleClient()
    result = AgentLoop(reg, llm, output_guard=guard, tracer=tracer).run(
        AgentContext(task=agent_task, extra={"user_id": user_id, "mode": mode}),
        system_prompt=system_prompt,
    )

    summary = {
        "run_id": tracer.run.id,
        "stop_reason": result.stop_reason,
        "brief_id": None,
        "brief_status": None,
        "item_count": 0,
        "notification_sent": False,
        "error": None,
        "content": result.content,
        "mode": mode,
        "token_input": tracer.run.token_input,
        "token_output": tracer.run.token_output,
    }

    if mode != "chat" and result.stop_reason in SUCCESS_STOP_REASONS and result.structured:
        brief = persist_brief(
            db, user_id=user_id, run_id=tracer.run.id,
            structured=result.structured, max_items=max_items, root=root,
        )
        summary["brief_id"] = brief.id
        summary["item_count"] = brief.item_count

        # HITL：订阅要求"先审后发"时，简报保持待审，通知后置到审批通过。
        if subscription and subscription.require_approval:
            brief.status = "pending"
            db.commit()
            summary["brief_status"] = "pending"
            summary["notification_sent"] = False
        else:
            summary["brief_status"] = "published"
            summary["notification_sent"] = _notify(
                (notifiers if notifiers is not None else build_default_notifiers()),
                subscription, brief,
            )
    elif result.stop_reason not in SUCCESS_STOP_REASONS:
        summary["error"] = f"run ended with {result.stop_reason}"
    return summary


def _notify(notifiers: dict[str, Notifier], subscription, brief: Brief) -> bool:
    """Push the finished brief to the subscription's channel (email by default).

    Message 携带完整简报：邮件主题为"AI 新闻简报 <日期>（N 条）"，正文为
    Markdown 全文。Email 未配置 EMAIL_* 时由 EmailNotifier 以 DEMO 模式落
    盘 .eml（不失败、不丢简报）。
    """
    channel = (subscription.notification_channel if subscription else "email") or "email"
    notifier = notifiers.get(channel)
    if notifier is None:
        logger.warning("notification channel '%s' not available; brief already saved", channel)
        return False
    subject = f"AI 新闻简报 {brief.brief_date}（{brief.item_count} 条）"
    try:
        notifier.send(_notification_body(brief), subject=subject)
        return True
    except Exception as exc:  # notification is best-effort; never lose the brief
        logger.warning("notification failed (brief kept): %s", exc)
        return False


def _notification_body(brief: Brief) -> str:
    """Compose the pushed message: a short header followed by the full brief."""
    lines = [
        f"AI 新闻简报 {brief.brief_date}：共 {brief.item_count} 条",
        "",
        brief.content_markdown,
        "",
        "— 由 AI Radar Agent 自动生成并推送",
    ]
    return "\n".join(lines)


def _task_instruction(subscription) -> str:
    topics = subscription.topics_json if subscription else []
    topics_text = "、".join(topics) if topics else "AI 领域"
    return (
        f"为今日生成一份个性化 AI 新闻简报：重点围绕 {topics_text}。"
        "按要求的 JSON 结构输出最终简报（每一条都必须有真实来源 URL）。"
    )


# --- HITL review workflow ------------------------------------------------------


def pending_briefs(db: Session, user_id: int, limit: int = 20) -> list[Brief]:
    """Briefs awaiting human approval, newest first."""
    return (
        db.query(Brief)
        .filter(Brief.user_id == user_id, Brief.status == "pending")
        .order_by(Brief.id.desc())
        .limit(limit)
        .all()
    )


def reject_brief(db: Session, brief_id: int) -> Brief:
    """Reject a pending brief; raises ValueError for missing / not-pending rows."""
    brief = db.get(Brief, brief_id)
    if brief is None:
        raise ValueError("brief not found")
    if brief.status != "pending":
        raise ValueError("brief is not pending")
    brief.status = "rejected"
    db.commit()
    return brief


def approve_brief(db: Session, brief_id: int, *, notifiers: dict[str, Notifier] | None = None) -> Brief:
    """Publish a pending brief (HITL approval) and *then* send the notification."""
    brief = db.get(Brief, brief_id)
    if brief is None:
        raise ValueError("brief not found")
    if brief.status != "pending":
        raise ValueError("brief is not pending")
    brief.status = "published"
    db.commit()

    subscription = (
        db.query(Subscription)
        .filter(Subscription.user_id == brief.user_id)
        .order_by(Subscription.id)
        .first()
    )
    _notify(
        notifiers if notifiers is not None else build_default_notifiers(),
        subscription, brief,
    )
    return brief