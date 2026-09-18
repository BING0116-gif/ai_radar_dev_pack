"""Tracing tests: runs and steps persist for success and failure (CARD-011)."""

import pytest

from app.agent.context import AgentContext
from app.agent.loop import AgentLoop
from app.agent.registry import ToolRegistry
from app.core.llm_client import LLMResponse, LLMRequestError, ToolCall
from app.models import AgentRun, AgentStep, User
from app.news.providers import NewsItem, SearchProvider
from app.services.tracing import DbTracer
from app.tools.filesystem import register_filesystem_tools
from app.tools.web_search import register_web_search_tool


class ScriptedLLM:
    def __init__(self, *responses):
        self.responses = list(responses)

    def chat(self, messages, tools):
        if not self.responses:
            raise AssertionError("script exhausted")
        return self.responses.pop(0)


class _FailingLLM:
    def chat(self, messages, tools):
        raise LLMRequestError("connection refused")


class FixedProvider(SearchProvider):
    name = "fixed"

    def search(self, query, limit=10):
        return [NewsItem(title="t", url="https://example.com/x", source=self.name)]


def _call(call_id, name, arguments):
    return ToolCall(id=call_id, name=name, arguments=arguments)


@pytest.fixture
def registry(tmp_path):
    reg = ToolRegistry()
    register_filesystem_tools(reg, root=tmp_path)
    register_web_search_tool(reg, providers=[FixedProvider()])
    return reg


@pytest.fixture
def user(db_session):
    user = User(name="tracer")
    db_session.add(user)
    db_session.commit()
    return user


def _events(db_session, run_id):
    return (
        db_session.query(AgentStep)
        .filter(AgentStep.run_id == run_id)
        .order_by(AgentStep.step_no)
        .all()
    )


def test_successful_run_persists_run_and_all_event_types(db_session, registry, user):
    llm = ScriptedLLM(
        LLMResponse(tool_calls=[_call("c1", "web_search", {"query": "ai"})]),
        LLMResponse(content='{"title":"t","date":"2026-09-17","items":[]}'),
    )
    tracer = DbTracer(db_session, user)
    result = AgentLoop(registry, llm, max_steps=5, tracer=tracer).run(AgentContext(task="t"))

    assert result.stop_reason == "final_response"
    run = db_session.get(AgentRun, tracer.run.id)
    assert run.status == "completed"
    assert run.finished_at is not None
    assert run.step_count == len(_events(db_session, run.id))

    event_types = [s.event_type for s in _events(db_session, run.id)]
    assert {"run_start", "llm_turn", "tool_call", "tool_result", "run_finish"} <= set(event_types)


def test_run_ids_are_unique(db_session, registry, user):
    llm1 = ScriptedLLM(LLMResponse(content="a"))
    llm2 = ScriptedLLM(LLMResponse(content="b"))
    t1 = DbTracer(db_session, user)
    t2 = DbTracer(db_session, user)
    AgentLoop(registry, llm1, max_steps=3, tracer=t1).run(AgentContext(task="one"))
    AgentLoop(registry, llm2, max_steps=3, tracer=t2).run(AgentContext(task="two"))

    runs = db_session.query(AgentRun).all()
    assert len(runs) == 2
    assert runs[0].id != runs[1].id


def test_every_tool_call_gets_step_with_input(db_session, registry, user):
    llm = ScriptedLLM(
        LLMResponse(tool_calls=[
            _call("c1", "web_search", {"query": "mcp"}),
            _call("c2", "list_dir", {"path": "."}),
        ]),
        LLMResponse(content="done"),
    )
    tracer = DbTracer(db_session, user)
    AgentLoop(registry, llm, max_steps=5, tracer=tracer).run(AgentContext(task="t"))

    tool_steps = [s for s in _events(db_session, tracer.run.id) if s.event_type == "tool_call"]
    assert len(tool_steps) == 2
    assert {"web_search", "list_dir"} == {s.tool_name for s in tool_steps}
    assert all(s.tool_input_json for s in tool_steps)


def test_tool_failure_is_traced(db_session, registry, user):
    llm = ScriptedLLM(
        LLMResponse(tool_calls=[_call("c1", "read_file", {"path": "missing.md"})]),
        LLMResponse(content="ok"),
    )
    tracer = DbTracer(db_session, user)
    result = AgentLoop(registry, llm, max_steps=5, tracer=tracer).run(AgentContext(task="t"))
    assert result.calls[0].success is False

    results = [s for s in _events(db_session, tracer.run.id) if s.event_type == "tool_result"]
    assert results[0].success is False
    assert "not a file" in (results[0].tool_output_preview or "")


def test_error_run_marks_failed_and_records_run_error(db_session, registry, user):
    tracer = DbTracer(db_session, user)
    loop = AgentLoop(registry, _FailingLLM(), max_steps=3, tracer=tracer)
    with pytest.raises(LLMRequestError):
        loop.run(AgentContext(task="t"))

    run = db_session.get(AgentRun, tracer.run.id)
    assert run.status == "failed"
    assert "connection refused" in (run.error_message or "")
    events = [s.event_type for s in _events(db_session, run.id)]
    assert "run_error" in events


def test_trace_does_not_leak_env_api_key(db_session, registry, user, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-topsecret-demo-value")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.test")
    monkeypatch.setenv("LLM_MODEL", "m")
    llm = ScriptedLLM(
        LLMResponse(tool_calls=[_call("c1", "web_search", {"query": "q"})]),
        LLMResponse(content="fine"),
    )
    tracer = DbTracer(db_session, user)
    AgentLoop(registry, llm, max_steps=5, tracer=tracer).run(AgentContext(task="t"))

    previews = " ".join(s.tool_output_preview or "" for s in _events(db_session, tracer.run.id))
    assert "sk-topsecret-demo-value" not in previews