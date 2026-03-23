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
import sys
import time
from pathlib import Path

from .comparator import CompareResult, make_comparator
from .metrics_collector import (
    BenchmarkResults,
    BenchmarkScenario,
    RunMetrics,
    default_scenario,
    load_benchmark_config,
    run_benchmark_sweep,
)
from .reporter import generate_report
from .runner import (
    ValidationError,
    configure_and_build,
    run_baseline,
    run_with_failure_injection,
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
    _state_path(output_dir).write_text(
        json.dumps(state, indent=2), encoding="utf-8"
    )


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

    # Correctness stage.
    corr_grp = parser.add_argument_group("Correctness validation")
    corr_grp.add_argument(
        "--output-file-name",
        default="recon.h5",
        help="Name of the output file produced by both applications to compare.",
    )
    corr_grp.add_argument(
        "--max-attempts",
        type=int,
        default=10,
        help="Maximum resilient retry attempts before giving up.",
    )
    corr_grp.add_argument(
        "--injection-delay",
        type=float,
        default=5.0,
        help="Seconds to wait before injecting a failure into the MPI run.",
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
        "--resume",
        action="store_true",
        help=(
            "Resume a previous run from the last completed stage. "
            "Reads pipeline_state.json from --output-dir and skips already-completed stages."
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
) -> list[CompareResult]:
    """Run baseline + resilient, compare outputs. Returns a list of CompareResult."""
    print("\n" + "=" * 70, flush=True)
    print("[validate] STAGE 1: Correctness Validation", flush=True)
    print("=" * 70, flush=True)

    baseline_out = output_dir / "correctness" / "baseline"
    resilient_out = output_dir / "correctness" / "resilient"

    # --- Baseline run ---
    print("\n[validate] Running baseline (original) application...", flush=True)
    run_baseline(
        source_dir=original_src,
        build_dir=original_build,
        output_dir=baseline_out,
        executable_name=orig_exe,
        num_procs=args.num_procs,
        app_args=orig_app_args,
    )

    # --- Resilient run with failure injection ---
    print("\n[validate] Running resilient application with failure injection...", flush=True)
    run_with_failure_injection(
        source_dir=resilient_src,
        build_dir=resilient_build,
        output_dir=resilient_out,
        executable_name=res_exe,
        num_procs=args.num_procs,
        app_args=res_app_args,
        max_attempts=args.max_attempts,
        injection_delay=args.injection_delay,
        run_install=args.install_resilient,
        success_output_filename=args.output_file_name,
        veloc_config_name=args.veloc_config_name,
    )

    # --- Also run resilient without failure injection (failure-free check) ---
    print("\n[validate] Running resilient application without failure injection (failure-free check)...", flush=True)
    from .runner import run_once
    resilient_clean_out = output_dir / "correctness" / "resilient_clean"
    resilient_clean_out.mkdir(parents=True, exist_ok=True)
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

    # --- Compare outputs ---
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

    results: list[CompareResult] = []

    # Test 1: baseline vs resilient (with failure injection)
    baseline_file = baseline_out / args.output_file_name
    resilient_file = resilient_out / args.output_file_name
    print(
        f"\n[validate] Comparing outputs (failure-prone):\n"
        f"  baseline:  {baseline_file}\n"
        f"  resilient: {resilient_file}",
        flush=True,
    )
    result1 = comparator.compare(baseline_file, resilient_file)
    print(f"[validate] Test 1 (failure-prone): {result1}", flush=True)
    results.append(result1)

    # Test 2: baseline vs resilient (failure-free)
    resilient_clean_file = resilient_clean_out / args.output_file_name
    if resilient_clean_file.exists():
        print(
            f"\n[validate] Comparing outputs (failure-free):\n"
            f"  baseline:  {baseline_file}\n"
            f"  resilient: {resilient_clean_file}",
            flush=True,
        )
        result2 = comparator.compare(baseline_file, resilient_clean_file)
        print(f"[validate] Test 2 (failure-free): {result2}", flush=True)
        results.append(result2)
    else:
        print(
            f"[validate] Skipping failure-free comparison: "
            f"{resilient_clean_file} not found.",
            flush=True,
        )

    return results


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
        scenarios = default_scenario(
            num_procs=args.num_procs,
            app_args=res_app_args,
            injection_delay=args.injection_delay,
            max_attempts=args.max_attempts,
            num_runs=args.benchmark_num_runs if args.benchmark_num_runs is not None else 3,
        )

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
    )


def _stage_report(
    correctness_results: list[CompareResult],
    benchmark_results: BenchmarkResults | None,
    output_dir: Path,
) -> Path:
    """Generate plots and summary report."""
    print("\n" + "=" * 70, flush=True)
    print("[validate] STAGE 3: Graphical Reporting", flush=True)
    print("=" * 70, flush=True)

    return generate_report(
        correctness_results=correctness_results,
        benchmark_results=benchmark_results,
        output_dir=output_dir,
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
        print(f"\n[validate] To resume from the last completed stage, run:", file=sys.stderr, flush=True)
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
    build_root = Path(args.build_dir).resolve() if args.build_dir else output_dir / "build"

    original_build = build_root / "original"
    resilient_build = build_root / "resilient"

    orig_exe = args.original_executable_name or args.executable_name
    res_exe = args.resilient_executable_name or args.executable_name

    orig_app_args = shlex.split(args.original_args)
    res_app_args = shlex.split(args.resilient_args)

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

    print(
        f"\n[validate] VeloC Validation Framework\n"
        f"  Original codebase : {original_src}\n"
        f"  Resilient codebase: {resilient_src}\n"
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
