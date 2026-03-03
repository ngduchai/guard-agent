"""
Resilience MCP Server (Python).

This server exposes:
  - Resilience planning tools (e.g., VeLoC checkpoint configuration)
  - Codebase tools for reading/writing/applying simple text edits

It is intended to be called by an LLM-driven agent that is transforming
an existing user codebase into a resilient, ready-to-deploy codebase.

Run with: python -m resilience_mcp
"""

from pathlib import Path

from mcp.server import FastMCP

mcp = FastMCP(
    "guard-agent-resilience-mcp",
)

PROJECT_ROOT = Path.cwd()


def _safe_path(rel_path: str) -> Path:
    """
    Resolve a user-supplied relative path safely within PROJECT_ROOT.

    Paths outside PROJECT_ROOT are rejected so the LLM cannot modify
    arbitrary locations on the filesystem.
    """
    candidate = (PROJECT_ROOT / rel_path).resolve()
    try:
        candidate.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise ValueError(f"path {rel_path!r} escapes project root") from exc
    return candidate


@mcp.tool()
def list_project_files(
    root: str = ".",
    pattern: str = "**/*",
    max_files: int = 200,
) -> str:
    """
    List project files under a given root matching a glob pattern.

    Useful for an agent to discover which files exist before planning
    code transformations (e.g. which modules to instrument for resilience).

    - root: path relative to the project root.
    - pattern: glob pattern (e.g. '**/*.py', '**/*.c', '**/*.cu').
    - max_files: maximum number of entries to return.
    """
    base = _safe_path(root)
    if not base.exists():
        return f"No such directory: {root}"

    paths: list[str] = []
    for path in base.glob(pattern):
        if path.is_file():
            rel = path.relative_to(PROJECT_ROOT).as_posix()
            paths.append(rel)
            if len(paths) >= max_files:
                break
    if not paths:
        return "No files matched."
    return "\n".join(paths)


@mcp.tool()
def read_code_file(
    path: str,
    max_bytes: int = 20000,
) -> str:
    """
    Read a code file from the project.

    - path: file path relative to the project root.
    - max_bytes: truncate content to this many bytes to avoid huge responses.
    """
    target = _safe_path(path)
    if not target.exists():
        return f"File not found: {path}"
    if not target.is_file():
        return f"Not a file: {path}"
    data = target.read_text(encoding="utf-8", errors="replace")
    if len(data) > max_bytes:
        return data[:max_bytes] + "\n... [truncated] ..."
    return data


