"""
metrics_collector.py – Benchmarking and metrics collection for the VeloC
validation framework.

Provides:
  BenchmarkScenario   – configuration for a single benchmark scenario
  RunMetrics          – metrics collected from a single application run
  BenchmarkResults    – aggregated results across all scenarios and runs
  load_benchmark_config()   – parse a JSON benchmark config file
  default_scenario()        – create a single-scenario list from CLI defaults
  run_benchmark_sweep()     – execute all scenarios and collect metrics

Metrics collected per run
-------------------------
  elapsed_s             – wall-clock execution time
  injected              – whether a failure was injected
  num_attempts          – total retry attempts (resilient runs only)
  checkpoint_size_bytes – total bytes in VeloC scratch/persistent dirs (post-run)
  recovery_time_s       – estimated recovery time parsed from VeloC stdout
  peak_memory_bytes     – peak RSS of the mpirun process (polled via psutil)
"""

from __future__ import annotations

import json
import os
import re
import statistics
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from .runner import (
    RunResult,
    ValidationError,
    configure_and_build,
    extract_checkpoint_dirs_from_veloc_cfg,
    run_baseline,
    run_once,
    run_with_failure_injection,
)
from .dmtcp_runner import (
    check_dmtcp_available,
    dmtcp_run_once,
    dmtcp_run_with_failure_injection,
    measure_checkpoint_size as dmtcp_measure_checkpoint_size,
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ApproachConfig:
    """Configuration for a comparison approach (e.g., DMTCP)."""
    name: str                          # unique identifier, used as codebase label
    label: str                         # human-readable display name
    enabled: bool
    approach_type: str                 # "dmtcp", or future types
    codebase_dir: Path
    executable_name: str | None = None # None = use main --executable-name
    install_prefix: str | None = None  # for DMTCP: None = auto-discover


@dataclass
class BenchmarkScenario:
    """Configuration for a single benchmark scenario."""
    name: str
    num_procs: int
    app_args: list[str]
    inject_failures: bool = True    # True = resilient run with injection
    num_runs: int = 3               # repetitions for statistical stability
    injection_delay: float = 5.0
    max_attempts: int = 10


@dataclass
class RunMetrics:
    """Metrics collected from a single application run."""
    scenario_name: str
    codebase: str                           # "original" or "resilient"
    run_index: int
    elapsed_s: float
    injected: bool
    num_attempts: int
    checkpoint_size_bytes: int | None = None
    recovery_time_s: float | None = None
    peak_memory_bytes: int | None = None    # kept for backward compat with saved data
    memory_samples_bytes: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BenchmarkResults:
    """Aggregated results across all scenarios and runs."""
    scenarios: list[BenchmarkScenario]
    runs: list[RunMetrics]
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenarios": [asdict(s) for s in self.scenarios],
            "runs": [r.to_dict() for r in self.runs],
            "summary": self.summary,
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def load_benchmark_config(
    config_path: Path,
    default_num_runs: int = 3,
    override_num_runs: int | None = None,
) -> list[BenchmarkScenario]:
    """Parse a JSON benchmark config file into a list of BenchmarkScenario objects.

    Parameters
    ----------
    config_path:
        Path to the JSON config file.
    default_num_runs:
        Fallback ``num_runs`` value used for any scenario that does **not**
        specify ``num_runs`` in the JSON.  Only used when *override_num_runs*
        is ``None``.
    override_num_runs:
        When set (not ``None``), this value overrides the per-scenario
        ``num_runs`` in the JSON for **every** scenario.  This lets the caller
        pass ``NUM_RUNS`` from the environment to force a specific repetition
        count regardless of what the JSON says.  When ``None`` (the default),
        the JSON ``num_runs`` is used as-is (falling back to *default_num_runs*
        for scenarios that omit it).

    Priority (highest → lowest):
        1. *override_num_runs* (set via ``NUM_RUNS`` env var / ``--benchmark-num-runs``)
        2. Per-scenario ``num_runs`` in the JSON
        3. *default_num_runs* (3)

    Expected JSON schema::

        {
          "scenarios": [
            {
              "name": "small-4procs-no-failure",
              "num_procs": 4,
              "app_args": ["data.h5", "294.078", "3", "2", "0", "2"],
              "inject_failures": false,
              "num_runs": 3,          // optional – used when override_num_runs is None
              "injection_delay": 5.0,
              "max_attempts": 10
            },
            ...
          ]
        }
    """
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    scenarios: list[BenchmarkScenario] = []
    for entry in raw.get("scenarios", []):
        # Skip comment-only entries (keys starting with "_")
        if set(entry.keys()) <= {"_comment"}:
            continue
        # Expand environment variables in app_args strings so that config files
        # can use ${VAR:-default} notation (bash-style defaults are NOT supported
        # by os.path.expandvars; only $VAR / ${VAR} are expanded).  For bash-style
        # defaults we apply a simple regex substitution first.
        def _expand_arg(arg: str) -> str:
            def _sub_default(m: re.Match) -> str:  # type: ignore[type-arg]
                return os.environ.get(m.group(1), m.group(2))
            arg = re.sub(r"\$\{(\w+):-([^}]*)\}", _sub_default, arg)
            return os.path.expandvars(arg)

        raw_args = entry.get("app_args", [])
        expanded_args: list[str] = [_expand_arg(str(a)) for a in raw_args]
        # Priority: override_num_runs > JSON num_runs > default_num_runs.
        if override_num_runs is not None:
            num_runs = override_num_runs
        elif "num_runs" in entry:
            num_runs = int(entry["num_runs"])
        else:
            num_runs = default_num_runs
        scenarios.append(
            BenchmarkScenario(
                name=entry["name"],
                num_procs=int(entry["num_procs"]),
                app_args=expanded_args,
                inject_failures=bool(entry.get("inject_failures", True)),
                num_runs=num_runs,
                injection_delay=float(entry.get("injection_delay", 5.0)),
                max_attempts=int(entry.get("max_attempts", 10)),
            )
        )
    if not scenarios:
        raise ValueError(f"No scenarios found in benchmark config {config_path}")
    return scenarios


def default_scenario(
    num_procs: int,
    app_args: list[str],
    injection_delay: float = 5.0,
    max_attempts: int = 10,
    num_runs: int = 3,
) -> list[BenchmarkScenario]:
    """Create a minimal two-scenario list from CLI defaults.

    Produces one failure-free scenario (to measure baseline overhead) and one
    failure-injection scenario (to measure recovery cost).
    """
    return [
        BenchmarkScenario(
            name="default-no-failure",
            num_procs=num_procs,
            app_args=app_args,
            inject_failures=False,
            num_runs=num_runs,
            injection_delay=injection_delay,
            max_attempts=max_attempts,
        ),
        BenchmarkScenario(
            name="default-with-failure",
            num_procs=num_procs,
            app_args=app_args,
            inject_failures=True,
            num_runs=num_runs,
            injection_delay=injection_delay,
            max_attempts=max_attempts,
        ),
    ]


def load_approaches_config(
    config_path: Path,
    repo_root: Path,
) -> list[ApproachConfig]:
    """Parse a JSON approaches config into a list of enabled ApproachConfig objects.

    Returns an empty list if the file does not exist (backward compat).
    """
    if not config_path.exists():
        return []
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    approaches: list[ApproachConfig] = []
    for entry in raw.get("approaches", []):
        if not entry.get("enabled", True):
            continue
        codebase_dir = Path(entry["codebase_dir"])
        if not codebase_dir.is_absolute():
            codebase_dir = repo_root / codebase_dir
        approaches.append(
            ApproachConfig(
                name=entry["name"],
                label=entry.get("label", entry["name"]),
                enabled=True,
                approach_type=entry.get("type", "unknown"),
                codebase_dir=codebase_dir,
                executable_name=entry.get("executable_name"),
                install_prefix=entry.get("install_prefix"),
            )
        )
    return approaches


# ---------------------------------------------------------------------------
# Checkpoint size measurement
# ---------------------------------------------------------------------------

def _measure_checkpoint_size(veloc_cfg_path: Path) -> int | None:
    """Sum the total bytes in VeloC scratch/persistent directories."""
    dirs = extract_checkpoint_dirs_from_veloc_cfg(veloc_cfg_path)
    if not dirs:
        return None
    total = 0
    for d in dirs:
        if not d.exists():
            continue
        for root, _subdirs, files in os.walk(d):
            for fname in files:
                try:
                    total += (Path(root) / fname).stat().st_size
                except OSError:
                    pass
    return total


# ---------------------------------------------------------------------------
# Recovery time estimation
# ---------------------------------------------------------------------------

_RECOVERY_TIME_PATTERNS = [
    # VeloC log lines with explicit timing (heuristic – adjust as VeloC output evolves)
    re.compile(r"[Rr]estart.*?completed.*?(\d+(?:\.\d+)?)\s*s", re.IGNORECASE),
    re.compile(r"[Rr]ecovery.*?(\d+(?:\.\d+)?)\s*s", re.IGNORECASE),
    re.compile(r"[Rr]estarted.*?in\s+(\d+(?:\.\d+)?)\s*s", re.IGNORECASE),
]

# Pattern to detect that a restart actually happened (even without timing info).
# Matches lines like: "[task-1]: Restarted from checkpoint version 3, outer_iter=3"
_RESTART_DETECTED_PATTERN = re.compile(
    r"[Rr]estart(?:ed)?\s+from\s+checkpoint", re.IGNORECASE
)


def _parse_recovery_time(stdout: str) -> float | None:
    """Heuristic: search VeloC stdout for restart/recovery timing lines."""
    for line in stdout.splitlines():
        for pattern in _RECOVERY_TIME_PATTERNS:
            m = pattern.search(line)
            if m:
                try:
                    return float(m.group(1))
                except (ValueError, IndexError):
                    pass
    return None


def _detect_restart(stdout: str) -> bool:
    """Return True if the stdout indicates a VeloC restart from checkpoint."""
    for line in stdout.splitlines():
        if _RESTART_DETECTED_PATTERN.search(line):
            return True
    return False


# ---------------------------------------------------------------------------
# Memory monitoring (sample-based)
# ---------------------------------------------------------------------------

def _monitor_memory_samples(
    pid: int,
    samples_holder: list[list[int]],
    stop_event: threading.Event,
    interval: float = 0.5,
) -> None:
    """Poll the RSS of *pid* (and its children) every *interval* seconds.

    Stores all collected samples in ``samples_holder[0]``.  The caller should
    set *stop_event* when the monitored process has finished.
    """
    try:
        import psutil
    except ImportError:
        return

    samples: list[int] = []
    try:
        proc = psutil.Process(pid)
        while not stop_event.is_set():
            try:
                # Sum RSS of the main process and all children (mpirun + workers).
                total_rss = proc.memory_info().rss
                try:
                    for child in proc.children(recursive=True):
                        try:
                            total_rss += child.memory_info().rss
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                samples.append(total_rss)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
            stop_event.wait(interval)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    samples_holder[0] = samples


# ---------------------------------------------------------------------------
# Single-scenario run with metrics
# ---------------------------------------------------------------------------

def _run_scenario_once(
    scenario: BenchmarkScenario,
    codebase: str,
    run_index: int,
    source_dir: Path,
    build_dir: Path,
    output_dir: Path,
    executable_name: str,
    veloc_config_name: str = "veloc.cfg",
    run_install: bool = False,
    install_prefix: str | None = None,
    dmtcp_coord_port: int = 0,
) -> RunMetrics:
    """Execute one run of *scenario* for *codebase* and collect metrics."""
    run_output_dir = output_dir / codebase / scenario.name / f"run_{run_index}"
    run_output_dir.mkdir(parents=True, exist_ok=True)

    # Locate veloc.cfg for checkpoint size measurement (resilient only).
    veloc_cfg: Path | None = None
    if codebase == "resilient":
        for candidate in (build_dir / veloc_config_name, source_dir / veloc_config_name):
            if candidate.exists():
                veloc_cfg = candidate
                break

    # Prepare memory monitoring.
    mem_samples_holder: list[list[int]] = [[]]
    mem_stop_event = threading.Event()

    if codebase == "dmtcp":
        # ── DMTCP run ──────────────────────────────────────────────────
        ckpt_dir = run_output_dir / "dmtcp_ckpt"
        coord_port = dmtcp_coord_port if dmtcp_coord_port else 7800

        if scenario.inject_failures:
            result: RunResult = dmtcp_run_with_failure_injection(
                build_dir=build_dir,
                executable_name=executable_name,
                num_procs=scenario.num_procs,
                app_args=scenario.app_args,
                output_dir=run_output_dir,
                ckpt_dir=ckpt_dir,
                coord_port=coord_port,
                injection_delay=scenario.injection_delay,
                run_cwd=run_output_dir,
                install_prefix=install_prefix,
                memory_monitor_fn=_monitor_memory_samples,
                memory_stop_event=mem_stop_event,
                memory_samples_holder=mem_samples_holder,
            )
        else:
            result = dmtcp_run_once(
                build_dir=build_dir,
                executable_name=executable_name,
                num_procs=scenario.num_procs,
                app_args=scenario.app_args,
                output_dir=run_output_dir,
                ckpt_dir=ckpt_dir,
                coord_port=coord_port,
                run_cwd=run_output_dir,
                install_prefix=install_prefix,
                memory_monitor_fn=_monitor_memory_samples,
                memory_stop_event=mem_stop_event,
                memory_samples_holder=mem_samples_holder,
            )
            if not result.succeeded:
                raise ValidationError(
                    f"DMTCP benchmark run failed for scenario={scenario.name!r}, "
                    f"run={run_index}, exit code={result.exit_code}",
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exit_code=result.exit_code,
                    output_dir=run_output_dir,
                )
        # DMTCP checkpoint size.
        ckpt_size: int | None = dmtcp_measure_checkpoint_size(ckpt_dir)

    elif scenario.inject_failures and codebase == "resilient":
        # ── Resilient run with failure injection ───────────────────────
        # Memory is monitored per-attempt inside run_with_failure_injection;
        # samples are accumulated across all attempts and returned via
        # result.memory_samples_bytes.
        result = run_with_failure_injection(
            source_dir=source_dir,
            build_dir=build_dir,
            output_dir=run_output_dir,
            executable_name=executable_name,
            num_procs=scenario.num_procs,
            app_args=scenario.app_args,
            max_attempts=scenario.max_attempts,
            injection_delay=scenario.injection_delay,
            run_install=run_install,
            veloc_config_name=veloc_config_name,
            require_injection=False,  # benchmarking: OK if app finishes before injection
            memory_monitor_fn=_monitor_memory_samples,
            memory_stop_event=mem_stop_event,
            memory_samples_holder=mem_samples_holder,
        )
        # VeloC checkpoint size.
        ckpt_size = None
        if veloc_cfg is not None:
            ckpt_size = _measure_checkpoint_size(veloc_cfg)

    else:
        # ── Clean run (no failure injection) ───────────────────────────
        # Used for original and failure-free resilient benchmarks.
        veloc_sources = [source_dir, build_dir] if codebase == "resilient" else None
        result = run_once(
            build_dir=build_dir,
            executable_name=executable_name,
            num_procs=scenario.num_procs,
            app_args=scenario.app_args,
            output_dir=run_output_dir,
            run_cwd=run_output_dir,
            veloc_config_sources=veloc_sources,
            veloc_config_name=veloc_config_name,
            memory_monitor_fn=_monitor_memory_samples,
            memory_stop_event=mem_stop_event,
            memory_samples_holder=mem_samples_holder,
        )
        if not result.succeeded:
            raise ValidationError(
                f"Benchmark run failed for scenario={scenario.name!r}, "
                f"codebase={codebase!r}, run={run_index}, "
                f"exit code={result.exit_code}",
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.exit_code,
                output_dir=run_output_dir,
            )
        # VeloC checkpoint size (resilient clean runs only).
        ckpt_size = None
        if veloc_cfg is not None:
            ckpt_size = _measure_checkpoint_size(veloc_cfg)

    # Memory samples: prefer result.memory_samples_bytes (filled by
    # run_with_failure_injection / dmtcp runners), fall back to
    # mem_samples_holder (filled by run_once's background thread).
    if result.memory_samples_bytes:
        mem_samples = result.memory_samples_bytes
    else:
        mem_samples = mem_samples_holder[0] if mem_samples_holder[0] else []
    peak_mem = max(mem_samples) if mem_samples else None

    return RunMetrics(
        scenario_name=scenario.name,
        codebase=codebase,
        run_index=run_index,
        elapsed_s=result.elapsed_s,
        injected=result.injected,
        num_attempts=result.num_attempts,
        checkpoint_size_bytes=ckpt_size,
        recovery_time_s=None,
        peak_memory_bytes=peak_mem,
        memory_samples_bytes=mem_samples,
    )


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

def _aggregate(values: list[float]) -> dict[str, float]:
    """Return mean, std, min, max for a list of floats."""
    if not values:
        return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "n": 0}
    return {
        "mean": statistics.mean(values),
        "std": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
        "n": len(values),
    }


