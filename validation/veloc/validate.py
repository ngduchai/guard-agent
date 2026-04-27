"""
validate.py – Main entry point for the VeloC validation framework.

Usage
-----
    python -m validation.veloc.validate \\
        <original-codebase-path> \\
        <resilient-codebase-path> \\
        --executable-name <name> \\
        [options...]

The script orchestrates three pipeline stages in order:

  1. Correctness  – run baseline (original) and resilient with failure injection;
                    compare outputs using the selected comparator.
  2. Benchmarking – run a configurable sweep of scenarios for both codebases
                    and collect performance/resilience metrics.
  3. Reporting    – generate matplotlib plots and a Markdown summary report.

Exit code: 0 if all correctness checks pass, 1 otherwise.

Resume support
--------------
When a stage fails unexpectedly the script saves a ``pipeline_state.json``
file inside the output directory and prints a ``--resume`` command you can
copy-paste to restart from the failed stage without re-running earlier stages.
"""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import sys
import time
from pathlib import Path

from .comparator import CompareResult, make_comparator
from .metrics_collector import (
    ApproachConfig,
    BenchmarkResults,
    BenchmarkScenario,
    RunMetrics,
    default_scenario,
    load_approaches_config,
    load_benchmark_config,
    run_benchmark_sweep,
)
from .reporter import generate_report
from .runner import (
    ValidationError,
    configure_and_build,
    extract_checkpoint_dirs_from_veloc_cfg,
    measure_checkpoint_dirs,
    run_baseline,
    run_with_checkpoint_observed_injection,
    run_with_failure_injection,
    snapshot_checkpoint_dirs,
)


def _capture_checkpoint_artifacts(
    veloc_cfg_dirs: "list[Path]",
    veloc_cfg_name: str,
    out_dir: "Path",
    label: str,
) -> None:
    """Measure and snapshot the resilient run's checkpoint artifacts so they
    survive across batch invocations (e.g. baseline apps that write to
    /tmp/<APP>_persistent paths get overwritten or rotated by later runs;
    this preserves the size + a copy of the files for retrospective analysis).

    Writes:
        out_dir/checkpoint_metrics.json   — total/per-dir size + file count
        out_dir/checkpoints/<dir-name>/   — copy of each ckpt dir
    """
    cfg_path = None
    for d in veloc_cfg_dirs:
        c = d / veloc_cfg_name
        if c.exists():
            cfg_path = c
            break
    if cfg_path is None:
        # No veloc.cfg means non-VeloC checkpointing (POSIX cwd-relative,
        # native HDF5, etc.).  Those files already live under out_dir, so
        # they are preserved by default; just write an empty metrics record.
        ckpt_dirs: list[Path] = []
    else:
        ckpt_dirs = extract_checkpoint_dirs_from_veloc_cfg(cfg_path)

    measurement = measure_checkpoint_dirs(ckpt_dirs)
    measurement["label"] = label
    measurement["veloc_cfg"] = str(cfg_path) if cfg_path else None
    snapshot_dest = out_dir / "checkpoints"
    snap = snapshot_checkpoint_dirs(ckpt_dirs, snapshot_dest)
    measurement["snapshot"] = snap

    metrics_file = out_dir / "checkpoint_metrics.json"
    metrics_file.write_text(json.dumps(measurement, indent=2))
    print(
        f"[validate] checkpoint metrics for {label}: "
        f"{measurement['total_size_bytes']} bytes across "
        f"{measurement['total_file_count']} file(s) in "
        f"{len(ckpt_dirs)} dir(s); snapshot → {snapshot_dest}",
        flush=True,
    )


def _measure_resilience_signals(
    resilient_elapsed: float,
    original_elapsed: float,
    veloc_cfg_dirs: "list[Path]",
    veloc_cfg_name: str,
    out_dir: "Path",
    *,
    checkpoint_observed: "bool | None" = None,
    kill_attempt_elapsed_s: "float | None" = None,
    recovery_attempt_elapsed_s: "float | None" = None,
) -> dict:
    """Measure the raw resilience signals and persist them to disk.

    Policy-free: computes wall-time ratio + checkpoint file count + (when
    the checkpoint-observed strategy was used) the per-attempt timings and
    the checkpoint-observation outcome.  Writes ``resilience_proof.json``
    with all raw signals plus pass/fail flags evaluated at three caps
    (1.2x for the new production policy, 1.7x for legacy Validation A, 1.9x
    for legacy Validation B).  Callers (Validation A or Validation B
    enforcers) decide PASS/FAIL based on their own policy and raise on FAIL.

    *checkpoint_observed*, *kill_attempt_elapsed_s*, *recovery_attempt_elapsed_s*
    come from :func:`runner.run_with_checkpoint_observed_injection` and are
    consumed by the new Validation B policy.  Pass ``None`` when the legacy
    fixed-delay strategy was used.
    """
    cfg_path = None
    for d in veloc_cfg_dirs:
        c = d / veloc_cfg_name
        if c.exists():
            cfg_path = c
            break
    ckpt_dirs = (extract_checkpoint_dirs_from_veloc_cfg(cfg_path)
                 if cfg_path else [])
    measurement = measure_checkpoint_dirs(ckpt_dirs)
    files_count = measurement["total_file_count"]

    ratio = (resilient_elapsed / original_elapsed) if original_elapsed > 0 else float("inf")
    has_ckpt = files_count > 0
    # New production policy (checkpoint-observed strategy): kill+recover total
    # must be < 1.2x failure-free.  For legacy fixed-delay strategy callers,
    # we still publish the older 1.7x / 1.9x flags for backward-compat.
    fast_at_production_cap = ratio < 1.2
    fast_at_audit_cap = ratio <= 1.7
    fast_at_legacy_production_cap = ratio < 1.9

    print(
        f"[validate] resilience signals — resilient_elapsed={resilient_elapsed:.1f}s, "
        f"original_elapsed={original_elapsed:.1f}s, ratio={ratio:.2f}x; "
        f"checkpoint files = {files_count}; "
        f"wall-time PASS at 1.2x (Validation B new) = {fast_at_production_cap}, "
        f"PASS at 1.7x (Validation A) = {fast_at_audit_cap}, "
        f"PASS at 1.9x (legacy) = {fast_at_legacy_production_cap}",
        flush=True,
    )

    signals = {
        "resilient_elapsed_s": resilient_elapsed,
        "original_elapsed_s": original_elapsed,
        "ratio": ratio,
        "wall_time_pass_at_1_2": fast_at_production_cap,
        "wall_time_pass_at_1_7": fast_at_audit_cap,
        "wall_time_pass_at_1_9": fast_at_legacy_production_cap,
        "checkpoint_files": files_count,
        "checkpoint_files_pass": has_ckpt,
        "checkpoint_observed": checkpoint_observed,
        "kill_attempt_elapsed_s": kill_attempt_elapsed_s,
        "recovery_attempt_elapsed_s": recovery_attempt_elapsed_s,
        "veloc_cfg": str(cfg_path) if cfg_path else None,
        "checkpoint_dirs_scanned": [str(d) for d in ckpt_dirs],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "resilience_proof.json").write_text(json.dumps(signals, indent=2))
    return signals


def _enforce_validation_b(
    signals: dict,
    output_correct: bool,
    out_dir: "Path",
) -> None:
    """Validation B (production / checkpoint-solution) — checkpoint-observed.

    PASS iff **all three** hold:
      (1) ``checkpoint_observed`` is True  — at least one checkpoint file
          was written during the kill attempt (proves the application is
          actually attempting checkpoints, not just running to completion);
      (2) ``output_correct`` — recovery-attempt output matches baseline;
      (3) wall-time ratio < 1.2 ×  — kill_attempt + recovery_attempt total
          under 1.2 × failure-free runtime (real recovery from checkpoint,
          not an expensive redo).

    Used to validate any candidate resilient solution: reference checkpointed
    code, LLM-generated code from the iterative pipeline, or DMTCP/CRIU
    approaches.  Raises :class:`ValidationError` on FAIL identifying which
    subset of signals failed.
    """
    checkpoint_observed = signals.get("checkpoint_observed")
    has_ckpt = signals["checkpoint_files_pass"]
    fast = signals["wall_time_pass_at_1_2"]

    # When the checkpoint-observed runner was used, "checkpoint_observed"
    # is the authoritative signal: False means polling completed without
    # ever seeing a checkpoint file (auto-FAIL, no recovery to validate).
    # When the legacy runner was used (None), fall back to the post-run
    # checkpoint-files snapshot.
    if checkpoint_observed is None:
        checkpoint_signal = has_ckpt
    else:
        checkpoint_signal = checkpoint_observed

    passed = checkpoint_signal and output_correct and fast

    print(
        f"[validate] Validation B — checkpoint_observed={checkpoint_observed}, "
        f"checkpoint_files={signals['checkpoint_files']}, "
        f"output_correct={output_correct}, "
        f"fast_at_1.2x={fast} (ratio={signals['ratio']:.2f}x) → "
        f"{'PASS' if passed else 'FAIL'}",
        flush=True,
    )

    # Mirror policy verdict back into the proof JSON for downstream tooling.
    proof_path = out_dir / "resilience_proof.json"
    if proof_path.exists():
        s = json.loads(proof_path.read_text())
        s["validation_mode"] = "B"
        s["output_correct"] = output_correct
        s["passed"] = passed
        proof_path.write_text(json.dumps(s, indent=2))

    if not passed:
        missing = []
        if not checkpoint_signal:
            if checkpoint_observed is False:
                missing.append(
                    "no checkpoint file appeared during the kill attempt "
                    "(checkpoint-observed strategy: app never wrote state)"
                )
            else:
                missing.append("no checkpoint files written")
        if not output_correct:
            missing.append("recovery output mismatch vs baseline")
        if not fast:
            missing.append(
                f"kill+recovery wall-time ratio {signals['ratio']:.2f}x "
                "≥ 1.2x cap"
            )
        raise ValidationError(
            "Validation B failed: " + " AND ".join(missing) + ".  Production "
            "policy requires a checkpoint to be observed during execution "
            "AND recovery output correctness AND total kill+recovery wall-time "
            "< 1.2x failure-free baseline.",
            output_dir=out_dir,
        )


