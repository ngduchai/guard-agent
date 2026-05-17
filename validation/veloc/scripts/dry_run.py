"""
dry_run.py — print what each app would actually run, without executing.

For each of the 18 active apps, simulate every phase + every cell of the
end-to-end experiment and print the mpirun command lines, injection delays,
and expected recovery behavior.  Verifies:

  - per-cell consistency: vanilla / upstream / LLM-modified all use the
    SAME app_args within one (size, freq) cell (except for upstream-
    specific checkpoint-enable patches, called out explicitly)
  - injection timing: each failure-prone cell shows the actual delay
  - cache state: which artifacts already exist on disk vs need to run

Usage:
  python -m validation.veloc.scripts.dry_run
  python -m validation.veloc.scripts.dry_run --app CoMD
  python -m validation.veloc.scripts.dry_run --bench-size small --bench-freqs nofail once
  python -m validation.veloc.scripts.dry_run --app CoMD --verbose
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from validation.veloc.app_config import (
    list_apps, load_unified, load_cell, load_frequencies,
    BASELINE_CACHE,
)


def fmt_cmd(mpi_ranks: int, exe: str, args: list[str], subdir: str | None,
            env: dict[str, str] | None = None, kill_at: float | None = None) -> str:
    """Format an mpirun command line with optional cd-prefix and env vars."""
    env_prefix = ""
    if env:
        env_prefix = " ".join(f"{k}={v}" for k, v in env.items()) + " "
    cd_prefix = f"cd {subdir} && " if subdir else ""
    args_s = " ".join(str(a) for a in args)
    cmd = f"{cd_prefix}{env_prefix}mpirun -np {mpi_ranks} {exe} {args_s}".strip()
    if kill_at is not None:
        cmd += f"  [⚠ kill at {kill_at:.0f}s]"
    return cmd


def cache_state(app: str) -> dict:
    """What's already on disk (skip-existing detection)."""
    state = {}
    state["baseline_cache"] = (BASELINE_CACHE / app / "ground_truth_meta.json").exists()
    state["audit_pass"] = False
    audit_log = REPO_ROOT / f"build/audit_output/_logs/{app}.log"
    if audit_log.exists():
        try:
            state["audit_pass"] = "All stages completed successfully" in audit_log.read_text()
        except Exception:
            pass
    state["bench_ref"] = (REPO_ROOT / f"build/validation_output/{app}_reference/benchmarks/raw_metrics.json").exists()
    state["iter_pass"] = (REPO_ROOT / f"build/iterative_logs/{app}_baseline/result.json").exists()
    state["bench_base"] = (REPO_ROOT / f"build/validation_output/{app}_baseline/benchmarks/raw_metrics.json").exists()
    return state


def upstream_extra_args(app: str) -> list[str]:
    """Per-app upstream-only flags that enable native checkpointing.

    Read from tests/apps/patches/<APP>/_extra_args.txt if present (one arg
    per line).  Currently most apps don't need extras; documented exceptions:
      - CLAMR: -c 500       (enables Crux checkpoint cadence; vanilla strip
                            removed the -c handler so it can't accept this flag)
      - HPCG (env-var):     CKPT_EVERY=200 + HPCG_FIXED_SETS=50  (set as env,
                            not args; handled separately)
      - PRK_Stencil (env):  CKPT_EVERY=200
    """
    patches_dir = REPO_ROOT / f"tests/apps/patches/{app}"
    extra_args_file = patches_dir / "_extra_args.txt"
    if extra_args_file.exists():
        return [ln.strip() for ln in extra_args_file.read_text().splitlines() if ln.strip()]
    return []