def _build_summary(runs: list[RunMetrics]) -> dict[str, Any]:
    """Build a nested summary dict: scenario → codebase → metric → stats."""
    summary: dict[str, Any] = {}
    for run in runs:
        s = run.scenario_name
        c = run.codebase
        summary.setdefault(s, {}).setdefault(c, {
            "elapsed_s": [],
            "checkpoint_size_bytes": [],
            "recovery_time_s": [],
            "peak_memory_bytes": [],
            "memory_samples_bytes": [],
            "num_attempts": [],
        })
        bucket = summary[s][c]
        bucket["elapsed_s"].append(run.elapsed_s)
        if run.checkpoint_size_bytes is not None:
            bucket["checkpoint_size_bytes"].append(run.checkpoint_size_bytes)
        if run.recovery_time_s is not None:
            bucket["recovery_time_s"].append(run.recovery_time_s)
        if run.peak_memory_bytes is not None:
            bucket["peak_memory_bytes"].append(run.peak_memory_bytes)
        if run.memory_samples_bytes:
            bucket["memory_samples_bytes"].extend(run.memory_samples_bytes)
        bucket["num_attempts"].append(run.num_attempts)

    # Replace raw lists with aggregated stats.
    for s in summary:
        for c in summary[s]:
            bucket = summary[s][c]
            for metric in list(bucket.keys()):
                bucket[metric] = _aggregate(bucket[metric])

    return summary


