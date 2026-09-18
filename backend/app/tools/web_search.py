"""web_search agent tool: query pluggable news providers, fall back on failure.

Results are cheaply pre-processed (in-batch dedup + scoring signals) before
being handed to the model, but the tool never decides what the agent does
next — that remains the LLM's call.
"""

from dataclasses import asdict

from pydantic import BaseModel, Field

from app.agent.registry import ToolDefinition, ToolRegistry
from app.news.dedup import attach_signals, dedupe_items
from app.news.providers import ProviderError, SearchProvider, build_default_providers


class WebSearchParams(BaseModel):
    query: str = Field(description="search query, e.g. 'Claude Code'")
    limit: int = Field(default=5, ge=1, le=20, description="max items")
    provider: str = Field(default="auto", description="auto | google_news | hacker_news")
    keywords: list[str] = Field(
        default_factory=list,
        description="optional user keywords used to compute the keyword_match signal",
    )


class WebSearchTool:
    """Runs a query across providers until one returns results."""

    def __init__(self, providers: list[SearchProvider]):
        self._providers = providers

    def web_search(self, query: str, limit: int = 5, provider: str = "auto",
                   keywords: list[str] | None = None) -> dict:
        pool = self._select(provider)
        last_error: str | None = None
        for prov in pool:
            try:
                items = prov.search(query, limit=limit)
            except ProviderError as exc:
                last_error = str(exc)
                continue  # try the next provider
            if items:
                dicts = [asdict(item) for item in items]
                kept, _dropped = dedupe_items(dicts)
                payload = [attach_signals(item, keywords) for item in kept]
                return {
                    "query": query,
                    "provider": prov.name,
                    "items": payload,
                }
        raise ProviderError(f"all search providers failed: {last_error or 'no results'}")

    def _select(self, provider: str) -> list[SearchProvider]:
        if provider == "auto":
            return self._providers
        for prov in self._providers:
            if prov.name == provider:
                return [prov]
        raise ProviderError(f"unknown provider: {provider}")


def register_web_search_tool(
    registry: ToolRegistry, providers: list[SearchProvider] | None = None
) -> None:
    """Register web_search; ``providers`` defaults to the built-in two."""
    tool = WebSearchTool(providers if providers is not None else build_default_providers())
    registry.register(ToolDefinition(
        name="web_search",
        description="Search real news via key-free providers (Google News RSS / Hacker News).",
        parameters_model=WebSearchParams,
        func=tool.web_search,
        timeout_seconds=30,
    ))