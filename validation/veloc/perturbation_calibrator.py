"""Pre-flight calibration for per-app `perturbation:` YAML specs.

The cold-replay detector's slope test (see plan
``/home/ndhai/.claude/plans/tranquil-napping-meerkat.md``) depends on
each app having a perturbation knob that satisfies three invariants:

1. **Output sensitivity** — perturbing the knob across its declared
   range must produce a meaningfully different output (otherwise
   ``output_correct`` always passes trivially for both honest recovery
   and cold-replay, defeating the cache-class half of the defense).

2. **Timing stability** — the perturbation must NOT shift vanilla
   execution time materially (otherwise the slope-test's wall-time-ratio
   denominators are noisy and the slope comes out wrong even for honest
   recovery).

3. **Safety** — vanilla must exit cleanly at both extremes of the range
   (otherwise random perturbations during validation cycles will
   eventually hit a crashing value and the experiment stalls).

This module automates the three checks. Run before activating a new
app's perturbation spec in the validator.

CLI:

.. code-block:: bash

    build/venv/bin/python -m validation.veloc.perturbation_calibrator SAMRAI
    build/venv/bin/python -m validation.veloc.perturbation_calibrator Nyx --update-yaml

On success the script prints a short report. With ``--update-yaml`` it
also flips ``calibration.safe_value_range_verified: true`` in the app's
``tests/apps/configs/<APP>.yaml`` so the validator trusts the spec.

This is invoked manually per app — not part of any automated pipeline.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

# Avoid heavy imports at module load: validate.py pulls in a large dep tree
# (matplotlib, etc.) for the report stage. We only need a couple of helpers,
# so import inside the functions that use them.


REPO_ROOT = Path(__file__).resolve().parents[2]
VANILLAS_DIR = REPO_ROOT / "tests" / "apps" / "vanillas"
CONFIGS_DIR = REPO_ROOT / "tests" / "apps" / "configs"
BUILD_ROOT = REPO_ROOT / "build"


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class VanillaRun:
    """One vanilla execution at a specific perturbation value (or unperturbed)."""

    label: str  # "unperturbed" | "min" | "max"
    perturbation_value: "float | int | None"  # None for unperturbed
    elapsed_s: float
    exit_code: int
    output_file: Path
    crashed: bool = False
    error_message: str = ""


@dataclass
class CalibrationResult:
    """All three runs + the three invariant checks + pass/fail verdict."""

    app: str
    spec_method: str
    spec_range: tuple
    runs: dict[str, VanillaRun] = field(default_factory=dict)

    # Invariant 1: output sensitivity
    output_diff_min_vs_unperturbed: "float | None" = None
    output_diff_max_vs_unperturbed: "float | None" = None
    output_diff_threshold: "float | None" = None
    output_sensitivity_ok: "bool | None" = None

    # Invariant 2: timing stability
    timing_delta_min_pct: "float | None" = None
    timing_delta_max_pct: "float | None" = None
    timing_stability_threshold_pct: float = 0.30  # default 30% (see calibrate() docstring)
    timing_stability_ok: "bool | None" = None

    # Invariant 3: safety (no crashes)
    safety_ok: bool = True

    passed: bool = False
    failure_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "app": self.app,
            "spec_method": self.spec_method,
            "spec_range": list(self.spec_range),
            "runs": {
                label: {
                    "value": r.perturbation_value,
                    "elapsed_s": r.elapsed_s,
                    "exit_code": r.exit_code,
                    "crashed": r.crashed,
                    "output_file_size": (
                        r.output_file.stat().st_size if r.output_file.exists() else None
                    ),
                    "error_message": r.error_message,
                }
                for label, r in self.runs.items()
            },
            "output_diff_min_vs_unperturbed": self.output_diff_min_vs_unperturbed,
            "output_diff_max_vs_unperturbed": self.output_diff_max_vs_unperturbed,
            "output_diff_threshold": self.output_diff_threshold,
            "output_sensitivity_ok": self.output_sensitivity_ok,
            "timing_delta_min_pct": self.timing_delta_min_pct,
            "timing_delta_max_pct": self.timing_delta_max_pct,
            "timing_stability_threshold_pct": self.timing_stability_threshold_pct,
            "timing_stability_ok": self.timing_stability_ok,
            "safety_ok": self.safety_ok,
            "passed": self.passed,
            "failure_reasons": self.failure_reasons,
        }


# ---------------------------------------------------------------------------
# Vanilla execution helpers
# ---------------------------------------------------------------------------


def _setup_run_cwd(
    *,
    cwd: Path,
    source_dir: Path,
    build_dir: Path,
    app_args: list[str],
    app_input_subdir: "str | None",
    veloc_config_name: str,
    extra_source_dirs: "list[Path] | None",
) -> None:
    """Mirror runner._symlink_input_data + _copy_veloc_cfg in a fresh cwd."""
    from .runner import _copy_veloc_cfg, _symlink_input_data

    if cwd.exists():
        shutil.rmtree(cwd)
    cwd.mkdir(parents=True, exist_ok=True)
    _copy_veloc_cfg(source_dir, build_dir, cwd, veloc_config_name)
    _symlink_input_data(
        source_dir,
        build_dir,
        cwd,
        app_args,
        extra_source_dirs=extra_source_dirs,
        input_subdir=app_input_subdir,
    )


def _run_vanilla_at_value(
    *,
    label: str,
    value: "float | int | None",
    source_dir: Path,
    build_dir: Path,
    executable_name: str,
    num_procs: int,
    app_args: list[str],
    perturbation_spec,  # PerturbationSpec or None when unperturbed
    scratch_root: Path,
    veloc_config_name: str,
    app_input_subdir: "str | None",
    extra_source_dirs: "list[Path] | None",
    output_file_name: str,
    timeout_s: "float | None" = None,
    run_once_fn: "Callable | None" = None,
    apply_perturbation_fn: "Callable | None" = None,
) -> VanillaRun:
    """Execute one vanilla run at the given perturbation value (or unperturbed).

    ``run_once_fn`` and ``apply_perturbation_fn`` are injectable so unit
    tests can mock the heavy subprocess + filesystem work.
    """
    if run_once_fn is None:
        from .runner import run_once as run_once_fn
    if apply_perturbation_fn is None:
        from .app_config import apply_perturbation as apply_perturbation_fn

    cwd = scratch_root / f"calib_{label}"
    _setup_run_cwd(
        cwd=cwd,
        source_dir=source_dir,
        build_dir=build_dir,
        app_args=app_args,
        app_input_subdir=app_input_subdir,
        veloc_config_name=veloc_config_name,
        extra_source_dirs=extra_source_dirs,
    )

    effective_args = list(app_args)
    env_override: dict = {}
    if value is not None and perturbation_spec is not None:
        effective_args, env_override, _modified_file = apply_perturbation_fn(
            perturbation_spec,
            value,
            cwd=cwd,
            source_dir=source_dir,
            app_args=effective_args,
            env={},
        )

    import os

    run_env = dict(os.environ)
    if env_override:
        run_env.update(env_override)

    output_dir = cwd  # outputs land in cwd
    t_start = time.monotonic()
    try:
        result = run_once_fn(
            build_dir=build_dir,
            executable_name=executable_name,
            num_procs=num_procs,
            app_args=effective_args,
            output_dir=output_dir,
            run_cwd=cwd,
            env=run_env,
            veloc_config_name=veloc_config_name,
            timeout_s=timeout_s,
        )
        elapsed = result.elapsed_s if hasattr(result, "elapsed_s") else (time.monotonic() - t_start)
        exit_code = result.exit_code if hasattr(result, "exit_code") else 0
        return VanillaRun(
            label=label,
            perturbation_value=value,
            elapsed_s=elapsed,
            exit_code=exit_code,
            output_file=cwd / output_file_name,
            crashed=(exit_code != 0),
            error_message="" if exit_code == 0 else f"nonzero exit {exit_code}",
        )
    except Exception as exc:
        return VanillaRun(
            label=label,
            perturbation_value=value,
            elapsed_s=time.monotonic() - t_start,
            exit_code=-1,
            output_file=cwd / output_file_name,
            crashed=True,
            error_message=f"{type(exc).__name__}: {exc}",
        )


# ---------------------------------------------------------------------------
# Output diff
# ---------------------------------------------------------------------------


def _compute_output_diff(
    *,
    baseline_file: Path,
    candidate_file: Path,
    method: str,
    atol: float,
    rtol: float,
) -> float:
    """Return a single scalar quantifying ``|baseline - candidate|``.

    For numeric comparators this is the max absolute element-wise difference;
    for text comparators it is 1.0 if files differ, 0.0 if they match (binary
    signal — the calibrator's sensitivity test still works because we only
    require diff > threshold).
    """
    if not baseline_file.exists():
        raise FileNotFoundError(f"baseline output missing: {baseline_file}")
    if not candidate_file.exists():
        raise FileNotFoundError(f"candidate output missing: {candidate_file}")

    if method in ("numeric-tolerance", "numeric"):
        # Read raw doubles and compute max abs diff. The validator uses
        # NumericToleranceComparator with the same dtype convention.
        import numpy as np

        try:
            a = np.fromfile(str(baseline_file), dtype=np.float64)
            b = np.fromfile(str(candidate_file), dtype=np.float64)
        except Exception as exc:
            raise RuntimeError(f"failed to load numeric outputs: {exc}") from exc
        n = min(len(a), len(b))
        if n == 0:
            raise RuntimeError("both output files have zero elements after fromfile")
        return float(np.max(np.abs(a[:n] - b[:n])))

    # Text / hash / other: binary signal.
    return 0.0 if baseline_file.read_bytes() == candidate_file.read_bytes() else 1.0


# ---------------------------------------------------------------------------
# Main calibration entry point
# ---------------------------------------------------------------------------


def calibrate(
    app: str,
    *,
    scratch_root: "Path | None" = None,
    output_diff_threshold: "float | None" = None,
    timing_stability_threshold_pct: float = 0.30,
    timeout_s: "float | None" = None,
    run_once_fn: "Callable | None" = None,
    apply_perturbation_fn: "Callable | None" = None,
) -> CalibrationResult:
    """Run the 3-point calibration for ``app``'s perturbation spec.

    Parameters
    ----------
    app
        App name as it appears in ``tests/apps/configs/<APP>.yaml``.
    scratch_root
        Where to write the three calibration cwds. Defaults to
        ``build/_calibration/<APP>/``. Cleared before each calibration.
    output_diff_threshold
        Minimum required ``|Z_P(extreme) - Z_unperturbed|`` for the
        sensitivity invariant. Defaults to ``1000 × app's tolerance``.
    timing_stability_threshold_pct
        Maximum allowed wall-time delta vs unperturbed. Default 0.30
        (30%) — much looser than the plan's nominal 5% because the
        slope test's ratio metric is invariant to uniform timing shifts
        induced by perturbation (both numerator and denominator scale
        by the same factor, so the ratio is unchanged). The remaining
        concern is only (a) kill-time-to-fraction mapping drift if the
        perturbation makes Z_P timing very different from the kill
        leg's timing, and (b) the per-app `production_cap_ratio` cap.
        Both are mild concerns; 30% leaves plenty of headroom. Use
        ``--timing-threshold-pct 0.15`` (tighter) if you want extra
        rigor.
    timeout_s
        Per-run timeout. Defaults to ``5 × nominal_runtime`` from the
        app's YAML.
    run_once_fn, apply_perturbation_fn
        Injection points for unit tests. Production code leaves these
        as None (uses the real ``runner.run_once`` and
        ``app_config.apply_perturbation``).

    Returns
    -------
    CalibrationResult with all 3 invariants checked and a pass/fail verdict.
    """
    from .app_config import load_cell

    cell = load_cell(app, size="validation", frequency="nofail")
    spec = cell.perturbation
    if spec is None:
        raise ValueError(
            f"{app} has no perturbation: block in its YAML; nothing to calibrate"
        )
    if spec.method == "disabled":
        raise ValueError(
            f"{app} perturbation is explicitly disabled (reason: {spec.reason}); "
            "nothing to calibrate"
        )

    # Wiring: where the source + (already-built) binary live + comparator config.
    source_dir = VANILLAS_DIR / app
    if not source_dir.exists():
        raise FileNotFoundError(f"vanilla source not found: {source_dir}")
    # build_dir must contain the built vanilla binary.  The
    # baseline_cache layout (populated by collect_baseline) is the
    # current source of vanilla binaries; the legacy tests_baseline
    # layout no longer exists for vanilla apps under the perturbation
    # pipeline.  Same fix as commit 15362cc2a for _compute_perturbed_baseline.
    build_dir = BUILD_ROOT / "baseline_cache" / app
    if not (build_dir / "_build").is_dir():
        raise FileNotFoundError(
            f"vanilla binary not built yet at {build_dir}/_build — run "
            f"the validator on {app} once to populate the baseline cache "
            f"(or call collect_baseline.collect()) before calibrating."
        )
    # cell.executable may carry a path prefix (e.g. SAMRAI's
    # './_build/bin/linadv').  run_validate.sh strips this to the
    # basename so _find_executable's os.walk-by-basename works against
    # the baseline_cache layout (which puts the built binary at
    # _build/_build/bin/<basename>, not _build/bin/<full_path>).
    # Mirror that normalization here.
    executable_name = Path(cell.executable).name
    num_procs = cell.mpi_ranks
    app_args = cell.app_args
    comparison = cell.comparison
    # `comparison.output_file: null` means the per-app comparison is
    # stdout-based (via keep_patterns / VALIDATION_SIGNATURE) rather
    # than file-based.  In that case the "output" to compare is the
    # run's stdout, captured by run_once at cwd/stdout.txt.  Default
    # to validation_output.bin for the more common file-based case.
    output_file_name = comparison.get("output_file") or "stdout.txt"
    method = comparison.get("method", "numeric-tolerance")
    atol = float(comparison.get("tolerance", 1e-12))
    rtol = atol

    if output_diff_threshold is None:
        output_diff_threshold = 1000.0 * atol

    if timeout_s is None and cell.nominal_runtime_s:
        timeout_s = 5.0 * cell.nominal_runtime_s

    if scratch_root is None:
        scratch_root = BUILD_ROOT / "_calibration" / app
    if scratch_root.exists():
        shutil.rmtree(scratch_root)
    scratch_root.mkdir(parents=True, exist_ok=True)

    lo, hi = spec.value_range

    result = CalibrationResult(
        app=app,
        spec_method=spec.method,
        spec_range=(lo, hi),
        output_diff_threshold=output_diff_threshold,
        timing_stability_threshold_pct=timing_stability_threshold_pct,
    )

    # Three runs (unperturbed, min, max).
    for label, value in (("unperturbed", None), ("min", lo), ("max", hi)):
        print(f"[calibrate {app}] running {label} (value={value})...", flush=True)
        run = _run_vanilla_at_value(
            label=label,
            value=value,
            source_dir=source_dir,
            build_dir=build_dir,
            executable_name=executable_name,
            num_procs=num_procs,
            app_args=app_args,
            perturbation_spec=spec,
            scratch_root=scratch_root,
            veloc_config_name="veloc.cfg",
            app_input_subdir=cell.input_subdir,
            extra_source_dirs=[source_dir],
            output_file_name=output_file_name,
            timeout_s=timeout_s,
            run_once_fn=run_once_fn,
            apply_perturbation_fn=apply_perturbation_fn,
        )
        result.runs[label] = run
        print(
            f"[calibrate {app}] {label}: elapsed={run.elapsed_s:.2f}s "
            f"exit={run.exit_code} crashed={run.crashed}",
            flush=True,
        )

    # Invariant 3: safety (check first; if anything crashed, other invariants
    # cannot be reliably evaluated).
    crashed_runs = [lbl for lbl, r in result.runs.items() if r.crashed]
    if crashed_runs:
        result.safety_ok = False
        result.failure_reasons.append(
            "safety: " + ", ".join(
                f"{lbl} crashed (exit={result.runs[lbl].exit_code}; "
                f"{result.runs[lbl].error_message})"
                for lbl in crashed_runs
            )
        )
        result.passed = False
        return result

    # Invariant 1: output sensitivity
    try:
        result.output_diff_min_vs_unperturbed = _compute_output_diff(
            baseline_file=result.runs["unperturbed"].output_file,
            candidate_file=result.runs["min"].output_file,
            method=method,
            atol=atol,
            rtol=rtol,
        )
        result.output_diff_max_vs_unperturbed = _compute_output_diff(
            baseline_file=result.runs["unperturbed"].output_file,
            candidate_file=result.runs["max"].output_file,
            method=method,
            atol=atol,
            rtol=rtol,
        )
    except (FileNotFoundError, RuntimeError) as exc:
        result.output_sensitivity_ok = False
        result.failure_reasons.append(f"sensitivity: output read failed: {exc}")
        result.passed = False
        return result

    if (
        result.output_diff_min_vs_unperturbed >= output_diff_threshold
        and result.output_diff_max_vs_unperturbed >= output_diff_threshold
    ):
        result.output_sensitivity_ok = True
    else:
        result.output_sensitivity_ok = False
        result.failure_reasons.append(
            f"sensitivity: |Z_P(min) - Z_X| = "
            f"{result.output_diff_min_vs_unperturbed:.3e}, "
            f"|Z_P(max) - Z_X| = {result.output_diff_max_vs_unperturbed:.3e}; "
            f"both must be >= threshold {output_diff_threshold:.3e}"
        )

    # Invariant 2: timing stability
    t_x = result.runs["unperturbed"].elapsed_s
    if t_x <= 0:
        result.timing_stability_ok = False
        result.failure_reasons.append(
            f"timing: unperturbed elapsed_s={t_x} is nonpositive"
        )
    else:
        result.timing_delta_min_pct = abs(
            result.runs["min"].elapsed_s - t_x
        ) / t_x
        result.timing_delta_max_pct = abs(
            result.runs["max"].elapsed_s - t_x
        ) / t_x
        if (
            result.timing_delta_min_pct <= timing_stability_threshold_pct
            and result.timing_delta_max_pct <= timing_stability_threshold_pct
        ):
            result.timing_stability_ok = True
        else:
            result.timing_stability_ok = False
            result.failure_reasons.append(
                f"timing: |t(min) - t(X)|/t(X) = "
                f"{result.timing_delta_min_pct:.3f}, "
                f"|t(max) - t(X)|/t(X) = {result.timing_delta_max_pct:.3f}; "
                f"both must be <= threshold {timing_stability_threshold_pct:.3f}"
            )

    result.passed = bool(
        result.safety_ok
        and result.output_sensitivity_ok
        and result.timing_stability_ok
    )
    return result


# ---------------------------------------------------------------------------
# YAML update on success
# ---------------------------------------------------------------------------


def mark_yaml_verified(app: str, *, yaml_path: "Path | None" = None) -> None:
    """Flip ``calibration.safe_value_range_verified: false`` to true in the
    app's YAML. Uses a simple regex rewrite to preserve all surrounding
    comments and ordering; a full YAML round-trip would re-flow the file."""
    import re

    if yaml_path is None:
        yaml_path = CONFIGS_DIR / f"{app}.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"YAML not found: {yaml_path}")
    text = yaml_path.read_text()
    new_text, n = re.subn(
        r"(\bsafe_value_range_verified:\s*)false\b",
        r"\1true",
        text,
        count=1,
    )
    if n == 0:
        raise ValueError(
            f"could not find 'safe_value_range_verified: false' in {yaml_path}; "
            "either already true or YAML missing the field"
        )
    yaml_path.write_text(new_text)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _format_report(result: CalibrationResult) -> str:
    lines = []
    lines.append(f"=== Calibration report: {result.app} ===")
    lines.append(f"  spec method: {result.spec_method}")
    lines.append(f"  value range: {result.spec_range}")
    lines.append("")
    for label, run in result.runs.items():
        lines.append(
            f"  [{label:11s}] value={run.perturbation_value!r:>10}  "
            f"elapsed={run.elapsed_s:6.2f}s  exit={run.exit_code}  "
            f"crashed={run.crashed}"
        )
        if run.crashed and run.error_message:
            lines.append(f"               error: {run.error_message}")
    lines.append("")
    lines.append("  Invariants:")
    lines.append(
        f"    1. safety_ok         = {result.safety_ok}"
    )
    lines.append(
        f"    2. output_sensitivity_ok = {result.output_sensitivity_ok}  "
        f"(threshold={result.output_diff_threshold!r}, "
        f"min_diff={result.output_diff_min_vs_unperturbed!r}, "
        f"max_diff={result.output_diff_max_vs_unperturbed!r})"
    )
    lines.append(
        f"    3. timing_stability_ok   = {result.timing_stability_ok}  "
        f"(threshold={result.timing_stability_threshold_pct:.2f}, "
        f"min_delta_pct={result.timing_delta_min_pct!r}, "
        f"max_delta_pct={result.timing_delta_max_pct!r})"
    )
    lines.append("")
    lines.append(f"  VERDICT: {'PASS' if result.passed else 'FAIL'}")
    if result.failure_reasons:
        lines.append("  Failure reasons:")
        for r in result.failure_reasons:
            lines.append(f"    - {r}")
    return "\n".join(lines)


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Calibrate an app's perturbation spec by running vanilla 3 times "
            "(unperturbed + min + max value) and checking sensitivity, "
            "timing stability, and safety invariants."
        ),
    )
    parser.add_argument("app", help="App name (matches tests/apps/configs/<APP>.yaml)")
    parser.add_argument(
        "--scratch-dir",
        type=Path,
        default=None,
        help="Where to write calibration cwds (default: build/_calibration/<APP>)",
    )
    parser.add_argument(
        "--output-diff-threshold",
        type=float,
        default=None,
        help="Min |Z_P - Z_X| for sensitivity (default: 1000 * app tolerance)",
    )
    parser.add_argument(
        "--timing-threshold-pct",
        type=float,
        default=0.30,
        help="Max |t_P - t_X|/t_X for timing stability (default: 0.30 = 30%%; "
             "loose because slope-test ratios are invariant to uniform perturbation "
             "timing shifts -- see calibrate() docstring)",
    )
    parser.add_argument(
        "--timeout-s",
        type=float,
        default=None,
        help="Per-run timeout (default: 5 * nominal_runtime_s)",
    )
    parser.add_argument(
        "--update-yaml",
        action="store_true",
        help=(
            "On PASS, flip safe_value_range_verified: true in the app's YAML. "
            "Off by default (calibration is a check, not a side effect)."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of the formatted report.",
    )
    args = parser.parse_args(argv)

    try:
        result = calibrate(
            args.app,
            scratch_root=args.scratch_dir,
            output_diff_threshold=args.output_diff_threshold,
            timing_stability_threshold_pct=args.timing_threshold_pct,
            timeout_s=args.timeout_s,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, default=str))
    else:
        print(_format_report(result))

    if result.passed and args.update_yaml:
        try:
            mark_yaml_verified(args.app)
            print(
                f"\n[calibrator] flipped safe_value_range_verified: true "
                f"in {CONFIGS_DIR / (args.app + '.yaml')}",
                flush=True,
            )
        except (FileNotFoundError, ValueError) as exc:
            print(f"WARNING: YAML update failed: {exc}", file=sys.stderr)
            return 3

    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
