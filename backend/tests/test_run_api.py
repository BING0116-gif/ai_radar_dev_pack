"""API tests for run/brief/trace endpoints (CARD-015)."""

import pytest

from app.agent.registry import ToolRegistry
from app.core.llm_client import LLMResponse, ToolCall
from app.news.providers import NewsItem, SearchProvider
from app.services import briefs as briefs_service
from app.services import runs as runs_service
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
        return [NewsItem(title="api story", url="https://example.com/api",
                         source=self.name, snippet="x" * 900)]


BRIEF_JSON = (
    '{"brief_date":"2026-09-18","intro":"hi","items":['
    '{"title":"api story","summary":"s","source_url":"https://example.com/api"}]}'
)


@pytest.fixture
def api_llm(monkeypatch):
    llm = ScriptedLLM(
        LLMResponse(tool_calls=[ToolCall(id="c1", name="web_search",
                                         arguments={"query": "AI"})]),
        LLMResponse(content=BRIEF_JSON),
    )
    monkeypatch.setattr(runs_service, "get_default_llm", lambda: llm)
    return llm


@pytest.fixture
def tmp_settings(tmp_path):
    from app.core.config import Settings

    return Settings(_env_file=None).model_copy(update={"WORKSPACE_ROOT": tmp_path})


@pytest.fixture
def patched_run_env(monkeypatch, tmp_settings):
    reg = ToolRegistry()
    register_web_search_tool(reg, providers=[FixedProvider()])
    monkeypatch.setattr(runs_service, "build_default_registry", lambda root=None: reg)
    monkeypatch.setattr(runs_service, "get_settings", lambda: tmp_settings)
    monkeypatch.setattr(briefs_service, "get_settings", lambda: tmp_settings)


def test_post_run_then_read_run_brief_and_steps(client, api_llm, patched_run_env):
    created = client.post("/api/runs")
    assert created.status_code == 200
    body = created.json()
    assert body["code"] == 0
    run_id = body["data"]["run_id"]
    assert isinstance(run_id, int)
    assert body["data"]["brief_id"] is not None

    run = client.get(f"/api/runs/{run_id}")
    assert run.json()["data"]["status"] == "completed"

    steps = client.get(f"/api/runs/{run_id}/steps")
    step_data = steps.json()["data"]
    event_types = {s["event_type"] for s in step_data}
    assert {"run_start", "tool_call", "tool_result", "run_finish"} <= event_types

    briefs = client.get("/api/briefs")
    assert len(briefs.json()["data"]) == 1
    brief_id = briefs.json()["data"][0]["id"]

    detail = client.get(f"/api/briefs/{brief_id}")
    assert "api story" in detail.json()["data"]["content_markdown"]


def test_run_not_found_returns_unified_404(client):
    resp = client.get("/api/runs/99999")
    assert resp.status_code == 404
    body = resp.json()
    assert set(body.keys()) == {"code", "message", "data"}
    assert body["code"] == 40401


def test_brief_not_found_returns_unified_404(client):
    resp = client.get("/api/briefs/99999")
    assert resp.status_code == 404
    assert resp.json()["code"] == 40402


def test_steps_do_not_expose_full_tool_output(client, api_llm, patched_run_env):
    run_id = client.post("/api/runs").json()["data"]["run_id"]
    steps = client.get(f"/api/runs/{run_id}/steps").json()["data"]
    previews = [s["tool_output_preview"] for s in steps if s["tool_output_preview"]]
    assert previews
    assert all(len(p) <= 500 for p in previews)  # truncated, never full output


def test_empty_lists_are_unified_ok(client):
    runs = client.get("/api/runs")
    briefs = client.get("/api/briefs")
    assert runs.status_code == 200 and runs.json()["code"] == 0
    assert briefs.status_code == 200 and briefs.json()["code"] == 0
    assert runs.json()["data"] == [] and briefs.json()["data"] == []