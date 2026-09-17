"""Tests for news providers and web tools (CARD-008), all offline via MockTransport."""

import httpx
import pytest

from app.agent.registry import ToolRegistry
from app.news.providers import (
    HackerNewsProvider,
    NewsItem,
    ProviderError,
    RSSSearchProvider,
    SearchProvider,
)
from app.tools.fetch_url import register_fetch_url_tool
from app.tools.web_search import register_web_search_tool

RSS_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<item>
  <title>AI news title</title>
  <link>https://example.com/a</link>
  <pubDate>Wed, 17 Sep 2026 00:00:00 GMT</pubDate>
  <description>&lt;p&gt;Some snippet&lt;/p&gt;</description>
</item>
<item>
  <title>Second</title>
  <link>https://example.com/b</link>
</item>
</channel></rss>"""

HN_JSON = {
    "hits": [
        {"title": "Great HN Story", "url": None, "objectID": "123",
         "story_text": "<p>details here</p>", "created_at": "2026-09-17T00:00:00Z"},
        {"title": "Other Story", "url": "https://x.com/y", "objectID": "456",
         "created_at": "2026-09-16T00:00:00Z"},
    ]
}

SIMPLE_HTML = b"""<html><head>
<title>My Page</title>
<meta property="article:published_time" content="2026-09-17T08:00:00Z"/>
</head><body>
<p>First paragraph with some news.</p>
<p>Second paragraph here.</p>
</body></html>"""


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


# --- provider parsing --------------------------------------------------------

def test_google_news_rss_parses_items():
    def handler(request):
        return httpx.Response(200, content=RSS_XML, request=request)

    provider = RSSSearchProvider(client=_client(handler))
    items = provider.search("ai", limit=10)
    assert [i.title for i in items] == ["AI news title", "Second"]
    assert items[0].url == "https://example.com/a"
    assert items[0].source == "google_news"
    assert items[0].published_at is not None
    assert items[0].snippet == "Some snippet"


def test_hacker_news_parses_items_and_retains_source():
    def handler(request):
        return httpx.Response(200, json=HN_JSON, request=request)

    provider = HackerNewsProvider(client=_client(handler))
    items = provider.search("coding", limit=10)
    assert len(items) == 2
    assert items[0].url == "https://news.ycombinator.com/item?id=123"
    assert items[0].source == "hacker_news"
    assert items[0].snippet == "details here"
    assert items[1].url == "https://x.com/y"


def test_provider_failure_raises_structured_error():
    def handler(request):
        raise httpx.ConnectTimeout("boom", request=request)

    provider = RSSSearchProvider(client=_client(handler))
    with pytest.raises(ProviderError):
        provider.search("ai")


# --- web_search tool ---------------------------------------------------------

class _FailingProvider(SearchProvider):
    name = "broken"

    def search(self, query, limit=10):
        raise ProviderError("network down")


class _FixedProvider(SearchProvider):
    name = "fixed"

    def search(self, query, limit=10):
        return [NewsItem(title="t", url="https://e.com/x", source=self.name)]


def test_web_search_falls_back_to_next_provider():
    registry = ToolRegistry()
    register_web_search_tool(registry, providers=[_FailingProvider(), _FixedProvider()])
    result = registry.execute("web_search", {"query": "ai", "provider": "auto"})
    assert result.success is True
    assert result.data["provider"] == "fixed"
    assert result.data["items"][0]["url"] == "https://e.com/x"


def test_web_search_all_failed_is_structured_failure():
    registry = ToolRegistry()
    register_web_search_tool(registry, providers=[_FailingProvider()])
    result = registry.execute("web_search", {"query": "ai"})
    assert result.success is False
    assert "all search providers failed" in (result.error or "")


def test_web_search_unknown_provider_rejected():
    registry = ToolRegistry()
    register_web_search_tool(registry, providers=[_FixedProvider()])
    result = registry.execute("web_search", {"query": "ai", "provider": "nope"})
    assert result.success is False
    assert "unknown provider" in (result.error or "")


# --- fetch_url tool ----------------------------------------------------------

def test_fetch_url_extracts_page():
    def handler(request):
        assert request.headers["user-agent"].startswith("AI-Radar")
        return httpx.Response(200, content=SIMPLE_HTML, request=request)

    registry = ToolRegistry()
    register_fetch_url_tool(registry, client=_client(handler))
    result = registry.execute("fetch_url", {"url": "https://example.com/page"})
    assert result.success is True
    assert result.data["title"] == "My Page"
    assert result.data["published_at"] == "2026-09-17T08:00:00Z"
    assert "First paragraph" in result.data["snippet"]


def test_fetch_url_rejects_non_http_scheme():
    registry = ToolRegistry()
    register_fetch_url_tool(registry, client=_client(lambda r: httpx.Response(200)))
    result = registry.execute("fetch_url", {"url": "file:///etc/passwd"})
    assert result.success is False
    assert "http" in (result.error or "")


def test_fetch_url_404_is_structured_failure_not_crash():
    def handler(request):
        return httpx.Response(404, content=b"not found", request=request)

    registry = ToolRegistry()
    register_fetch_url_tool(registry, client=_client(handler))
    result = registry.execute("fetch_url", {"url": "https://example.com/missing"})
    assert result.success is False
    assert "404" in (result.error or "")


def test_fetch_url_timeout_is_structured_failure_not_crash():
    def handler(request):
        raise httpx.ConnectTimeout("timed out", request=request)

    registry = ToolRegistry()
    register_fetch_url_tool(registry, client=_client(handler))
    result = registry.execute("fetch_url", {"url": "https://example.com/slow"})
    assert result.success is False
    assert "request failed" in (result.error or "")


def test_fetch_url_oversized_page_rejected():
    def handler(request):
        return httpx.Response(200, content=b"a" * (512 * 1024 + 1), request=request)

    registry = ToolRegistry()
    register_fetch_url_tool(registry, client=_client(handler))
    result = registry.execute("fetch_url", {"url": "https://example.com/huge"})
    assert result.success is False
    assert "too large" in (result.error or "")