@mcp.tool()
def write_code_file(
    path: str,
    content: str,
    overwrite: bool = False,
) -> str:
    """
    Write a code file in the project.

    Use this for: (1) creating **new** files (e.g. veloc.conf, new CMakeLists.txt),
    or (2) **explicitly** replacing an existing file with its **complete** new content
    (full overwrite). For modifying existing source (e.g. inserting #include or VeloC
    calls), use read_code_file then apply_text_patch so the original code is preserved.

    - path: relative path from project root.
    - content: full file content to write.
    - overwrite: if False, refuse to overwrite an existing file.
    """
    target = _safe_path(path)
    if target.exists() and not overwrite:
        return (
            f"Refusing to overwrite existing file {path!r} "
            "without overwrite=True."
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Wrote {path} ({len(content)} bytes)."


@mcp.tool()
def apply_text_patch(
    path: str,
    search: str,
    replace: str,
    max_replacements: int = 1,
) -> str:
    """
    Apply a simple text replacement patch to a file.

    This is a low-level code-editing primitive that an agent can combine
    with read_code_file and write_code_file to iteratively inject
    resilience code (e.g. VeLoC calls, retry wrappers).

    - path: relative file path.
    - search: substring to replace.
    - replace: replacement text.
    - max_replacements: maximum number of occurrences to replace
      (<= 0 means replace all).
    """
    target = _safe_path(path)
    if not target.exists():
        return f"File not found: {path}"
    text = target.read_text(encoding="utf-8", errors="replace")
    occurrences = text.count(search)
    if occurrences == 0:
        return f"No occurrences of search text found in {path}."

    if max_replacements and max_replacements > 0:
        new_text = text.replace(search, replace, max_replacements)
        applied = min(occurrences, max_replacements)
    else:
        new_text = text.replace(search, replace)
        applied = occurrences

    target.write_text(new_text, encoding="utf-8")
    return f"Applied {applied} replacement(s) in {path}."


@mcp.tool()
def ensure_directory(
    path: str,
) -> str:
    """
    Ensure that a directory exists under the project root.

    - path: directory path relative to the project root.

    This is useful for creating a separate workspace where the agent can write
    resilient variants of the user's code without touching the originals.
    """
    target = _safe_path(path)
    target.mkdir(parents=True, exist_ok=True)
    return f"Directory ensured at {path!r} (absolute: {target})"


@mcp.tool()
def copy_tree(
    source_root: str,
    target_root: str,
    pattern: str = "**/*",
    overwrite: bool = False,
    max_files: int = 500,
) -> str:
    """
    Copy a subset of the project tree into a new location under PROJECT_ROOT.

    - source_root: source directory relative to project root.
    - target_root: destination directory relative to project root.
    - pattern: glob pattern to select files (default: '**/*').
    - overwrite: if False, existing files in target_root are left untouched.
    - max_files: safety limit on the number of files to copy.

    Typical usage:
      - Create a resilient variant under 'build/resilient_copy/...'.
      - Keep original source tree read-only for the agent.
    """
    src = _safe_path(source_root)
    dst = _safe_path(target_root)
    if not src.exists() or not src.is_dir():
        return f"Source root {source_root!r} does not exist or is not a directory."

    dst.mkdir(parents=True, exist_ok=True)

    from shutil import copy2

    count = 0
    for path in src.glob(pattern):
        if not path.is_file():
            continue
        rel = path.relative_to(src)
        dest_path = dst / rel
        if dest_path.exists() and not overwrite:
            continue
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        copy2(path, dest_path)
        count += 1
        if count >= max_files:
            break

    return f"Copied {count} file(s) from {source_root!r} to {target_root!r}."


@mcp.tool()
def delete_path(
    path: str,
    recursive: bool = False,
) -> str:
    """
    Delete a file or (optionally) an entire directory tree under PROJECT_ROOT.

    - path: relative path from project root.
    - recursive: if True and the path is a directory, delete the directory tree.
      If False, only files (or empty directories) are removed.

    This is intended for cleaning up temporary workspaces created by the agent.
    """
    target = _safe_path(path)
    if not target.exists():
        return f"Path not found: {path}"

    if target.is_dir():
        if recursive:
            from shutil import rmtree

            rmtree(target)
            return f"Deleted directory tree {path!r}."
        if any(target.iterdir()):
            return f"Directory {path!r} is not empty; set recursive=True to delete."
        target.rmdir()
        return f"Deleted empty directory {path!r}."

    target.unlink()
    return f"Deleted file {path!r}."


@mcp.tool()
def veloc_configure_checkpoint(
    checkpoint_interval_seconds: int,
    local_dir: str = "./checkpoints/local",
    global_dir: str = "./checkpoints/global",
    max_versions: int = 5,
    async_flush: bool = True,
    compression: str | None = None,
) -> str:
    """
    Generate a VeLoC-style checkpoint configuration snippet.

    This helper does **not** try to mirror the full VELOC configuration
    language. Instead, it produces a small, human-readable template that
    the LLM or user can adapt into a `veloc.conf` file.

    Parameters
    ----------
    checkpoint_interval_seconds:
        Target wall-clock interval between durable checkpoints.
    local_dir:
        Node-local scratch directory for fast checkpoints.
    global_dir:
        Shared / parallel filesystem directory for durable checkpoints.
    max_versions:
        Maximum number of checkpoint versions to keep.
    async_flush:
        If true, suggest asynchronous flushing from local to global storage.
    compression:
        Optional compression algorithm name (e.g. "zlib", "zstd").
    """
    lines: list[str] = [
        "# Generated VeLoC configuration template",
        "# Adjust directory paths and options to match the target system.",
        "",
        f"scratch_dir = {local_dir}",
        f"global_dir = {global_dir}",
        "",
        f"checkpoint_interval_seconds = {checkpoint_interval_seconds}",
        f"max_versions = {max_versions}",
        "",
        "# Whether to flush checkpoints asynchronously from local to global storage",
        f"async_flush = {'1' if async_flush else '0'}",
    ]

    if compression and compression.lower() != "none":
        lines.extend(
            [
                "",
                "# Optional compression for checkpoint data",
                f"compression = {compression}",
            ]
        )

    lines.extend(
        [
            "",
            "# NOTE:",
            "# - Ensure this file is accessible as 'veloc.conf' from the",
            "#   application working directory, or update your VELOC_Init",
            "#   call to point at the correct path.",
            "# - You may need to align option names with the VELOC version",
            "#   installed on the target system.",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
