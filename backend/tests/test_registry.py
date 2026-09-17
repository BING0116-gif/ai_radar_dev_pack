"""Unit tests for the typed tool registry (CARD-005)."""

import json
import time

import pytest
from pydantic import BaseModel

from app.agent.registry import ToolDefinition, ToolRegistry


class AddParams(BaseModel):
    a: int
    b: int = 0


class EmptyParams(BaseModel):
    pass


def _add(a: int, b: int = 0) -> int:
    return a + b


def _boom() -> None:
    raise RuntimeError("boom")


def _slow() -> str:
    time.sleep(2)
    return "late"


@pytest.fixture
def add_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="add", description="add two integers", parameters_model=AddParams, func=_add,
    ))
    return registry


def test_register_and_lookup(add_registry):
    assert add_registry.names() == ["add"]
    tool = add_registry.get("add")
    assert tool is not None
    assert tool.func is _add


def test_duplicate_register_rejected(add_registry):
    with pytest.raises(ValueError):
        add_registry.register(ToolDefinition(
            name="add", description="dup", parameters_model=AddParams, func=_add,
        ))


def test_schema_export_is_function_calling(add_registry):
    schemas = add_registry.schemas()
    assert len(schemas) == 1
    entry = schemas[0]
    assert entry["type"] == "function"
    function = entry["function"]
    assert function["name"] == "add"
    assert function["description"] == "add two integers"
    params = function["parameters"]
    assert params["type"] == "object"
    assert set(params["properties"]) == {"a", "b"}
    assert params["required"] == ["a"]
    # Must be JSON-serializable so it can be posted to the LLM provider.
    json.dumps(schemas)


def test_execute_success(add_registry):
    result = add_registry.execute("add", {"a": 1, "b": 2})
    assert result.success is True
    assert result.data == 3
    assert result.error is None


def test_execute_uses_default_param(add_registry):
    result = add_registry.execute("add", {"a": 5})
    assert result.success is True
    assert result.data == 5


def test_invalid_args_return_structured_failure(add_registry):
    result = add_registry.execute("add", {"a": "not-an-int"})
    assert result.success is False
    assert "invalid arguments" in (result.error or "")


def test_unknown_tool_returns_structured_failure(add_registry):
    result = add_registry.execute("nope", {})
    assert result.success is False
    assert "unknown tool" in (result.error or "")


def test_tool_exception_is_caught(add_registry):
    add_registry.register(ToolDefinition(
        name="boom", description="raises", parameters_model=EmptyParams, func=_boom,
    ))
    result = add_registry.execute("boom", {})
    assert result.success is False
    assert "boom" in (result.error or "")


def test_timeout_returns_structured_failure(add_registry):
    add_registry.register(ToolDefinition(
        name="slow", description="sleeps", parameters_model=EmptyParams, func=_slow, timeout_seconds=0.05,
    ))
    result = add_registry.execute("slow", {})
    assert result.success is False
    assert "timed out" in (result.error or "")