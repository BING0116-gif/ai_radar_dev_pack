"""fetch_url agent tool: fetch an HTTP(S) page and extract title/summary/date.

Only ``http``/``https`` URLs are accepted (no ``file://`` or other schemes).
The page must be declared (or sniffable as) text/html; content is capped at
500 KB. Extraction is done with the stdlib HTML parser — no JavaScript is
executed. Network/HTTP failures surface as structured tool errors.
"""

from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field

from app.agent.registry import ToolDefinition, ToolRegistry
from app.news.providers import USER_AGENT

FETCH_TIMEOUT = 20.0  # spec: web tools may relax to 20 s
MAX_HTML_BYTES = 512 * 1024
SNIPPET_CHARS = 2000


class FetchURLError(Exception):
    """The URL is not fetchable under the fetch_url policy."""


class _PageExtractor(HTMLParser):
    """Collect <title>, a few <meta> fields, and the first <p> paragraphs."""

    def __init__(self) -> None:
        super().__init__()
        self.title: str | None = None
        self.published_at: str | None = None
        self.paragraphs: list[str] = []
        self._in_title = False
        self._in_p = False
        self._p_buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "p":
            self._in_p = True
        elif tag == "meta":
            self._read_meta(attr)
        elif tag == "time" and self.published_at is None:
            self.published_at = attr.get("datetime")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "p":
            text = " ".join(self._p_buf).strip()
            if text:
                self.paragraphs.append(text)
            self._p_buf = []
            self._in_p = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title = (self.title or "") + data
        elif self._in_p:
            self._p_buf.append(data)

    def _read_meta(self, attr: dict[str, str | None]) -> None:
        prop = (attr.get("property") or attr.get("name") or "").lower()
        content = attr.get("content")
        if self.title is None and prop in ("og:title", "twitter:title"):
            self.title = content
        if self.published_at is None and prop in (
            "article:published_time", "og:published_time", "date", "pubdate",
        ):
            self.published_at = content


class FetchUrlTool:
    def __init__(self, client: httpx.Client | None = None):
        self._client = client

    def fetch_url(self, url: str) -> dict:
        scheme = urlparse(url).scheme.lower()
        if scheme not in ("http", "https"):
            raise FetchURLError(f"only http/https URLs allowed, got scheme {scheme!r}")

        response = self._request(url)
        content = response.content
        if len(content) > MAX_HTML_BYTES:
            raise FetchURLError(f"page too large ({len(content)} bytes, max {MAX_HTML_BYTES})")

        extractor = _PageExtractor()
        try:
            extractor.feed(content.decode("utf-8", errors="replace"))
        except Exception as exc:  # pragma: no cover - parser is defensive
            raise FetchURLError(f"failed to parse page: {exc}") from exc

        body = " ".join(extractor.paragraphs)
        return {
            "url": str(response.url),
            "status_code": response.status_code,
            "title": (extractor.title or "").strip(),
            "published_at": extractor.published_at,
            "snippet": body[:SNIPPET_CHARS],
        }

    def _request(self, url: str) -> httpx.Response:
        kwargs = {"timeout": FETCH_TIMEOUT, "follow_redirects": True, "headers": {"User-Agent": USER_AGENT}}
        try:
            if self._client is not None:
                response = self._client.get(url, **kwargs)
            else:
                with httpx.Client(**kwargs) as client:
                    response = client.get(url, **kwargs)
        except httpx.HTTPError as exc:
            raise FetchURLError(f"request failed for {url}: {exc}") from exc
        if response.status_code >= 400:
            raise FetchURLError(f"HTTP {response.status_code} for {url}")
        return response


class FetchURLParams(BaseModel):
    url: str = Field(description="absolute http(s) URL to read")


def register_fetch_url_tool(registry: ToolRegistry, client: httpx.Client | None = None) -> None:
    """Register fetch_url; ``client`` is injectable for tests."""
    tool = FetchUrlTool(client=client)
    registry.register(ToolDefinition(
        name="fetch_url",
        description="Fetch an http(s) page and extract title, publish time and a text summary.",
        parameters_model=FetchURLParams,
        func=tool.fetch_url,
        timeout_seconds=45,
    ))