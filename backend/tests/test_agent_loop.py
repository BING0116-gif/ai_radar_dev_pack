"""Agent loop tests: fully scripted LLM, offline registry (CARD-009/010)."""

import pytest

from app.agent.context import AgentContext
from app.agent.guardrails import BriefOutputGuard
from app.agent.loop import AgentLoop
from app.agent.registry import ToolRegistry
from app.core.llm_client import LLMResponse, ToolCall
from app.news.providers import NewsItem, SearchProvider
from app.tools.filesystem import register_filesystem_tools
from app.tools.web_search import register_web_search_tool


class ScriptedLLM:
    """Replays predetermined responses; records every message batch it saw."""

    def __init__(self, *responses: LLMResponse):
        self.responses = list(responses)
        self.history: list[list[dict]] = []

    def chat(self, messages, tools):
        self.history.append(list(messages))
        if not self.responses:
            raise AssertionError("script exhausted")
        return self.responses.pop(0)


class FixedProvider(SearchProvider):
    name = "fixed"

    def search(self, query, limit=10):
        return [NewsItem(title=f"item for {query}", url="https://example.com/n", source=self.name)]


def _tool_call(call_id: str, name: str, arguments: dict) -> ToolCall:
    return ToolCall(id=call_id, name=name, arguments=arguments)


@pytest.fixture
def registry(tmp_path):
    reg = ToolRegistry()
    register_filesystem_tools(reg, root=tmp_path)
    register_web_search_tool(reg, providers=[FixedProvider()])
    return reg


@pytest.fixture
def context():
    return AgentContext(task="gather news about AI coding")


# --- acceptance 1: two tool calls then final ---------------------------------

def test_two_tool_calls_then_final(registry):
    llm = ScriptedLLM(
        LLMResponse(tool_calls=[_tool_call("c1", "web_search", {"query": "AI coding", "limit": 3})]),
        LLMResponse(tool_calls=[_tool_call("c2", "write_file", {"path": "notes/a.md", "content": "# brief"})]),
        LLMResponse(content="final summary"),
    )
    loop = AgentLoop(registry, llm, max_steps=5)
    result = loop.run(AgentContext(task="summarize AI news"))

    assert result.stop_reason == "final_response"
    assert result.content == "final summary"
    assert result.step_count == 3
    assert [c.name for c in result.calls] == ["web_search", "write_file"]
    assert all(c.success for c in result.calls)

    # observations were backfilled between turns (tool messages with ids),
    # and external tool output is wrapped in the untrusted-content boundary.
    tool_msgs_after_first = [m for m in llm.history[1] if m["role"] == "tool"]
    assert tool_msgs_after_first and tool_msgs_after_first[0]["tool_call_id"] == "c1"
    assert "<external_content" in tool_msgs_after_first[0]["content"]
    assert '"ok": true' in tool_msgs_after_first[0]["content"]


# --- acceptance 2: multiple tool_calls in one turn ---------------------------

def test_multiple_tool_calls_same_turn_backfilled(registry):
    llm = ScriptedLLM(
        LLMResponse(tool_calls=[
            _tool_call("c1", "web_search", {"query": "mcp"}),
            _tool_call("c2", "list_dir", {"path": "."}),
        ]),
        LLMResponse(content="done"),
    )
    result = AgentLoop(registry, llm, max_steps=5).run(AgentContext(task="t"))

    assert result.stop_reason == "final_response"
    assert len(result.calls) == 2
    tool_msgs = [m for m in llm.history[1] if m["role"] == "tool"]
    assert [m["tool_call_id"] for m in tool_msgs] == ["c1", "c2"]


# --- acceptance 3: tool failure does not end the loop ------------------------

def test_tool_failure_continues_to_next_turn(registry, tmp_path):
    llm = ScriptedLLM(
        LLMResponse(tool_calls=[_tool_call("c1", "read_file", {"path": "does_not_exist.md"})]),
        LLMResponse(content="final despite error"),
    )
    result = AgentLoop(registry, llm, max_steps=5).run(AgentContext(task="t"))

    assert result.stop_reason == "final_response"
    assert len(result.calls) == 1
    assert result.calls[0].success is False
    assert "not a file" in result.calls[0].output_preview


