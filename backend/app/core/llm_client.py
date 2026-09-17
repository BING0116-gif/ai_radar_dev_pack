"""OpenAI-compatible chat client used by the agent loop.

Only the wire format (``/chat/completions``) is assumed here, so any
OpenAI-compatible provider — DeepSeek, OpenAI, local vLLM — works as long as
``LLM_BASE_URL`` / ``LLM_MODEL`` / ``LLM_API_KEY`` are configured.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx
from pydantic import SecretStr

from app.core.config import get_settings

logger = logging.getLogger("app.core.llm_client")

CHAT_TIMEOUT = 30.0


class LLMConfigurationError(Exception):
    """LLM is not configured (missing base URL / model / key)."""


class LLMRequestError(Exception):
    """The LLM endpoint rejected the request or the network failed."""


@dataclass
class ToolCall:
    """A parsed function call requested by the model."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """A model reply: free-form content and/or tool calls."""

    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str | None = None


class LLMClient(Protocol):
    """What the agent loop needs from a model client."""

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LLMResponse:
        """Send messages (+tool schemas) and return a structured reply."""
        ...


class OpenAICompatibleClient:
    """Minimal /chat/completions client; ``client`` injectable for tests."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: SecretStr | str | None = None,
        model: str | None = None,
        client: httpx.Client | None = None,
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.LLM_BASE_URL).rstrip("/")
        key = api_key if api_key is not None else settings.LLM_API_KEY
        self.api_key = key if isinstance(key, SecretStr) else SecretStr(str(key))
        self.model = model or settings.LLM_MODEL
        self._client = client

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> LLMResponse:
        self._ensure_configured()
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
        }
        headers = {
            "Authorization": f"Bearer {self.api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/chat/completions"
        try:
            if self._client is not None:
                response = self._client.post(url, json=payload, headers=headers, timeout=CHAT_TIMEOUT)
            else:
                with httpx.Client(timeout=CHAT_TIMEOUT) as client:
                    response = client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise LLMRequestError(f"llm request failed: {exc}") from exc
        if response.status_code >= 400:
            raise LLMRequestError(f"llm HTTP {response.status_code}: {response.text[:300]}")
        return self._parse(response.json())

    def _ensure_configured(self) -> None:
        if not self.base_url or not self.model or not self.api_key.get_secret_value():
            raise LLMConfigurationError("LLM_BASE_URL / LLM_MODEL / LLM_API_KEY must be set")

    @staticmethod
    def _parse(payload: dict[str, Any]) -> LLMResponse:
        choice = payload["choices"][0]
        message = choice.get("message", {})
        tool_calls: list[ToolCall] = []
        for raw in message.get("tool_calls") or []:
            fn = raw.get("function", {})
            args_raw = fn.get("arguments") or "{}"
            try:
                arguments = json.loads(args_raw) if args_raw else {}
            except json.JSONDecodeError:
                arguments = {}
            tool_calls.append(ToolCall(
                id=raw.get("id") or "",
                name=fn.get("name") or "",
                arguments=arguments,
            ))
        return LLMResponse(
            content=message.get("content") or "",
            tool_calls=tool_calls,
            finish_reason=choice.get("finish_reason"),
        )