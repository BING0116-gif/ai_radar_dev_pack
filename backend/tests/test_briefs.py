"""Tests for brief persistence: schema parse, DB + file save (CARD-012)."""

import json
from datetime import date

from app.agent.guardrails import BriefOutputGuard
from app.models import AgentRun, Brief, User
from app.services.briefs import clean_and_limit_items, persist_brief, render_markdown

VALID_STRUCTURED = {
    "brief_date": "2026-09-17",
    "intro": "今日要点",
    "items": [
        {"title": "t1", "summary": "s1", "source_url": "https://a.example.com/1",
         "source_name": "A", "why_it_matters": "w1"},
        {"title": "t2", "summary": "s2", "source_url": "https://a.example.com/2"},
    ],
}


def _brief_text() -> str:
    return json.dumps(VALID_STRUCTURED)


def test_final_response_parses_into_brief_schema():
    result = BriefOutputGuard().validate(_brief_text())
    assert result.ok is True
    assert result.data["items"][0]["source_url"] == "https://a.example.com/1"


def test_clean_and_limit_items_drops_missing_url():
    items = [
        {"title": "ok", "source_url": "https://x.example.com"},
        {"title": "no-url"},
        {"title": "bad-scheme", "source_url": "ftp://y.example.com"},
        {"title": "ok2", "source_url": "https://z.example.com"},
    ]
    kept = clean_and_limit_items(items, max_items=10)
    assert [i["title"] for i in kept] == ["ok", "ok2"]


def test_max_items_respected():
    items = [{"title": f"t{i}", "source_url": "https://x.example.com"} for i in range(6)]
    assert len(clean_and_limit_items(items, max_items=3)) == 3


def test_persist_brief_saves_db_and_markdown(db_session, tmp_path):
    user = _make_user(db_session)
    run = AgentRun(user_id=user.id, status="completed")
    db_session.add(run)
    db_session.commit()

    brief = persist_brief(
        db_session, user_id=user.id, run_id=run.id,
        structured=VALID_STRUCTURED, max_items=10, root=tmp_path,
    )

    # database row
    saved = db_session.get(Brief, brief.id)
    assert saved.run_id == run.id
    assert saved.item_count == 2
    assert "今日要点" in saved.content_markdown
    assert "https://a.example.com/1" in saved.content_markdown
    # structured items persisted alongside the markdown
    assert saved.items_json[0]["title"] == "t1"
    assert saved.items_json[0]["source_url"] == "https://a.example.com/1"

    # workspace markdown file at workspace/briefs/YYYY-MM-DD-<run_id>.md
    expected = tmp_path / "briefs" / f"2026-09-17-{run.id}.md"
    assert expected.exists()
    assert saved.content_markdown == expected.read_text(encoding="utf-8")


def test_persist_respects_max_items(db_session, tmp_path):
    user = db_session.query(User).first() or _make_user(db_session)
    run = AgentRun(user_id=user.id, status="completed")
    db_session.add(run)
    db_session.commit()

    source = dict(VALID_STRUCTURED, items=[
        {"title": f"t{i}", "summary": "s", "source_url": f"https://x.example.com/{i}"}
        for i in range(5)
    ])
    brief = persist_brief(db_session, user_id=user.id, run_id=run.id,
                          structured=source, max_items=2, root=tmp_path)
    assert db_session.get(Brief, brief.id).item_count == 2


def test_brief_detail_schema_exposes_items(db_session, tmp_path):
    """The API envelope field maps the ORM items_json back to structured items."""
    from app.schemas.run import BriefDetail

    user = _make_user(db_session)
    run = AgentRun(user_id=user.id, status="completed")
    db_session.add(run)
    db_session.commit()

    brief = persist_brief(
        db_session, user_id=user.id, run_id=run.id,
        structured=VALID_STRUCTURED, max_items=10, root=tmp_path,
    )
    detail = BriefDetail.model_validate(db_session.get(Brief, brief.id))
    assert len(detail.items) == 2
    assert detail.items[0]["source_url"] == "https://a.example.com/1"


def test_brief_detail_schema_legacy_empty_items(db_session):
    """Old briefs without items still serialize with an empty list."""
    from app.schemas.run import BriefDetail

    user = _make_user(db_session)
    run = AgentRun(user_id=user.id, status="completed")
    db_session.add(run)
    db_session.commit()
    brief = Brief(user_id=user.id, run_id=run.id, brief_date=date.today())
    db_session.add(brief)
    db_session.commit()

    detail = BriefDetail.model_validate(db_session.get(Brief, brief.id))
    assert detail.items == []


def _make_user(db_session) -> User:
    user = User(name="u")
    db_session.add(user)
    db_session.commit()
    return user