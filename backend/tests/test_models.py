"""Model relationship and constraint tests (CARD-003)."""

from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import AgentRun, AgentStep, Brief, Subscription, User


def test_create_user_with_subscription(db_session):
    user = User(name="tester", role="Agent Developer")
    user.subscriptions.append(
        Subscription(
            topics_json=["AI Coding", "MCP"],
            keywords_json=["Claude", "Agent"],
            excluded_keywords_json=["spam"],
            max_items=8,
            language="zh",
        )
    )
    db_session.add(user)
    db_session.commit()

    assert user.id is not None
    persisted = db_session.get(Subscription, user.subscriptions[0].id)
    assert persisted.user_id == user.id
    assert persisted.user.name == "tester"
    assert persisted.topics_json == ["AI Coding", "MCP"]
    assert persisted.max_items == 8


def test_run_and_steps_related_query(db_session):
    user = User(name="tester")
    run = AgentRun(user=user, status="running")
    run.steps = [
        AgentStep(step_no=1, event_type="tool_call", tool_name="web_search",
                  tool_input_json={"q": "latest"}, duration_ms=120),
        AgentStep(step_no=2, event_type="tool_result", tool_name="web_search",
                  tool_output_preview="ok", duration_ms=30),
    ]
    db_session.add(run)
    db_session.commit()

    steps = db_session.query(AgentStep).filter(AgentStep.run_id == run.id).order_by(AgentStep.step_no).all()
    assert [s.step_no for s in steps] == [1, 2]
    assert steps[0].run.id == run.id
    assert run.steps[2 - 1].tool_name == "web_search"


def test_step_no_unique_per_run(db_session):
    run = AgentRun(user=User(name="tester"))
    db_session.add(run)
    db_session.commit()

    db_session.add(AgentStep(run_id=run.id, step_no=1, event_type="tool_call"))
    db_session.add(AgentStep(run_id=run.id, step_no=1, event_type="tool_call"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_brief_links_to_run(db_session):
    user = User(name="tester")
    run = AgentRun(user=user, status="completed")
    brief = Brief(user=user, run=run, brief_date=date.today(), title="Daily", item_count=3)
    db_session.add(brief)
    db_session.commit()

    assert brief.run_id == run.id
    persisted = db_session.get(Brief, brief.id)
    assert persisted.run.id == run.id
    assert persisted.user.id == user.id