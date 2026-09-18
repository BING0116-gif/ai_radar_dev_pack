"""Lightweight agent evaluation: fixed user profiles + Mock LLM -> metrics.

Measures the same things an interviewer asks about — relevance, duplicate
rate, source completeness, success rate, average steps — computed from the
*persisted outputs* (brief markdown) of deterministic Mock-LLM runs, so the
results are stable and require no live LLM or network.
"""

import json
import logging
import re
from dataclasses import dataclass

from app.core.llm_client import LLMResponse
from app.news.dedup import attach_signals, normalize_url

logger = logging.getLogger("app.services.eval")

EVAL_PROFILES = [
    {"name": "Agent Developer", "role": "Agent Developer",
     "topics": ["AI Coding"], "keywords": ["Claude", "Agent"]},
    {"name": "AI Researcher", "role": "Researcher",
     "topics": ["LLM", "MCP"], "keywords": ["model", "protocol"]},
    {"name": "Startup Founder", "role": "Founder",
     "topics": ["AI Startup"], "keywords": ["funding", "startup"]},
    {"name": "CS Student", "role": "Student",
     "topics": ["Deep Learning"], "keywords": ["paper", "training"]},
    {"name": "Product Manager", "role": "PM",
     "topics": ["AI Products"], "keywords": ["launch", "product"]},
]


@dataclass
class EvalSummary:
    runs: int
    success_rate: float
    avg_steps: float
    avg_relevance: float
    dup_rate: float
    source_completeness: float

    def short_report(self) -> str:
        return (
            "[eval summary]\n"
            f"  profiles/runs: {self.runs}\n"
            f"  success_rate:  {self.success_rate:.2f}\n"
            f"  avg_steps:     {self.avg_steps:.1f}\n"
            f"  avg_relevance: {self.avg_relevance:.2f}\n"
            f"  dup_rate:      {self.dup_rate:.2f}\n"
            f"  source_ok:     {self.source_completeness:.2f}"
        )


class MockBriefLLM:
    """Returns one deterministic final brief built from the given items."""

    def __init__(self, items: list[dict]):
        self._payload = json.dumps(
            {"brief_date": "2026-09-18", "intro": "eval", "items": items}, ensure_ascii=False
        )
        self.requests = 0

    def chat(self, messages, tools):
        self.requests += 1
        return LLMResponse(content=self._payload)


def _parse_items(markdown: str) -> list[dict]:
    """Recover items (title/url/summary) from our rendered brief markdown."""
    items = []
    for block in re.split(r"(?m)^## ", markdown)[1:]:
        lines = block.splitlines()
        title = lines[0].split(". ", 1)[-1].strip() if "." in lines[0] else lines[0].strip()
        url = re.search(r"\*\*链接\*\*:\s*(\S+)", block)
        summary = re.search(r"\*\*摘要\*\*:\s*(.*)", block)
        items.append({
            "title": title,
            "source_url": url.group(1) if url else "",
            "summary": summary.group(1).strip() if summary else "",
        })
    return items


def _valid_url(url: str) -> bool:
    return isinstance(url, str) and url.startswith(("http://", "https://"))


def _relevance(items: list[dict], keywords: list[str]) -> float:
    kws = [k for k in keywords if k]
    if not items or not kws:
        return 0.0
    scores = [attach_signals(i, kws)["keyword_match"] / len(kws) for i in items]
    return sum(scores) / len(scores)


def _dup_rate_batch(items: list[dict]) -> float:
    keys = [normalize_url(i.get("source_url", "")) for i in items if _valid_url(i.get("source_url", ""))]
    if len(keys) < 2:
        return 0.0
    # duplicated URLs over ALL items (missing-URL items lower the rate, not raise it)
    return (len(keys) - len(set(keys))) / len(items)


def _source_completeness(items: list[dict]) -> float:
    if not items:
        return 0.0
    return sum(1 for i in items if _valid_url(i.get("source_url", ""))) / len(items)


def _build_items(profile_index: int, prev_url: str) -> list[dict]:
    """Three items per profile: one in-batch dup + one dup against history."""
    kw = EVAL_PROFILES[profile_index]["keywords"][0] or "AI"
    base = f"https://eval.example/{profile_index}"
    return [
        {"title": f"{kw} news A", "summary": f"report about {kw} and tools", "source_url": base},
        {"title": f"{kw} news B", "summary": f"follow-up on {kw}", "source_url": base},  # in-batch dup
        {"title": f"{kw} news C", "summary": f"{kw} update today",
         "source_url": prev_url or f"{base}/c"},  # dup vs previous run (except first)
    ]


def run_evaluation(
    db,
    *,
    registry,
    root,
    notifiers,
    profiles: list[dict] | None = None,
) -> EvalSummary:
    """Deterministic eval across fixed profiles; returns an EvalSummary."""
    from app.models import AgentRun, User
    from app.services import runs as runs_service

    profiles = profiles or EVAL_PROFILES
    run_stats: list[dict] = []
    prev_url: str | None = None

    for index, profile in enumerate(profiles):
        user = User(name=profile["name"], role=profile["role"], timezone="Asia/Shanghai")
        db.add(user)
        db.flush()
        from app.models import Subscription

        db.add(Subscription(user_id=user.id, topics_json=profile["topics"],
                            keywords_json=profile["keywords"], max_items=5, language="zh-CN"))
        db.commit()

        items = _build_items(index, prev_url)
        prev_url = items[-1]["source_url"]
        llm = MockBriefLLM(items)
        summary = runs_service.run_agent(
            db, user.id, llm=llm, registry=registry, notifiers=notifiers, root=root, reason="eval",
        )

        run = db.get(AgentRun, summary["run_id"])
        from app.models import Brief

        brief = db.query(Brief).filter(Brief.run_id == run.id).first()
        parsed = _parse_items(brief.content_markdown) if brief else []
        run_stats.append({
            "ok": summary["stop_reason"] in ("final_response", "repaired"),
            "steps": run.step_count if run else 0,
            "items": parsed,
            "keywords": profile["keywords"],
        })

    runs_count = len(run_stats)
    summary = EvalSummary(
        runs=runs_count,
        success_rate=sum(1 for r in run_stats if r["ok"]) / runs_count,
        avg_steps=sum(r["steps"] for r in run_stats) / runs_count,
        avg_relevance=sum(_relevance(r["items"], r["keywords"]) for r in run_stats) / runs_count,
        dup_rate=sum(_dup_rate_batch(r["items"]) for r in run_stats) / runs_count,
        source_completeness=sum(_source_completeness(r["items"]) for r in run_stats) / runs_count,
    )
    logger.info("%s", summary.short_report().replace("\n", " | "))
    return summary