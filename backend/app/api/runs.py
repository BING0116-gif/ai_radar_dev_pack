"""Run / trace / brief REST API: exposes existing capabilities only.

Immediate-run POST calls ``run_agent``; everything else is read-only queries
over the persisted runs, steps and briefs. Response/error envelopes are the
project-wide ``{code, message, data}`` convention.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.subscriptions import get_or_create_demo_user
from app.db import get_db
from app.models import AgentRun, AgentStep, Brief
from app.schemas.common import ApiError, ApiResponse, ok
from app.schemas.run import BriefDetail, BriefSummary, RunCreated, RunSummary, StepResponse

router = APIRouter(prefix="/api", tags=["run-brief"])


@router.post("/runs", response_model=ApiResponse[RunCreated], status_code=200)
def create_run(db: Session = Depends(get_db)) -> ApiResponse[RunCreated]:
    """Immediately start one agent run for the demo user."""
    from app.services import runs as runs_service

    user = get_or_create_demo_user(db)
    db.commit()
    summary = runs_service.run_agent(
        db, user.id, llm=runs_service.get_default_llm(), reason="manual"
    )
    return ok(RunCreated(
        run_id=summary["run_id"],
        stop_reason=summary["stop_reason"],
        brief_id=summary["brief_id"],
    ))


@router.get("/runs", response_model=ApiResponse[list[RunSummary]])
def list_runs(db: Session = Depends(get_db)) -> ApiResponse[list[RunSummary]]:
    runs = db.query(AgentRun).order_by(AgentRun.id.desc()).limit(50).all()
    return ok([RunSummary.model_validate(r) for r in runs])


@router.get("/runs/{run_id}", response_model=ApiResponse[RunSummary])
def get_run(run_id: int, db: Session = Depends(get_db)) -> ApiResponse[RunSummary]:
    run = db.get(AgentRun, run_id)
    if run is None:
        raise ApiError("run not found", code=40401, status_code=404)
    return ok(RunSummary.model_validate(run))


@router.get("/runs/{run_id}/steps", response_model=ApiResponse[list[StepResponse]])
def get_run_steps(run_id: int, db: Session = Depends(get_db)) -> ApiResponse[list[StepResponse]]:
    if db.get(AgentRun, run_id) is None:
        raise ApiError("run not found", code=40401, status_code=404)
    steps = (
        db.query(AgentStep)
        .filter(AgentStep.run_id == run_id)
        .order_by(AgentStep.step_no)
        .all()
    )
    return ok([StepResponse.model_validate(s) for s in steps])


@router.get("/briefs", response_model=ApiResponse[list[BriefSummary]])
def list_briefs(db: Session = Depends(get_db)) -> ApiResponse[list[BriefSummary]]:
    briefs = db.query(Brief).order_by(Brief.brief_date.desc(), Brief.id.desc()).limit(50).all()
    return ok([BriefSummary.model_validate(b) for b in briefs])


@router.get("/briefs/{brief_id}", response_model=ApiResponse[BriefDetail])
def get_brief(brief_id: int, db: Session = Depends(get_db)) -> ApiResponse[BriefDetail]:
    brief = db.get(Brief, brief_id)
    if brief is None:
        raise ApiError("brief not found", code=40402, status_code=404)
    return ok(BriefDetail.model_validate(brief))