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
import os
import random
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

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


PERTURBATION_METHODS = ("regex_replace", "app_arg_override", "env_var_set")


@dataclass
class PerturbationSpec:
    """How to apply a random input perturbation for cold-replay detection.

    The perturbation is a small, deterministic-from-seed change to one input
    parameter of the app. It must (a) change the output meaningfully so the
    validator can distinguish honest recovery from cold-start replay running
    under the perturbed input, (b) not crash the binary, (c) not shift
    execution time by more than ~5% so the slope test stays valid.

    See plan: /home/ndhai/.claude/plans/tranquil-napping-meerkat.md.
    """
    method: str  # one of PERTURBATION_METHODS
    value_range: tuple[float, float] | tuple[int, int]
    # regex_replace only
    file: str | None = None
    pattern: str | None = None
    replacement_template: str | None = None
    # app_arg_override only
    arg_index: int | None = None
    # env_var_set only
    env_var: str | None = None
    # calibration metadata (set by perturbation_calibrator.py)
    calibration: dict = field(default_factory=dict)
    reason: str | None = None  # populated when method=='disabled' (perturbation: null)


def _parse_perturbation(raw: object) -> PerturbationSpec | None:
    """Parse the YAML ``perturbation:`` block into a :class:`PerturbationSpec`.

    Returns ``None`` if the key is absent or explicitly null. Raises
    ``ValueError`` on malformed input so the caller (load_cell) fails loudly
    rather than silently dropping the perturbation.
    """
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"perturbation must be a mapping, got {type(raw).__name__}")
    method = raw.get("method")
    if method == "disabled":
        # Explicit disabled marker with a reason — used when calibration
        # determines no safe knob exists for this app. Falls back to legacy
        # validator path.
        return PerturbationSpec(
            method="disabled",
            value_range=(0, 0),
            reason=str(raw.get("reason", "no reason given")),
        )
    if method not in PERTURBATION_METHODS:
        raise ValueError(
            f"perturbation.method must be one of {PERTURBATION_METHODS} "
            f"or 'disabled', got {method!r}"
        )
    vr = raw.get("value_range")
    if not (isinstance(vr, (list, tuple)) and len(vr) == 2):
        raise ValueError("perturbation.value_range must be a 2-element list [lo, hi]")
    lo, hi = vr[0], vr[1]
    if lo >= hi:
        raise ValueError(f"perturbation.value_range lo({lo}) must be < hi({hi})")
    spec = PerturbationSpec(
        method=method,
        value_range=(lo, hi),
        file=raw.get("file"),
        pattern=raw.get("pattern"),
        replacement_template=raw.get("replacement_template"),
        arg_index=raw.get("arg_index"),
        env_var=raw.get("env_var"),
        calibration=dict(raw.get("calibration", {})),
    )
    # Method-specific required-field validation.
    if method == "regex_replace":
        for fname in ("file", "pattern", "replacement_template"):
            if not getattr(spec, fname):
                raise ValueError(
                    f"perturbation.method=regex_replace requires '{fname}'"
                )
        if "{value" not in spec.replacement_template:
            raise ValueError(
                "perturbation.replacement_template must contain a '{value}' "
                "placeholder (format specs like '{value:.4f}' also accepted)"
            )
    elif method == "app_arg_override":
        if spec.arg_index is None:
            raise ValueError(
                "perturbation.method=app_arg_override requires 'arg_index'"
            )
    elif method == "env_var_set":
        if not spec.env_var:
            raise ValueError(
                "perturbation.method=env_var_set requires 'env_var'"
            )
    return spec


def resolve_perturbation_value(spec: PerturbationSpec, seed: int) -> Union[int, float]:
    """Resolve the random perturbation value deterministically from ``seed``.

    Int value_range -> randint (inclusive); float value_range -> uniform.
    The same seed always yields the same value (essential for the perturbed
    leg of the failure-injected run to match the leg of the failure-free run).
    """
    if spec.method == "disabled":
        raise ValueError("cannot resolve value for disabled perturbation spec")
    rng = random.Random(seed)
    lo, hi = spec.value_range
    if isinstance(lo, int) and isinstance(hi, int):
        return rng.randint(lo, hi)
    return rng.uniform(float(lo), float(hi))


