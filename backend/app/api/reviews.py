"""Human-in-the-loop review API: approve or reject pending briefs.

"先审后发" 流程：订阅开启 require_approval 后，生成的简报先落为
``pending``；通过 ``GET /api/reviews`` 查看待审队列，审批通过时才发布并
触发通知，打回则标记为 ``rejected``（不自动重生成）。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.subscriptions import get_or_create_demo_user
from app.db import get_db
from app.models import Brief
from app.schemas.common import ApiError, ApiResponse, ok
from app.schemas.run import BriefSummary

router = APIRouter(prefix="/api", tags=["review"])


def _load_pending_brief(brief_id: int, db: Session) -> Brief:
    brief = db.get(Brief, brief_id)
    if brief is None:
        raise ApiError("brief not found", code=40402, status_code=404)
    if brief.status != "pending":
        raise ApiError("brief is not pending", code=42204, status_code=422)
    return brief


@router.get("/reviews", response_model=ApiResponse[list[BriefSummary]])
def list_reviews(db: Session = Depends(get_db)) -> ApiResponse[list[BriefSummary]]:
    """Briefs awaiting approval (newest first)."""
    from app.services import runs as runs_service

    user = get_or_create_demo_user(db)
    db.commit()
    return ok([BriefSummary.model_validate(b) for b in runs_service.pending_briefs(db, user.id)])


@router.post("/reviews/{brief_id}/approve", response_model=ApiResponse[BriefSummary])
def approve_review(brief_id: int, db: Session = Depends(get_db)) -> ApiResponse[BriefSummary]:
    """Approve a pending brief: publish it and send the notification."""
    from app.services import runs as runs_service

    brief = _load_pending_brief(brief_id, db)
    approved = runs_service.approve_brief(db, brief.id)
    return ok(BriefSummary.model_validate(approved))


@router.post("/reviews/{brief_id}/reject", response_model=ApiResponse[BriefSummary])
def reject_review(brief_id: int, db: Session = Depends(get_db)) -> ApiResponse[BriefSummary]:
    """Reject a pending brief (marked rejected; no regenerate)."""
    from app.services import runs as runs_service

    brief = _load_pending_brief(brief_id, db)
    rejected = runs_service.reject_brief(db, brief.id)
    return ok(BriefSummary.model_validate(rejected))