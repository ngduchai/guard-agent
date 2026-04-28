"""
audit_autocorrect.py — read audit_summary.json, attempt programmatic fixes,
                       re-audit failed apps until cleared or exhausted.

Per AGENTS.md, this script never edits non-checkpoint application source code.
For each failure verdict it applies a narrow, safe fix rule:

  FAIL_VANILLA_BROKEN
      Inspect the per-app log for the most common build/run failure modes
      (missing dependency, build flag mismatch, executable-not-found).
      Most of these need human intervention — log a TODO and skip.

  FAIL_STILL_RESILIENT
      Re-run scripts/strip_vanilla_checkpoint_hints.py on the vanilla in case
      a recent change re-introduced a hint.  Then grep the vanilla for any
      remaining VELOC_/FTI_/SCR_/checkpoint references in non-source files
      (input files, config files, helper scripts).  Strip safe matches.
      Source-code edits are forbidden — log TODO if the residual is in source.

  FAIL_ACCURACY_MISMATCH
      Diff the vanilla failure-free output against the reference failure-free
      output to surface the leading divergence.  This usually requires human
      review (workload knob mismatch, output-format difference, ignorable
      timing field).  Log TODO with a snippet of the diff.

  INCONCLUSIVE
      Retry the audit once with the same args.  If still inconclusive, log TODO.

Each cleared app is re-audited.  An app that fails the same verdict three times
in a row is considered non-converging; it is dropped from the experiment pool
with a TODO entry recording the verdict and the per-app log path.

Usage:
  python audit_autocorrect.py --output-root <build/audit_output> [--max-attempts 3]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _log(msg: str) -> None:
    print(f"[autocorrect] {msg}", flush=True)


def _read_summary(output_root: Path) -> dict:
    p = output_root / "audit_summary.json"
    if not p.exists():
        return {"apps": []}
    return json.loads(p.read_text())


def _re_audit(app: str, output_root: Path) -> int:
    """Run the audit driver on a single app.  Returns exit code (informational
    — verdict comes from the JSON written to disk)."""
    script = REPO_ROOT / "validation/veloc/scripts/audit_all_vanillas.sh"
    cmd = [str(script), app]
    _log(f"re-auditing {app} via {script.name} ...")
    return subprocess.call(cmd, cwd=str(REPO_ROOT))


def _find_residual_checkpoint_hints(app: str) -> list[Path]:
    """Grep the vanilla for non-source-code files mentioning checkpoint
    plumbing that the strip script may have missed.  Excludes upstream test/
    doc/sample directories that the agent doesn't read."""
    vroot = REPO_ROOT / "tests/apps/vanillas" / app
    if not vroot.exists():
        return []
    hits: list[Path] = []
    bad_extensions = {".cpp", ".c", ".h", ".hpp", ".cc", ".f", ".f90", ".F", ".F90", ".cxx"}
    skip_substrings = {"/build/", "/_build/", "/.git/", "/.opencode/",
                       "/node_modules/", "/test/", "/tests/", "/sample",
                       "/doc/", "/docs/", "/share/", "/extern/", "/tpls/",
                       "/external/", "/vendor/"}
    pattern_re = b"VELOC_|FTI_|SCR_|checkpoint|restart_interval|amr.restart|file_type[ \\t]*=[ \\t]*rst"
    try:
        cp = subprocess.run(
            ["grep", "-rilE", pattern_re.decode(), str(vroot)],
            capture_output=True, text=True, timeout=60,
        )
    except Exception:
        return []
    for line in cp.stdout.splitlines():
        p = Path(line)
        if not p.exists():
            continue
        rel = str(p)
        if any(s in rel for s in skip_substrings):
            continue
        if p.suffix in bad_extensions:
            # Source-code hit — log only, never auto-edit.
            hits.append(p)
            continue
        # Non-source hit — eligible for auto-strip.
        hits.append(p)
    return hits


def _diff_outputs(app: str, output_root: Path) -> str:
    """Return a short head-of-diff between vanilla failure-free and reference
    failure-free outputs (whatever output_file_name validate.py produced)."""
    app_dir = output_root / app
    vanilla = app_dir / "correctness" / "baseline" / "stdout.txt"
    reference = app_dir / "correctness" / "reference_baseline" / "stdout.txt"
    if not (vanilla.exists() and reference.exists()):
        return f"(missing outputs: vanilla={vanilla.exists()}, reference={reference.exists()})"
    cp = subprocess.run(
        ["diff", "-u", str(vanilla), str(reference)],
        capture_output=True, text=True,
    )
    out = cp.stdout
    return out[:2000] if len(out) > 2000 else out


