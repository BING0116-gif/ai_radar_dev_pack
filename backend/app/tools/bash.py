"""Restricted bash agent tool: whitelisted commands only, no arbitrary shell.

Security model (CARD-007):
- the command is parsed with ``shlex``, never run through a shell;
- the executable must be in the allowlist and resolvable on ``PATH``;
- commands containing shell metacharacters (pipes, redirects, command
  substitution, backgrounding, ...) are rejected up front;
- the working directory is fixed to the workspace root;
- a hard timeout terminates the process; stdout/stderr are capped at 20 KB.
"""

import shlex
import shutil
import subprocess
from pathlib import Path

from pydantic import BaseModel, Field

from app.agent.registry import ToolDefinition, ToolRegistry
from app.core.config import get_settings

ALLOWED_COMMANDS = {"python", "grep", "find", "head", "tail", "wc", "sort", "cat"}
FORBIDDEN_METACHARS = set(";|&<>$`\n")
MAX_OUTPUT_BYTES = 20 * 1024  # 20 KB per stream
DEFAULT_TOOL_TIMEOUT = 10.0  # seconds (subprocess level)


class BashToolError(Exception):
    """The command violated the bash sandbox policy."""


class BashTool:
    """One sandboxed bash execution bound to a fixed working directory."""

    def __init__(self, cwd: Path):
        self.cwd = cwd.resolve()

    def bash(self, command: str, timeout: float = DEFAULT_TOOL_TIMEOUT) -> dict:
        """Run a whitelisted command; return output/exit code/truncation flags."""
        self._validate(command)

        argv = shlex.split(command)
        exe = shutil.which(argv[0])
        if exe is None:
            raise BashToolError(f"command not found on PATH: {argv[0]}")

        try:
            proc = subprocess.run(
                [exe, *argv[1:]],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=max(float(timeout), 0.1),
            )
        except subprocess.TimeoutExpired:
            # subprocess.run already terminated the child process.
            return {"exit_code": -1, "timed_out": True, "stdout": "", "stderr": "", "truncated": False}

        stdout, stdout_truncated = self._cap_output(proc.stdout)
        stderr, stderr_truncated = self._cap_output(proc.stderr)
        return {
            "exit_code": proc.returncode,
            "timed_out": False,
            "stdout": stdout,
            "stderr": stderr,
            "truncated": stdout_truncated or stderr_truncated,
        }

    # --- guards --------------------------------------------------------------

    def _validate(self, command: str) -> None:
        command = command or ""
        if not command.strip():
            raise BashToolError("empty command")
        if self._has_unquoted_metachar(command):
            raise BashToolError("command contains forbidden shell metacharacters")
        try:
            argv = shlex.split(command)
        except ValueError as exc:
            raise BashToolError(f"cannot parse command: {exc}") from exc
        if not argv or argv[0] not in ALLOWED_COMMANDS:
            raise BashToolError(f"command not allowed: {argv[0] if argv else ''}")

    @staticmethod
    def _has_unquoted_metachar(command: str) -> bool:
        """True if a forbidden metacharacter appears outside of quotes.

        Pipes/redirects/expansion only matter through a shell; we never run one,
        so metacharacters inside quoted arguments (e.g. ``;`` in ``python -c ...``)
        are harmless and allowed.
        """
        quote: str | None = None
        for ch in command:
            if quote is not None:
                if ch == quote:
                    quote = None
            elif ch in ("'", '"'):
                quote = ch
            elif ch in FORBIDDEN_METACHARS:
                return True
        return False

    @staticmethod
    def _cap_output(text: str) -> tuple[str, bool]:
        """Truncate a stream to MAX_OUTPUT_BYTES (byte-accurate) and flag it."""
        raw = text.encode("utf-8", errors="replace")
        if len(raw) <= MAX_OUTPUT_BYTES:
            return text, False
        return raw[:MAX_OUTPUT_BYTES].decode("utf-8", errors="replace"), True


class BashParams(BaseModel):
    command: str = Field(description="whitelisted shell command line, e.g. python -c ...")
    timeout: float = Field(default=DEFAULT_TOOL_TIMEOUT, ge=0.1, le=60, description="seconds")


def register_bash_tool(registry: ToolRegistry, cwd: Path | None = None) -> None:
    """Register the restricted bash tool. ``cwd`` defaults to WORKSPACE_ROOT."""
    bt = BashTool(cwd if cwd is not None else get_settings().WORKSPACE_ROOT)
    registry.register(ToolDefinition(
        name="bash",
        description="Run a whitelisted command (python/grep/find/head/tail/wc/sort/cat) in the workspace.",
        parameters_model=BashParams,
        func=bt.bash,
        timeout_seconds=60,  # outer guard; inner subprocess timeout is stricter
    ))