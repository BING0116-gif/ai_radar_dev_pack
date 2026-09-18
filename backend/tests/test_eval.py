"""Tests for the evaluation harness (CARD-018)."""

from app.models import User
from app.services.eval import (
    EVAL_PROFILES,
    EvalSummary,
    _dup_rate_batch,
    _parse_items,
    _relevance,
    _source_completeness,
    run_evaluation,
)
from app.services.runs import build_default_registry
from app.tools.notify import ConsoleNotifier


def _registry(tmp_path):
    reg = build_default_registry(root=tmp_path)
    return reg


def test_metric_helpers():
    items = [
        {"title": "Claude update", "summary": "about Claude agent", "source_url": "https://x.com/1"},
        {"title": "dup", "summary": "same", "source_url": "https://x.com/1"},
        {"title": "c", "summary": "no url"},
    ]
    assert _relevance(items, ["Claude"]) == 1 / 3  # only the first item mentions Claude
    assert _dup_rate_batch(items) == 1 / 3
    assert _source_completeness(items) == 2 / 3


def test_parse_items_round_trip():
    md = (
        "# t\n\n## 1. Alpha news\n**链接**: https://x.com/1\n**摘要**: about alpha\n\n"
        "## 2. Beta news\n**链接**: https://x.com/2\n"
    )
    parsed = _parse_items(md)
    assert parsed[0]["title"] == "Alpha news"
    assert parsed[0]["source_url"] == "https://x.com/1"
    assert parsed[0]["summary"] == "about alpha"
    assert parsed[1]["summary"] == ""


def test_run_evaluation_all_profiles(db_session, tmp_path):
    summary = run_evaluation(
        db_session,
        registry=_registry(tmp_path),
        root=tmp_path,
        notifiers={"console": ConsoleNotifier()},
        profiles=EVAL_PROFILES,
    )
    assert isinstance(summary, EvalSummary)
    assert summary.runs == 5
    assert summary.success_rate == 1.0
    assert summary.avg_steps >= 1.0
    assert 0.0 <= summary.avg_relevance <= 1.0
    assert summary.dup_rate > 0.0  # in-batch dups were intentionally planted
    assert summary.source_completeness == 1.0  # every item has a valid URL

    report = summary.short_report()
    assert "profiles/runs: 5" in report
    assert "success_rate:" in report

    # a demo user was created per profile
    assert db_session.query(User).count() == 5