# --- acceptance 4: max_steps -------------------------------------------------

def test_max_steps_stops_loop(registry):
    llm = ScriptedLLM(
        LLMResponse(tool_calls=[_tool_call("c1", "web_search", {"query": "a"})]),
        LLMResponse(tool_calls=[_tool_call("c2", "web_search", {"query": "b"})]),
        LLMResponse(tool_calls=[_tool_call("c3", "web_search", {"query": "c"})]),
    )
    result = AgentLoop(registry, llm, max_steps=3).run(AgentContext(task="t"))

    assert result.stop_reason == "max_steps"
    assert result.step_count == 3
    assert len(result.calls) == 3


# --- acceptance 5: repeated call protection -----------------------------------

def test_repeated_same_call_stops(registry):
    args = {"query": "same", "limit": 5}
    llm = ScriptedLLM(
        LLMResponse(tool_calls=[_tool_call("c1", "web_search", args)]),
        LLMResponse(tool_calls=[_tool_call("c2", "web_search", args)]),
        LLMResponse(tool_calls=[_tool_call("c3", "web_search", args)]),
    )
    result = AgentLoop(registry, llm, max_steps=5, repeat_threshold=2).run(AgentContext(task="t"))

    assert result.stop_reason == "repeated_call"
    assert len(result.calls) == 2  # third identical call was blocked before executing


def test_different_calls_do_not_trigger_repeat_guard(registry):
    llm = ScriptedLLM(
        LLMResponse(tool_calls=[_tool_call("c1", "web_search", {"query": "a"})]),
        LLMResponse(tool_calls=[_tool_call("c2", "web_search", {"query": "b"})]),
        LLMResponse(content="fine"),
    )
    result = AgentLoop(registry, llm, max_steps=5, repeat_threshold=2).run(AgentContext(task="t"))
    assert result.stop_reason == "final_response"


# --- external cancel ----------------------------------------------------------

def test_external_cancel(registry):
    llm = ScriptedLLM(LLMResponse(tool_calls=[_tool_call("c1", "web_search", {"query": "x"})]))
    result = AgentLoop(registry, llm, max_steps=5).run(
        AgentContext(task="t"), should_stop=lambda: True
    )
    assert result.stop_reason == "cancelled"
    assert result.step_count == 0


# --- CARD-010: final-output guard & one-shot repair ---------------------------

VALID_BRIEF = (
    '{"brief_date":"2026-09-17","intro":"hi","items":['
    '{"title":"n","summary":"s","source_url":"https://example.com/x"}]}'
)


def test_final_valid_json_passes_guard(registry):
    llm = ScriptedLLM(LLMResponse(content=VALID_BRIEF))
    loop = AgentLoop(registry, llm, max_steps=5, output_guard=BriefOutputGuard())
    result = loop.run(AgentContext(task="t"))
    assert result.stop_reason == "final_response"
    assert result.structured is not None
    assert result.structured["brief_date"] == "2026-09-17"


def test_final_invalid_json_repaired_once(registry):
    llm = ScriptedLLM(
        LLMResponse(content="sorry, here are bullets not json"),
        LLMResponse(content=VALID_BRIEF),
    )
    loop = AgentLoop(registry, llm, max_steps=5, output_guard=BriefOutputGuard())
    result = loop.run(AgentContext(task="t"))
    assert result.stop_reason == "repaired"
    assert result.structured is not None
    # the repair turn carried a user instruction with the validation error
    repair_msgs = llm.history[1]
    assert any(m.get("role") == "user" and "JSON" in m.get("content", "") for m in repair_msgs)


def test_final_invalid_twice_reported_as_invalid_output(registry):
    llm = ScriptedLLM(
        LLMResponse(content="not json"),
        LLMResponse(content="still not json"),
    )
    loop = AgentLoop(registry, llm, max_steps=5, output_guard=BriefOutputGuard())
    result = loop.run(AgentContext(task="t"))
    assert result.stop_reason == "invalid_output"
    assert result.structured is None