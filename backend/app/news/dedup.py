"""Cheap deduplication and lightweight scoring signals for news candidates.

This module performs *pre-processing only*: it never decides what the agent
does next. Whether to search again, which URL to read, or when to stop stays
entirely with the LLM. No ML, no network — pure string metrics + heuristics.
"""

import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit, urlunsplit

# --- normalization -----------------------------------------------------------

_PUNCT_RE = re.compile(r"[^\w]+", re.UNICODE)


def normalize_url(url: str) -> str:
    """Canonical key: lowercase host, drop fragment/query, strip trailing slash."""
    url = (url or "").strip()
    if not url:
        return ""
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    if not host:
        return ""
    netloc = f"{host}:{parsed.port}" if parsed.port else host
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme.lower(), netloc, path, "", ""))


def normalize_title(title: str) -> str:
    """Punctuation/space-insensitive, case-insensitive title key."""
    return _PUNCT_RE.sub("", (title or "").lower())


def title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_title(a), normalize_title(b)).ratio()


# --- in-batch dedup ----------------------------------------------------------

def dedupe_items(items: list[dict], title_threshold: float = 0.9) -> tuple[list[dict], list[dict]]:
    """Keep first occurrence per normalized URL or near-identical title."""
    seen_urls: set[str] = set()
    kept_titles: list[str] = []
    kept: list[dict] = []
    dropped: list[dict] = []
    for item in items:
        url_key = normalize_url(item.get("source_url", ""))
        title_key = normalize_title(item.get("title", ""))
        if url_key and url_key in seen_urls:
            dropped.append(item)
            continue
        if any(SequenceMatcher(None, title_key, old).ratio() >= title_threshold for old in kept_titles):
            dropped.append(item)
            continue
        if url_key:
            seen_urls.add(url_key)
        kept_titles.append(title_key)
        kept.append(item)
    return kept, dropped


# --- history (recent briefs) --------------------------------------------------

def extract_history_entries(markdown: str) -> list[tuple[str, str]]:
    """Parse (url, title) pairs back out of our own rendered brief markdown."""
    entries: list[tuple[str, str]] = []
    blocks = re.split(r"(?m)^## ", markdown)[1:]
    for block in blocks:
        first_line = block.splitlines()[0] if block.splitlines() else ""
        title = first_line.split(". ", 1)[-1].strip() if "." in first_line else first_line.strip()
        link = re.search(r"\*\*链接\*\*:\s*(\S+)", block)
        if link:
            entries.append((link.group(1), title))
    return entries


def filter_against_history(
    items: list[dict],
    history_entries: list[tuple[str, str]],
    title_threshold: float = 0.9,
) -> tuple[list[dict], list[dict]]:
    """Drop items whose URL or near-identical title already appeared recently."""
    hist_urls = {normalize_url(url) for url, _ in history_entries}
    hist_titles = [normalize_title(title) for _, title in history_entries]
    kept: list[dict] = []
    dropped: list[dict] = []
    for item in items:
        url_key = normalize_url(item.get("source_url", ""))
        title_key = normalize_title(item.get("title", ""))
        if url_key and url_key in hist_urls:
            dropped.append(item)
            continue
        if any(SequenceMatcher(None, title_key, old).ratio() >= title_threshold for old in hist_titles):
            dropped.append(item)
            continue
        kept.append(item)
    return kept, dropped


# --- lightweight scoring signals ----------------------------------------------

_KNOWN_SOURCE_QUALITY = {
    "techcrunch.com": 0.9,
    "theverge.com": 0.9,
    "arstechnica.com": 0.9,
    "github.blog": 0.9,
    "blog.google": 0.9,
    "openai.com": 0.95,
    "anthropic.com": 0.95,
    "deepmind.google": 0.95,
    "news.google.com": 0.7,
}
DEFAULT_SOURCE_QUALITY = 0.7


def source_quality(url: str) -> float:
    """Heuristic 0..1; a tiny known-domain map plus a generic default."""
    host = urlsplit(url or "").hostname or ""
    for domain, q in _KNOWN_SOURCE_QUALITY.items():
        if host == domain or host.endswith(f".{domain}"):
            return q
    return DEFAULT_SOURCE_QUALITY


def _parse_published(raw: str | None, now: datetime) -> datetime | None:
    if not raw:
        return None
    try:
        return parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        pass
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def freshness(published_at: str | None, now: datetime | None = None) -> float:
    """0..1 where 1 = today; missing/unparseable date gets a neutral 0.5."""
    published = _parse_published(published_at, now)
    if published is None:
        return 0.5
    now = now or datetime.now(timezone.utc)
    age_days = max(0.0, (now - published).total_seconds() / 86400.0)
    return max(0.0, 1.0 - age_days / 7.0)


def attach_signals(item: dict, keywords: list[str] | None = None) -> dict:
    """Return a copy of the item with auxiliary scoring fields."""
    out = dict(item)
    out["source_quality"] = round(source_quality(out.get("source_url", "")), 3)
    out["freshness"] = round(freshness(out.get("published_at")), 3)
    text = f"{out.get('title', '')} {out.get('summary', '')}".lower()
    out["keyword_match"] = sum(1 for k in (keywords or []) if k and k.lower() in text)
    return out