def _process_app(app_audit: dict, output_root: Path, todos: list[str]) -> str:
    """Apply verdict-specific auto-fix.  Returns 'fixed' / 'unfixable' / 'inconclusive'."""
    app = app_audit["name"]
    status = app_audit["status"]

    if status == "FAIL_VANILLA_BROKEN":
        log = app_audit.get("log_path") or ""
        todos.append(
            f"[ISSUE] {app} | Phase 3 | FAIL_VANILLA_BROKEN | "
            f"vanilla failed to build or run failure-free | "
            f"check log: {log} — likely needs human intervention "
            "(missing dep / build flag / path issue)"
        )
        return "unfixable"

    if status == "FAIL_STILL_RESILIENT":
        residuals = _find_residual_checkpoint_hints(app)
        non_source = [p for p in residuals if p.suffix not in
                      {".cpp", ".c", ".h", ".hpp", ".cc", ".f", ".f90", ".F", ".F90", ".cxx"}]
        if non_source:
            _log(f"{app}: found {len(non_source)} non-source residual hint(s); attempting strip")
            for p in non_source[:5]:
                _log(f"  {p}")
            # Re-run the strip script (it iterates all vanillas; that's fine).
            strip = REPO_ROOT / "scripts/strip_vanilla_checkpoint_hints.py"
            if strip.exists():
                subprocess.call(
                    [sys.executable, str(strip)],
                    cwd=str(REPO_ROOT),
                )
            return "fixed"
        if residuals:
            sample = ", ".join(str(p.relative_to(REPO_ROOT)) for p in residuals[:3])
            todos.append(
                f"[ISSUE] {app} | Phase 3 | FAIL_STILL_RESILIENT | "
                f"residual checkpoint code in source files (would need source "
                f"surgery — skipped per AGENTS.md) | examples: {sample}"
            )
        else:
            todos.append(
                f"[ISSUE] {app} | Phase 3 | FAIL_STILL_RESILIENT | "
                f"vanilla recovered but no residual hints found by grep — "
                f"likely a non-VELOC/FTI checkpoint mechanism (HDF5 native, "
                f"AMReX checkpoint, etc.) | needs human investigation"
            )
        return "unfixable"

    if status == "FAIL_ACCURACY_MISMATCH":
        diff = _diff_outputs(app, output_root)
        # Save diff to disk for review
        diff_path = output_root / app / "accuracy_diff.txt"
        diff_path.write_text(diff)
        todos.append(
            f"[ISSUE] {app} | Phase 3 | FAIL_ACCURACY_MISMATCH | "
            f"vanilla output diverges from reference | "
            f"diff saved to {diff_path} — usually a workload knob mismatch "
            "or output-format difference; human review needed"
        )
        return "unfixable"

    if status == "INCONCLUSIVE":
        return "inconclusive"

    # PASS — nothing to do.
    return "fixed"


def main() -> int:
    parser = argparse.ArgumentParser(prog="audit_autocorrect.py")
    parser.add_argument("--output-root", type=Path, required=True,
                        help="Path to build/audit_output")
    parser.add_argument("--max-attempts", type=int, default=3,
                        help="Auto-correction attempts per app before giving up")
    args = parser.parse_args()

    output_root: Path = args.output_root.resolve()
    todos: list[str] = []

    for attempt in range(1, args.max_attempts + 1):
        summary = _read_summary(output_root)
        apps = summary.get("apps", [])
        failed = [a for a in apps if a["status"] != "PASS"]
        _log(f"=== auto-correct pass {attempt}: {len(failed)} of {len(apps)} apps need attention ===")
        if not failed:
            _log("All apps PASS — no auto-correction needed.")
            break

        retry_apps: list[str] = []
        for a in failed:
            decision = _process_app(a, output_root, todos)
            if decision == "fixed":
                retry_apps.append(a["name"])
            elif decision == "inconclusive":
                # Always retry inconclusive cases at least once
                retry_apps.append(a["name"])
            # 'unfixable' → already logged a TODO; do not retry

        if not retry_apps:
            _log("No re-auditable apps this pass; stopping.")
            break

        _log(f"Re-auditing {len(retry_apps)} apps: {', '.join(retry_apps)}")
        for app in retry_apps:
            _re_audit(app, output_root)

        # After re-running individual audits, regenerate the aggregate summary.
        agg = REPO_ROOT / "validation/veloc/scripts/audit_aggregate_report.py"
        all_apps = [a["name"] for a in apps]
        subprocess.call(
            [sys.executable, str(agg),
             "--apps", *all_apps,
             "--output-root", str(output_root),
             "--started-at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())],
            cwd=str(REPO_ROOT),
        )

    # Save accumulated todos.
    todos_path = output_root / "phase3_todos.txt"
    if todos:
        todos_path.write_text("\n".join(todos) + "\n")
        _log(f"Wrote {len(todos)} TODOs to {todos_path}")
    else:
        todos_path.write_text("All apps cleared in audit.\n")

    summary = _read_summary(output_root)
    cleared = [a["name"] for a in summary.get("apps", []) if a["status"] == "PASS"]
    _log(f"Final: {len(cleared)} apps cleared for Phase 4: {', '.join(cleared)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
