"""Per-user subscription preferences (what the agent should look for)."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    # JSON lists; SQLAlchemy serializes them (works on SQLite and PostgreSQL).
    topics_json: Mapped[list[Any]] = mapped_column(JSON, default=list)
    keywords_json: Mapped[list[Any]] = mapped_column(JSON, default=list)
    excluded_keywords_json: Mapped[list[Any]] = mapped_column(JSON, default=list)

    max_items: Mapped[int] = mapped_column(Integer, default=5)
    language: Mapped[str] = mapped_column(String(16), default="zh")
    notification_channel: Mapped[str] = mapped_column(String(32), default="none")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # true = 生成简报先进入"待审"，人工通过后才发布+通知（HITL）
    require_approval: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("0"))

    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship(back_populates="subscriptions")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Subscription id={self.id} user_id={self.user_id}>"