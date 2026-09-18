"""Persist one agent run and its tool/LLM trace.

Implements the ``AgentTracer`` protocol defined in the loop. A run is created
as ``running``; every event becomes one row in ``agent_steps``; finishing or
failing updates the ``agent_runs`` row. Only truncated previews are stored —
never API keys and never unbounded tool output.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.agent.loop import AgentTracer, AgentRunResult
from app.models import AgentRun, AgentStep, User

RUN_STATUS_BY_STOP_REASON = {
    "final_response": "completed",
    "repaired": "completed",
    "invalid_output": "completed",
    "max_steps": "completed",
    "repeated_call": "completed",
    "cancelled": "aborted",
}
PREVIEW_CHARS = 500


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DbTracer(AgentTracer):
    """Writes run/step trace rows for one agent run."""

    def __init__(self, db: Session, user: User, run_reason: str = ""):
        self.db = db
        self.run = AgentRun(user_id=user.id, status="running")
        db.add(self.run)
        db.commit()
        db.refresh(self.run)
        self._step_no = 0
        self._log(
            event_type="run_start", tool_name=None, tool_input={"reason": run_reason},
            duration_ms=0, success=True, preview=None,
        )

    def on_llm_turn(self, response: Any, step_no: int) -> None:
        self._log(
            event_type="llm_turn", tool_name=None,
            tool_input={"tool_calls": len(response.tool_calls)},
            duration_ms=0, success=True,
            preview=(response.content or "")[:PREVIEW_CHARS] or None,
        )

    def on_tool_call(self, name: str, arguments: dict[str, Any]) -> None:
        self._log(
            event_type="tool_call", tool_name=name, tool_input=arguments,
            duration_ms=0, success=True, preview=None,
        )

    def on_tool_result(self, name: str, success: bool, preview: str, duration_ms: int) -> None:
        self._log(
            event_type="tool_result", tool_name=name, tool_input=None,
            duration_ms=duration_ms, success=success, preview=preview,
        )

    def on_finish(self, result: AgentRunResult) -> None:
        status = RUN_STATUS_BY_STOP_REASON.get(result.stop_reason, "completed")
        self.run.status = status
        self.run.finished_at = _utcnow()
        if result.stop_reason == "invalid_output":
            self.run.error_message = "final output still invalid after one repair"
        self.db.commit()
        self.db.refresh(self.run)
        self._log(
            event_type="run_finish", tool_name=result.stop_reason, tool_input={"status": status},
            duration_ms=0, success=status not in ("failed", "aborted"),
            preview=None,
        )

    def on_run_error(self, exc: BaseException) -> None:
        self.run.status = "failed"
        self.run.error_message = str(exc)[:1000]
        self.run.finished_at = _utcnow()
        self.db.commit()
        self.db.refresh(self.run)
        self._log(
            event_type="run_error", tool_name=None, tool_input=None,
            duration_ms=0, success=False, preview=str(exc)[:800],
        )

    def _log(
        self,
        event_type: str,
        tool_name: str | None,
        tool_input: dict[str, Any] | None,
        duration_ms: int,
        success: bool,
        preview: str | None,
    ) -> None:
        self._step_no += 1
        step = AgentStep(
            run_id=self.run.id,
            step_no=self._step_no,
            event_type=event_type,
            tool_name=tool_name,
            tool_input_json=tool_input or {},
            tool_output_preview=preview,
            duration_ms=duration_ms,
            success=success,
        )
        self.run.step_count = self._step_no  # keep the run row in sync with trace rows
        self.db.add(step)
        self.db.commit()