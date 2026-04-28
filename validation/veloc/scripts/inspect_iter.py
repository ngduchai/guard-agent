"""Inspect an iterative-baseline iteration: pull structured info out of
OpenCode's session DB and the iter directory, write a summary that explains
*why* the iteration succeeded or failed.

Usage:
    python -m validation.veloc.scripts.inspect_iter <iter_dir>
    python -m validation.veloc.scripts.inspect_iter <iter_dir> --session <id>

Without --session, the script picks the OpenCode session whose
``time_created`` lies between the iteration's prompt mtime and (mtime +
OPENCODE_TIMEOUT) and whose directory matches the iter's APP_DIR.

Outputs (written next to the iter dir):
    inspection.json   — structured analysis
    inspection.md     — human-readable summary

The structured fields:
    session_id, session_title, project_dir
    file_changes: { additions, deletions, files }
    tokens: { total, input, output, cache_read, cache_write }
    tool_calls: list of { tool, status, error?, input_summary }
    errors: list of error strings extracted from tool results
    text_summary: first/last assistant text snippets
    duration_s: opencode wallclock from stdout (if parseable)
"""

import argparse
import datetime
import json
import os
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB = Path.home() / ".local/share/opencode/opencode.db"


def _load_session_for_iter(db: sqlite3.Connection, iter_dir: Path,
                           explicit_sid: str | None,
                           opencode_timeout: int = 900) -> dict | None:
    """Return the session row that matches this iteration."""
    cur = db.cursor()
    if explicit_sid:
        row = cur.execute(
            "SELECT id, slug, directory, title, summary_additions, "
            "summary_deletions, summary_files, time_created, time_updated "
            "FROM session WHERE id = ?",
            (explicit_sid,),
        ).fetchone()
        return _row_to_dict(row) if row else None

    # Find the iter's APP_DIR — it's the parent of LOG_DIR's app-specific name.
    # iter_dir = build/iterative_logs/<APP>_<approach>/iter_N
    log_app_dir = iter_dir.parent.name           # e.g. "CoMD_baseline"
    app_name = log_app_dir.rsplit("_", 1)[0]
    app_root = iter_dir.parents[2] / "tests_baseline" / app_name
    # ^^ build/iterative_logs/<APP>_baseline/iter_N → parents[2] = build/

    # Time window: prompt.txt mtime → +opencode_timeout seconds
    prompt = iter_dir / "prompt.txt"
    if not prompt.exists():
        return None
    start_ms = int(prompt.stat().st_mtime * 1000)
    end_ms = start_ms + opencode_timeout * 1000

    rows = cur.execute(
        "SELECT id, slug, directory, title, summary_additions, "
        "summary_deletions, summary_files, time_created, time_updated "
        "FROM session "
        "WHERE time_created BETWEEN ? AND ? "
        "ORDER BY time_created",
        (start_ms - 60_000, end_ms + 60_000),  # ±60s slop
    ).fetchall()

    # Prefer the session whose directory matches the app dir; fall back to
    # the first one in the window.
    app_dir_str = str(app_root.resolve())
    for r in rows:
        if r[2] and Path(r[2]).resolve() == Path(app_dir_str).resolve():
            return _row_to_dict(r)
    if rows:
        return _row_to_dict(rows[0])
    return None


def _row_to_dict(row: tuple) -> dict:
    keys = ["id", "slug", "directory", "title", "summary_additions",
            "summary_deletions", "summary_files", "time_created",
            "time_updated"]
    return dict(zip(keys, row))


def _load_parts(db: sqlite3.Connection, session_id: str) -> list[dict]:
    cur = db.cursor()
    out = []
    for (data,) in cur.execute(
        "SELECT data FROM part WHERE session_id = ? ORDER BY time_created",
        (session_id,),
    ):
        if not data:
            continue
        try:
            out.append(json.loads(data))
        except json.JSONDecodeError:
            continue
    return out


