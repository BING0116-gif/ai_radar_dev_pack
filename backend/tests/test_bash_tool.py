"""Security and behavior tests for the restricted bash tool (CARD-007)."""

import pytest

from app.agent.registry import ToolRegistry
from app.tools.bash import register_bash_tool


@pytest.fixture
def registry(tmp_path):
    reg = ToolRegistry()
    register_bash_tool(reg, cwd=tmp_path)
    return reg


def test_bash_tool_registered(registry):
    assert registry.names() == ["bash"]


def test_whitelisted_command_runs(registry):
    result = registry.execute("bash", {"command": "python -c \"print('hello from tool')\""})
    assert result.success is True
    assert result.data["exit_code"] == 0
    assert "hello from tool" in result.data["stdout"]
    assert result.data["timed_out"] is False


def test_disallowed_commands_rejected(registry):
    for evil in ("rm -rf /", "curl http://evil.example", "sudo rm -rf /"):
        result = registry.execute("bash", {"command": evil})
        assert result.success is False, evil
        assert "not allowed" in (result.error or ""), evil


def test_forbidden_metacharacters_rejected(registry):
    # Metacharacters matter only when unquoted; each of these has one unquoted.
    for evil in ("python -c 'x' | grep y", "python -c 'print(1)'; python -c 'print(2)'",
                 "python -c 'a' > f.txt", "python -c 'a' & sleep 1",
                 "python $HOME/x", "python -c 'x'`y`"):
        result = registry.execute("bash", {"command": evil})
        assert result.success is False, evil
        assert "forbidden shell metacharacters" in (result.error or ""), evil


def test_quoted_metacharacters_allowed(registry):
    # ';' inside a quoted python -c argument is harmless (no shell involved).
    result = registry.execute("bash", {"command": "python -c \"import sys; sys.exit(0)\""})
    assert result.success is True
    assert result.data["exit_code"] == 0


def test_timeout_process_is_terminated(registry):
    result = registry.execute("bash", {
        "command": "python -c \"import time; time.sleep(5)\"",
        "timeout": 0.3,
    })
    assert result.success is True
    assert result.data["timed_out"] is True
    assert result.data["exit_code"] == -1


def test_output_truncation_has_marker(registry):
    result = registry.execute("bash", {"command": "python -c \"print('x' * 30000)\""})
    assert result.success is True
    assert result.data["truncated"] is True
    assert len(result.data["stdout"]) < 30000


def test_nonzero_exit_code_captured(registry):
    result = registry.execute("bash", {"command": "python -c \"import sys; sys.exit(3)\""})
    assert result.success is True
    assert result.data["exit_code"] == 3


def test_cwd_is_fixed_to_workspace(registry, tmp_path):
    result = registry.execute("bash", {"command": "python -c \"import os; print(os.getcwd())\""})
    assert result.success is True
    assert result.data["stdout"].strip() == str(tmp_path)