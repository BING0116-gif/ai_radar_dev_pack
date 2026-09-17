"""Typed tool registry: registration, JSON-Schema export, unified execution.

Tools are plain Python callables that never see the LLM; the LLM only ever
sees the exported function-calling schema. Execution always returns a
``ToolResult``: bad arguments, tool exceptions and timeouts are captured as
structured results (never raised), so the agent loop treats them as
observations and keeps deciding.
"""

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("registry")


@dataclass
class ToolResult:
    """Unified tool outcome; ``success=False`` is a normal, structured case."""

    success: bool
    data: Any = None
    error: str | None = None


@dataclass
class ToolDefinition:
    """Registration record: how to describe and how to run one tool."""

    name: str
    description: str
    parameters_model: type[BaseModel]  # one source of truth for schema + validation
    func: Callable[..., Any]  # called as func(**validated_params)
    timeout_seconds: float | None = None  # None -> use Settings.TOOL_TIMEOUT_SECONDS

    def to_json_schema(self) -> dict[str, Any]:
        """OpenAI-compatible function-calling schema shown to the LLM."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_model.model_json_schema(),
            },
        }


class ToolRegistry:
    """Registry of tools the agent is allowed to call."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def definitions(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def schemas(self) -> list[dict[str, Any]]:
        """Function-calling schemas for every registered tool (JSON-serializable)."""
        return [tool.to_json_schema() for tool in self._tools.values()]

    def execute(self, name: str, arguments: dict[str, Any] | None = None) -> ToolResult:
        """Validate arguments, run the tool, and never raise on tool failures."""
        arguments = arguments or {}
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(success=False, error=f"unknown tool: {name}")

        # Validate with the exact same model that produced the LLM-facing schema.
        try:
            params = tool.parameters_model.model_validate(arguments)
        except ValidationError as exc:
            return ToolResult(success=False, error=f"invalid arguments for '{name}': {exc}")

        timeout = (
            tool.timeout_seconds
            if tool.timeout_seconds is not None
            else float(get_settings().TOOL_TIMEOUT_SECONDS)
        )
        return self._execute_with_guard(tool, params, timeout)

    def _execute_with_guard(self, tool: ToolDefinition, params: BaseModel, timeout: float) -> ToolResult:
        pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"tool-{tool.name}")
        try:
            future = pool.submit(tool.func, **params.model_dump())
            try:
                data = future.result(timeout=timeout)
            except FutureTimeoutError:
                future.cancel()
                logger.warning("tool '%s' timed out after %ss", tool.name, timeout)
                return ToolResult(success=False, error=f"tool '{tool.name}' timed out after {timeout}s")
        except Exception as exc:  # exceptions raised inside the tool surface here
            logger.warning("tool '%s' failed: %s", tool.name, exc)
            return ToolResult(success=False, error=f"tool '{tool.name}' failed: {exc}")
        finally:
            # Do not block on a tool that is still running after a timeout.
            pool.shutdown(wait=False)
        logger.info("tool '%s' executed", tool.name)
        return ToolResult(success=True, data=data)