def _summarize_tool_call(part: dict) -> dict:
    state = part.get("state", {}) or {}
    status = state.get("status", "?")
    inp = state.get("input", {}) or {}
    output = state.get("output", "") or ""
    err = ""
    if status == "error":
        err = state.get("error", "") or output[:300]
    # Compact representation of the input.
    if isinstance(inp, dict):
        inp_repr = {k: (str(v)[:120] if not isinstance(v, list) else f"<list len={len(v)}>")
                    for k, v in list(inp.items())[:6]}
    else:
        inp_repr = str(inp)[:200]
    return {
        "tool": part.get("tool", "?"),
        "status": status,
        "error": err,
        "input": inp_repr,
    }


def _compute_disk_file_changes(iter_dir: Path, session: dict | None,
                               opencode_timeout: int = 900) -> dict:
    """Inspect the project dir and count files actually modified during this
    iteration.  Reliable when the DB summary_* fields are not populated.

    A file counts as modified if:
      - it lives under session.directory
      - its mtime falls inside [prompt.txt mtime, prompt.txt mtime + opencode_timeout]
      - it is not under a noisy subdir (.git, .venv, build artifacts, __pycache__)
    """
    out = {"additions": None, "deletions": None, "files": 0,
           "modified_paths": [], "added_paths": []}

    prompt = iter_dir / "prompt.txt"
    if not prompt.exists() or not session:
        return out

    project_dir = Path(session.get("directory", "")) if session else None
    if not project_dir or not project_dir.is_dir():
        return out

    start = prompt.stat().st_mtime
    end = start + opencode_timeout

    _SKIP_DIRS = {".git", ".venv", "_build", "build", "__pycache__",
                  "node_modules", ".cache", ".opencode"}
    _BINARY_EXTS = {".o", ".a", ".so", ".pyc", ".bin"}

    modified: list[str] = []
    for root, dirs, files in os.walk(project_dir):
        # prune noisy dirs in-place
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fn in files:
            path = Path(root) / fn
            try:
                st = path.stat()
            except OSError:
                continue
            if not (start - 5 <= st.st_mtime <= end + 5):
                continue
            if path.suffix in _BINARY_EXTS:
                continue
            modified.append(str(path.relative_to(project_dir)))

    out["files"] = len(modified)
    out["modified_paths"] = sorted(modified)[:30]  # cap for readability
    return out


def analyze(iter_dir: Path, db_path: Path,
            explicit_sid: str | None = None) -> dict:
    db = sqlite3.connect(db_path)
    session = _load_session_for_iter(db, iter_dir, explicit_sid)
    result: dict = {
        "iter_dir": str(iter_dir),
        "session": session,
        "file_changes": None,
        "tokens": {"input": 0, "output": 0, "total": 0,
                   "cache_read": 0, "cache_write": 0, "reasoning": 0},
        "tool_calls": [],
        "errors": [],
        "text_first": None,
        "text_last": None,
        "step_count": 0,
        "warnings": [],
    }
    if not session:
        result["warnings"].append("No matching OpenCode session found in DB")
        return result

    sid = session["id"]
    # NOTE: session.summary_* in OpenCode's DB is unreliable (often 0 even
    # when the agent made dozens of edits — possibly populated only by
    # certain code paths).  Compute file changes from disk by counting
    # files in the project dir that were modified during the iteration's
    # wallclock window: prompt.txt mtime → +OPENCODE_TIMEOUT.
    result["file_changes"] = _compute_disk_file_changes(iter_dir, session)
    # Also keep the DB-reported summary so any discrepancy is visible.
    result["file_changes_db_summary"] = {
        "additions": session.get("summary_additions") or 0,
        "deletions": session.get("summary_deletions") or 0,
        "files": session.get("summary_files") or 0,
    }

    parts = _load_parts(db, sid)
    texts: list[str] = []
    for p in parts:
        t = p.get("type")
        if t == "text":
            txt = p.get("text", "")
            if txt:
                texts.append(txt)
        elif t == "tool":
            tc = _summarize_tool_call(p)
            result["tool_calls"].append(tc)
            if tc["status"] == "error":
                result["errors"].append(
                    f"{tc['tool']}: {tc['error'] or '(no error message)'}"
                )
        elif t == "step-finish":
            result["step_count"] += 1
            tk = p.get("tokens", {}) or {}
            result["tokens"]["input"] += tk.get("input", 0) or 0
            result["tokens"]["output"] += tk.get("output", 0) or 0
            result["tokens"]["total"] += tk.get("total", 0) or 0
            result["tokens"]["reasoning"] += tk.get("reasoning", 0) or 0
            cache = tk.get("cache", {}) or {}
            result["tokens"]["cache_read"] += cache.get("read", 0) or 0
            result["tokens"]["cache_write"] += cache.get("write", 0) or 0

    if texts:
        result["text_first"] = texts[0][:600]
        result["text_last"] = texts[-1][:600]

    # Derive per-iter signal: did the agent edit any source file?
    fc = result["file_changes"]
    result["edited_source"] = (fc.get("files") or 0) > 0

    return result


