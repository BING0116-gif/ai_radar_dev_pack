"""A generated daily brief; run_id links it back to the agent run that produced it."""

from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow


class Brief(Base):
    __tablename__ = "briefs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("agent_runs.id"), index=True)

    brief_date: Mapped[date] = mapped_column(Date, index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    content_markdown: Mapped[str] = mapped_column(Text, default="")
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    user: Mapped["User"] = relationship()
    run: Mapped["AgentRun"] = relationship()

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Brief id={self.id} date={self.brief_date} run_id={self.run_id}>"