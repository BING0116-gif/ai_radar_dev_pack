"""HITL review workflow (A2) + per-item feedback loop tests."""

import pytest

from app.agent.prompts import build_system_prompt
from app.agent.registry import ToolRegistry
from app.core.llm_client import LLMResponse
from app.models import Feedback, Subscription
from app.news.providers import NewsItem, SearchProvider
from app.services import briefs as briefs_service
from app.services import runs as runs_service
from app.tools.web_search import register_web_search_tool


class ScriptedLLM:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.last_messages = None

    def chat(self, messages, tools):
        self.last_messages = messages
        if not self.responses:
            raise AssertionError("script exhausted")
        return self.responses.pop(0)


class FixedProvider(SearchProvider):
    name = "fixed"

    def search(self, query, limit=10):
        return [NewsItem(title="api story", url="https://example.com/api",
                         source=self.name, snippet="x" * 900)]


BRIEF_JSON = (
    '{"brief_date":"2026-09-18","intro":"hi","items":['
    '{"title":"api story","summary":"s","source_url":"https://example.com/api"}]}'
)


@pytest.fixture
def api_llm(monkeypatch):
    llm = ScriptedLLM(LLMResponse(content=BRIEF_JSON))
    monkeypatch.setattr(runs_service, "get_default_llm", lambda: llm)
    return llm


@pytest.fixture
def tmp_settings(tmp_path):
    from app.core.config import Settings

    return Settings(_env_file=None).model_copy(update={"WORKSPACE_ROOT": tmp_path})


@pytest.fixture
def patched_run_env(monkeypatch, tmp_settings):
    reg = ToolRegistry()
    register_web_search_tool(reg, providers=[FixedProvider()])
    monkeypatch.setattr(runs_service, "build_default_registry", lambda root=None: reg)
    monkeypatch.setattr(runs_service, "get_settings", lambda: tmp_settings)
    monkeypatch.setattr(briefs_service, "get_settings", lambda: tmp_settings)


def _enable_approval(client, db_session, *, on: bool = True) -> None:
    """Materialize the demo user and toggle require_approval on their subscription."""
    resp = client.get("/api/subscription")
    user_id = resp.json()["data"]["user_id"]
    sub = db_session.query(Subscription).filter(
        Subscription.user_id == user_id
    ).first()
    if sub is None:
        sub = Subscription(user_id=user_id, max_items=5)
        db_session.add(sub)
    sub.require_approval = on
    db_session.commit()


# --- HITL review flow ----------------------------------------------------------


