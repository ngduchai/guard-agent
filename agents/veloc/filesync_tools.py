"""
Local filesystem tools for the VeloC agent.

These tools run in the same process as the agent and let the LLM list, read,
and write files under the BUILD_DIR (the agent's self-contained sandbox).

All file access — reads AND writes — is strictly restricted to the directory
returned by ``get_project_root()`` (i.e. ``GUARD_AGENT_PROJECT_ROOT``, which
``setup.sh`` sets to the ``build/`` directory).  Any path that resolves outside
that directory is rejected immediately and the caller receives a structured
error dict that includes the ``allowed_root`` so the LLM can self-correct.

All functions are plain Python callables — no SDK decorator is required.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from agents.veloc.config import get_project_root


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _get_allowed_root() -> str:
    """Return the single allowed root for all agent file access (BUILD_DIR)."""
    return os.path.normpath(os.path.abspath(get_project_root()))


def _resolve_path(path: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Resolve *path* to an absolute path under the allowed root.

    Returns:
        ``(abs_path, None)`` on success, or ``('', error_dict)`` when the
        resolved path escapes the allowed root.  The error dict always contains:

        - ``error``        – human-readable reason
        - ``allowed_root`` – the absolute path the agent is permitted to access
        - ``requested_path`` – the original *path* argument
    """
    allowed_root = _get_allowed_root()
    # Resolve relative paths against the allowed root so the LLM can use
    # short names like "examples/art_simple/main.cc".
    if os.path.isabs(path):
        abs_path = os.path.normpath(path)
    else:
        abs_path = os.path.normpath(os.path.join(allowed_root, path))

    if not abs_path.startswith(allowed_root + os.sep) and abs_path != allowed_root:
        return None, {
            "error": (
                "Access denied: the requested path is outside the allowed directory. "
                "All file operations must stay within the allowed_root shown below."
            ),
            "allowed_root": allowed_root,
            "requested_path": path,
        }
    return abs_path, None


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------

def list_directory(dir_path: str) -> Dict[str, Any]:
    """List entries (files and subdirectories) in a directory.

    Args:
        dir_path: Path relative to the allowed root (BUILD_DIR), or absolute.

    Returns:
        Dict with ``path`` (resolved), ``allowed_root``, and ``entries``
        (list of dicts with ``name``, ``type`` ('file'/'dir'), and ``size``
        for files).  On error, returns a dict with ``error`` and
        ``allowed_root``.
    """
    allowed_root = _get_allowed_root()
    abs_path, err = _resolve_path(dir_path)
    if err is not None:
        return err
    try:
        if not os.path.isdir(abs_path):
            return {
                "path": abs_path,
                "allowed_root": allowed_root,
                "error": f"Not a directory: {dir_path}",
                "entries": [],
            }
        entries: List[Dict[str, Any]] = []
        for name in sorted(os.listdir(abs_path)):
            full = os.path.join(abs_path, name)
            if os.path.isdir(full):
                entries.append({"name": name, "type": "dir"})
            else:
                entries.append({"name": name, "type": "file", "size": os.path.getsize(full)})
        return {"path": abs_path, "allowed_root": allowed_root, "entries": entries}
    except Exception as exc:
        return {"path": dir_path, "allowed_root": allowed_root, "error": str(exc), "entries": []}


def read_file(file_path: str) -> Dict[str, Any]:
    """Read the full contents of a text file.

    Args:
        file_path: Path relative to the allowed root (BUILD_DIR), or absolute.

    Returns:
        Dict with ``path`` (resolved), ``allowed_root``, and ``contents``
        (str).  On error, returns a dict with ``error`` and ``allowed_root``.
    """
    allowed_root = _get_allowed_root()
    abs_path, err = _resolve_path(file_path)
    if err is not None:
        return err
    try:
        if not os.path.isfile(abs_path):
            return {
                "path": abs_path,
                "allowed_root": allowed_root,
                "error": f"Not a file: {file_path}",
                "contents": None,
            }
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            contents = f.read()
        return {"path": abs_path, "allowed_root": allowed_root, "contents": contents}
    except Exception as exc:
        return {"path": file_path, "allowed_root": allowed_root, "error": str(exc), "contents": None}


def write_file(file_path: str, contents: str) -> Dict[str, Any]:
    """Write text contents to a file, creating parent directories as needed.

    Writes are restricted to the allowed root (BUILD_DIR) exactly like reads.
    No separate output-root env var is consulted; the entire BUILD_DIR is the
    writable sandbox.

    Args:
        file_path: Path relative to the allowed root (BUILD_DIR), or absolute.
        contents: Full text content to write.

    Returns:
        Dict with ``path`` (resolved), ``allowed_root``, and ``written``
        (True).  On error, returns a dict with ``error`` and ``allowed_root``.
    """
    allowed_root = _get_allowed_root()
    abs_path, err = _resolve_path(file_path)
    if err is not None:
        return err
    try:
        parent = os.path.dirname(abs_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(contents)
        return {"path": abs_path, "allowed_root": allowed_root, "written": True}
    except Exception as exc:
        return {"path": file_path, "allowed_root": allowed_root, "written": False, "error": str(exc)}
