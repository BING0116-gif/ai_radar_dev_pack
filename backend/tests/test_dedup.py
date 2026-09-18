"""Tests for news dedup and lightweight scoring signals (CARD-013)."""

import pytest

from app.agent.registry import ToolRegistry
from app.news.dedup import (
    attach_signals,
    dedupe_items,
    extract_history_entries,
    filter_against_history,
    normalize_title,
    normalize_url,
    title_similarity,
)
from app.news.providers import NewsItem, SearchProvider
from app.tools.web_search import register_web_search_tool


def test_normalize_url_drops_query_fragment_and_case():
    assert normalize_url("https://Example.COM/a?utm_source=x#frag") == "https://example.com/a"
    assert normalize_url("https://example.com/a/") == "https://example.com/a"


def test_normalize_title_collapses_punctuation_and_case():
    assert normalize_title("OpenAI releases GPT-5!") == "openaireleasesgpt5"


def test_same_url_deduplicated():
    items = [
        {"title": "A", "source_url": "https://x.com/a"},
        {"title": "B", "source_url": "https://x.com/a?utm=1"},
    ]
    kept, dropped = dedupe_items(items)
    assert len(kept) == 1 and len(dropped) == 1
    assert kept[0]["title"] == "A"


def test_high_similarity_titles_deduplicated():
    items = [
        {"title": "OpenAI releases GPT-5", "source_url": "https://x.com/1"},
        {"title": "OpenAI Releases GPT 5", "source_url": "https://y.com/2"},
    ]
    kept, dropped = dedupe_items(items)
    assert len(kept) == 1 and len(dropped) == 1


def test_low_similarity_titles_both_kept():
    items = [
        {"title": "OpenAI releases GPT-5", "source_url": "https://x.com/1"},
        {"title": "Local bakery opens downtown", "source_url": "https://y.com/2"},
    ]
    kept, dropped = dedupe_items(items)
    assert len(kept) == 2 and not dropped


def test_extract_history_entries_round_trip():
    markdown = (
        "# AI 新闻简报 2026-09-17\n\n"
        "## 1. First story\n**来源**: A\n**链接**: https://x.com/1\n\n"
        "## 2. Second story\n**链接**: https://y.com/2\n"
    )
    entries = extract_history_entries(markdown)
    assert ("https://x.com/1", "First story") in entries
    assert ("https://y.com/2", "Second story") in entries


def test_filter_against_history_identifies_duplicates():
    items = [
        {"title": "Fresh news", "source_url": "https://x.com/new"},
        {"title": "Old story", "source_url": "https://x.com/old"},
        {"title": "Old Story!", "source_url": "https://y.com/old"},
    ]
    history = [("https://x.com/old", "Old story")]
    kept, dropped = filter_against_history(items, history)
    assert [i["title"] for i in kept] == ["Fresh news"]
    assert len(dropped) == 2  # same URL + near-identical title


def test_attach_signals():
    item = {"title": "Claude Code tips", "summary": "agent coding", "source_url": "https://anthropic.com/x"}
    out = attach_signals(item, keywords=["Claude", "none"])
    assert out["keyword_match"] == 1
    assert out["source_quality"] == 0.95  # anthropic.com in known map
    assert 0.0 <= out["freshness"] <= 1.0


class _DupProvider(SearchProvider):
    name = "dup"

    def search(self, query, limit=10):
        return [
            NewsItem(title="Same story", url="https://example.com/a", source=self.name),
            NewsItem(title="Same Story!", url="https://example.com/a?utm=2", source=self.name),
            NewsItem(title="Different story", url="https://example.com/b", source=self.name),
        ]


def test_web_search_dedupes_and_attaches_signals():
    registry = ToolRegistry()
    register_web_search_tool(registry, providers=[_DupProvider()])
    result = registry.execute("web_search", {"query": "q", "keywords": ["Same"]})
    assert result.success is True
    items = result.data["items"]
    assert len(items) == 2  # one duplicated pair removed
    assert all("source_quality" in i and "freshness" in i and "keyword_match" in i for i in items)


def test_agent_ordering_unaffected_by_dedup(tmp_path):
    """Dedup happens inside the tool; the loop's model-driven ordering is untouched."""
    from app.agent.context import AgentContext
    from app.agent.loop import AgentLoop
    from app.core.llm_client import LLMResponse, ToolCall
    from app.tools.filesystem import register_filesystem_tools

    class ScriptedLLM:
        def __init__(self, *responses):
            self.responses = list(responses)

        def chat(self, messages, tools):
            return self.responses.pop(0)

    registry = ToolRegistry()
    register_web_search_tool(registry, providers=[_DupProvider()])
    register_filesystem_tools(registry, root=tmp_path)

    llm = ScriptedLLM(
        LLMResponse(tool_calls=[ToolCall(id="c1", name="web_search", arguments={"query": "q"})]),
        LLMResponse(tool_calls=[ToolCall(id="c2", name="list_dir", arguments={"path": "."})]),
        LLMResponse(content="final"),
    )
    result = AgentLoop(registry, llm, max_steps=5).run(AgentContext(task="t"))
    assert result.stop_reason == "final_response"
    assert [c.name for c in result.calls] == ["web_search", "list_dir"]