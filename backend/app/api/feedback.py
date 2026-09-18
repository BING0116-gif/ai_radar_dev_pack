"""Per-item feedback API: the user's like/dislike/read stance on news items.

Stored as the personalization signals consumed by the next run's prompt
(see ``runs.recent_feedback``). Same (user, item) can only hold the latest
verdict — posting again upserts.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.subscriptions import get_or_create_demo_user
from app.db import get_db
from app.models import Feedback
from app.schemas.common import ApiError, ApiResponse, ok
from app.schemas.feedback import FeedbackPayload, FeedbackResponse

router = APIRouter(prefix="/api", tags=["feedback"])


@router.get("/feedback", response_model=ApiResponse[list[FeedbackResponse]])
def list_feedback(db: Session = Depends(get_db)) -> ApiResponse[list[FeedbackResponse]]:
    """All feedback rows (latest first); the UI builds an item_key -> verdict map."""
    user = get_or_create_demo_user(db)
    db.commit()
    rows = (
        db.query(Feedback)
        .filter(Feedback.user_id == user.id)
        .order_by(Feedback.updated_at.desc())
        .all()
    )
    return ok([FeedbackResponse.model_validate(r) for r in rows])


@router.post("/feedback", response_model=ApiResponse[FeedbackResponse])
def upsert_feedback(
    payload: FeedbackPayload, db: Session = Depends(get_db)
) -> ApiResponse[FeedbackResponse]:
    """Record the latest stance on an item (upsert by user + item_key)."""
    user = get_or_create_demo_user(db)
    row = (
        db.query(Feedback)
        .filter(Feedback.user_id == user.id, Feedback.item_key == payload.item_key)
        .first()
    )
    if row is None:
        row = Feedback(user_id=user.id, item_key=payload.item_key)
        db.add(row)
    if payload.item_title:
        row.item_title = payload.item_title
    row.verdict = payload.verdict
    try:
        db.commit()
    except Exception as exc:  # unexpected constraint failures
        db.rollback()
        raise ApiError(f"failed to save feedback: {exc}") from exc
    db.refresh(row)
    return ok(FeedbackResponse.model_validate(row))


@router.delete("/feedback", response_model=ApiResponse[dict])
def delete_feedback(item_key: str = Query(...), db: Session = Depends(get_db)) -> ApiResponse[dict]:
    """Remove the feedback for an item (client "取消反馈").

    ``item_key`` 走 query 参数而不是路径段，避免包含 ``/`` 的来源 URL
    （如 https://...）在路径参数中被截断导致的 404。
    """
    user = get_or_create_demo_user(db)
    row = (
        db.query(Feedback)
        .filter(Feedback.user_id == user.id, Feedback.item_key == item_key)
        .first()
    )
    removed = row is not None
    if row is not None:
        db.delete(row)
        db.commit()
    return ok({"removed": removed})