def apply_perturbation(
    spec: PerturbationSpec,
    value: Union[int, float],
    cwd: Path,
    source_dir: Path,
    app_args: list[str],
    env: dict,
) -> tuple[list[str], dict, Path | None]:
    """Apply the perturbation to one of {input file, app_args, env}.

    Returns ``(modified_app_args, modified_env, modified_file_or_None)``.

    For ``regex_replace``: reads ``source_dir / spec.file`` (or follows the
    symlink in ``cwd / spec.file`` to find the original), applies the regex
    substitution, writes the modified copy to ``cwd / spec.file`` (replacing
    any symlink). Source files are NEVER modified.

    For ``app_arg_override``: returns a new app_args list with
    ``app_args[spec.arg_index]`` replaced by ``str(value)``.

    For ``env_var_set``: returns a new env dict with ``env[spec.env_var]``
    set to ``str(value)``.
    """
    if spec.method == "disabled":
        return list(app_args), dict(env), None

    new_args = list(app_args)
    new_env = dict(env)
    modified_file: Path | None = None

    if spec.method == "regex_replace":
        target_in_cwd = cwd / spec.file
        # Materialize any symlinked ancestor between `cwd` and the
        # target file BEFORE reading or writing — otherwise an
        # innocuous-looking unlink()+write_text() at `cwd/<spec.file>`
        # would resolve through a directory symlink and modify the
        # vanilla source tree (silent contamination of
        # tests/apps/vanillas/<APP>/...).  The runner sets up
        # cwd/<input_subdir> as a directory-level symlink to
        # source_dir/<input_subdir> via _symlink_input_data; any
        # spec.file under that subdir would trigger the bug.
        try:
            rel_parts = target_in_cwd.relative_to(cwd).parts[:-1]
        except ValueError:
            rel_parts = ()
        # Walk top-down from cwd toward the file's directory; first
        # symlinked ancestor encountered is replaced with a real dir
        # whose children re-symlink back to the original source.  Once
        # one ancestor is materialized, deeper ancestors are also real
        # directories (or symlinks rooted under the new real dir,
        # which means they no longer leak out of cwd).
        cur = cwd
        for part in rel_parts:
            cur = cur / part
            if cur.is_symlink():
                link_target = cur.resolve()
                cur.unlink()
                cur.mkdir(parents=True, exist_ok=True)
                if link_target.is_dir():
                    for entry in link_target.iterdir():
                        dst = cur / entry.name
                        if dst.exists() or dst.is_symlink():
                            continue
                        dst.symlink_to(entry)

        # Resolve the source content via either the cwd file (now safe
        # to read since ancestors are materialized) or source_dir.
        if target_in_cwd.is_symlink():
            source_path = target_in_cwd.resolve()
        elif target_in_cwd.exists():
            source_path = target_in_cwd
        else:
            source_path = source_dir / spec.file
        if not source_path.exists():
            raise FileNotFoundError(
                f"perturbation target file not found: {source_path}"
            )
        content = source_path.read_text()
        replacement = spec.replacement_template.format(value=value)
        new_content, n_subs = re.subn(spec.pattern, replacement, content, count=1)
        if n_subs == 0:
            raise ValueError(
                f"perturbation regex {spec.pattern!r} did not match anything "
                f"in {source_path}"
            )
        # Write modified copy into cwd, replacing any existing symlink.
        if target_in_cwd.is_symlink() or target_in_cwd.exists():
            target_in_cwd.unlink()
        target_in_cwd.parent.mkdir(parents=True, exist_ok=True)
        target_in_cwd.write_text(new_content)
        modified_file = target_in_cwd

    elif spec.method == "app_arg_override":
        if spec.arg_index >= len(new_args):
            raise IndexError(
                f"perturbation.arg_index={spec.arg_index} out of range for "
                f"app_args of length {len(new_args)}"
            )
        new_args[spec.arg_index] = str(value)

    elif spec.method == "env_var_set":
        new_env[spec.env_var] = str(value)

    return new_args, new_env, modified_file


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
    # Input perturbation (None for legacy / un-perturbed apps)
    perturbation: PerturbationSpec | None = None


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
        perturbation=_parse_perturbation(cfg.get("perturbation")),
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
