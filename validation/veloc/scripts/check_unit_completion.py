"""check_unit_completion.py — F-5 chain-script orphan-completion verifier.

When a chain script's wrapper (run_validate.sh / run_iterative.sh) is
SIGKILL'd at a hard wallclock cap, the inner validate.py / iter loop
often continues running as an orphan and successfully completes 1-5
minutes later.  The chain script sees `rc=137` and naively logs
"FAILED" — then the next chain run wastes 15+ min re-doing work that
already succeeded.  Hit at HyPar_reference, HyPar_baseline,
LAMMPS_baseline, etc.

This script returns the AUTHORITATIVE verdict for a unit by inspecting
the on-disk artifact, NOT the wrapper's rc.

Usage:
  python -m validation.veloc.scripts.check_unit_completion \\
      --unit HyPar_reference --rc 137

Exit codes:
  0 — unit ACTUALLY completed (orphan finished after wrapper died, or
      wrapper completed normally)
  1 — unit ACTUALLY failed
  2 — indeterminate (no on-disk artifact — chain script should treat as failure)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BUILD_ROOT = REPO_ROOT / "build"


def _check_iter_unit(unit: str) -> tuple[int, str]:
    """unit like 'HyPar_baseline' -> check build/iterative_logs/<unit>/result.json"""
    rj = BUILD_ROOT / "iterative_logs" / unit / "result.json"
    if not rj.exists():
        return (2, f"no result.json at {rj}")
    try:
        d = json.loads(rj.read_text(encoding="utf-8"))
    except Exception as exc:
        return (2, f"cannot parse {rj}: {exc}")
    passed = d.get("passed")
    via = d.get("_passed_via")
    if passed is True:
        return (0, f"iter unit PASSED (via={via}, iters={d.get('iterations')})")
    return (1, f"iter unit FAILED (passed={passed})")


def _check_bench_unit(unit: str) -> tuple[int, str]:
    """unit like 'HyPar_reference' -> check build/validation_output/<unit>/pipeline_state.json + benchmarks/raw_metrics.json"""
    out_dir = BUILD_ROOT / "validation_output" / unit
    if not out_dir.is_dir():
        return (2, f"no validation_output dir for {unit}")
    state = out_dir / "pipeline_state.json"
    if state.exists():
        try:
            d = json.loads(state.read_text(encoding="utf-8"))
            if d.get("finished") is True:
                return (0, f"bench unit FINISHED (stages={d.get('completed_stages')})")
        except Exception:
            pass
    # No `finished:true` — check raw_metrics.json directly as last resort.
    raw = out_dir / "benchmarks" / "raw_metrics.json"
    if raw.exists():
        try:
            d = json.loads(raw.read_text(encoding="utf-8"))
            n_runs = len(d.get("runs") or [])
            if n_runs > 0:
                return (0, f"bench unit has {n_runs} recorded runs (raw_metrics.json present)")
        except Exception:
            pass
    return (1, f"bench unit appears incomplete (no finished pipeline_state, no raw_metrics)")


def _check_audit_unit(unit: str) -> tuple[int, str]:
    """unit like 'CoMD' -> check build/audit_output/<unit>/correctness/resilient/resilience_proof.json"""
    proof = BUILD_ROOT / "audit_output" / unit / "correctness" / "resilient" / "resilience_proof.json"
    if not proof.exists():
        return (2, f"no resilience_proof.json at {proof}")
    try:
        d = json.loads(proof.read_text(encoding="utf-8"))
        passed = d.get("passed")
        if passed is True:
            return (0, f"audit unit PASSED")
        return (1, f"audit unit FAILED (passed={passed})")
    except Exception as exc:
        return (2, f"cannot parse {proof}: {exc}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="check_unit_completion.py")
    p.add_argument("--unit", required=True,
                   help="Unit ID, e.g. 'HyPar_reference', 'LAMMPS_baseline', 'CoMD' (audit)")
    p.add_argument("--stage", choices=("iter", "bench", "audit"), default="bench",
                   help="Which stage's artifact to inspect (default: bench)")
    p.add_argument("--rc", type=int, default=None,
                   help="Optional: wrapper rc (informational; verdict comes from disk)")
    args = p.parse_args(argv)

    if args.stage == "iter":
        rc, msg = _check_iter_unit(args.unit)
    elif args.stage == "bench":
        rc, msg = _check_bench_unit(args.unit)
    else:
        rc, msg = _check_audit_unit(args.unit)

    label = {0: "ACTUALLY_PASSED", 1: "ACTUALLY_FAILED", 2: "INDETERMINATE"}[rc]
    wrapper_rc_note = f" wrapper_rc={args.rc}" if args.rc is not None else ""
    print(f"[unit_completion] {args.unit} {label}{wrapper_rc_note}: {msg}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
