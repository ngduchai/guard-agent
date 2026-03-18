from __future__ import annotations

"""
Local filesystem tools for the VeloC agent (OpenAI Agents SDK).

These tools run in the same environment as the agent runner and let the LLM
list, read, and write files under the project root on the user's machine.
"""

import os
from typing import Any, Dict, List

from agents.veloc.config import get_project_root
from agents.veloc._sdk_loader import function_tool


def _debug_enabled() -> bool:
    return os.getenv("DEPLOY_AGENT_DEBUG_LLM") == "1"


def _debug_print(message: str) -> None:
    if _debug_enabled():
        print(f"[filesync_tools] {message}")


def _resolve_path_relative_to_root(path: str) -> str:
    """Resolve path to an absolute path under the project root. Rejects escapes."""
    root = os.path.abspath(get_project_root())
    if os.path.isabs(path):
        abs_path = os.path.abspath(path)
    else:
        abs_path = os.path.abspath(os.path.join(root, path))
    # Ensure result is under project root (no .. escape)
    abs_path = os.path.normpath(abs_path)
    if not abs_path.startswith(root):
        raise PermissionError(f"Path is outside project root: {path}")
    return abs_path


def _resolve_write_path(path: str) -> str:
    """
    Resolve a write path under an explicit output root.

    To prevent accidental modifications of the repository, writes are restricted to
    GUARD_AGENT_OUTPUT_ROOT when set. This should be a path under the project root.
    """
    root = os.path.abspath(get_project_root())
    out_root_raw = (os.getenv("GUARD_AGENT_OUTPUT_ROOT") or "").strip()
    if not out_root_raw:
        raise PermissionError(
            "Writes are restricted. Set GUARD_AGENT_OUTPUT_ROOT to an output directory under the project root."
        )
    out_root = os.path.abspath(os.path.join(root, out_root_raw)) if not os.path.isabs(out_root_raw) else os.path.abspath(out_root_raw)
    out_root = os.path.normpath(out_root)
    if not out_root.startswith(root):
        raise PermissionError("GUARD_AGENT_OUTPUT_ROOT must be under the project root.")
    if os.path.isabs(path):
        abs_path = os.path.abspath(path)
    else:
        abs_path = os.path.abspath(os.path.join(out_root, path))
    abs_path = os.path.normpath(abs_path)
    if not abs_path.startswith(out_root):
        raise PermissionError(f"Write path is outside output root: {path}")
    return abs_path


@function_tool
def list_directory(dir_path: str) -> Dict[str, Any]:
    """List entries (files and subdirectories) in a directory on the user's machine.

    Args:
        dir_path: Path to the directory, absolute or relative to the project root.

    Returns:
        A dict with 'path' (resolved path), 'entries' (list of dicts with 'name',
        'type' ('file' or 'dir'), and for files 'size' in bytes).
    """
    try:
        resolved = _resolve_path_relative_to_root(dir_path)
        if not os.path.isdir(resolved):
            return {
                "path": resolved,
                "error": f"Not a directory: {dir_path}",
                "entries": [],
            }
        entries: List[Dict[str, Any]] = []
        for name in sorted(os.listdir(resolved)):
            full = os.path.join(resolved, name)
            if os.path.isdir(full):
                entries.append({"name": name, "type": "dir"})
            else:
                entries.append({"name": name, "type": "file", "size": os.path.getsize(full)})
        _debug_print(f"list_directory '{dir_path}' -> {len(entries)} entries")
        return {"path": resolved, "entries": entries}
    except Exception as exc:
        _debug_print(f"list_directory failed for '{dir_path}': {exc!r}")
        return {"path": dir_path, "error": str(exc), "entries": []}


@function_tool
def read_file(file_path: str) -> Dict[str, Any]:
    """Read the full contents of a text file on the user's machine.

    Args:
        file_path: Path to the file, absolute or relative to the project root.

    Returns:
        A dict with 'path' (resolved path), 'contents' (file contents as string),
        or 'error' if the file could not be read.
    """
    try:
        resolved = _resolve_path_relative_to_root(file_path)
        if not os.path.isfile(resolved):
            return {"path": resolved, "error": f"Not a file: {file_path}", "contents": None}
        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            contents = f.read()
        _debug_print(f"read_file '{file_path}' -> {len(contents)} chars")
        return {"path": resolved, "contents": contents}
    except Exception as exc:
        _debug_print(f"read_file failed for '{file_path}': {exc!r}")
        return {"path": file_path, "error": str(exc), "contents": None}


@function_tool
def write_file(file_path: str, contents: str) -> Dict[str, Any]:
    """Write contents to a file on the user's machine. Creates parent directories if needed.

    Args:
        file_path: Path to the file, absolute or relative to the project root.
        contents: Full file contents to write (text).

    Returns:
        A dict with 'path' (resolved path), 'written' (True if successful),
        or 'error' if the write failed.
    """
    try:
        resolved = _resolve_write_path(file_path)
        os.makedirs(os.path.dirname(resolved) or ".", exist_ok=True)
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(contents)
        _debug_print(f"write_file '{file_path}' -> {len(contents)} chars")
        return {"path": resolved, "written": True}
    except Exception as exc:
        _debug_print(f"write_file failed for '{file_path}': {exc!r}")
        return {"path": file_path, "written": False, "error": str(exc)}