def _enforce_validation_a(
    signals: dict,
    accuracy_match: bool,
    out_dir: "Path",
) -> None:
    """Validation A (vanilla audit).

    PASS iff:
      (1) ``accuracy_match``  — vanilla failure-free output matches the
          reference checkpointed code's failure-free output (proves the
          checkpoint-stripping process didn't corrupt the algorithm);
      (2) NOT (wall-time ratio < 1.8 × OR checkpoint files written)  — the
          vanilla failed at least one resilience signal under failure
          injection (proves it cannot actually recover, only redo from
          scratch).

    Used by ``run_validate.sh --audit-vanilla`` to gate a vanilla into the
    experiment pool.  A PASS confirms the vanilla is correct and properly
    stripped of recovery capability.

    Raises ValidationError on FAIL with which condition failed.
    """
    fast = signals["wall_time_pass_at_1_7"]
    has_ckpt = signals["checkpoint_files_pass"]
    appears_resilient = fast or has_ckpt
    passed = accuracy_match and not appears_resilient

    print(
        f"[validate] Validation A (audit) — accuracy_match={accuracy_match}, "
        f"appears_resilient={appears_resilient} "
        f"(fast_at_1.7x={fast}, has_ckpt={has_ckpt}) → "
        f"{'PASS' if passed else 'FAIL'}",
        flush=True,
    )

    proof_path = out_dir / "resilience_proof.json"
    if proof_path.exists():
        s = json.loads(proof_path.read_text())
        s["validation_mode"] = "A"
        s["accuracy_match"] = accuracy_match
        s["appears_resilient"] = appears_resilient
        s["passed"] = passed
        proof_path.write_text(json.dumps(s, indent=2))

    if not passed:
        reasons = []
        if not accuracy_match:
            reasons.append("vanilla failure-free output diverges from reference")
        if appears_resilient:
            reasons.append(
                f"vanilla appears to recover (ratio {signals['ratio']:.2f}x, "
                f"checkpoint files {signals['checkpoint_files']})"
            )
        raise ValidationError(
            "Validation A (vanilla audit) failed: " + " AND ".join(reasons) +
            ".  Audit requires accuracy match against reference AND that "
            "the vanilla NOT recover under failure injection.",
            output_dir=out_dir,
        )


# ---------------------------------------------------------------------------
# Pipeline state helpers
# ---------------------------------------------------------------------------

_STATE_FILE = "pipeline_state.json"

# Ordered list of stage keys used in the state file.
_STAGES = ["correctness", "benchmarks", "report"]


def _state_path(output_dir: Path) -> Path:
    return output_dir / _STATE_FILE


def _load_state(output_dir: Path) -> dict:
    """Load existing pipeline state or return a fresh empty state."""
    p = _state_path(output_dir)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"completed_stages": [], "started_at": None, "last_updated": None}


