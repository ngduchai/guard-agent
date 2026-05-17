"""stage_summary.py — F-7 aggregate verdict + regression flag for a stage.

Reads per-app artifacts (iter result.json or bench raw_metrics.json or
audit per-app dirs) under a stage's output root, computes the aggregate
PASS/FAIL distribution, and writes a `_stage_summary.json` with a
`regression_flag` bit that orchestrators can use to STOP descending into
the next tier when the current tier's pass rate dropped below threshold.

Mirrors the existing audit_aggregate_report.py pattern (per-app
inspection → summary stats → per-status counts) but generalised across
the three stage types.

Stages:
  iter   — input: build/iterative_logs/, reads result.json per <APP>_baseline
  bench  — input: build/validation_output/, reads raw_metrics.json per
                  <APP>_{reference,baseline}
  audit  — input: build/audit_output/, reuses audit_aggregate_report's logic

Usage:
  python -m validation.veloc.scripts.stage_summary iter
  python -m validation.veloc.scripts.stage_summary bench --min-pass-rate 0.80
  python -m validation.veloc.scripts.stage_summary audit
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _summarize_iter(min_pass_rate: float) -> dict:
    root = REPO_ROOT / "build" / "iterative_logs"
    by_status: dict[str, int] = {}
    apps: list[dict] = []
    for d in sorted(root.glob("*_baseline")):
        rj = d / "result.json"
        if not rj.exists():
            apps.append({"app": d.name, "status": "MISSING"})
            by_status["MISSING"] = by_status.get("MISSING", 0) + 1
            continue
        try:
            r = json.loads(rj.read_text(encoding="utf-8"))
        except Exception as exc:
            apps.append({"app": d.name, "status": "PARSE_ERROR", "error": str(exc)})
            by_status["PARSE_ERROR"] = by_status.get("PARSE_ERROR", 0) + 1
            continue
        status = "PASS" if r.get("passed") else "FAIL"
        apps.append({
            "app": d.name,
            "status": status,
            "passed_via": r.get("_passed_via"),
            "iterations": r.get("iterations"),
            "total_tokens": r.get("total_tokens"),
        })
        by_status[status] = by_status.get(status, 0) + 1
    return _finalize(by_status, apps, min_pass_rate, stage="iter")


def _summarize_bench(min_pass_rate: float) -> dict:
    """For bench, "pass" means raw_metrics.json exists with finished=True
    upstream pipeline and no recorded F-2 workload-parity violations."""
    root = REPO_ROOT / "build" / "validation_output"
    by_status: dict[str, int] = {}
    apps: list[dict] = []
    for d in sorted(root.glob("*")):
        if not d.is_dir():
            continue
        raw = d / "benchmarks" / "raw_metrics.json"
        if not raw.exists():
            apps.append({"app": d.name, "status": "MISSING"})
            by_status["MISSING"] = by_status.get("MISSING", 0) + 1
            continue
        try:
            r = json.loads(raw.read_text(encoding="utf-8"))
        except Exception as exc:
            apps.append({"app": d.name, "status": "PARSE_ERROR", "error": str(exc)})
            by_status["PARSE_ERROR"] = by_status.get("PARSE_ERROR", 0) + 1
            continue
        # F-2 workload parity check
        parity = (r.get("summary") or {}).get("_workload_parity") or {}
        bad_cells = [k for k, v in parity.items() if isinstance(v, dict) and not v.get("ok")]
        n_runs = len(r.get("runs") or [])
        if bad_cells:
            status = "FAIL_WORKLOAD_PARITY"
        elif n_runs == 0:
            status = "FAIL_NO_RUNS"
        else:
            status = "PASS"
        apps.append({
            "app": d.name,
            "status": status,
            "n_runs": n_runs,
            "workload_parity_bad_cells": bad_cells,
        })
        by_status[status] = by_status.get(status, 0) + 1
    return _finalize(by_status, apps, min_pass_rate, stage="bench")


def _summarize_audit(min_pass_rate: float) -> dict:
    """For audit, just re-read audit_summary.json (already produced by
    audit_aggregate_report.py) and add the F-7 regression flag."""
    root = REPO_ROOT / "build" / "audit_output"
    s = root / "audit_summary.json"
    if not s.exists():
        return {
            "stage": "audit", "missing_summary": True,
            "min_pass_rate": min_pass_rate, "regression_flag": True,
        }
    raw = json.loads(s.read_text(encoding="utf-8"))
    by_status = raw.get("by_status", {})
    apps = raw.get("apps", [])
    return _finalize(by_status, apps, min_pass_rate, stage="audit",
                     extra={"source": str(s)})


def _finalize(by_status: dict[str, int], apps: list[dict],
              min_pass_rate: float, stage: str,
              extra: dict | None = None) -> dict:
    total = sum(by_status.values())
    passed = by_status.get("PASS", 0)
    pass_rate = (passed / total) if total else 0.0
    out = {
        "stage": stage,
        "total": total,
        "by_status": by_status,
        "pass_rate": pass_rate,
        "min_pass_rate": min_pass_rate,
        # F-7 regression flag: orchestrators should NOT proceed to the
        # next tier when this is True.  Concrete bug it prevents: the
        # parse_run_cmd regression that landed mid-experiment and caused
        # 5 of 6 fast-tier audits to FAIL — the bug ran ~50 min into
        # mid-tier before it surfaced because nothing inspected the
        # aggregate audit verdict on stage completion.
        "regression_flag": pass_rate < min_pass_rate,
        "apps": apps,
    }
    if extra:
        out.update(extra)
    return out


_STAGES = {
    "iter": _summarize_iter,
    "bench": _summarize_bench,
    "audit": _summarize_audit,
}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="stage_summary.py")
    p.add_argument("stage", choices=sorted(_STAGES.keys()))
    p.add_argument("--min-pass-rate", type=float, default=0.80,
                   help="Minimum pass rate; below this, regression_flag=True (default 0.80)")
    p.add_argument("--out", type=Path, default=None,
                   help="Write summary JSON to this path (default: print to stdout)")
    args = p.parse_args(argv)

    summary = _STAGES[args.stage](args.min_pass_rate)
    text = json.dumps(summary, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"[stage_summary] {args.stage} summary written to {args.out}", file=sys.stderr)
    else:
        print(text)

    # Exit 1 when regression detected, so chain scripts can `set -e` off it.
    return 1 if summary.get("regression_flag") else 0


if __name__ == "__main__":
    sys.exit(main())
