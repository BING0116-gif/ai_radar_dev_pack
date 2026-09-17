"""One tool call (or LLM turn) inside an agent run — the trace unit shown in the UI."""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow


class AgentStep(Base):
    __tablename__ = "agent_steps"
    __table_args__ = (UniqueConstraint("run_id", "step_no", name="uq_agent_steps_run_step"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("agent_runs.id"), index=True)
    step_no: Mapped[int] = mapped_column(Integer)

    event_type: Mapped[str] = mapped_column(String(32))  # llm_turn / tool_call / tool_result / ...
    tool_name: Mapped[str | None] = mapped_column(String(64), default=None)
    tool_input_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    tool_output_preview: Mapped[str | None] = mapped_column(Text, default=None)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    run: Mapped["AgentRun"] = relationship(back_populates="steps")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<AgentStep run_id={self.run_id} step_no={self.step_no} type={self.event_type!r}>"