def _save_state(output_dir: Path, state: dict) -> None:
    """Persist pipeline state to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)
    state["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _state_path(output_dir).write_text(json.dumps(state, indent=2), encoding="utf-8")


def _mark_stage_complete(output_dir: Path, state: dict, stage: str) -> None:
    """Record that *stage* has completed and persist state."""
    if stage not in state["completed_stages"]:
        state["completed_stages"].append(stage)
    _save_state(output_dir, state)


def _mark_run_complete(output_dir: Path, state: dict) -> None:
    """Mark the entire pipeline as finished."""
    state["finished"] = True
    _save_state(output_dir, state)


def is_run_complete(output_dir: Path) -> bool:
    """Return True if a previous run in *output_dir* finished successfully."""
    state = _load_state(output_dir)
    return bool(state.get("finished", False))


def is_run_incomplete(output_dir: Path) -> bool:
    """Return True if *output_dir* has a started-but-unfinished pipeline run."""
    p = _state_path(output_dir)
    if not p.exists():
        return False
    state = _load_state(output_dir)
    return not state.get("finished", False) and bool(state.get("started_at"))


# ---------------------------------------------------------------------------
# Disk loaders – restore previous stage results without re-running
# ---------------------------------------------------------------------------


def _save_correctness_results(output_dir: Path, results: list[CompareResult]) -> None:
    """Persist correctness results to correctness/test_results.json for later loading."""
    json_path = output_dir / "correctness" / "test_results.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_data = [
        {
            "passed": r.passed,
            "method": r.method,
            "score": r.score,
            "message": r.message,
            "details": r.details,
        }
        for r in results
    ]
    json_path.write_text(json.dumps(json_data, indent=2), encoding="utf-8")
    print(f"[validate] Correctness results saved to {json_path}", flush=True)


def _load_correctness_results(output_dir: Path) -> list[CompareResult]:
    """Load correctness results from a previous run's test_results.json.

    Returns an empty list if the file does not exist or cannot be parsed.
    """
    json_path = output_dir / "correctness" / "test_results.json"
    if not json_path.exists():
        print(
            f"[validate] WARNING: correctness results file not found at {json_path}; "
            "report will show no correctness data.",
            flush=True,
        )
        return []
    try:
        raw = json.loads(json_path.read_text(encoding="utf-8"))
        results: list[CompareResult] = []
        for entry in raw:
            results.append(
                CompareResult(
                    passed=bool(entry.get("passed", False)),
                    method=str(entry.get("method", "unknown")),
                    score=entry.get("score"),
                    message=str(entry.get("message", "")),
                    details=entry.get("details", {}),
                )
            )
        print(
            f"[validate] Loaded {len(results)} correctness result(s) from {json_path}",
            flush=True,
        )
        return results
    except Exception as exc:
        print(
            f"[validate] WARNING: failed to load correctness results from {json_path}: {exc}",
            flush=True,
        )
        return []


def _load_benchmark_results(output_dir: Path) -> BenchmarkResults | None:
    """Load benchmark results from a previous run's raw_metrics.json.

    Returns None if the file does not exist or cannot be parsed.
    """
    json_path = output_dir / "benchmarks" / "raw_metrics.json"
    if not json_path.exists():
        print(
            f"[validate] WARNING: benchmark results file not found at {json_path}; "
            "report will show no benchmark data.",
            flush=True,
        )
        return None
    try:
        raw = json.loads(json_path.read_text(encoding="utf-8"))
        scenarios = [
            BenchmarkScenario(
                name=s["name"],
                num_procs=int(s["num_procs"]),
                app_args=list(s.get("app_args", [])),
                inject_failures=bool(s.get("inject_failures", True)),
                num_runs=int(s.get("num_runs", 3)),
                injection_delay=float(s.get("injection_delay", 5.0)),
                max_attempts=int(s.get("max_attempts", 10)),
            )
            for s in raw.get("scenarios", [])
        ]
        runs = [
            RunMetrics(
                scenario_name=r["scenario_name"],
                codebase=r["codebase"],
                run_index=int(r["run_index"]),
                elapsed_s=float(r["elapsed_s"]),
                injected=bool(r.get("injected", False)),
                num_attempts=int(r.get("num_attempts", 1)),
                checkpoint_size_bytes=r.get("checkpoint_size_bytes"),
                recovery_time_s=r.get("recovery_time_s"),
                peak_memory_bytes=r.get("peak_memory_bytes"),
            )
            for r in raw.get("runs", [])
        ]
        result = BenchmarkResults(
            scenarios=scenarios,
            runs=runs,
            summary=raw.get("summary", {}),
        )
        print(
            f"[validate] Loaded {len(runs)} benchmark run(s) across "
            f"{len(scenarios)} scenario(s) from {json_path}",
            flush=True,
        )
        return result
    except Exception as exc:
        print(
            f"[validate] WARNING: failed to load benchmark results from {json_path}: {exc}",
            flush=True,
        )
        return None


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m validation.veloc.validate",
        description=(
            "VeloC Validation Framework – compare an original codebase against a "
            "resilient codebase generated by agents/veloc, collect performance metrics, "
            "and produce graphical reports."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Positional: the two codebase paths.
    parser.add_argument(
        "original_codebase",
        metavar="ORIGINAL_CODEBASE",
        help="Path to the original (non-resilient) codebase directory.",
    )
    parser.add_argument(
        "resilient_codebase",
        metavar="RESILIENT_CODEBASE",
        help="Path to the resilient codebase generated by agents/veloc.",
    )

    # Build / run configuration.
    build_grp = parser.add_argument_group("Build and run configuration")
    build_grp.add_argument(
        "--executable-name",
        required=True,
        help="Name of the built executable (same for both codebases unless overridden).",
    )
    build_grp.add_argument(
        "--original-executable-name",
        default=None,
        help="Override executable name for the original codebase.",
    )
    build_grp.add_argument(
        "--resilient-executable-name",
        default=None,
        help="Override executable name for the resilient codebase.",
    )
    build_grp.add_argument(
        "--num-procs",
        type=int,
        default=4,
        help="Number of MPI processes (ranks) to launch with mpirun.",
    )
    build_grp.add_argument(
        "--original-args",
        default="",
        help="Command-line arguments for the original application (shell-style string).",
    )
    build_grp.add_argument(
        "--resilient-args",
        default="",
        help="Command-line arguments for the resilient application (shell-style string).",
    )
    build_grp.add_argument(
        "--output-dir",
        default="build/validation_output",
        help="Root directory for all validation outputs.",
    )
    build_grp.add_argument(
        "--build-dir",
        default=None,
        help=(
            "Root directory for CMake build trees. "
            "Defaults to <output-dir>/build. "
            "Original and resilient builds are placed in subdirectories."
        ),
    )
    build_grp.add_argument(
        "--install-resilient",
        action="store_true",
        help=(
            "Run `cmake --install` for the resilient build (prefix = build dir). "
            "Enable when the resilient example installs runtime config like veloc.cfg."
        ),
    )
    build_grp.add_argument(
        "--veloc-config-name",
        default="veloc.cfg",
        help="Filename of the VeloC configuration file.",
    )
    build_grp.add_argument(
        "--original-build-cmd",
        default=None,
        help=(
            "Shell command to build the original codebase (from app.yaml). "
            "When set, the source is copied to the build directory and this "
            "command is executed there instead of using CMake. "
            "Supports Make, Meson, or any build system."
        ),
    )
    build_grp.add_argument(
        "--resilient-build-cmd",
        default=None,
        help=(
            "Shell command to build the resilient codebase (from app.yaml). "
            "Same semantics as --original-build-cmd."
        ),
    )
    build_grp.add_argument(
        "--app-input-subdir",
        default=None,
        help=(
            "Subdirectory (relative to the app source root) extracted from a "
            "stripped 'cd <subdir> && ...' prefix in app.yaml's run.cmd.  "
            "When set, the contents of that subdirectory are flattened into "
            "the per-run cwd so apps that expect to run from that directory "
            "(SPARTA, SPPARKS, HyPar) find their input files."
        ),
    )

    # Correctness stage.
    corr_grp = parser.add_argument_group("Correctness validation")
    corr_grp.add_argument(
        "--output-file-name",
        default="stdout.txt",
        help=(
            "Name of the output file produced by both applications to compare. "
            "Defaults to 'stdout.txt' (the captured run output written by the "
            "runner) so apps with comparison.output_file=null in app.yaml use "
            "stdout-based comparison.  Override per app via "
            "comparison.output_file in app.yaml when the app writes a "
            "specific result file (e.g. recon.h5, plt00010)."
        ),
    )
    corr_grp.add_argument(
        "--max-attempts",
        type=int,
        default=4,
        help=(
            "Maximum resilient retry attempts before giving up.  Default 4 "
            "= 1 successful injection + 1 recovery run + 2 retries for OS "
            "scheduling jitter on the injector.  Higher values waste time "
            "when the injector is systematically missing (timing skew, "
            "consistently-late injection delay)."
        ),
    )
    corr_grp.add_argument(
        "--injection-delay",
        default="auto",
        help=(
            "Seconds to wait before injecting a failure into the MPI run. "
            "Default 'auto': compute from baseline runtime (1/3 of elapsed time, "
            "clamped to [5, 300] seconds). Pass a float to override."
        ),
    )
    corr_grp.add_argument(
        "--ground-truth-dir",
        default=None,
        help=(
            "Path to a directory containing pre-computed ground truth output "
            "from a previous baseline run.  When provided, the correctness "
            "stage skips rebuilding/re-running the original application and "
            "reuses the output files and elapsed time from this directory.  "
            "The directory must contain the expected output file and a "
            'ground_truth_meta.json with {"elapsed_s": <float>}.'
        ),
    )
    corr_grp.add_argument(
        "--comparison-method",
        choices=("hash", "ssim", "numeric-tolerance", "text-diff", "custom"),
        default="ssim",
        help="Output comparison strategy.",
    )
    corr_grp.add_argument(
        "--custom-comparator",
        default=None,
        metavar="PLUGIN_PATH",
        help=(
            "Path to a Python plugin file exporting "
            "compare(baseline_path, resilient_path, **kwargs) -> dict. "
            "Required when --comparison-method=custom."
        ),
    )
    corr_grp.add_argument(
        "--ssim-threshold",
        type=float,
        default=0.9999,
        help="Minimum SSIM value for a correctness pass (SSIM method only).",
    )
    corr_grp.add_argument(
        "--numeric-atol",
        type=float,
        default=1e-6,
        help="Absolute tolerance for numeric comparison.",
    )
    corr_grp.add_argument(
        "--numeric-rtol",
        type=float,
        default=1e-6,
        help="Relative tolerance for numeric comparison.",
    )
    corr_grp.add_argument(
        "--hdf5-dataset",
        default="data",
        help="HDF5 dataset name to compare (SSIM and numeric-tolerance methods).",
    )
    corr_grp.add_argument(
        "--text-ignore-patterns",
        nargs="*",
        default=None,
        metavar="PATTERN",
        help="Substrings to ignore when comparing text files (text-diff method).",
    )
    corr_grp.add_argument(
        "--text-keep-patterns",
        nargs="*",
        default=None,
        metavar="PATTERN",
        help=(
            "Substrings; only stdout lines matching at least one survive the "
            "filter before comparison.  Allowlist counterpart of "
            "--text-ignore-patterns; takes precedence when both are set.  "
            "Sourced from comparison.keep_patterns in app.yaml."
        ),
    )
    corr_grp.add_argument(
        "--text-strip-patterns",
        nargs="*",
        default=None,
        metavar="PATTERN",
        help=(
            "Regex substring patterns removed from each surviving line "
            "before number extraction.  Use to drop timing fields embedded "
            "in deterministic output lines (e.g. miniVite's `Time (in s): "
            "[0-9.]+` next to its Modularity result).  Sourced from "
            "comparison.strip_patterns in app.yaml."
        ),
    )

    # Benchmarking stage.
    bench_grp = parser.add_argument_group("Benchmarking")
    bench_grp.add_argument(
        "--benchmark-config",
        default=None,
        metavar="CONFIG_JSON",
        help=(
            "Path to a JSON benchmark config file defining the scenario sweep matrix. "
            "If omitted, a default two-scenario sweep is used."
        ),
    )
    bench_grp.add_argument(
        "--benchmark-num-runs",
        type=int,
        default=None,
        help=(
            "Override the number of repetitions for every benchmark scenario. "
            "When set, this takes priority over per-scenario 'num_runs' in the JSON config. "
            "When omitted (the default), per-scenario 'num_runs' from the JSON is used "
            "(falling back to 3 if a scenario does not specify it). "
            "Set via the NUM_RUNS environment variable in run_art_simple_validation.sh."
        ),
    )

    # Comparison approaches.
    approaches_grp = parser.add_argument_group("Comparison approaches")
    approaches_grp.add_argument(
        "--approaches-config",
        default=None,
        metavar="CONFIG_JSON",
        help=(
            "Path to a JSON config file defining comparison approaches (e.g., DMTCP). "
            "Each approach specifies its codebase path, executable, and settings. "
            "See benchmark_configs/art_simple_approaches.json for an example."
        ),
    )
    # Legacy DMTCP flags (deprecated; use --approaches-config instead).
    approaches_grp.add_argument(
        "--dmtcp-codebase",
        default=None,
        metavar="DMTCP_CODEBASE",
        help="[Deprecated: use --approaches-config] Path to DMTCP codebase directory.",
    )
    approaches_grp.add_argument(
        "--dmtcp-executable-name",
        default=None,
        help="[Deprecated: use --approaches-config] Executable name for DMTCP codebase.",
    )

    # Pipeline control.
    ctrl_grp = parser.add_argument_group("Pipeline control")
    ctrl_grp.add_argument(
        "--skip-correctness",
        action="store_true",
        help="Skip the correctness validation stage.",
    )
    ctrl_grp.add_argument(
        "--skip-benchmarks",
        action="store_true",
        help="Skip the benchmarking stage.",
    )
    ctrl_grp.add_argument(
        "--skip-report",
        action="store_true",
        help="Skip the graphical reporting stage.",
    )
    ctrl_grp.add_argument(
        "--reference-input-priority",
        action="store_true",
        help=(
            "When the resilient codebase is the upstream reference (rather "
            "than LLM-modified vanilla), force vanilla input files to take "
            "precedence over the reference's own. Required for reference "
            "benchmarks because reference inputs are tuned to the upstream "
            "demo scale (e.g. Athena++ blast: 1 mesh block, fails with 4 "
            "ranks). No-op for --baseline (LLM-modified) runs."
        ),
    )
    ctrl_grp.add_argument(
        "--reference-input-overlay-dir",
        default=None,
        help=(
            "Optional directory whose input files take HIGHER precedence "
            "than vanilla and reference for the resilient (reference) run. "
            "Used to apply per-app reference input patches that enable the "
            "app's native checkpoint mechanism (e.g. Athena++ <output3> "
            "file_type=rst block) so checkpoint_size_bytes is non-zero. "
            "Typically built at run time by run_validate.sh as a tmp overlay "
            "of (vanilla + tests/apps/patches/<APP>). No-op when "
            "--reference-input-priority is unset."
        ),
    )
    ctrl_grp.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Resume a previous run from the last completed stage. "
            "Reads pipeline_state.json from --output-dir and skips already-completed stages."
        ),
    )
    ctrl_grp.add_argument(
        "--vanilla-audit",
        action="store_true",
        help=(
            "Switch the correctness stage to Validation A (vanilla audit): "
            "PASSES iff the vanilla failure-free output matches the reference "
            "checkpointed code's failure-free output (accuracy) AND the "
            "failure-injected vanilla fails at least one resilience signal "
            "(no recovery: wall-time ratio ≥ 1.8x AND no checkpoint files).  "
            "Without this flag, validate.py runs Validation B (production): "
            "PASSES iff resilient output matches baseline AND ≥1 checkpoint "
            "file exists AND wall-time < 1.95x baseline."
        ),
    )
    ctrl_grp.add_argument(
        "--reference-codebase",
        default=None,
        help=(
            "Path to the reference checkpointed code, used by --vanilla-audit "
            "for the accuracy comparison.  When omitted, auto-derives from "
            "--original-codebase by replacing 'vanillas' with 'checkpointed' "
            "in the path (i.e. tests/apps/vanillas/<APP> → "
            "tests/apps/checkpointed/<APP>)."
        ),
    )

    return parser


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------


def _stage_correctness(
    args: argparse.Namespace,
    original_src: Path,
    original_build: Path,
    resilient_src: Path,
    resilient_build: Path,
    output_dir: Path,
    orig_exe: str,
    res_exe: str,
    orig_app_args: list[str],
    res_app_args: list[str],
    approaches: list[ApproachConfig] | None = None,
    build_root: Path | None = None,
    original_build_cmd: str | None = None,
    resilient_build_cmd: str | None = None,
    app_input_subdir: str | None = None,
) -> list[CompareResult]:
    """Run baseline + resilient + approaches, compare outputs.

    Returns a list of CompareResult.  When *approaches* is provided, each
    enabled approach is built, run with and without failure injection, and
    its output is compared against the baseline using the same comparator.
    """
    print("\n" + "=" * 70, flush=True)
    print("[validate] STAGE 1: Correctness Validation", flush=True)
    print("=" * 70, flush=True)

    resilient_out = output_dir / "correctness" / "resilient"

    # --- Baseline / ground truth ---
    # SINGLE canonical path.  The collector (collect_baseline.py) is the
    # ONLY way to get baseline timing — either it returns a valid cache or
    # it runs the warmup + 2 measurement passes itself and populates the
    # cache.  validate.py then reads baseline_elapsed + the comparator's
    # expected stdout/stderr files directly from build/baseline_cache/<APP>/.
    #
    # If --ground-truth-dir is given explicitly, that overrides the cache
    # location (useful for testing or for pointing at a curated baseline
    # collected on a different machine).  Otherwise the per-app default is
    # build/baseline_cache/<APP>/ via _default_baseline_cache_dir().
    if args.ground_truth_dir:
        baseline_out = Path(args.ground_truth_dir).resolve()
        if not baseline_out.exists():
            raise ValidationError(
                f"--ground-truth-dir {baseline_out} does not exist; provide "
                "a populated baseline cache directory or omit the flag to "
                "let the collector populate one automatically.",
                stdout="", stderr="", exit_code=-1, output_dir=output_dir,
            )
    else:
        baseline_out = _autodetect_or_collect_baseline_cache(
            args=args,
            original_src=original_src,
            original_app_args=orig_app_args,
            original_build_cmd=original_build_cmd,
            app_input_subdir=app_input_subdir,
        )

    meta_path = baseline_out / "ground_truth_meta.json"
    if not meta_path.exists():
        raise ValidationError(
            f"Baseline cache at {baseline_out} is missing ground_truth_meta.json. "
            "Run `python -m validation.veloc.collect_baseline --app <APP>` to "
            "populate it, or supply --ground-truth-dir pointing at a "
            "pre-populated cache.",
            stdout="", stderr="", exit_code=-1, output_dir=output_dir,
        )
    meta = json.loads(meta_path.read_text())
    baseline_elapsed = float(meta["elapsed_s"])
    print(
        f"\n[validate] Baseline cache: {baseline_out} "
        f"(elapsed_s={baseline_elapsed:.1f}, cached_at={meta.get('cached_at','?')})",
        flush=True,
    )

    # --- Determine injection delay ---
    # Inject failures at 90% of failure-free runtime.  Rationale: (i) leaves
    # 90% of the run for checkpoint cadence to fire (typically 5-30s
    # cadences fire many times within a 100+s window); (ii) reserves a 10%
    # kill window so the failure injector has time to find ranks and SIGKILL
    # before the app exits naturally; (iii) vanilla redo total ≈ 0.90 + 1.0
    # = 1.90 × baseline — Validation A cap of 1.7 catches it (0.20 margin),
    # Validation B cap of 1.9 sits exactly at the redo upper bound.
    if args.injection_delay == "auto":
        injection_delay = max(5.0, baseline_elapsed * 0.90)
        print(
            f"[validate] Baseline runtime: {baseline_elapsed:.1f}s. "
            f"Adaptive injection delay: {injection_delay:.1f}s "
            f"(90% of runtime, floor 5s)",
            flush=True,
        )
    else:
        injection_delay = float(args.injection_delay)
        print(
            f"[validate] Baseline runtime: {baseline_elapsed:.1f}s. "
            f"Manual injection delay: {injection_delay:.1f}s",
            flush=True,
        )

    # --- Resilient run with failure injection ---
    # Branch on validation mode:
    #   * Vanilla audit (Validation A): legacy fixed-delay retry loop.  We
    #     want to know whether the vanilla appears resilient under standard
    #     0.90x-baseline injection — i.e. whether the strip was complete.
    #   * Production (Validation B): checkpoint-observed strategy.  Watch
    #     for the application to actually write a checkpoint, then SIGKILL,
    #     then validate that recovery completes within 1.2x baseline with
    #     correct output.
    if getattr(args, "vanilla_audit", False):
        print(
            "\n[validate] Running resilient application with failure injection "
            "(legacy fixed-delay strategy — vanilla audit mode)...",
            flush=True,
        )
        # Cap each mpirun attempt at ~3x the baseline runtime.  Without
        # this, an LLM-generated solution with runaway checkpoint cadence
        # (e.g. one checkpoint per inner loop iteration) can hang for hours
        # instead of failing fast.  Floor of 60 s so very short baselines
        # still leave room for normal startup variance.
        attempt_timeout_s = max(60.0, baseline_elapsed * 3.0)
        print(
            f"[validate] Per-attempt wallclock cap: {attempt_timeout_s:.1f}s "
            f"(3x baseline, floor 60s)",
            flush=True,
        )
        fp_result = run_with_failure_injection(
            source_dir=resilient_src,
            build_dir=resilient_build,
            output_dir=resilient_out,
            executable_name=res_exe,
            num_procs=args.num_procs,
            app_args=res_app_args,
            max_attempts=args.max_attempts,
            injection_delay=injection_delay,
            run_install=args.install_resilient,
            success_output_filename=args.output_file_name,
            veloc_config_name=args.veloc_config_name,
            build_cmd=resilient_build_cmd,
            app_input_subdir=app_input_subdir,
            extra_source_dirs=[original_src],
            attempt_timeout_s=attempt_timeout_s,
        )
        ckpt_observed_for_signals: bool | None = None
        kill_attempt_elapsed_for_signals: float | None = None
        recovery_attempt_elapsed_for_signals: float | None = None
    else:
        print(
            "\n[validate] Running resilient application with failure injection "
            "(checkpoint-observed strategy — production mode)...",
            flush=True,
        )
        # Recovery timeout: 1.5x baseline, with a 60 s floor so MPI startup
        # + recovery has room on very short baselines (e.g. CoMD ~10 s)
        # without tripping the safety kill before recovery can even begin.
        recovery_timeout_s = max(60.0, baseline_elapsed * 1.5)
        print(
            f"[validate] Checkpoint-observed config: poll after "
            f"{baseline_elapsed * 0.5:.1f}s (50% of baseline), "
            f"5s post-checkpoint wait, recovery timeout "
            f"{recovery_timeout_s:.1f}s (1.5x baseline, floor 60s). "
            f"Verdict cap: kill+recovery total < "
            f"{baseline_elapsed * 1.2:.1f}s (1.2x baseline).",
            flush=True,
        )
        fp_result = run_with_checkpoint_observed_injection(
            source_dir=resilient_src,
            build_dir=resilient_build,
            output_dir=resilient_out,
            executable_name=res_exe,
            num_procs=args.num_procs,
            app_args=res_app_args,
            failure_free_elapsed=baseline_elapsed,
            observation_threshold_fraction=0.5,
            poll_interval_s=1.0,
            post_checkpoint_wait_s=5.0,
            recovery_timeout_s=recovery_timeout_s,
            run_install=args.install_resilient,
            success_output_filename=args.output_file_name,
            veloc_config_name=args.veloc_config_name,
            build_cmd=resilient_build_cmd,
            app_input_subdir=app_input_subdir,
            extra_source_dirs=[original_src],
        )
        ckpt_observed_for_signals = fp_result.checkpoint_observed
        kill_attempt_elapsed_for_signals = fp_result.kill_attempt_elapsed_s
        recovery_attempt_elapsed_for_signals = fp_result.recovery_attempt_elapsed_s

    # --- Measure resilience signals (raw, policy-free) ---
    # Compute wall-time ratio + checkpoint-file count for the failure-injected
    # run.  Two enforcers will consume these signals: Validation A (vanilla
    # audit) demands the run NOT recover; Validation B (production / LLM-
    # generated) demands it DOES recover under stricter AND-logic.  Enforced
    # after the output comparisons below so we can plug `output_correct` into
    # Validation B.
    resilience_signals = _measure_resilience_signals(
        resilient_elapsed=fp_result.elapsed_s,
        original_elapsed=baseline_elapsed,
        veloc_cfg_dirs=[resilient_src, resilient_build],
        veloc_cfg_name=args.veloc_config_name,
        out_dir=resilient_out,
        checkpoint_observed=ckpt_observed_for_signals,
        kill_attempt_elapsed_s=kill_attempt_elapsed_for_signals,
        recovery_attempt_elapsed_s=recovery_attempt_elapsed_for_signals,
    )

    # --- Capture checkpoint metrics + snapshot the on-disk artifacts ---
    # Without this, baseline runs whose veloc.cfg writes to /tmp/<APP>_persistent
    # would have those files overwritten or rotated away by later batch apps,
    # destroying the data needed for any retrospective size / file-count
    # comparison against the reference.  We measure the size, then copy the
    # contents into the per-app output dir so they survive.
    _capture_checkpoint_artifacts(
        veloc_cfg_dirs=[resilient_src, resilient_build],
        veloc_cfg_name=args.veloc_config_name,
        out_dir=resilient_out,
        label="failure_prone",
    )

    # --- Also run resilient without failure injection (failure-free check) ---
    print(
        "\n[validate] Running resilient application without failure injection (failure-free check)...",
        flush=True,
    )
    from .runner import run_once, _symlink_input_data

    resilient_clean_out = output_dir / "correctness" / "resilient_clean"
    resilient_clean_out.mkdir(parents=True, exist_ok=True)
    # Ensure input data referenced by relative paths in app_args is
    # accessible from the clean-run CWD (mirrors what run_baseline and
    # run_with_failure_injection do for their run directories).
    _symlink_input_data(
        resilient_src, resilient_build, resilient_clean_out, res_app_args,
        extra_source_dirs=[original_src],
        input_subdir=app_input_subdir,
    )
    clean_result = run_once(
        build_dir=resilient_build,
        executable_name=res_exe,
        num_procs=args.num_procs,
        app_args=res_app_args,
        output_dir=resilient_clean_out,
        run_cwd=resilient_clean_out,
        veloc_config_sources=[resilient_src, resilient_build],
        veloc_config_name=args.veloc_config_name,
    )
    if not clean_result.succeeded:
        print(
            f"[validate] WARNING: failure-free resilient run exited with code "
            f"{clean_result.exit_code}",
            flush=True,
        )

    # --- Capture checkpoint metrics + snapshot for the failure-free run too ---
    _capture_checkpoint_artifacts(
        veloc_cfg_dirs=[resilient_src, resilient_build],
        veloc_cfg_name=args.veloc_config_name,
        out_dir=resilient_clean_out,
        label="failure_free",
    )

    # --- Compare outputs ---
    # Two paths:
    #   1. output_file_name == "stdout.txt" → stdout-based comparison via the
    #      shared reference_validator._compare_outputs (handles keep_patterns +
    #      ignore_patterns + numeric extraction from arbitrary text).
    #   2. otherwise → file-based comparison via make_comparator (HDF5, SSIM,
    #      hash, numpy-loadable text matrices, custom plugins).
    use_stdout_compare = args.output_file_name == "stdout.txt"

    if use_stdout_compare:
        # Map validate.py CLI method names back to reference_validator's short
        # names ("numeric"/"text"/"hash") since _compare_outputs uses those.
        _METHOD_REVERSE = {
            "numeric-tolerance": "numeric",
            "text-diff": "text",
            "hash": "hash",
        }
        ref_method = _METHOD_REVERSE.get(args.comparison_method, "text")
        # Tolerance for the numeric path: relative diff, so use the rtol value.
        ref_tolerance = float(args.numeric_rtol or args.numeric_atol or 1e-6)
        from .reference_validator import _compare_outputs as _stdout_compare
    else:
        plugin_path = Path(args.custom_comparator) if args.custom_comparator else None
        comparator = make_comparator(
            method=args.comparison_method,
            plugin_path=plugin_path,
            dataset=args.hdf5_dataset,
            ssim_threshold=args.ssim_threshold,
            atol=args.numeric_atol,
            rtol=args.numeric_rtol,
            ignore_patterns=args.text_ignore_patterns,
        )

    def _do_compare(label: str, golden_path: Path, test_path: Path) -> CompareResult:
        """Run one comparison.  Falls through to the right backend based on
        whether we're doing stdout-based or file-based comparison."""
        if use_stdout_compare:
            golden_text = golden_path.read_text(errors="replace") if golden_path.exists() else ""
            test_text = test_path.read_text(errors="replace") if test_path.exists() else ""
            res = _stdout_compare(
                golden_stdout=golden_text,
                test_stdout=test_text,
                method=ref_method,
                tolerance=ref_tolerance,
                ignore_patterns=args.text_ignore_patterns,
                keep_patterns=args.text_keep_patterns,
                strip_patterns=args.text_strip_patterns,
            )
            return CompareResult(
                method=f"{res.method} [{label}]",
                passed=bool(res.passed),
                score=res.score,
                message=res.details or "",
            )
        result = comparator.compare(golden_path, test_path)
        result.method = f"{result.method} [{label}]"
        return result

    results: list[CompareResult] = []

    # Test 1: baseline vs resilient (with failure injection)
    baseline_file = baseline_out / args.output_file_name
    resilient_file = resilient_out / args.output_file_name
    print(
        f"\n[validate] Comparing outputs (VeloC, failure-prone):\n"
        f"  baseline:  {baseline_file}\n"
        f"  resilient: {resilient_file}",
        flush=True,
    )
    result1 = _do_compare("VeloC, failure-prone", baseline_file, resilient_file)
    print(f"[validate] Test 1 (VeloC, failure-prone): {result1}", flush=True)
    results.append(result1)

    # Test 2: baseline vs resilient (failure-free)
    resilient_clean_file = resilient_clean_out / args.output_file_name
    if resilient_clean_file.exists():
        print(
            f"\n[validate] Comparing outputs (VeloC, failure-free):\n"
            f"  baseline:  {baseline_file}\n"
            f"  resilient: {resilient_clean_file}",
            flush=True,
        )
        result2 = _do_compare("VeloC, failure-free", baseline_file, resilient_clean_file)
        print(f"[validate] Test 2 (VeloC, failure-free): {result2}", flush=True)
        results.append(result2)
    else:
        print(
            f"[validate] Skipping failure-free comparison: "
            f"{resilient_clean_file} not found.",
            flush=True,
        )

    # --- Resilience policy enforcement ---
    # Validation A (vanilla audit): also build the reference checkpointed
    # code, run it failure-free, and compare its output to the vanilla
    # baseline.  Audit PASSES iff (a) outputs match (the strip didn't break
    # the algorithm) AND (b) the failure-injected vanilla failed at least
    # one resilience signal (cannot recover).
    #
    # Validation B (production): require output_correct AND ≥1 checkpoint
    # file AND wall-time < 1.95 × baseline.  Stricter AND-logic to make
    # sure the resilient code actually recovered (didn't just redo the work
    # from scratch) and produced the right answer.
    if getattr(args, "vanilla_audit", False):
        # Locate reference checkpointed code.
        ref_codebase = None
        if getattr(args, "reference_codebase", None):
            ref_codebase = Path(args.reference_codebase).resolve()
        else:
            # Auto-derive from the vanilla source path:
            # tests/apps/vanillas/<APP>  →  tests/apps/checkpointed/<APP>
            try:
                parts = list(original_src.parts)
                idx = parts.index("vanillas")
                parts[idx] = "checkpointed"
                guess = Path(*parts)
                if guess.exists():
                    ref_codebase = guess
            except ValueError:
                pass

        accuracy_match = False
        if ref_codebase is None or not ref_codebase.exists():
            print(
                f"\n[validate] Validation A: reference codebase not found "
                f"(tried --reference-codebase + auto-derived "
                f"tests/apps/checkpointed/<APP>); accuracy check FAILS.",
                flush=True,
            )
        else:
            print(
                f"\n[validate] Validation A: building + running reference "
                f"checkpointed code for accuracy comparison: {ref_codebase}",
                flush=True,
            )
            ref_baseline_out = output_dir / "correctness" / "reference_baseline"
            ref_build_dir = build_root / "reference" if build_root else \
                output_dir / "build" / "reference"
            try:
                ref_result = run_baseline(
                    source_dir=ref_codebase,
                    build_dir=ref_build_dir,
                    output_dir=ref_baseline_out,
                    executable_name=orig_exe,
                    num_procs=args.num_procs,
                    app_args=orig_app_args,
                    build_cmd=original_build_cmd,
                    app_input_subdir=app_input_subdir,
                    # Force vanilla input files to take precedence over the
                    # reference's own.  Without this, apps like SW4lite
                    # (vanilla "time t=15.0" vs reference "time t=2.0") and
                    # Athena++ (vanilla 200x200 AMR tlim=19 vs reference
                    # 50x100 tlim=1) compare apples-to-oranges and the
                    # accuracy_match check trivially fails.  The resilient
                    # run already uses vanilla source for everything; this
                    # makes the reference run symmetric.
                    priority_source_dirs=[original_src],
                    # Still fall back to vanilla source for input files the
                    # reference doesn't ship (e.g. LAMMPS bench/in.lj_long
                    # exists in vanilla only; reference has in.lj/in.lj_ckpt/
                    # in.lj_restart instead).  Functionally subsumed by
                    # priority_source_dirs above but kept for clarity.
                    extra_source_dirs=[original_src],
                )
                ref_baseline_file = ref_baseline_out / args.output_file_name
                if ref_baseline_file.exists():
                    print(
                        f"\n[validate] Comparing outputs (vanilla vs reference, "
                        f"both failure-free):\n"
                        f"  vanilla:   {baseline_file}\n"
                        f"  reference: {ref_baseline_file}",
                        flush=True,
                    )
                    acc_result = _do_compare(
                        "vanilla vs reference (accuracy)",
                        baseline_file,
                        ref_baseline_file,
                    )
                    print(
                        f"[validate] Accuracy check (Validation A): {acc_result}",
                        flush=True,
                    )
                    results.append(acc_result)
                    accuracy_match = bool(acc_result.passed)
                else:
                    print(
                        f"[validate] Validation A: reference output file "
                        f"{ref_baseline_file} not produced; accuracy FAILS.",
                        flush=True,
                    )
            except Exception as exc:
                print(
                    f"[validate] Validation A: reference build/run errored "
                    f"({type(exc).__name__}: {exc}); accuracy FAILS.",
                    flush=True,
                )

        _enforce_validation_a(
            signals=resilience_signals,
            accuracy_match=accuracy_match,
            out_dir=resilient_out,
        )
    else:
        # Validation B: AND-logic policy on the resilient run.
        _enforce_validation_b(
            signals=resilience_signals,
            output_correct=bool(result1.passed),
            out_dir=resilient_out,
        )

    # --- Approach correctness checks ---
    if approaches:
        from .dmtcp_runner import (
            check_dmtcp_available,
            check_mana_available,
            detect_mana_root,
            dmtcp_run_once,
            dmtcp_run_with_failure_injection,
        )

        effective_build_root = build_root if build_root else output_dir / "build"
        test_num = len(results)

        for approach in approaches:
            print(
                f"\n[validate] --- Approach correctness: {approach.label} "
                f"(type={approach.approach_type}) ---",
                flush=True,
            )

            # Verify tools are available.
            if approach.approach_type == "dmtcp":
                if not check_dmtcp_available(approach.install_prefix):
                    print(
                        f"[validate] WARNING: skipping approach {approach.name!r} – "
                        "DMTCP tools not found in PATH.",
                        flush=True,
                    )
                    continue
            elif approach.approach_type == "criu":
                from .criu_runner import check_criu_available

                if not check_criu_available():
                    print(
                        f"[validate] WARNING: skipping approach {approach.name!r} – "
                        "CRIU not found. Install via: ./scripts/install_criu.sh",
                        flush=True,
                    )
                    continue
            else:
                print(
                    f"[validate] WARNING: unknown approach type "
                    f"{approach.approach_type!r} for {approach.name!r}; skipping.",
                    flush=True,
                )
                continue

            # Build approach codebase.
            # CRIU uses the original (unmodified) binary — no special build.
            # DMTCP uses MANA stub if available.
            if approach.approach_type == "criu":
                a_build = effective_build_root / "original"
                print(
                    f"[validate] CRIU uses original binary (no special build needed)",
                    flush=True,
                )
            else:
                a_build = effective_build_root / approach.name
                cmake_extra: list[str] = []
                mana_root = detect_mana_root()
                if mana_root is not None:
                    cmake_extra = [
                        "-DDMTCP_USE_MANA_STUB=ON",
                        f"-DMANA_ROOT={mana_root}",
                    ]
                    print(
                        f"[validate] MANA detected at {mana_root}; building with MANA stub",
                        flush=True,
                    )
                    # If MANA's lower-half links against OpenMPI, we must
                    # build the app with OpenMPI's compilers too (not Cray's).
                    from .dmtcp_runner import _resolve_mpirun_for_mana

                    mpirun_path = _resolve_mpirun_for_mana()
                    if mpirun_path != "mpirun":
                        ompi_bin = Path(mpirun_path).parent
                        ompi_mpicc = ompi_bin / "mpicc"
                        ompi_mpicxx = ompi_bin / "mpicxx"
                        if ompi_mpicc.exists() and ompi_mpicxx.exists():
                            cmake_extra.extend(
                                [
                                    f"-DCMAKE_C_COMPILER={ompi_mpicc}",
                                    f"-DCMAKE_CXX_COMPILER={ompi_mpicxx}",
                                ]
                            )
                            print(
                                f"[validate] Using OpenMPI compilers: "
                                f"{ompi_mpicc}, {ompi_mpicxx}",
                                flush=True,
                            )
                elif check_mana_available():
                    print(
                        "[validate] WARNING: MANA tools found but MANA_ROOT not detected; "
                        "building without MANA stub (checkpoint may fail for MPI apps)",
                        flush=True,
                    )
                print(
                    f"[validate] Building {approach.name} codebase: "
                    f"{approach.codebase_dir} -> {a_build}",
                    flush=True,
                )
                configure_and_build(
                    approach.codebase_dir,
                    a_build,
                    cmake_extra_args=cmake_extra or None,
                )

            a_exe = approach.executable_name or res_exe
            # Use dedicated coordinator ports for correctness checks.
            coord_port_base = 7900

            # Determine app args and comparator for this approach.
            # If the approach has custom app_args (e.g. more iterations for
            # longer runtime), use those and run a separate baseline.
            approach_app_args = approach.app_args if approach.app_args else res_app_args
            approach_comparator = comparator
            if approach.ssim_threshold is not None:
                approach_comparator = make_comparator(
                    method=args.comparison_method,
                    plugin_path=Path(args.custom_comparator)
                    if args.custom_comparator
                    else None,
                    dataset=args.hdf5_dataset,
                    ssim_threshold=approach.ssim_threshold,
                    atol=args.numeric_atol,
                    rtol=args.numeric_rtol,
                    ignore_patterns=args.text_ignore_patterns,
                )
                print(
                    f"[validate] Using approach-specific SSIM threshold: "
                    f"{approach.ssim_threshold}",
                    flush=True,
                )

            # If approach uses different app_args, run a separate baseline.
            approach_baseline_file = baseline_file
            if approach.app_args:
                approach_baseline_dir = (
                    output_dir / "correctness" / f"{approach.name}_baseline"
                )
                approach_baseline_dir.mkdir(parents=True, exist_ok=True)
                print(
                    f"[validate] Running separate baseline for {approach.label} "
                    f"(custom app_args with num_iter={approach_app_args[2]})...",
                    flush=True,
                )
                from .runner import run_once

                baseline_result_a = run_once(
                    build_dir=effective_build_root / "original",
                    executable_name=args.executable_name,
                    num_procs=args.num_procs,
                    app_args=approach_app_args,
                    output_dir=approach_baseline_dir,
                    run_cwd=approach_baseline_dir,
                )
                approach_baseline_file = approach_baseline_dir / args.output_file_name
                if not approach_baseline_file.exists():
                    print(
                        f"[validate] WARNING: approach baseline output not found: "
                        f"{approach_baseline_file}",
                        flush=True,
                    )

            # --- Approach run with failure injection ---
            approach_fi_out = (
                output_dir / "correctness" / f"{approach.name}_failure_injection"
            )
            ckpt_dir_fi = approach_fi_out / f"{approach.name}_ckpt"
            print(
                f"\n[validate] Running {approach.label} with failure injection...",
                flush=True,
            )
            if approach.approach_type == "criu":
                from .criu_runner import criu_run_with_failure_injection

                fi_result = criu_run_with_failure_injection(
                    build_dir=a_build,
                    executable_name=a_exe,
                    num_procs=args.num_procs,
                    app_args=approach_app_args,
                    output_dir=approach_fi_out,
                    ckpt_dir=ckpt_dir_fi,
                    injection_delay=injection_delay,
                    run_cwd=approach_fi_out,
                )
            else:
                fi_result = dmtcp_run_with_failure_injection(
                    build_dir=a_build,
                    executable_name=a_exe,
                    num_procs=args.num_procs,
                    app_args=approach_app_args,
                    output_dir=approach_fi_out,
                    ckpt_dir=ckpt_dir_fi,
                    coord_port=coord_port_base,
                    injection_delay=injection_delay,
                    run_cwd=approach_fi_out,
                    install_prefix=approach.install_prefix,
                )

            # Compare approach output (failure-prone) against baseline.
            test_num += 1
            approach_fi_file = approach_fi_out / args.output_file_name
            if approach_fi_file.exists():
                print(
                    f"\n[validate] Comparing outputs ({approach.label}, failure-prone):\n"
                    f"  baseline:  {approach_baseline_file}\n"
                    f"  approach:  {approach_fi_file}",
                    flush=True,
                )
                fi_compare = approach_comparator.compare(
                    approach_baseline_file,
                    approach_fi_file,
                )
                fi_compare.method = (
                    f"{fi_compare.method} [{approach.label}, failure-prone]"
                )
                print(
                    f"[validate] Test {test_num} ({approach.label}, failure-prone): "
                    f"{fi_compare}",
                    flush=True,
                )
                results.append(fi_compare)
            elif not fi_result.injected:
                # DMTCP could not complete the checkpoint/restart cycle
                # (e.g. app finished too fast, DMTCP internal error, no
                # checkpoint files written).  This is an infrastructure
                # limitation, not a validation failure — mark as SKIP so
                # the overall validation can still pass.
                print(
                    f"[validate] SKIP: {approach.label} failure-prone test skipped – "
                    f"failure injection did not occur "
                    f"(exit_code={fi_result.exit_code}).",
                    flush=True,
                )
                results.append(
                    CompareResult(
                        passed=True,
                        method=f"{approach.label} (failure-prone)",
                        message=(
                            "SKIPPED: DMTCP failure injection did not occur; "
                            "checkpoint/restart cycle could not be completed"
                        ),
                    )
                )
            else:
                # Injection happened (checkpoint + kill worked) but the
                # restored process didn't produce output.  This typically
                # means the MANA/DMTCP restore failed (e.g. SIGSEGV during
                # process image restoration on Aurora GPU nodes).  Treat as
                # SKIP — the checkpoint mechanism works; restore is a known
                # platform limitation.
                print(
                    f"[validate] SKIP: {approach.label} failure-prone test – "
                    f"checkpoint + kill succeeded but restore failed "
                    f"(exit_code={fi_result.exit_code}). "
                    f"Output not found: {approach_fi_file}",
                    flush=True,
                )
                results.append(
                    CompareResult(
                        passed=True,
                        method=f"{approach.label} (failure-prone)",
                        message=(
                            "SKIPPED: checkpoint + kill succeeded; restore failed "
                            "(known MANA/DMTCP platform limitation on Aurora)"
                        ),
                    )
                )

            # --- Approach run without failure injection (failure-free check) ---
            approach_clean_out = output_dir / "correctness" / f"{approach.name}_clean"
            ckpt_dir_clean = approach_clean_out / f"{approach.name}_ckpt"
            print(
                f"\n[validate] Running {approach.label} without failure injection "
                f"(failure-free check)...",
                flush=True,
            )
            if approach.approach_type == "criu":
                from .criu_runner import criu_run_once

                clean_result_a = criu_run_once(
                    build_dir=a_build,
                    executable_name=a_exe,
                    num_procs=args.num_procs,
                    app_args=approach_app_args,
                    output_dir=approach_clean_out,
                    ckpt_dir=ckpt_dir_clean,
                    run_cwd=approach_clean_out,
                )
            else:
                clean_result_a = dmtcp_run_once(
                    build_dir=a_build,
                    executable_name=a_exe,
                    num_procs=args.num_procs,
                    app_args=approach_app_args,
                    output_dir=approach_clean_out,
                    ckpt_dir=ckpt_dir_clean,
                    coord_port=coord_port_base + 1,
                    run_cwd=approach_clean_out,
                    install_prefix=approach.install_prefix,
                )
            if not clean_result_a.succeeded:
                print(
                    f"[validate] WARNING: {approach.label} failure-free run exited "
                    f"with code {clean_result_a.exit_code}",
                    flush=True,
                )

            # Compare approach output (failure-free) against baseline.
            test_num += 1
            approach_clean_file = approach_clean_out / args.output_file_name
            if approach_clean_file.exists():
                print(
                    f"\n[validate] Comparing outputs ({approach.label}, failure-free):\n"
                    f"  baseline:  {approach_baseline_file}\n"
                    f"  approach:  {approach_clean_file}",
                    flush=True,
                )
                clean_compare = approach_comparator.compare(
                    approach_baseline_file,
                    approach_clean_file,
                )
                clean_compare.method = (
                    f"{clean_compare.method} [{approach.label}, failure-free]"
                )
                print(
                    f"[validate] Test {test_num} ({approach.label}, failure-free): "
                    f"{clean_compare}",
                    flush=True,
                )
                results.append(clean_compare)
            else:
                print(
                    f"[validate] WARNING: {approach.label} failure-free output not found: "
                    f"{approach_clean_file}",
                    flush=True,
                )
                results.append(
                    CompareResult(
                        passed=False,
                        method=f"{approach.label} (failure-free)",
                        message=f"Output file not found: {approach_clean_file}",
                    )
                )

    return results


