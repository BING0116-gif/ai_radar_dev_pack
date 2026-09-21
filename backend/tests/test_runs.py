"""Tests for run_agent orchestration and notification behavior (CARD-014)."""

from datetime import date

from app.agent.registry import ToolRegistry
from app.core.llm_client import LLMResponse, ToolCall
from app.models import AgentRun, Brief, Subscription, User
from app.news.providers import NewsItem, SearchProvider
from app.services.runs import recent_titles, run_agent
from app.tools.filesystem import register_filesystem_tools
from app.tools.notify import ConsoleNotifier, Notifier, NotifyError
from app.tools.web_search import register_web_search_tool


class ScriptedLLM:
    def __init__(self, *responses):
        self.responses = list(responses)

    def chat(self, messages, tools):
        if not self.responses:
            raise AssertionError("script exhausted")
        return self.responses.pop(0)


class FixedProvider(SearchProvider):
    name = "fixed"

    def search(self, query, limit=10):
        return [NewsItem(title="story", url="https://example.com/s", source=self.name)]


BRIEF_JSON = (
    '{"brief_date":"2026-09-18","intro":"hi","items":['
    '{"title":"story","summary":"s","source_url":"https://example.com/s"}]}'
)


def _user_with_subscription(db_session, notification_channel="console"):
    user = User(name="demo", role="Agent Developer", timezone="Asia/Shanghai")
    user.subscriptions.append(Subscription(
        topics_json=["AI Coding"], keywords_json=["agent"], max_items=5,
        language="zh-CN", notification_channel=notification_channel,
    ))
    db_session.add(user)
    db_session.commit()
    return user


def _registry(tmp_path):
    reg = ToolRegistry()
    register_filesystem_tools(reg, root=tmp_path)
    register_web_search_tool(reg, providers=[FixedProvider()])
    return reg


def test_run_agent_persists_brief_and_notifies(db_session, tmp_path):
    user = _user_with_subscription(db_session)
    llm = ScriptedLLM(LLMResponse(content=BRIEF_JSON))
    summary = run_agent(db_session, user.id, llm=llm, registry=_registry(tmp_path),
                        notifiers={"console": ConsoleNotifier()}, root=tmp_path)

    assert summary["stop_reason"] == "final_response"
    assert summary["brief_id"] is not None
    assert summary["item_count"] == 1
    assert summary["notification_sent"] is True
    run = db_session.get(AgentRun, summary["run_id"])
    assert run.status == "completed"
    brief = db_session.get(Brief, summary["brief_id"])
    assert brief.item_count == 1
    assert (tmp_path / "briefs" / f"2026-09-18-{run.id}.md").exists()


class _FailingNotifier(Notifier):
    channel = "console"

    def send(self, message: str) -> None:
        raise NotifyError("channel down")


def test_notification_failure_does_not_lose_brief(db_session, tmp_path):
    user = _user_with_subscription(db_session, notification_channel="console")
    llm = ScriptedLLM(LLMResponse(content=BRIEF_JSON))
    summary = run_agent(db_session, user.id, llm=llm, registry=_registry(tmp_path),
                        notifiers={"console": _FailingNotifier()}, root=tmp_path)

    assert summary["brief_id"] is not None  # brief still saved
    assert summary["notification_sent"] is False
    assert db_session.get(Brief, summary["brief_id"]) is not None


def test_run_agent_unsupported_channel_keeps_brief(db_session, tmp_path):
    user = _user_with_subscription(db_session, notification_channel="email")
    llm = ScriptedLLM(LLMResponse(content=BRIEF_JSON))
    # notifiers 里没有 email -> 渠道不可用，但简报必须保存
    summary = run_agent(db_session, user.id, llm=llm, registry=_registry(tmp_path),
                        notifiers={"console": ConsoleNotifier()}, root=tmp_path)
    assert summary["brief_id"] is not None
    assert summary["notification_sent"] is False


def test_run_agent_email_demo_pushes_full_brief(db_session, tmp_path):
    """默认邮件推送：无 SMTP 也"发出"（.eml 落盘）且携带完整简报。"""
    from app.core.config import Settings
    from app.tools.notify import EmailNotifier

    user = _user_with_subscription(db_session, notification_channel="email")
    llm = ScriptedLLM(LLMResponse(content=BRIEF_JSON))
    settings = Settings(_env_file=None).model_copy(update={"WORKSPACE_ROOT": tmp_path})
    summary = run_agent(db_session, user.id, llm=llm, registry=_registry(tmp_path),
                        notifiers={"email": EmailNotifier(settings)}, root=tmp_path)

    assert summary["notification_sent"] is True
    emails = list((tmp_path / "emails").glob("*.eml"))
    assert len(emails) == 1
    content = emails[0].read_text(encoding="utf-8")
    assert "Subject: AI 新闻简报 2026-09-18（1 条）" in content
    assert "story" in content  # 简报正文随邮件推送


def test_recent_titles_from_briefs(db_session):
    user = _user_with_subscription(db_session)
    brief = Brief(user_id=user.id, run_id=1, brief_date=date.today(),
                  content_markdown="## 1. Old headline\n**链接**: https://x.com/1\n")
    db_session.add(brief)
    db_session.commit()
    assert "Old headline" in recent_titles(db_session, user.id)