"""Tests for the final-brief output guard and JSON recovery (CARD-010)."""

from app.agent.guardrails import BriefOutputGuard, extract_json

GOOD = {
    "title": "T",
    "date": "2026-09-17",
    "items": [{"title": "n", "summary": "s", "reason": "r",
               "source_url": "https://example.com/x"}],
}


def test_extract_json_direct():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_from_markdown_fence():
    text = 'Here is the result:\n```json\n{"items": [1]}\n```\nthanks'
    assert extract_json(text) == {"items": [1]}


def test_extract_json_from_braces_in_prose():
    text = "output: {\"a\": 1} end"
    assert extract_json(text) == {"a": 1}


def test_extract_json_none_when_absent():
    assert extract_json("no json here") is None


def test_guard_accepts_valid_brief():
    result = BriefOutputGuard().validate('{"title":"T","date":"2026-09-17","items":['
                                         '{"title":"n","summary":"s","reason":"r",'
                                         '"source_url":"https://example.com/x"}]}')
    assert result.ok is True
    assert result.data["title"] == "T"
    assert result.data["items"][0]["source_url"] == "https://example.com/x"


def test_guard_rejects_missing_source_url():
    bad = {'title': "T", "date": "2026-09-17",
           "items": [{"title": "n", "summary": "s"}]}
    text = __import__("json").dumps(bad)
    result = BriefOutputGuard().validate(text)
    assert result.ok is False
    assert "source_url" in (result.error or "")


def test_guard_rejects_non_json():
    result = BriefOutputGuard().validate("sorry, just prose")
    assert result.ok is False
    assert "no JSON" in (result.error or "")