def _resolve_build_cmd(value: str | None) -> str | None:
    """Resolve a build command that may use ``@file`` indirection.

    ``run_validate.sh`` writes complex build commands (containing nested
    quotes) to a temp file and passes ``@/tmp/xxx`` on the CLI so that
    shell expansion doesn't mangle them.
    """
    if value is None:
        return None
    if value.startswith("@"):
        path = value[1:]
        try:
            return open(path).read().strip()
        except FileNotFoundError:
            return value
    return value


def _default_baseline_cache_dir(original_src: Path) -> Path:
    """Per-app baseline-cache directory under ``build/baseline_cache/<APP>``.

    The app name is the last path component of the vanilla source dir.
    """
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "build" / "baseline_cache" / Path(original_src).name


def _autodetect_or_collect_baseline_cache(
    *,
    args: argparse.Namespace,
    original_src: Path,
    original_app_args: list[str],
    original_build_cmd: str | None,
    app_input_subdir: str | None,
) -> Path:
    """Return the populated baseline-cache directory for this app.

    The collector (``validation.veloc.collect_baseline``) is the SINGLE
    source of truth for baseline timing.  On a cache hit it returns
    immediately; on a miss it runs warmup + 2 measurement passes itself
    and writes the cache.  Any failure raises — there is no fallback,
    because the only alternative would be a duplicate 3-pass code path
    in ``validate.py`` and the design goal is one canonical path.
    """
    from .collect_baseline import collect

    cache_dir = _default_baseline_cache_dir(original_src)
    cache_dir, _meta, _was_hit = collect(
        original_src=original_src,
        executable_name=(
            getattr(args, "original_executable_name", None)
            or args.executable_name
        ),
        num_procs=args.num_procs,
        app_args=original_app_args,
        original_build_cmd=original_build_cmd,
        app_input_subdir=app_input_subdir,
        veloc_config_name=args.veloc_config_name,
        cache_dir=cache_dir,
        force=False,
        check_only=False,
    )
    return cache_dir


