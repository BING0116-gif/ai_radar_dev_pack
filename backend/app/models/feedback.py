"""Per-item user feedback: the personalization signals for future runs.

One row per (user, item): the latest verdict for a given news item wins
("like" = more of this, "dislike" = avoid this, "read" = already covered).
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow

# like | dislike | read
VERDICTS = ("like", "dislike", "read")


class Feedback(Base):
    __tablename__ = "feedbacks"
    __table_args__ = (
        UniqueConstraint("user_id", "item_key", name="uq_feedback_user_item"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    item_key: Mapped[str] = mapped_column(String(256), index=True)
    item_title: Mapped[str] = mapped_column(String(200), default="")
    verdict: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    user: Mapped["User"] = relationship()

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Feedback user={self.user_id} key={self.item_key[:24]!r} {self.verdict}>"