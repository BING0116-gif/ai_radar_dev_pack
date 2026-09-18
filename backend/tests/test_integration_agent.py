"""End-to-end integration with a Mock LLM: no network, no real provider (CARD-018).

Covers the full journey the interviewer asks about: search -> fetch -> write
-> final, plus persistence of trace rows and the brief, and history-title
injection for dedup hints.
"""

from datetime import date

import httpx

from app.agent.registry import ToolRegistry
from app.core.llm_client import LLMResponse, ToolCall
from app.models import AgentRun, AgentStep, Brief, User
from app.news.providers import NewsItem, SearchProvider
from app.services.runs import recent_titles, run_agent
from app.tools.fetch_url import register_fetch_url_tool
from app.tools.filesystem import register_filesystem_tools
from app.tools.notify import ConsoleNotifier
from app.tools.web_search import register_web_search_tool


class ScriptedLLM:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.history = []

    def chat(self, messages, tools):
        self.history.append(list(messages))
        return self.responses.pop(0)


class FixedProvider(SearchProvider):
    name = "fixed"

    def search(self, query, limit=10):
        return [NewsItem(title="hit", url="https://example.com/story", source=self.name,
                         snippet="deep dive here")]


BRIEF_JSON = (
    '{"brief_date":"2026-09-18","intro":"ok","items":['
    '{"title":"hit","summary":"deep dive here","source_url":"https://example.com/story"}]}'
)


def _offline_registry(tmp_path, page_html: bytes) -> ToolRegistry:
    def handler(request):
        assert request.headers["user-agent"].startswith("AI-Radar")
        return httpx.Response(200, content=page_html, request=request)

    registry = ToolRegistry()
    register_filesystem_tools(registry, root=tmp_path)
    register_web_search_tool(registry, providers=[FixedProvider()])
    register_fetch_url_tool(registry, client=httpx.Client(transport=httpx.MockTransport(handler)))
    return registry


def _user(db_session):
    user = User(name="integration")
    db_session.add(user)
    db_session.commit()
    return user


def test_full_search_fetch_write_final_chain(db_session, tmp_path):
    llm = ScriptedLLM(
        LLMResponse(tool_calls=[ToolCall(id="c1", name="web_search", arguments={"query": "AI"})]),
        LLMResponse(tool_calls=[ToolCall(id="c2", name="fetch_url",
                                         arguments={"url": "https://example.com/story"})]),
        LLMResponse(tool_calls=[ToolCall(id="c3", name="write_file",
                                         arguments={"path": "notes/final.md", "content": "draft"})]),
        LLMResponse(content=BRIEF_JSON),
    )
    user = _user(db_session)
    summary = run_agent(
        db_session, user.id, llm=llm, registry=_offline_registry(tmp_path, b"<h1>Hit</h1><p>deep dive here</p>"),
        notifiers={"console": ConsoleNotifier()}, root=tmp_path, reason="integration",
    )

    assert summary["stop_reason"] == "final_response"
    assert summary["brief_id"] is not None

    # trace rows exist for all six event kinds of interest
    run = db_session.get(AgentRun, summary["run_id"])
    assert run.status == "completed"
    event_names = [s.tool_name for s in
                   db_session.query(AgentStep).filter(AgentStep.run_id == run.id).all()
                   if s.tool_name]
    assert "web_search" in event_names and "fetch_url" in event_names and "write_file" in event_names

    # fetch result preview reached the trace (observable evidence)
    previews = " ".join(s.tool_output_preview or "" for s in
                        db_session.query(AgentStep).filter(AgentStep.run_id == run.id).all())
    assert "deep dive here" in previews

    # write tool really created the file in the sandbox
    assert (tmp_path / "notes" / "final.md").read_text(encoding="utf-8") == "draft"

    # brief persisted
    brief = db_session.get(Brief, summary["brief_id"])
    assert brief.item_count == 1
    assert "https://example.com/story" in brief.content_markdown


def test_previous_brief_titles_inject_into_prompt(db_session, tmp_path):
    user = _user(db_session)  # same user owns both history and the new run
    db_session.add(Brief(user_id=user.id, run_id=0, brief_date=date(2026, 9, 17),
                         title="dummy", item_count=1,
                         content_markdown="## 1. Old headline\n**链接**: https://old.example.com/1\n"))
    db_session.commit()

    llm = ScriptedLLM(LLMResponse(content=BRIEF_JSON))
    summary = run_agent(db_session, user.id, llm=llm, registry=_offline_registry(tmp_path, b"x"),
                        notifiers={"console": ConsoleNotifier()}, root=tmp_path, reason="integration")
    assert summary["stop_reason"] == "final_response"

    system_prompt = llm.history[0][0]["content"]
    assert "Old headline" in system_prompt  # dedup hint from history reached the model