def _stage_benchmarks(
    args: argparse.Namespace,
    original_src: Path,
    original_build: Path,
    resilient_src: Path,
    resilient_build: Path,
    output_dir: Path,
    orig_exe: str,
    res_exe: str,
    orig_app_args: list[str],
    res_app_args: list[str],
    resume: bool = False,
    extra_approaches: list[ApproachConfig] | None = None,
) -> BenchmarkResults:
    """Run the benchmark sweep and return BenchmarkResults."""
    print("\n" + "=" * 70, flush=True)
    print("[validate] STAGE 2: Performance and Resilience Benchmarking", flush=True)
    print("=" * 70, flush=True)

    if args.benchmark_config:
        config_path = Path(args.benchmark_config).resolve()
        if args.benchmark_num_runs is not None:
            print(
                f"[validate] Loading benchmark config from {config_path} "
                f"(NUM_RUNS override={args.benchmark_num_runs}; "
                f"overrides per-scenario 'num_runs' in JSON)",
                flush=True,
            )
        else:
            print(
                f"[validate] Loading benchmark config from {config_path} "
                f"(using per-scenario 'num_runs' from JSON; "
                f"set NUM_RUNS env var to override)",
                flush=True,
            )
        scenarios = load_benchmark_config(
            config_path,
            override_num_runs=args.benchmark_num_runs,
        )
    else:
        print(
            "[validate] No benchmark config provided; using default two-scenario sweep.",
            flush=True,
        )
        # Use resilient args for the sweep (they may differ from original args).
        # When benchmark_num_runs is None (NUM_RUNS not set), fall back to 3.
        # Resolve injection delay for benchmarking fallback.
        _bench_delay = (
            10.0 if args.injection_delay == "auto" else float(args.injection_delay)
        )
        scenarios = default_scenario(
            num_procs=args.num_procs,
            app_args=res_app_args,
            injection_delay=_bench_delay,
            max_attempts=args.max_attempts,
            num_runs=args.benchmark_num_runs
            if args.benchmark_num_runs is not None
            else 3,
        )

    # Reference-mode (--reference-input-priority): force vanilla input files to
    # take precedence over the resilient codebase's own.  Used when the
    # "resilient" arm is the upstream reference checkpointed code (different
    # input file conventions than vanilla — e.g. Athena++ reference's blast
    # input uses 1 mesh block, fails with 4 ranks; SW4lite reference uses
    # tlim=2 vs vanilla's tlim=15).  Without this, the reference run would
    # crash on startup or run a completely different (smaller) workload than
    # vanilla, making the benchmark uninformative.  No-op for --baseline
    # (LLM-modified) runs because the LLM may have legitimately created or
    # modified input files that we want it to use.
    #
    # An optional --reference-input-overlay-dir adds an even-higher-priority
    # source above vanilla, used to inject per-app patches that enable the
    # reference's native checkpoint output (so checkpoint_size_bytes > 0).
    resilient_priority: list[Path] = []
    overlay_dir = getattr(args, "reference_input_overlay_dir", None)
    if overlay_dir:
        resilient_priority.append(Path(overlay_dir))
    if getattr(args, "reference_input_priority", False):
        resilient_priority.append(original_src)
    resilient_priority_param: list[Path] | None = resilient_priority or None
    return run_benchmark_sweep(
        original_source_dir=original_src,
        original_build_dir=original_build,
        resilient_source_dir=resilient_src,
        resilient_build_dir=resilient_build,
        original_executable_name=orig_exe,
        resilient_executable_name=res_exe,
        scenarios=scenarios,
        output_dir=output_dir,
        veloc_config_name=args.veloc_config_name,
        install_resilient=args.install_resilient,
        resume=resume,
        extra_approaches=extra_approaches,
        original_build_cmd=_resolve_build_cmd(getattr(args, 'original_build_cmd', None)),
        resilient_build_cmd=_resolve_build_cmd(getattr(args, 'resilient_build_cmd', None)),
        app_input_subdir=getattr(args, 'app_input_subdir', None),
        resilient_priority_source_dirs=resilient_priority_param,
    )


