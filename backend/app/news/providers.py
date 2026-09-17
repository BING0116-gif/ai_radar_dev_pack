"""Pluggable, key-free news search providers.

Two providers ship by default (Google News RSS + Hacker News / Algolia).
A ``SearchProvider`` only knows how to turn a query into ``NewsItem``s; it
does not decide what the agent does with them. All network access goes
through ``httpx`` with an explicit User-Agent, timeout, and structured
failure reporting.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from urllib.parse import urlencode
from xml.etree import ElementTree

import httpx

USER_AGENT = "AI-Radar-Demo/0.1 (personalized AI news agent demo)"


class ProviderError(Exception):
    """A provider failed to fetch or parse results."""


@dataclass
class NewsItem:
    title: str
    url: str
    source: str
    published_at: str | None = None
    snippet: str | None = None


def _strip_html(text: str | None) -> str | None:
    if not text:
        return None
    return re.sub(r"<[^>]+>", " ", text).strip()


class SearchProvider(ABC):
    """Interface for turning a query into news items."""

    name: str = ""

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[NewsItem]:
        """Return up to ``limit`` items; raise ProviderError on failure."""


class _HttpMixin:
    """Shared httpx plumbing: explicit UA, redirects, timeout, client injection."""

    def __init__(self, client: httpx.Client | None = None):
        self._client = client

    def _get(self, url: str, timeout: float, params: dict | None = None) -> httpx.Response:
        if self._client is not None:
            return self._client.get(url, params=params, timeout=timeout)
        with httpx.Client(follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            return client.get(url, params=params, timeout=timeout)


class RSSSearchProvider(_HttpMixin, SearchProvider):
    """Google News live RSS feed, queried per search term."""

    name = "google_news"
    FEED_URL = "https://news.google.com/rss/search"
    TIMEOUT = 10.0

    def search(self, query: str, limit: int = 10) -> list[NewsItem]:
        url = f"{self.FEED_URL}?{urlencode({'q': query, 'hl': 'zh-CN', 'gl': 'CN', 'ceid': 'CN:zh-Hans'})}"
        try:
            response = self._get(url, timeout=self.TIMEOUT)
            response.raise_for_status()
            root = ElementTree.fromstring(response.content)
        except (httpx.HTTPError, ElementTree.ParseError) as exc:
            raise ProviderError(f"google news rss failed: {exc}") from exc

        items = []
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            if not title or not link:
                continue
            items.append(NewsItem(
                title=title,
                url=link,
                source=self.name,
                published_at=item.findtext("pubDate"),
                snippet=_strip_html(item.findtext("description")),
            ))
            if len(items) >= limit:
                break
        return items


class HackerNewsProvider(_HttpMixin, SearchProvider):
    """Hacker News search backed by the free Algolia API."""

    name = "hacker_news"
    SEARCH_URL = "https://hn.algolia.com/api/v1/search"
    TIMEOUT = 10.0

    def search(self, query: str, limit: int = 10) -> list[NewsItem]:
        try:
            response = self._get(
                self.SEARCH_URL,
                params={"query": query, "tags": "story", "hitsPerPage": limit},
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"hacker news search failed: {exc}") from exc

        items = []
        for hit in payload.get("hits", []):
            title = (hit.get("title") or "").strip()
            if not title:
                continue
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
            items.append(NewsItem(
                title=title,
                url=url,
                source=self.name,
                published_at=hit.get("created_at"),
                snippet=_strip_html(hit.get("story_text")),
            ))
            if len(items) >= limit:
                break
        return items


def build_default_providers() -> list[SearchProvider]:
    """Providers used by the web_search tool when none are injected."""
    return [RSSSearchProvider(), HackerNewsProvider()]