# ---------------------------------------------------------------------------
# Benchmark progress helpers (fine-grained resume within the sweep)
# ---------------------------------------------------------------------------

_BENCH_PROGRESS_FILE = "benchmark_progress.json"


def _bench_progress_key(scenario_name: str, codebase: str, run_index: int) -> str:
    """Unique string key identifying a single benchmark run."""
    return f"{scenario_name}:{codebase}:{run_index}"


def _load_bench_progress(benchmarks_dir: Path) -> tuple[list[RunMetrics], set[str]]:
    """Load previously completed benchmark runs from *benchmark_progress.json*.

    Returns
    -------
    completed_runs : list[RunMetrics]
        All runs that were already completed in a previous (interrupted) sweep.
    completed_keys : set[str]
        Set of ``_bench_progress_key`` strings for fast membership testing.
    """
    progress_path = benchmarks_dir / _BENCH_PROGRESS_FILE
    if not progress_path.exists():
        return [], set()
    try:
        raw = json.loads(progress_path.read_text(encoding="utf-8"))
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
                memory_samples_bytes=r.get("memory_samples_bytes", []),
            )
            for r in raw.get("runs", [])
        ]
        keys = {
            _bench_progress_key(r.scenario_name, r.codebase, r.run_index)
            for r in runs
        }
        print(
            f"[metrics] Loaded {len(runs)} previously completed benchmark run(s) "
            f"from {progress_path}",
            flush=True,
        )
        return runs, keys
    except Exception as exc:
        print(
            f"[metrics] WARNING: could not load benchmark progress from {progress_path}: {exc}; "
            "starting sweep from scratch.",
            flush=True,
        )
        return [], set()