def render_md(analysis: dict) -> str:
    s = analysis.get("session") or {}
    fc = analysis.get("file_changes") or {}
    db_fc = analysis.get("file_changes_db_summary") or {}
    tk = analysis.get("tokens", {})
    n_modified = fc.get("files", 0) or 0
    lines = [
        f"# Iteration analysis: `{Path(analysis['iter_dir']).name}`",
        "",
        f"- **Session**: `{s.get('id','?')}`  ({s.get('title','?')})",
        f"- **Project dir**: `{s.get('directory','?')}`",
        f"- **Steps**: {analysis['step_count']}",
        f"- **Tokens**: input={tk.get('input',0)}  output={tk.get('output',0)}"
        f"  total={tk.get('total',0)}  cache_read={tk.get('cache_read',0)}",
        f"- **Files modified during this iter (disk scan)**: {n_modified}  →  "
        f"{'**EDITED SOURCE**' if n_modified else '**NO SOURCE EDITS**'}",
        f"- **DB session summary** (often unreliable): "
        f"+{db_fc.get('additions',0)} / -{db_fc.get('deletions',0)} across "
        f"{db_fc.get('files',0)} file(s)",
    ]
    paths = fc.get("modified_paths", [])
    if paths:
        lines.append("- Files changed:")
        for p in paths:
            lines.append(f"    - `{p}`")
        if n_modified > len(paths):
            lines.append(f"    - … (+{n_modified - len(paths)} more)")
    lines += ["", "## Tool calls"]
    if not analysis["tool_calls"]:
        lines.append("- _(none)_")
    for tc in analysis["tool_calls"]:
        line = f"- `{tc['tool']}` — {tc['status']}"
        if tc["error"]:
            line += f"  ⚠ `{tc['error'][:200]}`"
        lines.append(line)
        lines.append(f"  - input: `{json.dumps(tc['input'])[:300]}`")
    if analysis["errors"]:
        lines += ["", "## Errors during iteration"]
        for e in analysis["errors"]:
            lines.append(f"- {e}")
    if analysis.get("text_first"):
        lines += ["", "## First assistant text",
                  "```", analysis["text_first"], "```"]
    if analysis.get("text_last") and analysis.get("text_last") != analysis.get("text_first"):
        lines += ["", "## Last assistant text",
                  "```", analysis["text_last"], "```"]
    if analysis.get("warnings"):
        lines += ["", "## Warnings"] + [f"- {w}" for w in analysis["warnings"]]
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("iter_dir", type=Path,
                   help="Path to build/iterative_logs/<APP>_<approach>/iter_N")
    p.add_argument("--session", help="Override session ID auto-detection")
    p.add_argument("--db", type=Path, default=DEFAULT_DB,
                   help=f"OpenCode SQLite path (default {DEFAULT_DB})")
    p.add_argument("--write", action="store_true",
                   help="Write inspection.json + inspection.md into iter_dir")
    args = p.parse_args()

    if not args.iter_dir.exists():
        print(f"ERROR: {args.iter_dir} does not exist", file=sys.stderr)
        return 1
    if not args.db.exists():
        print(f"ERROR: OpenCode DB not found at {args.db}", file=sys.stderr)
        return 1

    analysis = analyze(args.iter_dir, args.db, args.session)
    md = render_md(analysis)
    if args.write:
        (args.iter_dir / "inspection.json").write_text(
            json.dumps(analysis, indent=2, default=str)
        )
        (args.iter_dir / "inspection.md").write_text(md)
        print(f"wrote: {args.iter_dir/'inspection.json'}")
        print(f"wrote: {args.iter_dir/'inspection.md'}")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
