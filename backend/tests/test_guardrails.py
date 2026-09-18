"""Tests for the final-brief output guard and JSON recovery (CARD-010/012)."""

import json

from app.agent.guardrails import BriefOutputGuard, extract_json

GOOD = {"a": 1}


def test_extract_json_direct():
    assert extract_json('{"a": 1}') == GOOD


def test_extract_json_from_markdown_fence():
    text = 'Here is the result:\n```json\n{"items": [1]}\n```\nthanks'
    assert extract_json(text) == {"items": [1]}


def test_extract_json_from_braces_in_prose():
    text = "output: {\"a\": 1} end"
    assert extract_json(text) == GOOD


def test_extract_json_none_when_absent():
    assert extract_json("no json here") is None


def _valid_brief_text() -> str:
    return json.dumps({
        "brief_date": "2026-09-17",
        "intro": "今日要点",
        "items": [{
            "title": "n",
            "summary": "s",
            "why_it_matters": "w",
            "source_name": "Example",
            "source_url": "https://example.com/x",
            "published_at": "2026-09-17T08:00:00Z",
            "topics": ["ai"],
        }],
    })


def test_guard_accepts_valid_brief():
    result = BriefOutputGuard().validate(_valid_brief_text())
    assert result.ok is True
    assert result.data["brief_date"] == "2026-09-17"
    assert result.data["items"][0]["source_url"] == "https://example.com/x"
    assert result.data["items"][0]["why_it_matters"] == "w"
    assert result.data["items"][0]["topics"] == ["ai"]


def test_guard_rejects_missing_source_url():
    bad = {
        "brief_date": "2026-09-17",
        "items": [{"title": "n", "summary": "s"}],
    }
    result = BriefOutputGuard().validate(json.dumps(bad))
    assert result.ok is False
    assert "source_url" in (result.error or "")


def test_guard_rejects_non_json():
    result = BriefOutputGuard().validate("sorry, just prose")
    assert result.ok is False
    assert "no JSON" in (result.error or "")