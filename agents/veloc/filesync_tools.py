"""
Local filesystem tools for the VeloC agent.

These tools run in the same process as the agent and let the LLM list, read,
write, and execute script files under the BUILD_DIR (the agent's self-contained
sandbox).

All file access — reads, writes, and script execution — is strictly restricted
to the directory returned by ``get_project_root()`` (i.e.
``GUARD_AGENT_PROJECT_ROOT``, which ``setup.sh`` sets to the ``build/``
directory).  Any path that resolves outside that directory is rejected
immediately and the caller receives a structured error dict that includes the
``allowed_root`` so the LLM can self-correct.

All functions are plain Python callables — no SDK decorator is required.
"""

from __future__ import annotations

import os
import subprocess
import stat
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


def remove_file(file_path: str) -> Dict[str, Any]:
    """Remove a single file that lives inside the BUILD_DIR sandbox.

    Only files that resolve inside the allowed root (BUILD_DIR) may be deleted.
    Any attempt to remove a path outside BUILD_DIR is rejected immediately and
    returns an error dict — the file is never touched.

    Directories are not removed by this tool; use it only for individual files.

    Args:
        file_path: Path to the file to delete, relative to BUILD_DIR or absolute.
                   Must resolve inside BUILD_DIR.

    Returns:
        Dict with:
        - ``path``         – resolved absolute path of the deleted file
        - ``allowed_root`` – the BUILD_DIR sandbox root
        - ``removed``      – True on success
        - ``error``        – present only when the operation failed (access denied,
                             file not found, is a directory, OS error, etc.)
    """
    allowed_root = _get_allowed_root()
    abs_path, err = _resolve_path(file_path)
    if err is not None:
        return err  # already contains allowed_root and error message

    if not os.path.exists(abs_path):
        return {
            "path": abs_path,
            "allowed_root": allowed_root,
            "removed": False,
            "error": f"File not found: {file_path}",
        }

    if os.path.isdir(abs_path):
        return {
            "path": abs_path,
            "allowed_root": allowed_root,
            "removed": False,
            "error": (
                f"Path is a directory, not a file: {file_path}. "
                "This tool only removes individual files."
            ),
        }

    try:
        os.remove(abs_path)
        return {"path": abs_path, "allowed_root": allowed_root, "removed": True}
    except Exception as exc:
        return {
            "path": abs_path,
            "allowed_root": allowed_root,
            "removed": False,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Script execution tool
# ---------------------------------------------------------------------------

#: Maximum bytes of stdout/stderr captured and returned to the LLM.
_MAX_OUTPUT_BYTES = 8 * 1024  # 8 KB

#: Safe PATH for sandboxed subprocesses — only standard system directories.
_SAFE_PATH = "/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin"


def execute_script(
    script_path: str,
    timeout: float = 120.0,
) -> Dict[str, Any]:
    """Execute a script file that lives inside the BUILD_DIR sandbox.

    The script must already exist inside the allowed root (BUILD_DIR).  It is
    executed with ``bash`` as the interpreter so the LLM does not need to set
    the executable bit.  The subprocess runs with:

    - ``cwd`` set to BUILD_DIR so relative paths in the script resolve inside
      the sandbox.
    - ``HOME`` overridden to BUILD_DIR to prevent ``~`` expansion outside the
      sandbox.
    - ``PATH`` restricted to standard system directories only.
    - All other environment variables inherited (so tools like ``mpirun``,
      ``cmake``, and ``python3`` remain accessible via their absolute paths or
      the restricted PATH).

    If the process does not finish within *timeout* seconds it is killed
    (SIGKILL) and a timeout error is returned alongside any partial output.

    Args:
        script_path: Path to the script file, relative to BUILD_DIR or absolute.
                     Must resolve inside BUILD_DIR.
        timeout:     Maximum wall-clock seconds to allow.  Defaults to 120 s.
                     Pass a larger value for long-running builds or MPI jobs.

    Returns:
        Dict with:
        - ``path``         – resolved absolute path of the script
        - ``allowed_root`` – the BUILD_DIR sandbox root
        - ``returncode``   – integer exit code (or ``None`` on timeout)
        - ``stdout``       – captured stdout (truncated to 8 KB)
        - ``stderr``       – captured stderr (truncated to 8 KB)
        - ``timed_out``    – True if the process was killed due to timeout
        - ``error``        – present only on access-denied or OS-level errors
    """
    allowed_root = _get_allowed_root()
    abs_path, err = _resolve_path(script_path)
    if err is not None:
        return err

    if not os.path.isfile(abs_path):
        return {
            "path": abs_path,
            "allowed_root": allowed_root,
            "error": f"Script not found: {script_path}",
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "timed_out": False,
        }

    # Build a sandboxed environment.
    env = dict(os.environ)
    env["HOME"] = allowed_root          # prevent ~ from escaping the sandbox
    env["PATH"] = _SAFE_PATH            # restrict to system tools only
    env["GUARD_AGENT_SANDBOX"] = "1"    # marker so scripts can detect sandbox

    timed_out = False
    proc: Optional[subprocess.Popen] = None
    try:
        proc = subprocess.Popen(
            ["bash", abs_path],
            cwd=allowed_root,           # working directory = BUILD_DIR
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            # Run in a new process group so we can kill the whole tree on timeout.
            start_new_session=True,
        )
        try:
            raw_stdout, raw_stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            # Kill the entire process group to clean up child processes.
            try:
                import signal
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                proc.kill()
            raw_stdout, raw_stderr = proc.communicate()

        stdout_str = raw_stdout.decode("utf-8", errors="replace")
        stderr_str = raw_stderr.decode("utf-8", errors="replace")

        # Truncate large outputs for the LLM context window.
        if len(stdout_str) > _MAX_OUTPUT_BYTES:
            stdout_str = stdout_str[:_MAX_OUTPUT_BYTES] + f"\n…[stdout truncated at {_MAX_OUTPUT_BYTES} bytes]"
        if len(stderr_str) > _MAX_OUTPUT_BYTES:
            stderr_str = stderr_str[:_MAX_OUTPUT_BYTES] + f"\n…[stderr truncated at {_MAX_OUTPUT_BYTES} bytes]"

        result: Dict[str, Any] = {
            "path": abs_path,
            "allowed_root": allowed_root,
            "returncode": proc.returncode,
            "stdout": stdout_str,
            "stderr": stderr_str,
            "timed_out": timed_out,
        }
        if timed_out:
            result["error"] = (
                f"Script exceeded the {timeout:.0f}s timeout and was killed. "
                "Partial output is included above."
            )
        return result

    except Exception as exc:
        return {
            "path": script_path,
            "allowed_root": allowed_root,
            "error": str(exc),
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "timed_out": False,
        }
