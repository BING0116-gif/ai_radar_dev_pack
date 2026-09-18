"""Tests for the OpenAI-compatible chat client (CARD-009)."""

import httpx
import pytest

from app.core.llm_client import LLMConfigurationError, LLMRequestError, OpenAICompatibleClient


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def _make(handler, **kwargs):
    kwargs.setdefault("base_url", "https://api.test")
    kwargs.setdefault("api_key", "sk-test")
    kwargs.setdefault("model", "mock-model")
    return OpenAICompatibleClient(client=_client(handler), **kwargs)


def test_parses_tool_calls_and_content():
    payload = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "thinking...",
                "tool_calls": [{
                    "id": "call_1", "type": "function",
                    "function": {"name": "web_search", "arguments": '{"query": "ai"}'},
                }],
            },
            "finish_reason": "tool_calls",
        }]
    }

    def handler(request):
        body = request.read()
        assert b'"tools"' in body
        assert b"Bearer sk-test" in request.headers["authorization"].encode()
        return httpx.Response(200, json=payload, request=request)

    client = _make(handler)
    response = client.chat([{"role": "user", "content": "hi"}], tools=[{"type": "function"}])
    assert response.content == "thinking..."
    assert response.finish_reason == "tool_calls"
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "web_search"
    assert response.tool_calls[0].arguments == {"query": "ai"}


def test_parses_usage_tokens():
    """Usage from the /chat/completions response lands on the LLMResponse (E1)."""
    payload = {
        "choices": [{"message": {"role": "assistant", "content": "hi"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 123, "completion_tokens": 45},
    }

    def handler(request):
        return httpx.Response(200, json=payload, request=request)

    response = _make(handler).chat([{"role": "user", "content": "hi"}], tools=[])
    assert response.token_input == 123
    assert response.token_output == 45


def test_usage_missing_defaults_to_zero():
    payload = {"choices": [{"message": {"role": "assistant", "content": "hi"}, "finish_reason": "stop"}]}

    def handler(request):
        return httpx.Response(200, json=payload, request=request)

    response = _make(handler).chat([{"role": "user", "content": "hi"}], tools=[])
    assert response.token_input == 0
    assert response.token_output == 0


def test_malformed_arguments_fall_back_to_empty():
    payload = {
        "choices": [{"message": {"tool_calls": [{
            "id": "c", "function": {"name": "x", "arguments": "not-json"},
        }]}}]
    }
    client = _make(lambda request: httpx.Response(200, json=payload, request=request))
    response = client.chat([], [])
    assert response.tool_calls[0].arguments == {}


def test_missing_configuration_raises():
    client = OpenAICompatibleClient(base_url="", api_key="", model="")
    with pytest.raises(LLMConfigurationError):
        client.chat([], [])


def test_http_error_raises_structured_error():
    client = _make(lambda request: httpx.Response(401, content=b"unauthorized", request=request))
    with pytest.raises(LLMRequestError) as exc_info:
        client.chat([], [])
    assert "401" in str(exc_info.value)