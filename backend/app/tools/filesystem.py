"""Sandboxed filesystem agent tools: list_dir / read_file / search_content / write_file.

Every path the agent supplies is interpreted as *workspace-relative* and is
resolved against the sandbox root (``WORKSPACE_ROOT``). Any path that would
resolve outside the root — via ``..``, absolute paths or symlinks — raises
``SandboxError``, which the registry turns into a structured ``ToolResult``.
"""

import os
from pathlib import Path

from pydantic import BaseModel, Field

from app.agent.registry import ToolDefinition, ToolRegistry
from app.core.config import get_settings

# --- safety limits (CARD-006) ---
MAX_READ_BYTES = 200 * 1024  # 200 KB per read_file call
MAX_SEARCH_HITS = 50  # at most 50 matched lines per search_content call


class SandboxError(Exception):
    """A filesystem access violated the workspace sandbox or a size limit."""


class FilesystemTools:
    """The four must-have file tools, bound to one sandbox root."""

    def __init__(self, root: Path):
        self.root = root.resolve()

    # --- sandbox resolution -------------------------------------------------

    def _resolve(self, rel: str) -> Path:
        """Resolve a workspace-relative path, rejecting any escape."""
        raw = Path(rel)
        candidate = raw if raw.is_absolute() else (self.root / raw)
        resolved = candidate.resolve()
        if not resolved.is_relative_to(self.root):
            raise SandboxError(f"path escapes workspace: {rel!r}")
        return resolved

    def _to_rel(self, path: Path) -> str:
        """Workspace-relative path with forward slashes (stable across OSes)."""
        return str(path.relative_to(self.root)).replace(os.sep, "/")

    # --- tools --------------------------------------------------------------

    def list_dir(self, path: str = ".") -> dict:
        """List entries (name, type, workspace-relative path) of a directory."""
        target = self._resolve(path)
        if not target.is_dir():
            raise SandboxError(f"not a directory: {path!r}")
        entries = []
        for entry in sorted(target.iterdir(), key=lambda e: e.name):
            entries.append({
                "name": entry.name,
                "type": "dir" if entry.is_dir() else "file",
                "relative_path": self._to_rel(entry),
            })
        return {"path": self._to_rel(target), "entries": entries}

    def read_file(self, path: str) -> dict:
        """Read a UTF-8 text file, capped at 200 KB."""
        target = self._resolve(path)
        if not target.is_file():
            raise SandboxError(f"not a file: {path!r}")
        data = target.read_bytes()
        if len(data) > MAX_READ_BYTES:
            raise SandboxError(f"file too large ({len(data)} bytes, max {MAX_READ_BYTES})")
        try:
            content = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SandboxError(f"binary or non-UTF-8 file: {path!r}") from exc
        return {"path": self._to_rel(target), "content": content, "size_bytes": len(data)}

    def search_content(self, keyword: str, dir: str = ".") -> dict:
        """Recursively search text lines containing ``keyword`` (case-insensitive)."""
        target = self._resolve(dir)
        if not target.is_dir():
            raise SandboxError(f"not a directory: {dir!r}")
        needle = keyword.lower()
        matches = []
        truncated = False
        for current, _dirs, files in sorted(os.walk(target)):
            for name in sorted(files):
                file_path = Path(current) / name
                try:
                    text = file_path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue  # binary or unreadable -> not a searchable text file
                for line_no, line in enumerate(text.splitlines(), start=1):
                    if needle in line.lower():
                        matches.append({
                            "relative_path": self._to_rel(file_path),
                            "line_number": line_no,
                            "line": line.strip()[:200],
                        })
                        if len(matches) >= MAX_SEARCH_HITS:
                            truncated = True
                            return {"matches": matches, "truncated": truncated}
        return {"matches": matches, "truncated": truncated}

    def write_file(self, path: str, content: str) -> dict:
        """Write UTF-8 text, creating parent directories as needed."""
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"path": self._to_rel(target), "bytes_written": len(content.encode("utf-8"))}


# --- parameters (single source of truth for LLM schema + validation) --------

class ListDirParams(BaseModel):
    path: str = Field(default=".", description="workspace-relative directory path")


class ReadFileParams(BaseModel):
    path: str = Field(description="workspace-relative file path")


class SearchContentParams(BaseModel):
    keyword: str = Field(description="substring to search, case-insensitive")
    dir: str = Field(default=".", description="workspace-relative directory to search in")


class WriteFileParams(BaseModel):
    path: str = Field(description="workspace-relative destination file path")
    content: str = Field(description="file content to write")


def register_filesystem_tools(registry: ToolRegistry, root: Path | None = None) -> None:
    """Register the four filesystem tools, bound to ``root`` (default: WORKSPACE_ROOT)."""
    fs = FilesystemTools(root if root is not None else get_settings().WORKSPACE_ROOT)
    registry.register(ToolDefinition(
        name="list_dir", description="List a directory's entries (name, type, relative path).",
        parameters_model=ListDirParams, func=fs.list_dir, timeout_seconds=20,
    ))
    registry.register(ToolDefinition(
        name="read_file", description="Read a UTF-8 text file (max 200 KB).",
        parameters_model=ReadFileParams, func=fs.read_file, timeout_seconds=20,
    ))
    registry.register(ToolDefinition(
        name="search_content", description="Recursively search text lines for a keyword (max 50 hits).",
        parameters_model=SearchContentParams, func=fs.search_content, timeout_seconds=60,
    ))
    registry.register(ToolDefinition(
        name="write_file", description="Write UTF-8 text to a file, creating parent directories.",
        parameters_model=WriteFileParams, func=fs.write_file, timeout_seconds=20,
    ))