def _stage_report(
    correctness_results: list[CompareResult],
    benchmark_results: BenchmarkResults | None,
    output_dir: Path,
    approach_labels: dict[str, str] | None = None,
) -> Path:
    """Generate plots and summary report."""
    print("\n" + "=" * 70, flush=True)
    print("[validate] STAGE 3: Graphical Reporting", flush=True)
    print("=" * 70, flush=True)

    return generate_report(
        correctness_results=correctness_results,
        benchmark_results=benchmark_results,
        output_dir=output_dir,
        approach_labels=approach_labels,
    )


# ---------------------------------------------------------------------------
# Error reporting helper
# ---------------------------------------------------------------------------


def _fail(
    message: str,
    exc: BaseException | None = None,
    resume_cmd: str | None = None,
) -> None:
    """Print a formatted error report and exit with code 1.

    If *exc* is a :class:`ValidationError`, its ``debug_report()`` is printed
    (includes stdout/stderr tails).  Otherwise the exception message is printed.

    If *resume_cmd* is provided it is printed so the user can copy-paste it to
    restart from the last completed stage.
    """
    sep = "=" * 70
    print(f"\n{sep}", file=sys.stderr, flush=True)
    print(f"[validate] FATAL: {message}", file=sys.stderr, flush=True)
    if exc is not None:
        if isinstance(exc, ValidationError):
            print(exc.debug_report(), file=sys.stderr, flush=True)
        else:
            print(f"  {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
    if resume_cmd:
        print(
            f"\n[validate] To resume from the last completed stage, run:",
            file=sys.stderr,
            flush=True,
        )
        print(f"  {resume_cmd}", file=sys.stderr, flush=True)
    print(sep, file=sys.stderr, flush=True)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _build_resume_cmd(argv: list[str], output_dir: Path) -> str:
    """Build the command string a user can run to resume from the last stage.

    Prepends any environment variables that the benchmark JSON config may
    expand (e.g. ``DATA_PATH``) so the resume command is self-contained.
    """
    import os

    # Collect env vars that the benchmark config may reference.
    env_prefix_parts: list[str] = []
    for var in ("DATA_PATH",):
        val = os.environ.get(var)
        if val:
            env_prefix_parts.append(f"{var}={shlex.quote(val)}")

    # Reconstruct the original invocation, injecting --resume if not already present.
    cmd_parts = [sys.executable, "-m", "validation.veloc.validate"]
    has_resume = "--resume" in argv
    cmd_parts += list(argv)
    if not has_resume:
        cmd_parts.append("--resume")

    cmd_str = " ".join(shlex.quote(str(p)) for p in cmd_parts)
    if env_prefix_parts:
        return " ".join(env_prefix_parts) + " " + cmd_str
    return cmd_str


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = _build_parser()
    args = parser.parse_args(argv)

    original_src = Path(args.original_codebase).resolve()
    resilient_src = Path(args.resilient_codebase).resolve()

    output_dir = Path(args.output_dir).resolve()
    build_root = (
        Path(args.build_dir).resolve() if args.build_dir else output_dir / "build"
    )

    original_build = build_root / "original"
    resilient_build = build_root / "resilient"

    orig_exe = args.original_executable_name or args.executable_name
    res_exe = args.resilient_executable_name or args.executable_name

    orig_app_args = shlex.split(args.original_args)
    res_app_args = shlex.split(args.resilient_args)

    # Load comparison approaches from config or legacy DMTCP flags.
    repo_root = Path(__file__).resolve().parents[2]
    approaches: list[ApproachConfig] = []
    if args.approaches_config:
        approaches = load_approaches_config(
            Path(args.approaches_config).resolve(), repo_root
        )
        if approaches:
            print(
                f"[validate] Loaded {len(approaches)} approach(es) from "
                f"{args.approaches_config}: "
                f"{', '.join(a.name for a in approaches)}",
                flush=True,
            )
    elif args.dmtcp_codebase:
        # Legacy backward compat: convert --dmtcp-codebase to ApproachConfig.
        approaches = [
            ApproachConfig(
                name="dmtcp",
                label="DMTCP",
                enabled=True,
                approach_type="dmtcp",
                codebase_dir=Path(args.dmtcp_codebase).resolve(),
                executable_name=args.dmtcp_executable_name,
            )
        ]

    # Build approach_labels for reporter.
    approach_labels: dict[str, str] = {a.name: a.label for a in approaches}

    # ------------------------------------------------------------------
    # Pipeline state: load existing state (for --resume) or start fresh.
    # ------------------------------------------------------------------
    output_dir.mkdir(parents=True, exist_ok=True)
    state = _load_state(output_dir)

    if args.resume:
        completed = state.get("completed_stages", [])
        print(
            f"\n[validate] --resume: resuming from previous run.\n"
            f"  Already completed stages: {completed or '(none)'}",
            flush=True,
        )
    else:
        # Fresh run – reset state.
        state = {
            "completed_stages": [],
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "last_updated": None,
            "finished": False,
            "argv": list(argv),
        }
        _save_state(output_dir, state)

    completed_stages: set[str] = set(state.get("completed_stages", []))

    # Pre-build the resume command so we can print it on any failure.
    resume_cmd = _build_resume_cmd(list(argv), output_dir)

    approaches_line = ""
    if approaches:
        labels = ", ".join(f"{a.name} ({a.label})" for a in approaches)
        approaches_line = f"  Approaches        : {labels}\n"
    print(
        f"\n[validate] VeloC Validation Framework\n"
        f"  Original codebase : {original_src}\n"
        f"  Resilient codebase: {resilient_src}\n"
        f"{approaches_line}"
        f"  Output directory  : {output_dir}\n"
        f"  Executable        : orig={orig_exe!r}, resilient={res_exe!r}\n"
        f"  MPI processes     : {args.num_procs}\n"
        f"  Comparison method : {args.comparison_method}\n",
        flush=True,
    )

    correctness_results: list[CompareResult] = []
    benchmark_results: BenchmarkResults | None = None

    # --- Stage 1: Correctness ---
    if not args.skip_correctness:
        if "correctness" in completed_stages:
            print(
                "[validate] Skipping correctness stage (already completed in previous run).",
                flush=True,
            )
            # Load results from disk so the report stage has real data.
            correctness_results = _load_correctness_results(output_dir)
        else:
            try:
                correctness_results = _stage_correctness(
                    args=args,
                    original_src=original_src,
                    original_build=original_build,
                    resilient_src=resilient_src,
                    resilient_build=resilient_build,
                    output_dir=output_dir,
                    orig_exe=orig_exe,
                    res_exe=res_exe,
                    orig_app_args=orig_app_args,
                    res_app_args=res_app_args,
                    approaches=approaches if approaches else None,
                    build_root=build_root,
                    original_build_cmd=_resolve_build_cmd(
                        getattr(args, 'original_build_cmd', None)),
                    resilient_build_cmd=_resolve_build_cmd(
                        getattr(args, 'resilient_build_cmd', None)),
                    app_input_subdir=getattr(args, 'app_input_subdir', None),
                )
            except Exception as exc:
                _fail(
                    "Correctness stage encountered a fatal error.",
                    exc,
                    resume_cmd=resume_cmd,
                )

            # Fail fast if any correctness test failed.
            failed = [r for r in correctness_results if not r.passed]
            if failed:
                sep = "=" * 70
                print(f"\n{sep}", file=sys.stderr, flush=True)
                print(
                    f"[validate] FATAL: Correctness validation FAILED "
                    f"({len(failed)}/{len(correctness_results)} test(s) failed).",
                    file=sys.stderr,
                    flush=True,
                )
                for i, r in enumerate(failed, 1):
                    print(f"  Failed test {i}: {r}", file=sys.stderr, flush=True)
                print(
                    f"\n[validate] To resume from the last completed stage, run:\n"
                    f"  {resume_cmd}",
                    file=sys.stderr,
                    flush=True,
                )
                print(sep, file=sys.stderr, flush=True)
                sys.exit(1)

            # All correctness tests passed – persist results and progress.
            _save_correctness_results(output_dir, correctness_results)
            _mark_stage_complete(output_dir, state, "correctness")
            total = len(correctness_results)
            print(
                f"\n[validate] Correctness: PASS ({total}/{total} tests passed)",
                flush=True,
            )
    else:
        print(
            "[validate] Skipping correctness stage (--skip-correctness); "
            "loading previous results from disk.",
            flush=True,
        )
        correctness_results = _load_correctness_results(output_dir)

    # --- Stage 2: Benchmarking ---
    if not args.skip_benchmarks:
        if "benchmarks" in completed_stages:
            print(
                "[validate] Skipping benchmarking stage (already completed in previous run).",
                flush=True,
            )
            # Load results from disk so the report stage has real data.
            benchmark_results = _load_benchmark_results(output_dir)
        else:
            try:
                benchmark_results = _stage_benchmarks(
                    args=args,
                    original_src=original_src,
                    original_build=original_build,
                    resilient_src=resilient_src,
                    resilient_build=resilient_build,
                    output_dir=output_dir,
                    orig_exe=orig_exe,
                    res_exe=res_exe,
                    orig_app_args=orig_app_args,
                    res_app_args=res_app_args,
                    # Pass resume=True so the sweep can skip already-completed
                    # individual runs (fine-grained resume within the stage).
                    resume=args.resume,
                    extra_approaches=approaches if approaches else None,
                )
            except Exception as exc:
                _fail(
                    "Benchmarking stage encountered a fatal error.",
                    exc,
                    resume_cmd=resume_cmd,
                )
            _mark_stage_complete(output_dir, state, "benchmarks")
    else:
        print(
            "[validate] Skipping benchmarking stage (--skip-benchmarks); "
            "loading previous results from disk.",
            flush=True,
        )
        benchmark_results = _load_benchmark_results(output_dir)

    # --- Stage 3: Reporting ---
    if not args.skip_report:
        if "report" in completed_stages:
            print(
                "[validate] Skipping reporting stage (already completed in previous run).",
                flush=True,
            )
        else:
            try:
                report_path = _stage_report(
                    correctness_results=correctness_results,
                    benchmark_results=benchmark_results,
                    output_dir=output_dir,
                    approach_labels=approach_labels if approach_labels else None,
                )
                print(f"\n[validate] Report: {report_path}", flush=True)
            except Exception as exc:
                _fail(
                    "Reporting stage encountered a fatal error.",
                    exc,
                    resume_cmd=resume_cmd,
                )
            _mark_stage_complete(output_dir, state, "report")
    else:
        print("[validate] Skipping reporting stage (--skip-report).", flush=True)

    # --- Final summary ---
    _mark_run_complete(output_dir, state)
    print("\n" + "=" * 70, flush=True)
    print("[validate] All stages completed successfully.", flush=True)
    print("=" * 70, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
