"""
app_config.py — single source of truth loader for per-app configuration.

Resolves a (size, frequency) cell into the effective config used by audit /
benchmark / iter runs.  Reads the unified YAML at tests/apps/configs/<APP>.yaml.

Usage:
    from validation.veloc.app_config import load_cell

    cell = load_cell("CoMD", size="small", frequency="once")
    cell.app_args              # ["-x", "80", ...]
    cell.injection_delay_s     # nominal_runtime × delay_fraction
    cell.failures_count_target # 1
    cell.wallclock_cap_s       # nominal_runtime × wallclock_cap_factor
    cell.num_runs              # benchmark.num_runs_per_cell

The unified YAML schema is the single source of truth; legacy app.yaml and
benchmark_configs/<APP>.json are deprecated wrappers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIGS_DIR = REPO_ROOT / "tests" / "apps" / "configs"
FREQUENCIES_FILE = CONFIGS_DIR / "_frequencies.yaml"
BASELINE_CACHE = REPO_ROOT / "build" / "baseline_cache"

VALID_SIZES = ("validation", "small", "medium", "large")
VALID_FREQS = ("nofail", "once", "multi", "burst")


def load_frequencies() -> dict:
    """Load the shared failure-injection frequency taxonomy (single source of
    truth — applies uniformly to ALL apps)."""
    return yaml.safe_load(FREQUENCIES_FILE.read_text())["frequencies"]


@dataclass
class AppCell:
    """Effective config for one (app, size, frequency) cell."""
    app: str
    size: str
    frequency: str
    # Build / run
    mpi_ranks: int
    build_cmd: str
    executable: str
    input_subdir: str | None
    app_args: list[str]
    # Comparison
    comparison: dict
    # Runtime hints
    nominal_runtime_s: float | None
    wallclock_cap_s: float | None
    # Failure injection (None when frequency=nofail)
    inject_failures: bool
    injection_delay_s: float | None
    failures_count_target: int | None
    # Benchmark
    num_runs: int


def _baseline_elapsed(app: str) -> float | None:
    meta = BASELINE_CACHE / app / "ground_truth_meta.json"
    if meta.exists():
        try:
            return float(json.loads(meta.read_text())["elapsed_s"])
        except (KeyError, ValueError, json.JSONDecodeError):
            return None
    return None


def load_unified(app: str) -> dict:
    """Load the raw unified config dict for app."""
    f = CONFIGS_DIR / f"{app}.yaml"
    if not f.exists():
        raise FileNotFoundError(f"No unified config for {app}: {f}")
    return yaml.safe_load(f.read_text())


def list_apps() -> list[str]:
    """All apps with a unified config (excludes shared meta files like _frequencies.yaml)."""
    return sorted(p.stem for p in CONFIGS_DIR.glob("*.yaml") if not p.name.startswith("_"))


def load_cell(app: str, size: str = "validation", frequency: str = "nofail") -> AppCell:
    """Resolve a (size, frequency) cell into effective parameters.

    nominal_runtime_s comes from (in priority order):
      1. measured baseline_cache/<APP>/ground_truth_meta.json (most accurate)
      2. cfg.sizes[size].nominal_runtime_s (manual estimate)
      3. None (caller must estimate)

    Raises ValueError if size/frequency invalid OR if the cell has no app_args
    (e.g. medium/large not yet defined for this app).
    """
    if size not in VALID_SIZES:
        raise ValueError(f"size must be one of {VALID_SIZES}, got {size!r}")
    if frequency not in VALID_FREQS:
        raise ValueError(f"frequency must be one of {VALID_FREQS}, got {frequency!r}")

    cfg = load_unified(app)
    sz = cfg["sizes"].get(size, {})
    # Frequencies are now sourced from the SHARED _frequencies.yaml — apps no
    # longer carry their own frequency definitions.
    fq = load_frequencies().get(frequency, {})

    app_args = sz.get("app_args")
    if app_args is None:
        raise ValueError(
            f"{app}.{size} has no app_args defined yet (TODO: "
            f'{sz.get("description", "no description")})'
        )

    # nominal runtime: prefer measured baseline (only meaningful for size=validation
    # since baseline_cache is populated by the validation-size audit)
    nominal = None
    if size == "validation":
        nominal = _baseline_elapsed(app) or sz.get("nominal_runtime_s")
    else:
        nominal = sz.get("nominal_runtime_s")

    cap_factor = float(cfg.get("wallclock_cap_factor", 3.0))
    wallclock_cap_s = nominal * cap_factor if nominal else None

    inject = bool(fq.get("inject_failures", False))
    delay_s = None
    target = None
    if inject:
        delay_fraction = float(fq.get("delay_fraction", 0.5))
        delay_s = nominal * delay_fraction if nominal else None
        target = int(fq.get("failures_count_target", 1))

    return AppCell(
        app=app,
        size=size,
        frequency=frequency,
        mpi_ranks=int(cfg.get("mpi_ranks", 4)),
        build_cmd=cfg.get("build", {}).get("cmd", ""),
        executable=cfg.get("executable", ""),
        input_subdir=cfg.get("input_subdir"),
        app_args=list(app_args),
        comparison=dict(cfg.get("comparison", {})),
        nominal_runtime_s=nominal,
        wallclock_cap_s=wallclock_cap_s,
        inject_failures=inject,
        injection_delay_s=delay_s,
        failures_count_target=target,
        num_runs=int(cfg.get("benchmark", {}).get("num_runs_per_cell", 3)),
    )


def matrix_for_app(app: str) -> list[AppCell | tuple[str, str, str]]:
    """Return all 16 cells for an app (those with TODO app_args returned as
    (size, freq, 'TODO: <reason>') tuples)."""
    out = []
    for size in VALID_SIZES:
        for freq in VALID_FREQS:
            try:
                out.append(load_cell(app, size, freq))
            except ValueError as e:
                out.append((size, freq, f"TODO: {str(e)[:80]}"))
    return out
