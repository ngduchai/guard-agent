"""
Resilience MCP Server (Python).

This server exposes:
  - Resilience planning tools (e.g., VeLoC checkpoint configuration)
  - Codebase tools for reading/writing/applying simple text edits
  - read_url to fetch online documents for code injection and build

It is intended to be called by an LLM-driven agent that is transforming
an existing user codebase into a resilient, ready-to-deploy codebase.

Run with: python -m resilience_mcp
"""

import re
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

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


def _strip_html(html: str) -> str:
    """Remove script/style blocks and HTML tags to get approximate plain text."""
    text = re.sub(r"<script[^>]*>[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


@mcp.tool()
def read_url(
    url: str,
    max_bytes: int = 100000,
    timeout_seconds: float = 15.0,
    strip_html: bool = True,
) -> str:
    """
    Fetch an URL and return its body as text for use in code injection or build guidance.

    Use this to read online documentation (e.g. VeloC API, CMake, MPI) when the agent
    needs up-to-date or external reference material. Only http and https URLs are allowed.

    - url: full URL (e.g. https://example.com/doc.md or https://veloc.readthedocs.io/...).
    - max_bytes: maximum response body size to return; excess is truncated (default 100000).
    - timeout_seconds: request timeout in seconds (default 15).
    - strip_html: if True (default), strip HTML tags and script/style from the response
      to produce readable text; if False, return the raw body.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return f"Refusing to open non-http(s) URL: scheme {parsed.scheme!r} not allowed."
    if not parsed.netloc:
        return "Invalid URL: missing host."

    req = Request(url, headers={"User-Agent": "guard-agent-resilience-mcp/1.0"})
    try:
        with urlopen(req, timeout=timeout_seconds) as resp:
            body = resp.read(max_bytes + 1)
            content_type = (resp.headers.get_content_type() or "").lower()
    except HTTPError as e:
        return f"HTTP error opening URL: {e.code} {e.reason}"
    except URLError as e:
        return f"Failed to open URL: {e.reason}"
    except TimeoutError:
        return f"Timeout after {timeout_seconds}s opening URL."
    except OSError as e:
        return f"Error opening URL: {e}"

    if len(body) > max_bytes:
        body = body[:max_bytes]
    try:
        text = body.decode("utf-8", errors="replace")
    except Exception as e:
        return f"Could not decode response as UTF-8: {e}"

    if strip_html and "html" in content_type:
        text = _strip_html(text)
    if len(text) > max_bytes:
        text = text[:max_bytes] + "\n... [truncated] ..."
    return text


@mcp.tool()
def write_code_file(
    path: str,
    content: str,
    overwrite: bool = True,
) -> str:
    """
    Write a code file in the project.

    Use this for:
      1. Creating **new** files (e.g. veloc.conf, new CMakeLists.txt), or
      2. **Explicitly** replacing an existing file with its **complete** new content
         (full overwrite), including any injected resilience / VeloC logic.

    - path: relative path from project root.
    - content: full file content to write.
    - overwrite: if False, refuse to overwrite an existing file. Defaults to True so
      agents can safely regenerate files in a dedicated workspace.
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

_VELOC_GUIDES = {
    "general": "veloc_llm_guide.md",
    "api": "veloc_c_api.md",
    "config": "veloc_config.md",
}


@mcp.tool()
def veloc_llm_guide(
    guide: str = "general",
) -> str:
    """
    Load VeloC documentation for the agent. Choose which guide(s) to load.

    - guide: One of "general", "api", "config", or "all".
      - general: Integration guide (when to use VeloC, injection algorithm, build guidance).
      - api: C API reference (init, Mem_protect, Checkpoint, Restart, etc.).
      - config: Configuration file reference (scratch, persistent, mode, etc.).
      - all: Concatenate general + api + config (use for full code injection + config generation).
    """
    base = PROJECT_ROOT / "shared" / "veloc"
    if not base.exists():
        return "VeloC guides directory not found; rely on general checkpoint/restart best practices."

    to_load: list[str] = (
        list(_VELOC_GUIDES.keys()) if guide.strip().lower() == "all" else [guide.strip().lower()]
    )
    parts: list[str] = []
    for key in to_load:
        fname = _VELOC_GUIDES.get(key)
        if not fname:
            continue
        path = base / fname
        if path.exists():
            parts.append(path.read_text(encoding="utf-8", errors="replace"))
        else:
            parts.append(f"[Guide {key!r} not found at {path}]")

    if not parts:
        return "No VeloC guide found; rely on general checkpoint/restart best practices."
    return "\n\n---\n\n".join(parts)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
