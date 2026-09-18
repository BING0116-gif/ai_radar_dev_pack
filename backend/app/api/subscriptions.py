"""Subscription settings API: read/update one demo user's preferences."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Subscription, User
from app.schemas.common import ApiError, ApiResponse, ok
from app.schemas.subscription import SubscriptionResponse, SubscriptionUpdate

router = APIRouter(prefix="/api", tags=["subscription"])


def get_or_create_demo_user(db: Session) -> User:
    """Return the first user, creating the Demo user on first request."""
    user = db.query(User).order_by(User.id).first()
    if user is None:
        user = User(name="Demo User", role="Agent Developer", timezone="Asia/Shanghai")
        db.add(user)
        db.flush()
    return user


def _to_response(user: User, sub: Subscription | None) -> SubscriptionResponse:
    """Combine user identity and subscription preferences into one response."""
    return SubscriptionResponse(
        id=sub.id if sub else None,
        user_id=user.id,
        name=user.name,
        role=user.role,
        email=user.email,
        timezone=user.timezone,
        max_items=sub.max_items if sub else 5,
        topics=sub.topics_json if sub else [],
        keywords=sub.keywords_json if sub else [],
        excluded_keywords=sub.excluded_keywords_json if sub else [],
        language=sub.language if sub else "zh-CN",
        notification_channel=sub.notification_channel if sub else "none",
        enabled=sub.enabled if sub else True,
    )


def _get_or_none(db: Session, user: User) -> Subscription | None:
    return db.query(Subscription).filter(Subscription.user_id == user.id).first()


@router.get("/subscription", response_model=ApiResponse[SubscriptionResponse])
def get_subscription(db: Session = Depends(get_db)) -> ApiResponse[SubscriptionResponse]:
    """Return the demo user's identity and subscription preferences."""
    user = get_or_create_demo_user(db)
    db.commit()
    return ok(_to_response(user, _get_or_none(db, user)))


@router.put("/subscription", response_model=ApiResponse[SubscriptionResponse])
def update_subscription(
    payload: SubscriptionUpdate, db: Session = Depends(get_db)
) -> ApiResponse[SubscriptionResponse]:
    """Create or update the demo user's subscription preferences."""
    user = get_or_create_demo_user(db)
    if payload.timezone:
        user.timezone = payload.timezone
    if payload.role is not None:
        user.role = payload.role.strip()

    sub = _get_or_none(db, user)
    if sub is None:
        sub = Subscription(user_id=user.id)
        db.add(sub)
    sub.max_items = payload.max_items
    sub.topics_json = payload.topics
    sub.keywords_json = payload.keywords
    sub.excluded_keywords_json = payload.excluded_keywords
    sub.language = payload.language
    sub.notification_channel = payload.notification_channel
    sub.enabled = payload.enabled

    try:
        db.commit()
    except Exception as exc:  # e.g. database constraint failures
        db.rollback()
        raise ApiError(f"failed to save subscription: {exc}") from exc
    return ok(_to_response(user, sub))