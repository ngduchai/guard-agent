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


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

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
    peak_memory_bytes: int | None = None

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

def load_benchmark_config(config_path: Path) -> list[BenchmarkScenario]:
    """Parse a JSON benchmark config file into a list of BenchmarkScenario objects.

    Expected JSON schema::

        {
          "scenarios": [
            {
              "name": "small-4procs-no-failure",
              "num_procs": 4,
              "app_args": ["data.h5", "294.078", "3", "2", "0", "2"],
              "inject_failures": false,
              "num_runs": 3,
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
        scenarios.append(
            BenchmarkScenario(
                name=entry["name"],
                num_procs=int(entry["num_procs"]),
                app_args=expanded_args,
                inject_failures=bool(entry.get("inject_failures", True)),
                num_runs=int(entry.get("num_runs", 3)),
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

_RECOVERY_PATTERNS = [
    # VeloC log lines (heuristic – adjust as VeloC output evolves)
    re.compile(r"[Rr]estart.*?completed.*?(\d+(?:\.\d+)?)\s*s", re.IGNORECASE),
    re.compile(r"[Rr]ecovery.*?(\d+(?:\.\d+)?)\s*s", re.IGNORECASE),
    re.compile(r"[Rr]estarted.*?in\s+(\d+(?:\.\d+)?)\s*s", re.IGNORECASE),
]


def _parse_recovery_time(stdout: str) -> float | None:
    """Heuristic: search VeloC stdout for restart/recovery timing lines."""
    for line in stdout.splitlines():
        for pattern in _RECOVERY_PATTERNS:
            m = pattern.search(line)
            if m:
                try:
                    return float(m.group(1))
                except (ValueError, IndexError):
                    pass
    return None


# ---------------------------------------------------------------------------
# Peak memory monitoring
# ---------------------------------------------------------------------------

def _monitor_peak_memory(pid: int, result_holder: list[int | None], interval: float = 0.5) -> None:
    """Poll the RSS of *pid* every *interval* seconds; store peak in result_holder[0]."""
    try:
        import psutil
    except ImportError:
        result_holder[0] = None
        return

    peak = 0
    try:
        proc = psutil.Process(pid)
        while True:
            try:
                rss = proc.memory_info().rss
                if rss > peak:
                    peak = rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
            time.sleep(interval)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    result_holder[0] = peak if peak > 0 else None


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

    # Start memory monitor in a background thread.
    peak_mem_holder: list[int | None] = [None]

    if scenario.inject_failures and codebase == "resilient":
        # Resilient run with failure injection.
        result: RunResult = run_with_failure_injection(
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
        )
    else:
        # Clean run (no failure injection) – used for both original and
        # failure-free resilient benchmarks.
        # For the resilient codebase, ensure veloc.cfg is present in the CWD.
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

    # Checkpoint size (post-run).
    ckpt_size: int | None = None
    if veloc_cfg is not None:
        ckpt_size = _measure_checkpoint_size(veloc_cfg)

    # Recovery time (from stdout).
    recovery_time = _parse_recovery_time(result.stdout) if result.injected else None

    return RunMetrics(
        scenario_name=scenario.name,
        codebase=codebase,
        run_index=run_index,
        elapsed_s=result.elapsed_s,
        injected=result.injected,
        num_attempts=result.num_attempts,
        checkpoint_size_bytes=ckpt_size,
        recovery_time_s=recovery_time,
        peak_memory_bytes=peak_mem_holder[0],
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
        bucket["num_attempts"].append(run.num_attempts)

    # Replace raw lists with aggregated stats.
    for s in summary:
        for c in summary[s]:
            bucket = summary[s][c]
            for metric in list(bucket.keys()):
                bucket[metric] = _aggregate(bucket[metric])

    return summary


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
) -> BenchmarkResults:
    """Execute all scenarios for both codebases and collect RunMetrics.

    For each scenario:
      - The *original* codebase is always run without failure injection.
      - The *resilient* codebase is run with or without failure injection
        depending on ``scenario.inject_failures``.

    Each scenario is repeated ``scenario.num_runs`` times for statistical
    stability.
    """
    # Build both codebases once before the sweep.
    print("[metrics] building original codebase...", flush=True)
    configure_and_build(original_source_dir, original_build_dir)
    print("[metrics] building resilient codebase...", flush=True)
    configure_and_build(resilient_source_dir, resilient_build_dir, run_install=install_resilient)

    all_runs: list[RunMetrics] = []

    for scenario in scenarios:
        print(
            f"\n[metrics] === scenario: {scenario.name!r} "
            f"(num_procs={scenario.num_procs}, inject={scenario.inject_failures}, "
            f"num_runs={scenario.num_runs}) ===",
            flush=True,
        )

        for run_idx in range(1, scenario.num_runs + 1):
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
                output_dir=output_dir / "benchmarks",
                executable_name=original_executable_name,
                veloc_config_name=veloc_config_name,
            )
            all_runs.append(orig_metrics)
            print(
                f"[metrics] original run {run_idx}: elapsed={orig_metrics.elapsed_s:.2f}s",
                flush=True,
            )

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
                output_dir=output_dir / "benchmarks",
                executable_name=resilient_executable_name,
                veloc_config_name=veloc_config_name,
                run_install=install_resilient,
            )
            all_runs.append(res_metrics)
            print(
                f"[metrics] resilient run {run_idx}: elapsed={res_metrics.elapsed_s:.2f}s, "
                f"injected={res_metrics.injected}, attempts={res_metrics.num_attempts}",
                flush=True,
            )

    summary = _build_summary(all_runs)
    results = BenchmarkResults(scenarios=scenarios, runs=all_runs, summary=summary)

    # Save raw metrics JSON.
    raw_path = output_dir / "benchmarks" / "raw_metrics.json"
    results.save(raw_path)
    print(f"\n[metrics] raw metrics saved to {raw_path}", flush=True)

    return results