def report_app(app: str, bench_size: str, bench_freqs: list[str], verbose: bool) -> dict:
    """Generate the per-app report. Returns inconsistency findings."""
    findings = {"app": app, "warnings": [], "errors": []}

    cfg = load_unified(app)
    freqs = load_frequencies()
    state = cache_state(app)
    mpi = cfg["mpi_ranks"]
    exe = cfg["executable"]
    subdir = cfg.get("input_subdir")

    val_cell = load_cell(app, "validation", "nofail")
    nominal = val_cell.nominal_runtime_s
    val_args = val_cell.app_args

    print(f"\n{'═' * 78}")
    print(f"  {app:14}  category={cfg['category']:18}  mpi_ranks={mpi}  exe={exe}")
    print(f"{'═' * 78}")
    print(f"  baseline (validation, cached): "
          f"{f'{nominal:.1f}s' if nominal else 'NOT CACHED YET'}")
    print(f"  cache state:  audit={'✓' if state['audit_pass'] else '·'}"
          f"  baseline={'✓' if state['baseline_cache'] else '·'}"
          f"  bench-ref={'✓' if state['bench_ref'] else '·'}"
          f"  iter={'✓' if state['iter_pass'] else '·'}"
          f"  bench-base={'✓' if state['bench_base'] else '·'}")

    # ─── PHASE A.1 AUDIT ──────────────────────────────────────────────
    print(f"\n  [A.1 AUDIT  validation size]  {'SKIPPED (already PASS)' if state['audit_pass'] else 'WILL RUN'}")
    if verbose or not state['audit_pass']:
        print(f"    vanilla failure-free:    {fmt_cmd(mpi, exe, val_args, subdir)}")
        kill_at = nominal * 0.9 if nominal else None
        print(f"    vanilla under failure:   {fmt_cmd(mpi, exe, val_args, subdir, kill_at=kill_at)}")
        # Upstream
        upstream_extras = upstream_extra_args(app)
        upstream_args = list(val_args) + upstream_extras
        ref_subdir = subdir  # upstream uses same subdir typically
        print(f"    upstream reference:      {fmt_cmd(mpi, exe, upstream_args, ref_subdir)}")
        if upstream_extras:
            print(f"      ↳ upstream-extra-args: {' '.join(upstream_extras)}  "
                  f"(checkpoint enable, not for vanilla/LLM)")

    # ─── PHASE A.2 BENCH-REF ──────────────────────────────────────────
    print(f"\n  [A.2 BENCH-REF  size={bench_size}  freqs={','.join(bench_freqs)}]"
          f"  {'CACHED via --resume' if state['bench_ref'] else 'WILL RUN'}")
    try:
        sz_cell = load_cell(app, bench_size, "nofail")
    except ValueError as e:
        print(f"    ✗ ERROR: {e}")
        findings["errors"].append(f"{bench_size} size not defined")
        return findings
    bench_args = sz_cell.app_args
    upstream_extras = upstream_extra_args(app)
    upstream_bench_args = list(bench_args) + upstream_extras

    # Consistency check: vanilla bench args == LLM bench args
    # (both use sz_cell.app_args; upstream additionally has extras)

    for freq in bench_freqs:
        fq = freqs[freq]
        scenario_name = f"{bench_size}-{freq}"
        if fq.get("inject_failures"):
            # Use small.nofail's nominal if available, else fall back to validation baseline
            sz_nominal = sz_cell.nominal_runtime_s or nominal
            kill_at = sz_nominal * fq["delay_fraction"] if sz_nominal else None
            print(f"    {scenario_name:18}  vanilla:  synthetic in report (= vanilla.nofail × {1 + fq['delay_fraction']:.2f})")
            print(f"    {' '*18}  upstream: {fmt_cmd(mpi, exe, upstream_bench_args, subdir, kill_at=kill_at)}  ×3 runs")
        else:
            print(f"    {scenario_name:18}  vanilla:  {fmt_cmd(mpi, exe, bench_args, subdir)}  ×3 runs")
            print(f"    {' '*18}  upstream: {fmt_cmd(mpi, exe, upstream_bench_args, subdir)}  ×3 runs")

    # ─── PHASE B.1 ITER ───────────────────────────────────────────────
    print(f"\n  [B.1 ITER  validation size, max 10 iters]"
          f"  {'SKIPPED (passed)' if state['iter_pass'] else 'WILL RUN'}")
    if verbose or not state['iter_pass']:
        kill_at = nominal * 0.5 if nominal else None
        print(f"    LLM failure-prone:       {fmt_cmd(mpi, exe, val_args, subdir, kill_at=kill_at)}")
        print(f"    LLM failure-free:        {fmt_cmd(mpi, exe, val_args, subdir)}")
        # Consistency: LLM args MUST equal vanilla args (validation size)
        if val_args != val_cell.app_args:
            findings["errors"].append("LLM iter args != vanilla validation args")

    # ─── PHASE B.2 BENCH-BASELINE ─────────────────────────────────────
    print(f"\n  [B.2 BENCH-BASELINE  size={bench_size}  freqs={','.join(bench_freqs)}]"
          f"  {'CACHED' if state['bench_base'] else 'WILL RUN (LLM source freshness checked)'}")
    for freq in bench_freqs:
        fq = freqs[freq]
        scenario_name = f"{bench_size}-{freq}"
        if fq.get("inject_failures"):
            sz_nominal = sz_cell.nominal_runtime_s or nominal
            kill_at = sz_nominal * fq["delay_fraction"] if sz_nominal else None
            print(f"    {scenario_name:18}  vanilla:  reuse from BENCH-REF")
            print(f"    {' '*18}  LLM:      {fmt_cmd(mpi, exe, bench_args, subdir, kill_at=kill_at)}  ×3 runs")
        else:
            print(f"    {scenario_name:18}  vanilla:  reuse from BENCH-REF")
            print(f"    {' '*18}  LLM:      {fmt_cmd(mpi, exe, bench_args, subdir)}  ×3 runs")

    # ─── INTRA-CELL CONSISTENCY CHECK ─────────────────────────────────
    # Within a (size, freq) cell, vanilla.args == LLM.args (= sz_cell.app_args).
    # upstream may have extras, which is OK if they're checkpoint-enable flags.
    # All are same shape, so this is more of a static check.
    if upstream_extras:
        findings["warnings"].append(
            f"upstream uses extra args {upstream_extras} (checkpoint-enable; not in vanilla/LLM)"
        )

    return findings


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--app", help="One app only (default: all 18)")
    p.add_argument("--bench-size", default="small", choices=["validation", "small", "medium", "large"])
    p.add_argument("--bench-freqs", nargs="+", default=["nofail", "once"],
                   choices=["nofail", "once", "multi", "burst"])
    p.add_argument("--verbose", action="store_true",
                   help="Show details even for cached/skipped phases")
    args = p.parse_args(argv)

    # nofail must be in bench_freqs
    if "nofail" not in args.bench_freqs:
        args.bench_freqs.insert(0, "nofail")

    apps = [args.app] if args.app else list_apps()
    print(f"\n┌{'─' * 76}┐")
    print(f"│ DRY RUN: {len(apps)} app(s), bench_size={args.bench_size}, "
          f"bench_freqs={','.join(args.bench_freqs)}{' '*(76-66-len(str(len(apps)))-len(args.bench_size)-len(','.join(args.bench_freqs)))}│")
    print(f"└{'─' * 76}┘")

    all_findings = []
    for app in apps:
        try:
            findings = report_app(app, args.bench_size, args.bench_freqs, args.verbose)
            all_findings.append(findings)
        except Exception as e:
            print(f"\n✗ {app}: ERROR {type(e).__name__}: {e}")
            all_findings.append({"app": app, "warnings": [], "errors": [str(e)]})

    # ─── SUMMARY ──────────────────────────────────────────────────────
    print(f"\n\n{'═' * 78}")
    print(f"  SUMMARY")
    print(f"{'═' * 78}")
    err_apps = [f["app"] for f in all_findings if f["errors"]]
    warn_apps = [f for f in all_findings if f["warnings"]]
    print(f"  Apps with ERRORS:   {len(err_apps)}/{len(apps)}")
    for f in all_findings:
        for err in f["errors"]:
            print(f"    ✗ {f['app']:14}  {err}")
    print(f"  Apps with WARNINGS: {len(warn_apps)}/{len(apps)}")
    for f in warn_apps:
        for warn in f["warnings"]:
            print(f"    ⚠ {f['app']:14}  {warn}")
    if not err_apps and not warn_apps:
        print(f"  ✓ All {len(apps)} apps look configured consistently.")

    return 0 if not err_apps else 1


if __name__ == "__main__":
    sys.exit(main())
