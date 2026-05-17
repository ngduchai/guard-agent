"""
generate_benchmark_configs.py — derive validation/veloc/benchmark_configs/<APP>.json
from the unified per-app configs at tests/apps/configs/<APP>.yaml.

The unified config (tests/apps/configs/<APP>.yaml) is the single source of
truth for per-app workload (size dimension) and failure-injection cadence
(frequency dimension).  This script regenerates the legacy
benchmark_configs/<APP>.json files that validate.py + metrics_collector.py
still consume — keeping them in sync with the unified source.

Run after editing any tests/apps/configs/<APP>.yaml.

Default: emit one scenario per (size, frequency) cell where the cell has
defined app_args (validation + small for all 18 apps; medium + large only
for apps with manually-populated workloads).  Use --sizes / --freqs to
restrict.

Usage:
  python -m validation.veloc.scripts.generate_benchmark_configs
  python -m validation.veloc.scripts.generate_benchmark_configs --sizes small --freqs nofail once
  python -m validation.veloc.scripts.generate_benchmark_configs --app CoMD --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from validation.veloc.app_config import (
    list_apps, load_unified, load_frequencies, VALID_SIZES, VALID_FREQS,
)

OUT_DIR = REPO_ROOT / "validation" / "veloc" / "benchmark_configs"


def build_scenarios(app: str, sizes: list[str], freqs: list[str]) -> list[dict]:
    """Build the JSON scenarios array from the unified config.

    For cells with no defined app_args (medium/large for most apps), the cell
    is silently skipped.  injection_delay is left at runtime-resolution time
    (set to None here; consumer computes nominal_runtime × delay_fraction).
    """
    cfg = load_unified(app)
    freq_defs = load_frequencies()
    num_runs = int(cfg.get("benchmark", {}).get("num_runs_per_cell", 3))
    cap_factor = float(cfg.get("wallclock_cap_factor", 3.0))
    # Upstream-only opt-in flags that enable the reference's native
    # checkpointer (e.g. CLAMR's Crux needs `-c <interval>`).  Appended to
    # the base app_args ONLY for the upstream-resilient codebase via
    # `resilient_app_args`; vanilla and the LLM-baseline never see them, so
    # the LLM's task and the vanilla strip-out audit remain unaffected.
    #
    # Canonical source is `tests/apps/patches/<APP>/_extra_args.txt` (one
    # arg per line, blank lines and `# comments` ignored) — same file
    # `dry_run.py:upstream_extra_args()` displays.  Fallback to a YAML
    # `reference_extra_args` field is supported for callers that prefer
    # keeping all app config in one place.
    reference_extra_args: list[str] = []
    patches_extra_args = REPO_ROOT / "tests" / "apps" / "patches" / app / "_extra_args.txt"
    if patches_extra_args.exists():
        for ln in patches_extra_args.read_text().splitlines():
            ln = ln.split("#", 1)[0].strip()
            if ln:
                reference_extra_args.append(ln)
    elif cfg.get("reference_extra_args"):
        reference_extra_args = [str(a) for a in cfg["reference_extra_args"]]

    # Reference-mode args FULL REPLACEMENT (not append).  Used when the
    # vanilla `app_args` is incompatible with the upstream-checkpointed
    # binary's input format — e.g. QMCPACK vanilla uses
    # `he_simple_opt.xml` (no checkpoint attribute) but the upstream
    # binary requires `he_simple_opt_ckpt.xml` (which has the
    # `<qmc checkpoint="0">` attribute).  When set, OVERRIDES
    # `reference_extra_args` for resilient_app_args derivation.
    # Sourced from YAML `reference_extra_args_replace` (no _extra_args
    # equivalent — replacement is rare and per-app design choice).
    reference_extra_args_replace: list[str] | None = None
    if cfg.get("reference_extra_args_replace"):
        reference_extra_args_replace = [
            str(a) for a in cfg["reference_extra_args_replace"]
        ]

    # Recovery-attempt args (attempt_2+).  Most upstream-checkpointed
    # binaries need different CLI args / input files on the recovery
    # attempt to actually restore a checkpoint instead of starting fresh
    # (LAMMPS read_restart, SPARTA read_restart, SW4lite restart=,
    # Athena++ -r <file>, QMCPACK He.cont.xml, Smilei restart_dir=...).
    # When the file is absent we leave recovery_extra_args == None and
    # the runner falls back to attempt_1 args on attempt_2 (correct for
    # auto-detecting binaries: HPCG, MMSP, OpenLB, CoMD).  Per-app file:
    #   tests/apps/patches/<APP>/_extra_args_recovery.txt
    # One arg per line; "# comments" stripped.  When set, the args
    # FULLY REPLACE the resilient_app_args on attempt_2+ — they are not
    # appended to the base, because the recovery flags often need the
    # primary input file substituted (e.g. -in in.lj_restart instead of
    # -in in.lj_long), not just additional flags.
    recovery_extra_args: list[str] | None = None
    patches_recovery_args = (
        REPO_ROOT / "tests" / "apps" / "patches" / app / "_extra_args_recovery.txt"
    )
    if patches_recovery_args.exists():
        recovery_extra_args = []
        for ln in patches_recovery_args.read_text().splitlines():
            ln = ln.split("#", 1)[0].strip()
            if ln:
                recovery_extra_args.append(ln)
    elif cfg.get("reference_recovery_args"):
        recovery_extra_args = [str(a) for a in cfg["reference_recovery_args"]]

    scenarios = []
    for size in sizes:
        sz = cfg["sizes"].get(size, {})
        # None = "not defined yet" (skip).  Empty list = "defined as no args"
        # (e.g., HyPar reads everything from cwd) — keep.
        if sz.get("app_args") is None:
            continue
        # Nominal runtime: prefer the YAML estimate, but if absent fall back
        # to the measured baseline_cache (populated by the validation-size
        # audit).  load_cell uses the same precedence.  This pre-resolves
        # injection_delay at generate-time so the consumer (metrics_collector
        # load_benchmark_config) doesn't need to handle null at load.
        nominal = sz.get("nominal_runtime_s")
        if nominal is None:
            from validation.veloc.app_config import _baseline_elapsed
            nominal = _baseline_elapsed(app)
        for freq in freqs:
            fq = freq_defs.get(freq, {})
            inject = bool(fq.get("inject_failures", False))
            base_args = list(sz["app_args"])
            scenario = {
                "name": f"{size}-{freq}",
                "_size": size,
                "_frequency": freq,
                "num_procs": int(cfg.get("mpi_ranks", 4)),
                "app_args": base_args,
                "inject_failures": inject,
                "num_runs": num_runs,
            }
            if reference_extra_args_replace is not None:
                # Full replacement (rare; QMCPACK uses this for the ckpt
                # input file).  Overrides reference_extra_args.
                scenario["resilient_app_args"] = list(reference_extra_args_replace)
            elif reference_extra_args:
                # `original_app_args` left null = vanilla uses default `app_args`;
                # `resilient_app_args` carries the upstream-only opt-in flags.
                scenario["resilient_app_args"] = base_args + reference_extra_args
            if recovery_extra_args is not None:
                # Recovery args fully replace the attempt_1 args on attempt_2+.
                # The framework only applies these when codebase=="resilient"
                # and source_dir is the upstream-checkpointed tree (NOT the
                # LLM baseline) — see metrics_collector._run_scenario_once.
                scenario["resilient_app_args_recovery"] = list(recovery_extra_args)
            if inject:
                delay_fraction = float(fq.get("delay_fraction", 0.5))
                # Nominal runtime preferred from baseline_cache at consumer time;
                # if known here, pre-compute. Otherwise consumers will need to
                # resolve via app_config.load_cell at runtime.
                if nominal:
                    scenario["injection_delay"] = round(nominal * delay_fraction, 1)
                else:
                    # Sentinel meaning "compute at runtime from baseline_cache"
                    scenario["injection_delay"] = None
                scenario["max_attempts"] = int(fq.get("failures_count_target", 1)) + 2
                scenario["failures_count_target"] = int(fq.get("failures_count_target", 1))
                if nominal:
                    scenario["wallclock_cap_s"] = round(nominal * cap_factor, 1)
            else:
                scenario["injection_delay"] = 0.0
                scenario["max_attempts"] = 1
            scenarios.append(scenario)
    return scenarios


def write_one(app: str, sizes: list[str], freqs: list[str], dry_run: bool) -> dict:
    """Write benchmark_configs/<APP>.json. Returns the dict written."""
    scenarios = build_scenarios(app, sizes, freqs)
    out = OUT_DIR / f"{app}.json"
    payload = {
        "_generated_from": f"tests/apps/configs/{app}.yaml + tests/apps/configs/_frequencies.yaml",
        "_generator": "validation.veloc.scripts.generate_benchmark_configs",
        "_note": (
            "DO NOT EDIT THIS FILE DIRECTLY. Edit the unified config and "
            "re-run the generator. injection_delay=null means 'resolve at "
            "runtime via baseline_cache × frequency.delay_fraction'."
        ),
        "scenarios": scenarios,
    }
    if not dry_run:
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return payload


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--app", help="Generate for one app only (default: all 18)")
    p.add_argument("--sizes", nargs="+", default=["small"],
                   choices=VALID_SIZES,
                   help=("Sizes to include (default: small only).  validation-size "
                         "resilience is measured by AUDIT (vanilla + upstream) and ITER "
                         "(LLM-modified) — no need to re-measure in bench."))
    p.add_argument("--freqs", nargs="+", default=["nofail", "once"],
                   choices=VALID_FREQS,
                   help="Frequencies to include (default: nofail once)")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    apps = [args.app] if args.app else list_apps()
    for app in apps:
        try:
            payload = write_one(app, args.sizes, args.freqs, args.dry_run)
            n = len(payload["scenarios"])
            verb = "would write" if args.dry_run else "wrote"
            print(f"  {verb} {app}.json — {n} scenario(s): "
                  f"{[s['name'] for s in payload['scenarios']]}")
        except Exception as e:
            print(f"  ERR {app}: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
