"""The model-driven agent loop.

The loop itself is generic and has *no* opinion about tool order: each turn
it hands ``messages + tool schemas`` to the LLM, executes whatever tool calls
the model decides to make, appends the observations, and lets the model
decide again. The loop only owns control flow:

- when to ask the model again (tool calls present);
- when to stop (final answer, ``AGENT_MAX_STEPS``, repeated tool+args, or an
  external cancel flag);
- structured recording of every executed call.

The scheduler, news providers and filesystem tools never decide call order.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from app.agent.context import AgentContext
from app.agent.registry import ToolRegistry
from app.core.config import get_settings
from app.core.llm_client import LLMClient

logger = logging.getLogger("app.agent.loop")

REPEAT_THRESHOLD = 3
OUTPUT_PREVIEW_CHARS = 500

# Minimal default until CARD-010 introduces the dedicated prompts module.
DEFAULT_SYSTEM_PROMPT = (
    "You are an AI news agent. Use the provided tools when they help. "
    "Decide yourself which tools to call, how many times, and when to stop. "
    "When you have enough information, reply with the final result and no tool calls."
)


@dataclass
class ToolCallRecord:
    """One executed tool call (the trace unit for later cards)."""

    name: str
    arguments: dict[str, Any]
    success: bool
    output_preview: str


@dataclass
class AgentRunResult:
    stop_reason: str  # final_response | max_steps | repeated_call | cancelled
    content: str = ""
    step_count: int = 0
    calls: list[ToolCallRecord] = field(default_factory=list)


class AgentLoop:
    """Generic function-calling loop; the ordering is decided by the LLM."""

    def __init__(
        self,
        registry: ToolRegistry,
        llm: LLMClient,
        *,
        max_steps: int | None = None,
        repeat_threshold: int = REPEAT_THRESHOLD,
    ):
        self.registry = registry
        self.llm = llm
        self.max_steps = max_steps or int(get_settings().AGENT_MAX_STEPS)
        self.repeat_threshold = repeat_threshold

    def run(
        self,
        context: AgentContext,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        should_stop: Callable[[], bool] | None = None,
    ) -> AgentRunResult:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context.task},
        ]
        tools = self.registry.schemas()
        calls: list[ToolCallRecord] = []
        previous_call_signature: tuple | None = None
        repeat_streak = 0

        for step in range(1, self.max_steps + 1):
            if should_stop is not None and should_stop():
                logger.info("agent run cancelled at step %s", step)
                return AgentRunResult(stop_reason="cancelled", step_count=step - 1, calls=calls)

            response = self.llm.chat(messages, tools)

            if not response.tool_calls:  # final answer
                return AgentRunResult(
                    stop_reason="final_response", content=response.content, step_count=step, calls=calls,
                )

            signature = tuple(
                (tc.name, _canonical_args(tc.arguments)) for tc in response.tool_calls
            )
            repeat_streak = repeat_streak + 1 if signature == previous_call_signature else 1
            if repeat_streak > self.repeat_threshold:
                logger.warning("agent stopped: repeated tool call %s", signature)
                return AgentRunResult(stop_reason="repeated_call", step_count=step, calls=calls)
            previous_call_signature = signature

            messages.append(_assistant_tool_message(response))
            for tc in response.tool_calls:
                result = self.registry.execute(tc.name, tc.arguments)
                preview = _preview(result.data if result.success else result.error)
                calls.append(ToolCallRecord(
                    name=tc.name, arguments=tc.arguments, success=result.success, output_preview=preview,
                ))
                observation = {
                    "ok": result.success,
                    "data": result.data if result.success else None,
                    "error": result.error,
                }
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(observation, ensure_ascii=False, default=str),
                })
                logger.info("step %s tool=%s success=%s", step, tc.name, result.success)

        return AgentRunResult(stop_reason="max_steps", step_count=self.max_steps, calls=calls)


def _assistant_tool_message(response) -> dict[str, Any]:
    """Assistant message carrying tool calls, in OpenAI wire format."""
    return {
        "role": "assistant",
        "content": response.content or "",
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.name,
                    "arguments": json.dumps(tc.arguments, ensure_ascii=False, default=str),
                },
            }
            for tc in response.tool_calls
        ],
    }


def _canonical_args(arguments: dict[str, Any]) -> str:
    return json.dumps(arguments, sort_keys=True, ensure_ascii=False, default=str)


def _preview(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str) if not isinstance(value, str) else value
    return text[:OUTPUT_PREVIEW_CHARS]