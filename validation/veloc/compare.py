"""
compare.py – Compare validation results between two approaches.

Usage
-----
    python -m validation.veloc.compare \\
        <app_name> \\
        --output-dir-a <path> --label-a <label> \\
        --output-dir-b <path> --label-b <label> \\
        [--original-src <path>] \\
        [--resilient-src-a <path>] [--resilient-src-b <path>] \\
        [--report-dir <path>]

Typical usage via runner script:

    ./build/run_compare.sh art_simple

This compares validation_output/art_simple_baseline/ (OpenCode alone)
against validation_output/art_simple/ (OpenCode + guard-agent) and
produces a side-by-side report.
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@dataclass
class CorrectnessEntry:
    passed: bool
    method: str
    score: float | None
    message: str


@dataclass
class IterativeMetrics:
    """Metrics from the iterative evaluation loop (run_iterative.sh)."""
    passed: bool
    iterations: int
    max_iters: int
    total_elapsed_s: float | None
    wall_elapsed_s: float | None
    total_input_tokens: int | None
    total_output_tokens: int | None
    total_tokens: int | None
    per_iteration: list[dict]  # [{iter, opencode_elapsed_s, validation_elapsed_s, tokens, ...}]


@dataclass
class ApproachData:
    label: str
    output_dir: Path
    correctness: list[CorrectnessEntry]
    benchmark_summary: dict
    benchmark_runs: list[dict]
    source_dir: Path | None  # resilient source for diff
    iterative: IterativeMetrics | None = None  # from run_iterative.sh


def _load_correctness(output_dir: Path) -> list[CorrectnessEntry]:
    json_path = output_dir / "correctness" / "test_results.json"
    if not json_path.exists():
        return []
    try:
        raw = json.loads(json_path.read_text(encoding="utf-8"))
        return [
            CorrectnessEntry(
                passed=bool(e.get("passed", False)),
                method=str(e.get("method", "unknown")),
                score=e.get("score"),
                message=str(e.get("message", "")),
            )
            for e in raw
        ]
    except Exception:
        return []


def _load_benchmarks(output_dir: Path) -> tuple[dict, list[dict]]:
    json_path = output_dir / "benchmarks" / "raw_metrics.json"
    if not json_path.exists():
        return {}, []
    try:
        raw = json.loads(json_path.read_text(encoding="utf-8"))
        return raw.get("summary", {}), raw.get("runs", [])
    except Exception:
        return {}, []


def _load_iterative(result_path: Path | None) -> IterativeMetrics | None:
    """Load iterative evaluation metrics from result.json."""
    if result_path is None or not result_path.exists():
        return None
    try:
        raw = json.loads(result_path.read_text(encoding="utf-8"))
        return IterativeMetrics(
            passed=bool(raw.get("passed", False)),
            iterations=int(raw.get("iterations", 0)),
            max_iters=int(raw.get("max_iters", 0)),
            total_elapsed_s=raw.get("total_elapsed_s"),
            wall_elapsed_s=raw.get("wall_elapsed_s"),
            total_input_tokens=raw.get("total_input_tokens"),
            total_output_tokens=raw.get("total_output_tokens"),
            total_tokens=raw.get("total_tokens"),
            per_iteration=raw.get("per_iteration", []),
        )
    except Exception:
        return None


def _load_approach(
    label: str,
    output_dir: Path,
    source_dir: Path | None = None,
    iterative_result: Path | None = None,
) -> ApproachData:
    correctness = _load_correctness(output_dir)
    summary, runs = _load_benchmarks(output_dir)
    iterative = _load_iterative(iterative_result)
    return ApproachData(
        label=label,
        output_dir=output_dir,
        correctness=correctness,
        benchmark_summary=summary,
        benchmark_runs=runs,
        source_dir=source_dir,
        iterative=iterative,
    )


# ---------------------------------------------------------------------------
# Source diff analysis
# ---------------------------------------------------------------------------

_SOURCE_EXTS = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hxx", ".cfg"}


def _count_source_changes(
    original_dir: Path,
    modified_dir: Path,
) -> dict:
    """Compare source files between original and modified directories.

    Returns a dict with change statistics.
    """
    if not original_dir or not original_dir.is_dir():
        return {"error": "original dir not found"}
    if not modified_dir or not modified_dir.is_dir():
        return {"error": "modified dir not found"}

    orig_files = {
        f.relative_to(original_dir): f
        for f in original_dir.rglob("*")
        if f.is_file() and f.suffix in _SOURCE_EXTS
    }
    mod_files = {
        f.relative_to(modified_dir): f
        for f in modified_dir.rglob("*")
        if f.is_file() and f.suffix in _SOURCE_EXTS
    }

    added_files = sorted(set(mod_files) - set(orig_files))
    removed_files = sorted(set(orig_files) - set(mod_files))
    common_files = sorted(set(orig_files) & set(mod_files))

    lines_added = 0
    lines_removed = 0
    files_changed = 0
    changed_file_details: list[dict] = []

    for rel_path in common_files:
        try:
            orig_lines = orig_files[rel_path].read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()
            mod_lines = mod_files[rel_path].read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()
        except OSError:
            continue

        diff = list(difflib.unified_diff(orig_lines, mod_lines, lineterm=""))
        if not diff:
            continue

        files_changed += 1
        a = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
        r = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
        lines_added += a
        lines_removed += r
        changed_file_details.append({
            "file": str(rel_path),
            "lines_added": a,
            "lines_removed": r,
        })

    # Count lines in new files
    for rel_path in added_files:
        try:
            content = mod_files[rel_path].read_text(
                encoding="utf-8", errors="replace"
            )
            n = len(content.splitlines())
            lines_added += n
            changed_file_details.append({
                "file": str(rel_path),
                "lines_added": n,
                "lines_removed": 0,
                "new_file": True,
            })
        except OSError:
            pass

    return {
        "files_changed": files_changed,
        "files_added": len(added_files),
        "files_removed": len(removed_files),
        "lines_added": lines_added,
        "lines_removed": lines_removed,
        "details": changed_file_details,
    }


# ---------------------------------------------------------------------------
# VeloC API coverage check
# ---------------------------------------------------------------------------

import re

_VELOC_PATTERNS = {
    "include": re.compile(r'#include\s*[<"]veloc[\.h]'),
    "init": re.compile(r"\bVELOC_Init\b|veloc::get_client\b"),
    "finalize": re.compile(r"\bVELOC_Finalize\b"),
    "mem_protect": re.compile(r"\bVELOC_Mem_protect\b|->mem_protect\b"),
    "checkpoint": re.compile(r"\bVELOC_Checkpoint\b|->checkpoint\b"),
    "restart": re.compile(r"\bVELOC_Restart\b|->restart\b|VELOC_Restart_test\b|->restart_test\b"),
    "veloc_cfg": None,  # checked via file existence
}


def _check_veloc_coverage(source_dir: Path) -> dict[str, bool]:
    """Check which VeloC API elements are present in the source."""
    if not source_dir or not source_dir.is_dir():
        return {}

    results: dict[str, bool] = {k: False for k in _VELOC_PATTERNS}

    # Check for veloc.cfg file
    results["veloc_cfg"] = any(source_dir.rglob("veloc.cfg"))

    for f in source_dir.rglob("*"):
        if not f.is_file() or f.suffix not in _SOURCE_EXTS:
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for key, pattern in _VELOC_PATTERNS.items():
            if pattern is not None and not results[key]:
                if pattern.search(content):
                    results[key] = True

    return results


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_comparison(
    app_name: str,
    a: ApproachData,
    b: ApproachData,
    original_dir: Path | None = None,
    report_dir: Path | None = None,
) -> str:
    """Generate a side-by-side comparison report.

    Returns the report as a string and optionally writes it to report_dir.
    """
    lines: list[str] = []

    lines.append(f"# Comparison Report: {app_name}")
    lines.append(f"")
    lines.append(f"| | **{a.label}** | **{b.label}** |")
    lines.append(f"|---|---|---|")

    # --- Correctness ---
    a_pass = sum(1 for c in a.correctness if c.passed)
    a_total = len(a.correctness)
    b_pass = sum(1 for c in b.correctness if c.passed)
    b_total = len(b.correctness)

    a_status = f"{a_pass}/{a_total} passed" if a_total else "not run"
    b_status = f"{b_pass}/{b_total} passed" if b_total else "not run"
    lines.append(f"| **Correctness** | {a_status} | {b_status} |")

    # SSIM scores if available
    a_scores = [c.score for c in a.correctness if c.score is not None]
    b_scores = [c.score for c in b.correctness if c.score is not None]
    if a_scores or b_scores:
        a_ssim = f"{min(a_scores):.6f}" if a_scores else "—"
        b_ssim = f"{min(b_scores):.6f}" if b_scores else "—"
        lines.append(f"| Min SSIM score | {a_ssim} | {b_ssim} |")

    # --- Iterative evaluation metrics ---
    if a.iterative or b.iterative:
        lines.append(f"| **Evaluation metrics** | | |")

        a_rounds = str(a.iterative.iterations) if a.iterative else "—"
        b_rounds = str(b.iterative.iterations) if b.iterative else "—"
        lines.append(f"| Rounds (iterations) | {a_rounds} | {b_rounds} |")

        def _fmt_time(t: float | None) -> str:
            if t is None:
                return "—"
            if t >= 3600:
                return f"{t/3600:.1f}h"
            if t >= 60:
                return f"{t/60:.1f}m"
            return f"{t:.1f}s"

        a_time = _fmt_time(a.iterative.total_elapsed_s) if a.iterative else "—"
        b_time = _fmt_time(b.iterative.total_elapsed_s) if b.iterative else "—"
        lines.append(f"| Total elapsed time | {a_time} | {b_time} |")

        a_wall = _fmt_time(a.iterative.wall_elapsed_s) if a.iterative else "—"
        b_wall = _fmt_time(b.iterative.wall_elapsed_s) if b.iterative else "—"
        lines.append(f"| Wall-clock time | {a_wall} | {b_wall} |")

        def _fmt_tokens(t: int | None) -> str:
            if t is None or t == 0:
                return "—"
            if t >= 1_000_000:
                return f"{t/1_000_000:.1f}M"
            if t >= 1_000:
                return f"{t/1_000:.1f}K"
            return str(t)

        a_tok = _fmt_tokens(a.iterative.total_tokens) if a.iterative else "—"
        b_tok = _fmt_tokens(b.iterative.total_tokens) if b.iterative else "—"
        lines.append(f"| Total tokens | {a_tok} | {b_tok} |")

        a_in = _fmt_tokens(a.iterative.total_input_tokens) if a.iterative else "—"
        b_in = _fmt_tokens(b.iterative.total_input_tokens) if b.iterative else "—"
        lines.append(f"| Input tokens | {a_in} | {b_in} |")

        a_out = _fmt_tokens(a.iterative.total_output_tokens) if a.iterative else "—"
        b_out = _fmt_tokens(b.iterative.total_output_tokens) if b.iterative else "—"
        lines.append(f"| Output tokens | {a_out} | {b_out} |")

        a_passed = "PASS" if (a.iterative and a.iterative.passed) else "**FAIL**" if a.iterative else "—"
        b_passed = "PASS" if (b.iterative and b.iterative.passed) else "**FAIL**" if b.iterative else "—"
        lines.append(f"| Final result | {a_passed} | {b_passed} |")

    # --- Source diff ---
    if original_dir and original_dir.is_dir():
        a_diff = _count_source_changes(original_dir, a.source_dir) if a.source_dir else {}
        b_diff = _count_source_changes(original_dir, b.source_dir) if b.source_dir else {}

        a_added = a_diff.get("lines_added", "—")
        a_removed = a_diff.get("lines_removed", "—")
        b_added = b_diff.get("lines_added", "—")
        b_removed = b_diff.get("lines_removed", "—")
        a_files = a_diff.get("files_changed", 0) + a_diff.get("files_added", 0)
        b_files = b_diff.get("files_changed", 0) + b_diff.get("files_added", 0)

        lines.append(f"| **Code changes** | | |")
        lines.append(f"| Files modified/added | {a_files} | {b_files} |")
        lines.append(f"| Lines added | +{a_added} | +{b_added} |")
        lines.append(f"| Lines removed | -{a_removed} | -{b_removed} |")

    # --- VeloC API coverage ---
    if a.source_dir or b.source_dir:
        a_cov = _check_veloc_coverage(a.source_dir) if a.source_dir else {}
        b_cov = _check_veloc_coverage(b.source_dir) if b.source_dir else {}

        if a_cov or b_cov:
            lines.append(f"| **VeloC API coverage** | | |")
            api_items = [
                ("include", "Header include"),
                ("init", "Init/get_client"),
                ("mem_protect", "Mem_protect"),
                ("checkpoint", "Checkpoint"),
                ("restart", "Restart/Restart_test"),
                ("finalize", "Finalize"),
                ("veloc_cfg", "veloc.cfg file"),
            ]
            for key, label in api_items:
                a_val = "yes" if a_cov.get(key, False) else "**MISSING**"
                b_val = "yes" if b_cov.get(key, False) else "**MISSING**"
                lines.append(f"| {label} | {a_val} | {b_val} |")

    # --- Benchmark summary ---
    a_runs = [r for r in a.benchmark_runs if r.get("codebase") == "resilient"]
    b_runs = [r for r in b.benchmark_runs if r.get("codebase") == "resilient"]
    if a_runs or b_runs:
        lines.append(f"| **Benchmark (resilient runs)** | | |")

        a_times = [r["elapsed_s"] for r in a_runs if "elapsed_s" in r]
        b_times = [r["elapsed_s"] for r in b_runs if "elapsed_s" in r]
        if a_times or b_times:
            a_avg = f"{sum(a_times)/len(a_times):.1f}s" if a_times else "—"
            b_avg = f"{sum(b_times)/len(b_times):.1f}s" if b_times else "—"
            lines.append(f"| Avg execution time | {a_avg} | {b_avg} |")

        a_attempts = [r["num_attempts"] for r in a_runs if "num_attempts" in r]
        b_attempts = [r["num_attempts"] for r in b_runs if "num_attempts" in r]
        if a_attempts or b_attempts:
            a_avg_att = f"{sum(a_attempts)/len(a_attempts):.1f}" if a_attempts else "—"
            b_avg_att = f"{sum(b_attempts)/len(b_attempts):.1f}" if b_attempts else "—"
            lines.append(f"| Avg restart attempts | {a_avg_att} | {b_avg_att} |")

    lines.append("")

    # --- Detailed correctness results ---
    if a.correctness or b.correctness:
        lines.append("## Correctness Details")
        lines.append("")

        max_tests = max(len(a.correctness), len(b.correctness))
        if max_tests > 0:
            lines.append(f"| Test | {a.label} | {b.label} |")
            lines.append("|---|---|---|")
            for i in range(max_tests):
                ac = a.correctness[i] if i < len(a.correctness) else None
                bc = b.correctness[i] if i < len(b.correctness) else None
                a_cell = _format_correctness(ac) if ac else "—"
                b_cell = _format_correctness(bc) if bc else "—"
                method = (ac.method if ac else bc.method if bc else f"Test {i+1}")
                lines.append(f"| {method} | {a_cell} | {b_cell} |")
            lines.append("")

    # --- Changed files detail ---
    if original_dir and original_dir.is_dir():
        for approach in [a, b]:
            if not approach.source_dir:
                continue
            diff = _count_source_changes(original_dir, approach.source_dir)
            details = diff.get("details", [])
            if details:
                lines.append(f"## Files changed by {approach.label}")
                lines.append("")
                for d in details:
                    new_tag = " (new)" if d.get("new_file") else ""
                    lines.append(
                        f"- `{d['file']}`{new_tag}: "
                        f"+{d['lines_added']} / -{d['lines_removed']}"
                    )
                lines.append("")

    # --- Per-iteration breakdown ---
    if a.iterative or b.iterative:
        lines.append("## Per-Iteration Breakdown")
        lines.append("")
        for approach in [a, b]:
            if not approach.iterative or not approach.iterative.per_iteration:
                continue
            lines.append(f"### {approach.label}")
            lines.append("")
            lines.append("| Iter | OpenCode time | Validation time | Total | Tokens | Passed |")
            lines.append("|---:|---:|---:|---:|---:|:---:|")
            for p in approach.iterative.per_iteration:
                oc_t = f"{p.get('opencode_elapsed_s', 0):.1f}s"
                val_t = f"{p.get('validation_elapsed_s', 0):.1f}s"
                tot_t = f"{p.get('total_elapsed_s', 0):.1f}s"
                tok = p.get("total_tokens", 0)
                tok_s = f"{tok/1000:.1f}K" if tok and tok > 0 else "—"
                passed = "PASS" if p.get("validation_passed") else "FAIL"
                lines.append(f"| {p.get('iter', '?')} | {oc_t} | {val_t} | {tot_t} | {tok_s} | {passed} |")
            lines.append("")

    report = "\n".join(lines)

    if report_dir:
        report_dir = Path(report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"comparison_{app_name}.md"
        report_path.write_text(report, encoding="utf-8")
        print(f"[compare] Report saved to {report_path}", flush=True)

    return report


def _format_correctness(c: CorrectnessEntry) -> str:
    status = "PASS" if c.passed else "**FAIL**"
    if c.score is not None:
        return f"{status} ({c.score:.6f})"
    return status


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m validation.veloc.compare",
        description="Compare validation results between two approaches.",
    )
    parser.add_argument("app_name", help="Application name (e.g. art_simple)")
    parser.add_argument(
        "--output-dir-a", required=True,
        help="Validation output directory for approach A.",
    )
    parser.add_argument(
        "--label-a", default="Approach A",
        help="Label for approach A.",
    )
    parser.add_argument(
        "--output-dir-b", required=True,
        help="Validation output directory for approach B.",
    )
    parser.add_argument(
        "--label-b", default="Approach B",
        help="Label for approach B.",
    )
    parser.add_argument(
        "--original-src", default=None,
        help="Original (unmodified) source directory for diff analysis.",
    )
    parser.add_argument(
        "--resilient-src-a", default=None,
        help="Resilient source directory for approach A (for diff/coverage).",
    )
    parser.add_argument(
        "--resilient-src-b", default=None,
        help="Resilient source directory for approach B (for diff/coverage).",
    )
    parser.add_argument(
        "--report-dir", default=None,
        help="Directory to save the comparison report. Prints to stdout if omitted.",
    )
    parser.add_argument(
        "--iterative-result-a", default=None,
        help="Path to result.json from run_iterative.sh for approach A.",
    )
    parser.add_argument(
        "--iterative-result-b", default=None,
        help="Path to result.json from run_iterative.sh for approach B.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    args = _build_parser().parse_args(argv)

    a = _load_approach(
        label=args.label_a,
        output_dir=Path(args.output_dir_a).resolve(),
        source_dir=Path(args.resilient_src_a).resolve() if args.resilient_src_a else None,
        iterative_result=Path(args.iterative_result_a).resolve() if args.iterative_result_a else None,
    )
    b = _load_approach(
        label=args.label_b,
        output_dir=Path(args.output_dir_b).resolve(),
        source_dir=Path(args.resilient_src_b).resolve() if args.resilient_src_b else None,
        iterative_result=Path(args.iterative_result_b).resolve() if args.iterative_result_b else None,
    )

    original_dir = Path(args.original_src).resolve() if args.original_src else None

    report = generate_comparison(
        app_name=args.app_name,
        a=a,
        b=b,
        original_dir=original_dir,
        report_dir=args.report_dir,
    )

    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