def _save_bench_progress(benchmarks_dir: Path, runs: list[RunMetrics]) -> None:
    """Persist the list of completed runs to *benchmark_progress.json*."""
    progress_path = benchmarks_dir / _BENCH_PROGRESS_FILE
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    data = {"runs": [r.to_dict() for r in runs]}
    progress_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main sweep function
# ---------------------------------------------------------------------------

def run_benchmark_sweep(
    original_source_dir: Path,
    original_build_dir: Path,
    resilient_source_dir: Path,
    resilient_build_dir: Path,
    original_executable_name: str,
    resilient_executable_name: str,
    scenarios: list[BenchmarkScenario],
    output_dir: Path,
    veloc_config_name: str = "veloc.cfg",
    install_resilient: bool = False,
    resume: bool = False,
    dmtcp_source_dir: Path | None = None,
    dmtcp_build_dir: Path | None = None,
    dmtcp_executable_name: str | None = None,
    dmtcp_coord_base_port: int = 7800,
    extra_approaches: list[ApproachConfig] | None = None,
) -> BenchmarkResults:
    """Execute all scenarios for all codebases and collect RunMetrics.

    For each scenario:
      - The *original* codebase is always run without failure injection.
      - The *resilient* codebase is run with or without failure injection
        depending on ``scenario.inject_failures``.
      - The *dmtcp* codebase (if provided) is run with the same logic as
        resilient, but using DMTCP transparent checkpointing.

    Each scenario is repeated ``scenario.num_runs`` times for statistical
    stability.

    Parameters
    ----------
    resume:
        When ``True``, load previously completed runs from
        ``benchmark_progress.json`` and skip them.
    dmtcp_source_dir, dmtcp_build_dir, dmtcp_executable_name:
        When all three are provided and DMTCP is available, the sweep
        includes a third "dmtcp" codebase.  When ``None``, only original
        and resilient codebases are benchmarked (backward-compatible).
    dmtcp_coord_base_port:
        Base port for DMTCP coordinators.  Each run gets a unique port
        derived from this base to avoid collisions.
    """
    benchmarks_dir = output_dir / "benchmarks"
    build_root = output_dir / "build"

    # Merge legacy DMTCP params with extra_approaches into a unified list.
    active_approaches: list[ApproachConfig] = []
    if extra_approaches:
        active_approaches = list(extra_approaches)
    elif (
        dmtcp_source_dir is not None
        and dmtcp_build_dir is not None
        and dmtcp_executable_name is not None
    ):
        # Backward compat: convert legacy params to ApproachConfig.
        active_approaches = [
            ApproachConfig(
                name="dmtcp",
                label="DMTCP",
                enabled=True,
                approach_type="dmtcp",
                codebase_dir=dmtcp_source_dir,
                executable_name=dmtcp_executable_name,
            )
        ]

    # Filter to approaches whose tools are available.
    verified_approaches: list[ApproachConfig] = []
    for approach in active_approaches:
        if approach.approach_type == "dmtcp":
            if check_dmtcp_available(approach.install_prefix):
                verified_approaches.append(approach)
            else:
                print(
                    f"[metrics] WARNING: approach {approach.name!r} skipped – "
                    "DMTCP tools not found.",
                    flush=True,
                )
        else:
            print(
                f"[metrics] WARNING: unknown approach type {approach.approach_type!r} "
                f"for {approach.name!r}; skipping.",
                flush=True,
            )

    # Load previously completed runs when resuming.
    if resume:
        all_runs, completed_keys = _load_bench_progress(benchmarks_dir)
        if completed_keys:
            print(
                f"[metrics] Resuming benchmark sweep – {len(completed_keys)} run(s) already done.",
                flush=True,
            )
    else:
        all_runs = []
        completed_keys: set[str] = set()

    # Build all codebases once before the sweep.
    print("[metrics] building original codebase...", flush=True)
    configure_and_build(original_source_dir, original_build_dir)
    print("[metrics] building resilient codebase...", flush=True)
    configure_and_build(resilient_source_dir, resilient_build_dir, run_install=install_resilient)

    # Build approach codebases and resolve their build dirs.
    approach_build_dirs: dict[str, Path] = {}
    for approach in verified_approaches:
        # Use legacy dmtcp_build_dir if it was passed directly, otherwise
        # create a build dir under the output build root.
        if approach.approach_type == "dmtcp" and dmtcp_build_dir is not None and not extra_approaches:
            a_build = dmtcp_build_dir
        else:
            a_build = build_root / approach.name
        print(f"[metrics] building {approach.name} codebase...", flush=True)
        configure_and_build(approach.codebase_dir, a_build)
        approach_build_dirs[approach.name] = a_build

    total_scenarios = len(scenarios)
    for scenario_idx, scenario in enumerate(scenarios, 1):
        print(
            f"\n[metrics] === scenario {scenario_idx}/{total_scenarios}: {scenario.name!r} "
            f"(num_procs={scenario.num_procs}, inject={scenario.inject_failures}, "
            f"num_runs={scenario.num_runs}) ===",
            flush=True,
        )

        for run_idx in range(1, scenario.num_runs + 1):
            # --- Original run ---
            orig_key = _bench_progress_key(scenario.name, "original", run_idx)
            if orig_key in completed_keys:
                print(
                    f"[metrics] --- original run {run_idx}/{scenario.num_runs} "
                    f"[SKIPPED – already completed] ---",
                    flush=True,
                )
            else:
                print(
                    f"[metrics] --- original run {run_idx}/{scenario.num_runs} ---",
                    flush=True,
                )
                orig_metrics = _run_scenario_once(
                    scenario=scenario,
                    codebase="original",
                    run_index=run_idx,
                    source_dir=original_source_dir,
                    build_dir=original_build_dir,
                    output_dir=benchmarks_dir,
                    executable_name=original_executable_name,
                    veloc_config_name=veloc_config_name,
                )
                all_runs.append(orig_metrics)
                completed_keys.add(orig_key)
                _save_bench_progress(benchmarks_dir, all_runs)
                print(
                    f"[metrics] original run {run_idx}: elapsed={orig_metrics.elapsed_s:.2f}s",
                    flush=True,
                )

            # --- Resilient run ---
            res_key = _bench_progress_key(scenario.name, "resilient", run_idx)
            if res_key in completed_keys:
                print(
                    f"[metrics] --- resilient run {run_idx}/{scenario.num_runs} "
                    f"[SKIPPED – already completed] ---",
                    flush=True,
                )
            else:
                print(
                    f"[metrics] --- resilient run {run_idx}/{scenario.num_runs} ---",
                    flush=True,
                )
                res_metrics = _run_scenario_once(
                    scenario=scenario,
                    codebase="resilient",
                    run_index=run_idx,
                    source_dir=resilient_source_dir,
                    build_dir=resilient_build_dir,
                    output_dir=benchmarks_dir,
                    executable_name=resilient_executable_name,
                    veloc_config_name=veloc_config_name,
                    run_install=install_resilient,
                )
                all_runs.append(res_metrics)
                completed_keys.add(res_key)
                _save_bench_progress(benchmarks_dir, all_runs)
                print(
                    f"[metrics] resilient run {run_idx}: elapsed={res_metrics.elapsed_s:.2f}s, "
                    f"injected={res_metrics.injected}, attempts={res_metrics.num_attempts}",
                    flush=True,
                )

            # --- Extra approach runs (DMTCP, etc.) ---
            for approach in verified_approaches:
                a_key = _bench_progress_key(scenario.name, approach.name, run_idx)
                if a_key in completed_keys:
                    print(
                        f"[metrics] --- {approach.name} run {run_idx}/{scenario.num_runs} "
                        f"[SKIPPED – already completed] ---",
                        flush=True,
                    )
                else:
                    coord_port = dmtcp_coord_base_port + scenario_idx * 100 + run_idx
                    a_exe = approach.executable_name or resilient_executable_name
                    a_build = approach_build_dirs[approach.name]
                    print(
                        f"[metrics] --- {approach.name} run {run_idx}/{scenario.num_runs} ---",
                        flush=True,
                    )
                    a_metrics = _run_scenario_once(
                        scenario=scenario,
                        codebase=approach.name,
                        run_index=run_idx,
                        source_dir=approach.codebase_dir,
                        build_dir=a_build,
                        output_dir=benchmarks_dir,
                        executable_name=a_exe,
                        dmtcp_coord_port=coord_port,
                        install_prefix=approach.install_prefix,
                    )
                    all_runs.append(a_metrics)
                    completed_keys.add(a_key)
                    _save_bench_progress(benchmarks_dir, all_runs)
                    print(
                        f"[metrics] {approach.name} run {run_idx}: "
                        f"elapsed={a_metrics.elapsed_s:.2f}s, "
                        f"injected={a_metrics.injected}",
                        flush=True,
                    )

    summary = _build_summary(all_runs)
    results = BenchmarkResults(scenarios=scenarios, runs=all_runs, summary=summary)

    # Save final raw metrics JSON.
    raw_path = benchmarks_dir / "raw_metrics.json"
    results.save(raw_path)
    print(f"\n[metrics] raw metrics saved to {raw_path}", flush=True)

    return results
