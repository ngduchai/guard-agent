"""
audit_aggregate_report.py — summarise vanilla-audit results across many apps.

For each audited app the audit driver (run_validate.sh --audit-vanilla) writes
its artifacts under build/audit_output/<APP>/.  This aggregator inspects only
the JSON files written by the validation framework, so verdicts stay decoupled
from validate.py's exit code (which intentionally signals "resilience proof
FAIL = audit PASS" by exiting nonzero — we cannot use that as a pass/fail
signal directly).

Per-app verdict
---------------
Each app gets one of these statuses:

    PASS        – vanilla works failure-free AND fails the resilience proof
                  under failure injection (i.e. the strip-out is complete).
    FAIL_VANILLA_BROKEN
                – vanilla failed to build or run failure-free; we cannot use
                  it for experiments until the build/run is fixed.
    FAIL_STILL_RESILIENT
                – the failure-injected run actually recovered (resilience
                  proof passed), meaning checkpoint code is still wired up
                  somewhere.  Need to strip more.
    INCONCLUSIVE
                – the resilience proof artifact is missing (e.g. the run
                  timed out or crashed before we could measure it).

Outputs
-------
* prints a summary table to stdout
* writes build/audit_output/audit_summary.json with per-app + aggregate stats

The script never raises on per-app errors; it captures whatever happened and
records it in the JSON for follow-up.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class AppAudit:
    name: str
    status: str
    reason: str
    baseline_elapsed_s: float | None
    resilient_elapsed_s: float | None
    ratio: float | None
    wall_time_pass_at_1_7: bool | None
    checkpoint_files: int | None
    accuracy_match: bool | None
    appears_resilient: bool | None
    proof_passed: bool | None
    log_path: str | None


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _audit_one(name: str, output_root: Path) -> AppAudit:
    """Compute the audit verdict for one app from its on-disk artifacts.

    Reads the proof JSON written by `_measure_resilience_signals` and the
    accuracy/Validation-A status mirrored back by `_enforce_validation_a`.

    Baseline existence is checked at the canonical cache location
    ``build/baseline_cache/<APP>/stdout.txt`` (per the post-2026-04-26
    single-canonical-path design).  The cache root is computed relative
    to ``output_root`` (sibling directory of ``audit_output``).
    """
    app_dir = output_root / name
    correctness_dir = app_dir / "correctness"
    proof_path = correctness_dir / "resilient" / "resilience_proof.json"
    # Baseline lives in the canonical per-app cache, NOT in audit_output.
    cache_root = output_root.parent / "baseline_cache"
    baseline_stdout = cache_root / name / "stdout.txt"
    log_path = output_root / "_logs" / f"{name}.log"

    proof = _read_json(proof_path)

    base_elapsed: float | None = None
    res_elapsed: float | None = None
    ratio: float | None = None
    wall_time_pass_at_1_7: bool | None = None
    ckpt_count: int | None = None
    accuracy_match: bool | None = None
    appears_resilient: bool | None = None
    proof_passed: bool | None = None

    if proof is not None:
        base_elapsed = proof.get("original_elapsed_s")
        res_elapsed = proof.get("resilient_elapsed_s")
        ratio = proof.get("ratio")
        wall_time_pass_at_1_7 = proof.get("wall_time_pass_at_1_7")
        ckpt_count = proof.get("checkpoint_files")
        accuracy_match = proof.get("accuracy_match")
        appears_resilient = proof.get("appears_resilient")
        proof_passed = proof.get("passed")

    base_kw = dict(
        baseline_elapsed_s=base_elapsed,
        resilient_elapsed_s=res_elapsed,
        ratio=ratio,
        wall_time_pass_at_1_7=wall_time_pass_at_1_7,
        checkpoint_files=ckpt_count,
        accuracy_match=accuracy_match,
        appears_resilient=appears_resilient,
        proof_passed=proof_passed,
        log_path=str(log_path) if log_path.exists() else None,
    )

    # 1) Vanilla must at least build + run failure-free.  The cache's
    #    stdout.txt is the cheapest proxy: collect_baseline.py only writes
    #    it on a successful run (atomic ground_truth_meta.json + stdout.txt).
    if not baseline_stdout.exists():
        return AppAudit(
            name=name,
            status="FAIL_VANILLA_BROKEN",
            reason=(
                "Vanilla failed to build or run failure-free "
                f"(no {baseline_stdout})."
            ),
            **base_kw,
        )

    # 2) Proof artifact missing — failure-injected stage didn't reach signal
    #    measurement (timeout, crash before injection, runner error).
    if proof is None:
        return AppAudit(
            name=name,
            status="INCONCLUSIVE",
            reason=(
                "Failure-injected run did not produce resilience_proof.json "
                "(check the per-app log for runner errors)."
            ),
            **base_kw,
        )

    # For Validation A proofs, `proof.passed` IS the audit verdict
    # (PASS = audit cleared = vanilla works AND cannot recover).  Trust it
    # directly.  Use `appears_resilient` and `accuracy_match` only to
    # discriminate failure subcategories.
    if proof_passed is True:
        return AppAudit(
            name=name,
            status="PASS",
            reason=(
                f"Vanilla works failure-free, matches reference, and cannot "
                f"recover (ratio {ratio:.2f}x, checkpoint files={ckpt_count})."
            ),
            **base_kw,
        )

    # FAIL — distinguish subcategory.
    if accuracy_match is False:
        return AppAudit(
            name=name,
            status="FAIL_ACCURACY_MISMATCH",
            reason=(
                "Vanilla failure-free output diverges from reference "
                "checkpointed code's failure-free output — checkpoint-strip "
                "process likely broke the algorithm."
            ),
            **base_kw,
        )

    if appears_resilient is True:
        return AppAudit(
            name=name,
            status="FAIL_STILL_RESILIENT",
            reason=(
                f"Vanilla recovered from failure injection (ratio {ratio:.2f}x, "
                f"checkpoint files={ckpt_count}); strip-out is incomplete."
            ),
            **base_kw,
        )

    return AppAudit(
        name=name,
        status="INCONCLUSIVE",
        reason=(
            f"Validation A failed but neither accuracy_match nor "
            f"appears_resilient is decisively True; check per-app log."
        ),
        **base_kw,
    )


def _print_table(audits: list[AppAudit]) -> None:
    name_w = max((len(a.name) for a in audits), default=4)
    name_w = max(name_w, len("App"))
    status_w = 22

    print()
    print(f"{'App'.ljust(name_w)}  {'Status'.ljust(status_w)}  Detail")
    print("-" * (name_w + 2 + status_w + 2 + 60))
    for a in audits:
        print(f"{a.name.ljust(name_w)}  {a.status.ljust(status_w)}  {a.reason}")
    print()


def _summary_stats(audits: list[AppAudit]) -> dict:
    by_status: dict[str, int] = {}
    for a in audits:
        by_status[a.status] = by_status.get(a.status, 0) + 1
    return {"total": len(audits), "by_status": by_status}


def main() -> int:
    parser = argparse.ArgumentParser(prog="audit_aggregate_report.py")
    parser.add_argument("--apps", nargs="+", required=True, help="App names to summarise.")
    parser.add_argument(
        "--output-root", required=True, type=Path,
        help="Path to build/audit_output (per-app artifacts live underneath).",
    )
    parser.add_argument(
        "--started-at", default=None,
        help="ISO timestamp recorded in the summary (informational only).",
    )
    args = parser.parse_args()

    output_root: Path = args.output_root.resolve()
    audits = [_audit_one(name, output_root) for name in args.apps]
    _print_table(audits)

    summary = {
        "started_at": args.started_at,
        "output_root": str(output_root),
        **_summary_stats(audits),
        "apps": [asdict(a) for a in audits],
    }
    summary_path = output_root / "audit_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"Summary written to {summary_path}")
    print(f"By status: {summary['by_status']}")

    failed = sum(1 for a in audits if a.status != "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
