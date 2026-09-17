"""Sandbox and behavior tests for the filesystem tools (CARD-006)."""

import pytest

from app.agent.registry import ToolRegistry
from app.tools.filesystem import register_filesystem_tools


@pytest.fixture
def registry(tmp_path):
    reg = ToolRegistry()
    register_filesystem_tools(reg, root=tmp_path)
    return reg


def test_four_tools_registered(registry, tmp_path):
    assert registry.names() == ["list_dir", "read_file", "search_content", "write_file"]
    assert registry.get("list_dir") is not None


def test_write_read_roundtrip_creates_parent_dirs(registry):
    result = registry.execute("write_file", {"path": "notes/sub/a.txt", "content": "hello 知微"})
    assert result.success is True

    read = registry.execute("read_file", {"path": "notes/sub/a.txt"})
    assert read.success is True
    assert read.data["content"] == "hello 知微"
    assert read.data["path"] == "notes/sub/a.txt"


def test_list_dir_returns_type_and_relative(registry, tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "readme.md").write_text("x", encoding="utf-8")
    (tmp_path / "top.txt").write_text("y", encoding="utf-8")

    result = registry.execute("list_dir", {"path": "."})
    assert result.success is True
    entries = {e["name"]: e for e in result.data["entries"]}
    assert entries["docs"]["type"] == "dir"
    assert entries["docs"]["relative_path"] == "docs"
    assert entries["top.txt"]["type"] == "file"
    assert entries["top.txt"]["relative_path"] == "top.txt"


def test_dotdot_traversal_rejected(registry):
    result = registry.execute("read_file", {"path": "../../etc/passwd"})
    assert result.success is False
    assert "escapes workspace" in (result.error or "")


def test_absolute_path_escape_rejected(registry, tmp_path):
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    result = registry.execute("read_file", {"path": str(outside)})
    assert result.success is False
    assert "escapes workspace" in (result.error or "")


def test_mixed_traversal_rejected(registry):
    result = registry.execute("list_dir", {"path": "notes/../../.."})
    assert result.success is False
    assert "escapes workspace" in (result.error or "")


def test_binary_file_read_has_explicit_error(registry, tmp_path):
    (tmp_path / "blob.bin").write_bytes(b"\x00\x01\x02\xff\xfe")
    result = registry.execute("read_file", {"path": "blob.bin"})
    assert result.success is False
    assert "binary" in (result.error or "")


def test_oversized_file_rejected(registry, tmp_path):
    (tmp_path / "big.txt").write_bytes(b"a" * (200 * 1024 + 1))
    result = registry.execute("read_file", {"path": "big.txt"})
    assert result.success is False
    assert "too large" in (result.error or "")


def test_search_finds_keyword_recursively(registry, tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "note.md").write_text("nothing here\nclaude code is interesting", encoding="utf-8")
    (tmp_path / "plain.txt").write_text("Claude again", encoding="utf-8")

    result = registry.execute("search_content", {"keyword": "claude", "dir": "."})
    assert result.success is True
    paths = [m["relative_path"] for m in result.data["matches"]]
    assert "a/note.md" in paths
    assert "plain.txt" in paths
    assert result.data["truncated"] is False


def test_search_results_capped(registry, tmp_path):
    content = "\n".join(f"match line {i}" for i in range(100))
    (tmp_path / "many.txt").write_text(content, encoding="utf-8")

    result = registry.execute("search_content", {"keyword": "match"})
    assert result.success is True
    assert len(result.data["matches"]) == 50
    assert result.data["truncated"] is True


def test_search_without_hits_is_ok(registry, tmp_path):
    (tmp_path / "empty.txt").write_text("nothing", encoding="utf-8")
    result = registry.execute("search_content", {"keyword": "zzz"})
    assert result.success is True
    assert result.data["matches"] == []
    assert result.data["truncated"] is False