def test_require_approval_holds_brief_pending_then_approve_and_notify(
    client, api_llm, patched_run_env, db_session, monkeypatch
):
    _enable_approval(client, db_session)

    created = client.post("/api/runs")
    assert created.status_code == 200
    data = created.json()["data"]
    assert data["brief_status"] == "pending"

    # pending queue shows exactly this brief
    reviews = client.get("/api/reviews").json()["data"]
    assert len(reviews) == 1
    assert reviews[0]["status"] == "pending"
    brief_id = reviews[0]["id"]

    # approving publishes it
    approved = client.post(f"/api/reviews/{brief_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["data"]["status"] == "published"
    assert client.get("/api/reviews").json()["data"] == []


def test_reject_marks_brief_rejected(client, api_llm, patched_run_env, db_session):
    _enable_approval(client, db_session)
    client.post("/api/runs")
    brief_id = client.get("/api/reviews").json()["data"][0]["id"]

    rejected = client.post(f"/api/reviews/{brief_id}/reject")
    assert rejected.json()["data"]["status"] == "rejected"
    assert client.get("/api/reviews").json()["data"] == []


def test_review_actions_guard_bad_states(client, api_llm, patched_run_env, db_session):
    _enable_approval(client, db_session)

    missing = client.post("/api/reviews/99999/approve")
    assert missing.status_code == 404 and missing.json()["code"] == 40402

    client.post("/api/runs")
    brief_id = client.get("/api/reviews").json()["data"][0]["id"]

    # first approval consumes the pending state; second must fail with 42204
    client.post(f"/api/reviews/{brief_id}/approve")
    again = client.post(f"/api/reviews/{brief_id}/approve")
    assert again.status_code == 422 and again.json()["code"] == 42204


def test_brief_mode_default_still_publishes(client, api_llm, patched_run_env):
    created = client.post("/api/runs")
    body = created.json()["data"]
    assert body["brief_status"] == "published"
    assert body["brief_id"] is not None
    assert client.get("/api/reviews").json()["data"] == []


# --- feedback loop --------------------------------------------------------------


def test_feedback_upsert_and_list(client, db_session):
    first = client.post("/api/feedback", json={
        "item_key": "https://example.com/api",
        "item_title": "api story",
        "verdict": "like",
    })
    assert first.status_code == 200
    assert first.json()["data"]["verdict"] == "like"

    # same item, new verdict -> upsert (single row)
    second = client.post("/api/feedback", json={
        "item_key": "https://example.com/api",
        "verdict": "read",
    })
    assert second.json()["data"]["verdict"] == "read"

    rows = client.get("/api/feedback").json()["data"]
    assert len(rows) == 1
    assert rows[0]["item_key"] == "https://example.com/api"
    assert rows[0]["verdict"] == "read"
    assert rows[0]["item_title"] == "api story"

    counts = db_session.query(Feedback).count()
    assert counts == 1


def test_feedback_invalid_verdict_rejected(client):
    resp = client.post("/api/feedback", json={
        "item_key": "https://example.com/api", "verdict": "meh",
    })
    assert resp.status_code == 422
    assert resp.json()["code"] == 42200


def test_feedback_delete_accepts_url_keys(client):
    """item_key 常为含 / 的 URL，删除必须走 query 参数而不是路径段。"""
    from urllib.parse import quote

    client.post("/api/feedback", json={
        "item_key": "https://example.com/path/with/slashes",
        "item_title": "x", "verdict": "like",
    })
    assert len(client.get("/api/feedback").json()["data"]) == 1

    deleted = client.delete(f"/api/feedback?item_key={quote('https://example.com/path/with/slashes', safe='')}")
    assert deleted.status_code == 200
    assert deleted.json()["data"]["removed"] is True
    assert client.get("/api/feedback").json()["data"] == []


def test_recent_feedback_groups_and_prompt_injects(client, db_session):
    from app.models import User

    demo_user_id = client.get("/api/subscription").json()["data"]["user_id"]
    user_id = db_session.get(User, demo_user_id).id
    db_session.add_all([
        Feedback(user_id=user_id, item_key="k1", item_title="Agent 新框架发布",
                 verdict="like"),
        Feedback(user_id=user_id, item_key="k2", item_title="币圈无关内容",
                 verdict="dislike"),
        Feedback(user_id=user_id, item_key="k3", item_title="已读旧闻", verdict="read"),
    ])
    db_session.commit()

    signals = runs_service.recent_feedback(db_session, user_id)
    assert signals["like"] == ["Agent 新框架发布"]
    assert signals["dislike"] == ["币圈无关内容"]

    prompt = build_system_prompt(
        {"name": "T", "role": "dev", "timezone": "Asia/Shanghai"},
        {"topics": ["AI"]},
        feedback_signals=signals,
    )
    assert "个性化反馈信号" in prompt
    assert "Agent 新框架发布" in prompt
    assert "币圈无关内容" in prompt
    assert "已读旧闻" not in prompt  # "read" 不进入生成提示，只留 UI


def test_run_agent_injects_feedback_into_system_prompt(client, api_llm, patched_run_env, db_session):
    from app.models import User

    demo_user_id = client.get("/api/subscription").json()["data"]["user_id"]
    user_id = db_session.get(User, demo_user_id).id
    db_session.add(Feedback(user_id=user_id, item_key="k1",
                            item_title="Agent 新框架发布", verdict="like"))
    db_session.commit()

    client.post("/api/runs")
    system = next(m for m in api_llm.last_messages if m["role"] == "system")
    assert "个性化反馈信号" in system["content"]
    assert "Agent 新框架发布" in system["content"]