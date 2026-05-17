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
import shutil
import statistics
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from .runner import (
    RunResult,
    ValidationError,
    clear_checkpoint_dirs,
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
    app_args: list[str] | None = None  # override app args for correctness tests
    ssim_threshold: float | None = None  # override SSIM threshold (e.g. 0.95 for MANA)


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
    # Cap on injections within ONE run.  Default 1 = the "once" scenario
    # (single mid-run failure).  This field is intentionally NOT meant to
    # be set in benchmark_configs JSON — failure frequency should be driven
    # by injection_delay (the inter-failure period); how many failures
    # actually fire is a measured statistic, not a configured cap.  Kept
    # here as a safety bound to prevent runaway injection in pathological
    # scenarios (e.g. injection_delay too small relative to recovery time).
    failures_per_run: int = 1
    # Optional per-codebase overrides for app_args.  Used when the vanilla
    # binary takes different flags than the resilient one (e.g. ROSS:
    # phold vs pholdio with --io-store=1; QMCPACK: he_simple_opt.xml vs
    # he_simple_opt_ckpt.xml).  When set, takes precedence over `app_args`
    # for that codebase.  Default None falls back to `app_args`.
    original_app_args: list[str] | None = None
    resilient_app_args: list[str] | None = None
    # Recovery-attempt args (attempt_2+) for the *resilient* codebase.
    # Many upstream-checkpointed binaries (LAMMPS, SPARTA, SW4lite,
    # Athena++, QMCPACK, Smilei) need different CLI args / input files on
    # the recovery attempt to actually restore from a checkpoint, instead
    # of starting fresh.  When this field is set the runner uses it for
    # _launch_attempt(2); when it's None the runner falls back to
    # resilient_app_args (or app_args).  Sourced from
    # tests/apps/patches/<APP>/_extra_args_recovery.txt.
    resilient_app_args_recovery: list[str] | None = None


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
    # Per-checkpoint-frame breakdown (so cadence-driven cumulative size can be
    # normalized for fair comparison).  All three default None when no
    # checkpoint state is found.
    #   checkpoint_per_frame_bytes — bytes for ONE complete checkpoint write
    #     (= the storage you'd need for a single successful recovery).  For
    #     VeloC: (total / num_versions / num_dirs).  For POSIX: total / number
    #     of distinct frames inferred by grouping filenames on stripped
    #     numeric suffix.
    #   checkpoint_frames_on_disk — how many distinct frames are retained
    #     end-of-run.  VeloC: max_versions × num_dirs.  POSIX: count of
    #     distinct stripped-basename groups.
    #   checkpoint_files_count — raw number of files matched by the scanner.
    checkpoint_per_frame_bytes: int | None = None
    checkpoint_frames_on_disk: int | None = None
    checkpoint_files_count: int | None = None
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
        # F-10: stamp every artifact with the framework version so the
        # trust gate can refuse units measured on outdated code.
        from . import FRAMEWORK_VERSION
        return {
            "framework_version": FRAMEWORK_VERSION,
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
        # Optional per-codebase overrides — let vanilla vs resilient run
        # different binaries / different inputs without forking the scenario.
        def _expand_list(raw: list | None) -> list[str] | None:
            if raw is None:
                return None
            return [_expand_arg(str(a)) for a in raw]

        scenarios.append(
            BenchmarkScenario(
                name=entry["name"],
                num_procs=int(entry["num_procs"]),
                app_args=expanded_args,
                inject_failures=bool(entry.get("inject_failures", True)),
                num_runs=num_runs,
                injection_delay=float(entry.get("injection_delay", 5.0)),
                max_attempts=int(entry.get("max_attempts", 10)),
                failures_per_run=int(entry.get("failures_per_run", 1)),
                original_app_args=_expand_list(entry.get("original_app_args")),
                resilient_app_args=_expand_list(entry.get("resilient_app_args")),
                resilient_app_args_recovery=_expand_list(
                    entry.get("resilient_app_args_recovery")
                ),
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
        # Expand env vars in app_args (e.g. ${DATA_PATH:-default}).
        raw_app_args = entry.get("app_args")
        if raw_app_args is not None:
            def _expand_approach_arg(arg: str) -> str:
                def _sub(m: re.Match) -> str:
                    return os.environ.get(m.group(1), m.group(2))
                arg = re.sub(r"\$\{(\w+):-([^}]*)\}", _sub, arg)
                return os.path.expandvars(arg)
            raw_app_args = [_expand_approach_arg(str(a)) for a in raw_app_args]

        approaches.append(
            ApproachConfig(
                name=entry["name"],
                label=entry.get("label", entry["name"]),
                enabled=True,
                approach_type=entry.get("type", "unknown"),
                codebase_dir=codebase_dir,
                executable_name=entry.get("executable_name"),
                install_prefix=entry.get("install_prefix"),
                app_args=raw_app_args,
                ssim_threshold=entry.get("ssim_threshold"),
            )
        )
    return approaches


# ---------------------------------------------------------------------------
# Checkpoint size measurement
# ---------------------------------------------------------------------------

def _measure_checkpoint_size(veloc_cfg_path: Path) -> int | None:
    """Sum the total bytes in VeloC scratch/persistent directories.

    Kept for backwards compatibility — returns just the cumulative byte total.
    For the per-frame breakdown use :func:`_measure_checkpoint_metrics`.
    """
    m = _measure_checkpoint_metrics(veloc_cfg_path)
    return m["total_bytes"] if m is not None else None


def _parse_veloc_max_versions(veloc_cfg_path: Path) -> int:
    """Return ``max_versions`` from veloc.cfg, defaulting to 3 if absent."""
    try:
        for line in veloc_cfg_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            if key.strip() == "max_versions":
                return int(val.strip())
    except (OSError, ValueError):
        pass
    return 3  # VeloC's documented default


def _measure_checkpoint_metrics(veloc_cfg_path: Path) -> dict | None:
    """Compute VeloC checkpoint metrics: total + per-frame + frame count.

    Returns ``None`` when veloc.cfg has no resolvable scratch/persistent
    dirs.  Otherwise a dict with:
        total_bytes:        sum of all bytes in scratch/persistent dirs
        files_count:        number of files
        frames_on_disk:     max_versions × num_dirs (configured retention)
        per_frame_bytes:    total_bytes / frames_on_disk (size of ONE
                            complete checkpoint write — what you'd need
                            to recover from a single checkpoint)
    """
    dirs = extract_checkpoint_dirs_from_veloc_cfg(veloc_cfg_path)
    if not dirs:
        return None
    total = 0
    file_count = 0
    for d in dirs:
        if not d.exists():
            continue
        for root, _subdirs, files in os.walk(d):
            for fname in files:
                try:
                    total += (Path(root) / fname).stat().st_size
                    file_count += 1
                except OSError:
                    pass
    max_versions = _parse_veloc_max_versions(veloc_cfg_path)
    frames_on_disk = max_versions * len([d for d in dirs if d.exists()])
    per_frame = (total // frames_on_disk) if (frames_on_disk and total) else None
    return {
        "total_bytes": total,
        "files_count": file_count,
        "frames_on_disk": frames_on_disk if frames_on_disk else None,
        "per_frame_bytes": per_frame,
    }


# Native-checkpoint conventions per app:
#   AMReX (Nyx, WarpX):   chk00010/Header, chk00010/Level_0/Cell_H, …
#   SAMRAI:               restart_linadv/restore.000000000.00/HF_data
#   CLAMR (Crux):         checkpoint_output/backupNNNNN.crx
#   Athena++:             Blast.00001.rst (loose file)
#   CoMD:                 CoMD_state-N.txt (loose file)
#   QMCPACK:              *.cont.xml (loose file)
#   Smilei:               dump-N.h5 (loose file)
#   PRK_Stencil:          prk_stencil_state-* (loose file)
#   SPPARKS:              dump.ising.N (loose file)
#   HyPar:                op_0_NNNNN.bin (loose file)
#   SW4lite:              *.sw4checkpoint, *.cycle.* HDF5 (loose file)
#
# Two routes — both apply, dedup'd by resolved path:
#   (a) anything under a top-level dir matching _BENCH_CKPT_DIR_PREFIXES
#       (chk*, plt*, restart_*, checkpoint_output, dmtcp_ckpt, ckpt*, veloc*)
#       — handles AMReX, SAMRAI, CLAMR.
#   (b) loose file whose basename matches one of _CHECKPOINT_FILE_PATTERNS
#       — handles Athena++, CoMD, QMCPACK, Smilei, PRK, SPPARKS, HyPar, SW4lite.
_CHECKPOINT_FILE_PATTERNS = (
    "ckpt", "veloc", ".rst", "checkpoint", "_state-",
    "restart.", "comd_state", "prk_stencil_state", ".sstcpt",
    "test.0", "test.1", "test.2", "test.3", "test.4",
    "test.5", "test.6", "test.7", "test.8", "test.9",
    "blast.", ".h5", ".hdf5", ".cont.xml",
    "restart_dir", "dump-", ".crx", "backup", "op_0",
    "dump.ising", "restore.",
)
# NOTE: do not put ".txt" here — CoMD reference's checkpoint format is
# CoMD_state-N.txt (POSIX text checkpoint, real state file).  stdout.txt /
# stderr.txt are still excluded via the "stdout"/"stderr" substring rules.
_CHECKPOINT_FILE_EXCLUDE = (
    "injection_success.flag", "stdout", "stderr", ".gitkeep",
    "_validate", ".log", ".yaml", ".cfg", ".json",
    "athinput", "in.", ".vtk", ".tab", ".hst",
)


def _scan_checkpoint_files(run_cwd: Path) -> list[tuple[Path, int]] | None:
    """Walk *run_cwd* and return [(file, size_bytes), ...] for every
    checkpoint artifact.

    Two-route discovery (dedup'd):
      (a) every file under a top-level dir whose name starts with a known
          checkpoint-dir prefix (chk*, plt*, restart_*, checkpoint_output,
          dmtcp_ckpt, ckpt*, veloc*) — handles AMReX (chk00010/Header) and
          SAMRAI (restart_linadv/restore.*/HF_data).
      (b) loose files whose basename matches a checkpoint-file pattern
          (.rst, _state-, dump-, .crx, …) and is not in the exclude list
          — handles Athena++, CoMD, QMCPACK, Smilei, PRK, SPPARKS, HyPar,
          SW4lite.

    Returns ``None`` if *run_cwd* doesn't exist; an empty list if it
    exists but has no checkpoint artifacts.
    """
    if not run_cwd.is_dir():
        return None
    matched: list[tuple[Path, int]] = []
    seen: set[Path] = set()

    # Route (a): checkpoint dirs at ANY depth under run_cwd — sweep each
    # matching dir's entire subtree.  Top-level dirs cover AMReX (chk*/Header)
    # and SAMRAI (restart_*/restore.*/HF_data).  Nested dirs cover WarpX
    # which writes to diags/chkpoint00000500/Level_0/Bx_fp_H — `diags/` is
    # not itself a ckpt dir but `chkpoint*` underneath is.
    try:
        for d in run_cwd.rglob("*"):
            try:
                if not d.is_dir() or d.is_symlink():
                    continue
                low = d.name.lower()
                if not any(low.startswith(p) for p in _BENCH_CKPT_DIR_PREFIXES):
                    continue
                # Skip nested ckpt dirs whose parent is itself already a
                # ckpt dir — the outer sweep already covers them.
                parent_low = d.parent.name.lower() if d.parent != run_cwd else ""
                if parent_low and any(parent_low.startswith(p) for p in _BENCH_CKPT_DIR_PREFIXES):
                    continue
                for f in d.rglob("*"):
                    try:
                        if not f.is_file() or f.is_symlink():
                            continue
                        rp = f.resolve()
                        if rp in seen:
                            continue
                        seen.add(rp)
                        matched.append((f, f.stat().st_size))
                    except OSError:
                        continue
            except OSError:
                continue
    except OSError:
        pass

    # Route (b): loose files matching checkpoint-file patterns at any depth.
    for f in run_cwd.rglob("*"):
        try:
            if not f.is_file() or f.is_symlink():
                continue
            rp = f.resolve()
            if rp in seen:
                continue
            n = f.name.lower()
            if any(e in n for e in _CHECKPOINT_FILE_EXCLUDE):
                continue
            if any(p in n for p in _CHECKPOINT_FILE_PATTERNS):
                seen.add(rp)
                matched.append((f, f.stat().st_size))
        except OSError:
            continue

    return matched


def _measure_posix_checkpoint_size(run_cwd: Path) -> int | None:
    """Sum bytes of checkpoint-pattern files under *run_cwd* for apps whose
    checkpoint logic writes to cwd-relative paths (POSIX).  Used as a fallback
    when no veloc.cfg is present (every reference app in our suite, as well
    as agent-generated baselines that opt into cwd-relative writes).

    Returns 0 (not None) when the dir exists but has no matching files, so
    raw_metrics distinguishes "no measurement attempted" (None) from
    "measured, found nothing" (0).
    """
    matched = _scan_checkpoint_files(run_cwd)
    if matched is None:
        return None
    return sum(sz for _, sz in matched)


_FRAME_SUFFIX_RE = re.compile(r"[._-](\d+)(?=(\.[a-z0-9]+)?$)", re.IGNORECASE)
_AMREX_DIR_RE = re.compile(r"^(chk|plt)(\d+)", re.IGNORECASE)


def _frame_key(path: Path, run_cwd: Path, num_procs: int = 4) -> str:
    """Return a 'frame group' key for *path*.

    A "frame" = a complete checkpoint write event.  Files written by N ranks
    at the SAME timestep belong to the same frame; files at DIFFERENT
    timesteps are different frames.

    Heuristics (in priority order):
      1. AMReX dirs ``chk00050/<rank-files>`` → key = "chk00050"
         (each chk* dir = one frame; per-rank files inside collapse).
      2. Numbered file ``<base>.<N>`` or ``<base>_<N>``:
         * If N is "small" (≤ 2 × num_procs) → looks like a rank ID.
           Files in the same group share a frame: key = "<base>".
         * If N is "large" (> 2 × num_procs) → looks like a step number.
           Each unique N is a separate frame: key = "<base>:<N>".
    """
    try:
        rel = path.relative_to(run_cwd)
    except ValueError:
        rel = path
    parts = rel.parts
    # AMReX: top-level dir like "chk00050" — keep the digits in the key.
    if parts:
        m = _AMREX_DIR_RE.match(parts[0])
        if m:
            return f"{m.group(1).lower()}{m.group(2)}"
    name = path.name
    suffix_match = _FRAME_SUFFIX_RE.search(name)
    if suffix_match is None:
        return f"{rel.parent}/{name}".lower() if rel.parent != Path(".") else name.lower()
    digits = suffix_match.group(1)
    base = name[: suffix_match.start()] + name[suffix_match.end():]
    base_key = f"{rel.parent}/{base}".lower() if rel.parent != Path(".") else base.lower()
    n = int(digits)
    rank_threshold = max(num_procs * 2, 8)  # generous floor
    if n <= rank_threshold:
        # Per-rank file at the (single) latest checkpoint — group across ranks.
        return base_key
    else:
        # Per-step file — separate frame per timestep.
        return f"{base_key}:{n}"


def _measure_combined_checkpoint_metrics(
    veloc_cfg: "Path | None",
    run_cwd: Path,
) -> dict | None:
    """Sum VeloC scratch/persistent + POSIX run_cwd checkpoint scans.

    This is the honest replacement for the prior OR-fallback (#57): the OR
    pattern silently hid coordinator-style LLM solutions that wrote a small
    VeloC marker (returns >0) AND let the application framework write the
    real recovery state to a native chk*/ dir under run_cwd (never reached
    because OR short-circuited on the first non-zero scan).

    Returns ``None`` only when neither scan finds anything; otherwise a
    summed dict with ``total_bytes``, ``files_count``, ``frames_on_disk``,
    ``per_frame_bytes``.  Per-frame size uses the larger of the two scans'
    medians (the dominant checkpoint mechanism), so a tiny VeloC marker
    doesn't drown out a real native checkpoint.
    """
    veloc_m = _measure_checkpoint_metrics(veloc_cfg) if veloc_cfg is not None else None
    posix_m = _measure_posix_checkpoint_metrics(run_cwd)

    parts = [m for m in (veloc_m, posix_m)
             if m is not None and m.get("total_bytes", 0) > 0]
    if not parts:
        # If both scanners ran but found nothing, return a zeroed dict
        # rather than None so the caller distinguishes "scanned, no
        # checkpoints" (0) from "no scan attempted" (None).
        if veloc_m is not None or posix_m is not None:
            return {"total_bytes": 0, "files_count": 0,
                    "frames_on_disk": None, "per_frame_bytes": None}
        return None

    total_bytes = sum(m["total_bytes"] for m in parts)
    files_count = sum(m.get("files_count", 0) or 0 for m in parts)
    # Frames on disk: take the max (each scanner counts its own frames).
    frames_on_disk = max(
        (m.get("frames_on_disk") or 0) for m in parts
    ) or None
    # Per-frame: dominant scanner's per_frame, so a tiny marker doesn't
    # mislead.  Falls back to total/frames when neither has a per_frame.
    per_frame_candidates = [
        m.get("per_frame_bytes") for m in parts
        if m.get("per_frame_bytes")
    ]
    per_frame = max(per_frame_candidates) if per_frame_candidates else (
        (total_bytes // frames_on_disk) if frames_on_disk else None
    )
    return {
        "total_bytes": total_bytes,
        "files_count": files_count,
        "frames_on_disk": frames_on_disk,
        "per_frame_bytes": per_frame,
    }


def _measure_posix_checkpoint_metrics(run_cwd: Path) -> dict | None:
    """Compute POSIX checkpoint metrics: total + per-frame + frame count.

    Returns ``None`` if dir doesn't exist; otherwise a dict with:
        total_bytes      — sum of matched file sizes
        files_count      — number of matched files
        frames_on_disk   — distinct frames (= recovery snapshots) inferred
                           by grouping filenames on stripped numeric suffix
        per_frame_bytes  — total_bytes / frames_on_disk (size of ONE
                           complete checkpoint write across all ranks)
    """
    matched = _scan_checkpoint_files(run_cwd)
    if matched is None:
        return None
    total = sum(sz for _, sz in matched)
    if not matched:
        return {"total_bytes": 0, "files_count": 0,
                "frames_on_disk": None, "per_frame_bytes": None}
    # Group by frame-key.  Frame count = unique groups.
    groups: dict[str, int] = {}
    for path, sz in matched:
        k = _frame_key(path, run_cwd)
        groups[k] = groups.get(k, 0) + sz
    # Heuristic for "per-frame size": median group total (robust to outliers
    # like a single large initial-state file vs many small per-step writes).
    sorted_sizes = sorted(groups.values())
    n = len(sorted_sizes)
    median = sorted_sizes[n // 2] if n else 0
    return {
        "total_bytes": total,
        "files_count": len(matched),
        "frames_on_disk": n,
        "per_frame_bytes": median,
    }


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
    app_input_subdir: str | None = None,
    extra_source_dirs: list[Path] | None = None,
    priority_source_dirs: list[Path] | None = None,
) -> RunMetrics:
    """Execute one run of *scenario* for *codebase* and collect metrics.

    *app_input_subdir* and *extra_source_dirs* mirror the correctness-mode
    runner: when set, the contents of ``source_dir/<app_input_subdir>`` are
    flattened into the per-run cwd (covers SPARTA, SPPARKS, HyPar, OpenLB,
    MMSP, QMCPACK, HPCG whose ``run.cmd`` uses ``cd <subdir> && ...``), and
    the extra source dirs are searched as fallbacks when an input file is
    missing under *source_dir* (covers LAMMPS' ``bench/in.lj_long`` which
    lives only in the vanilla source).
    """
    from .runner import _symlink_input_data

    # Per-codebase app_args override (for apps where vanilla and reference
    # take different flags or input files — ROSS pholdio needs --io-store/--io-files,
    # which the LLM-modified baseline (vanilla phold) does NOT accept).
    #
    # `resilient_app_args` is generated from `tests/apps/patches/<APP>/_extra_args.txt`
    # and is REFERENCE-ONLY by intent (per generate_benchmark_configs.py:54-58 comment
    # "upstream-only opt-in flags").  But the override applies to ANY resilient
    # codebase, which broke ROSS_baseline (LLM phold rejecting --io-store=1).
    # Restrict it to the upstream-reference resilient (source_dir under
    # tests/apps/checkpointed/), excluding the LLM-baseline resilient (under
    # build/tests_baseline/).
    is_baseline_resilient = (
        codebase == "resilient" and "tests_baseline" in str(source_dir)
    )
    if codebase == "original" and scenario.original_app_args is not None:
        effective_args = scenario.original_app_args
    elif (
        codebase == "resilient"
        and not is_baseline_resilient
        and scenario.resilient_app_args is not None
    ):
        effective_args = scenario.resilient_app_args
    else:
        effective_args = scenario.app_args

    # Recovery-attempt args (attempt_2+ in checkpoint-observed runs).  Same
    # restriction as resilient_app_args: only applied to the upstream-reference
    # resilient (NOT the LLM baseline, which has its own checkpoint protocol).
    # When None the runner falls back to *effective_args* on attempt_2.
    recovery_app_args: list[str] | None = None
    if (
        codebase == "resilient"
        and not is_baseline_resilient
        and scenario.resilient_app_args_recovery is not None
    ):
        recovery_app_args = scenario.resilient_app_args_recovery

    run_output_dir = output_dir / codebase / scenario.name / f"run_{run_index}"
    run_output_dir.mkdir(parents=True, exist_ok=True)

    # Symlink input data files referenced by relative paths in app_args
    # so they resolve from the benchmark output directory.  The subdir-flatten
    # and extra-source-dir fallback are skipped for the *original* codebase
    # (no fallback search makes sense) but kept for any other codebase.
    # priority_source_dirs is only meaningful for non-original codebases, where
    # we want to force input files from a different tree (e.g. vanilla inputs
    # winning over reference's upstream-default inputs that are tuned for a
    # smaller demo workload — see Athena++ blast: vanilla 200x200 AMR vs
    # reference 50x100 demo, mesh-block / rank mismatch on the latter).
    _symlink_input_data(
        source_dir, build_dir, run_output_dir, effective_args,
        extra_source_dirs=extra_source_dirs if codebase != "original" else None,
        input_subdir=app_input_subdir,
        priority_source_dirs=priority_source_dirs if codebase != "original" else None,
    )

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
                app_args=effective_args,
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
                app_args=effective_args,
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
        # DMTCP checkpoint size.  Per-frame metrics use POSIX scan of the
        # ckpt_dir (DMTCP writes one .dmtcp file per process per checkpoint).
        ckpt_size: int | None = dmtcp_measure_checkpoint_size(ckpt_dir)
        ckpt_metrics = _measure_posix_checkpoint_metrics(ckpt_dir) if ckpt_dir.exists() else None
        if ckpt_metrics:
            ckpt_metrics["total_bytes"] = ckpt_size  # trust dmtcp's helper

    elif codebase == "criu":
        # ── CRIU run ──────────────────────────────────────────────────
        from .criu_runner import (
            criu_run_once,
            criu_run_with_failure_injection,
            measure_checkpoint_size as criu_measure_checkpoint_size,
        )
        ckpt_dir = run_output_dir / "criu_ckpt"

        if scenario.inject_failures:
            result = criu_run_with_failure_injection(
                build_dir=build_dir,
                executable_name=executable_name,
                num_procs=scenario.num_procs,
                app_args=effective_args,
                output_dir=run_output_dir,
                ckpt_dir=ckpt_dir,
                injection_delay=scenario.injection_delay,
                run_cwd=run_output_dir,
                memory_monitor_fn=_monitor_memory_samples,
                memory_stop_event=mem_stop_event,
                memory_samples_holder=mem_samples_holder,
            )
        else:
            result = criu_run_once(
                build_dir=build_dir,
                executable_name=executable_name,
                num_procs=scenario.num_procs,
                app_args=effective_args,
                output_dir=run_output_dir,
                ckpt_dir=ckpt_dir,
                run_cwd=run_output_dir,
                memory_monitor_fn=_monitor_memory_samples,
                memory_stop_event=mem_stop_event,
                memory_samples_holder=mem_samples_holder,
            )
            if not result.succeeded:
                raise ValidationError(
                    f"CRIU benchmark run failed for scenario={scenario.name!r}, "
                    f"run={run_index}, exit code={result.exit_code}",
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exit_code=result.exit_code,
                    output_dir=run_output_dir,
                )
        ckpt_size = criu_measure_checkpoint_size(ckpt_dir)
        ckpt_metrics = _measure_posix_checkpoint_metrics(ckpt_dir) if ckpt_dir.exists() else None
        if ckpt_metrics:
            ckpt_metrics["total_bytes"] = ckpt_size

    elif scenario.inject_failures and codebase == "resilient":
        # ── Resilient run with failure injection ───────────────────────
        # Memory is monitored per-attempt inside run_with_failure_injection;
        # samples are accumulated across all attempts and returned via
        # result.memory_samples_bytes.  ``failures_per_run`` defaults to 1
        # (the "once" scenario — single mid-run failure).  For higher-frequency
        # scenarios (multi/burst), the inter-failure period is set by
        # injection_delay (e.g. T_golden/4 for multi); the runner stops
        # injecting at the first of {max_attempts, run completion}.  How many
        # failures actually fire is the measurement output, not a configured
        # cap.
        result = run_with_failure_injection(
            source_dir=source_dir,
            build_dir=build_dir,
            output_dir=run_output_dir,
            executable_name=executable_name,
            num_procs=scenario.num_procs,
            app_args=effective_args,
            recovery_app_args=recovery_app_args,
            max_attempts=scenario.max_attempts,
            injection_delay=scenario.injection_delay,
            target_failures=scenario.failures_per_run,
            run_install=run_install,
            veloc_config_name=veloc_config_name,
            require_injection=False,  # benchmarking: OK if some injections miss
            memory_monitor_fn=_monitor_memory_samples,
            memory_stop_event=mem_stop_event,
            memory_samples_holder=mem_samples_holder,
            app_input_subdir=app_input_subdir,
            extra_source_dirs=extra_source_dirs,
            priority_source_dirs=(
                priority_source_dirs if codebase != "original" else None
            ),
        )
        # Checkpoint metrics: SUM both VeloC and POSIX scans (#57).  Old
        # behavior was OR (try VeloC first, fall back to POSIX only if VeloC=0)
        # which silently hid coordinator-pattern checkpoints — apps that use
        # VeloC for a small marker AND let the framework write the actual
        # state to its own dirs (e.g., LLM Nyx solution: 1944 B VeloC marker
        # + 70 MB AMReX chk dirs in run cwd).
        ckpt_metrics = _measure_combined_checkpoint_metrics(
            veloc_cfg, run_output_dir
        )
        ckpt_size = ckpt_metrics.get("total_bytes") if ckpt_metrics else None

    else:
        # ── Clean run (no failure injection) ───────────────────────────
        # Used for original and failure-free resilient benchmarks.
        veloc_sources = [source_dir, build_dir] if codebase == "resilient" else None
        result = run_once(
            build_dir=build_dir,
            executable_name=executable_name,
            num_procs=scenario.num_procs,
            app_args=effective_args,
            output_dir=run_output_dir,
            run_cwd=run_output_dir,
            veloc_config_sources=veloc_sources,
            veloc_config_name=veloc_config_name,
            memory_monitor_fn=_monitor_memory_samples,
            memory_stop_event=mem_stop_event,
            memory_samples_holder=mem_samples_holder,
            # 30-minute cap on a single failure-free benchmark run (bumped
            # from 15-min on 2026-05-03 — D4).  PRK_Stencil reference small-once
            # cells can legitimately take 700-1700s due to CKPT_EVERY=200
            # cadence, exceeding the prior 15-min cap.  30 min covers the
            # observed 1701s outlier with margin while still catching runaway
            # processes (real apps finish in 75-1700s).
            timeout_s=1800.0,
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
        # Checkpoint metrics for resilient clean runs: SUM VeloC + POSIX (#57)
        # — see comment in failure-injection branch above.
        ckpt_metrics = (
            _measure_combined_checkpoint_metrics(veloc_cfg, run_output_dir)
            if codebase == "resilient" else None
        )
        ckpt_size = ckpt_metrics.get("total_bytes") if ckpt_metrics else None

    # F-6: fast-pass red flag.  validate.py exiting 0 with elapsed << 1s
    # almost always means the framework crashed during setup (build error,
    # missing input, env-var lookup miss) BEFORE the actual measurement
    # ran.  Recording such a sample as a "valid" 0.7s benchmark cell
    # silently corrupts the result set.  Refuse to record.
    #
    # Floor is 1.0s absolute, OR 10% of injection_delay when configured
    # (failure-injection scenarios that haven't even reached the kill
    # point in a meaningful sense).  Override with FAST_PASS_FLOOR_S env
    # var.
    _ff_env = os.environ.get("FAST_PASS_FLOOR_S")
    fast_pass_floor = (
        float(_ff_env) if _ff_env else max(
            1.0,
            0.10 * (scenario.injection_delay or 0.0),
        )
    )
    if result.elapsed_s < fast_pass_floor:
        raise ValidationError(
            f"scenario {scenario.name!r} (run {run_index}, codebase={codebase}): "
            f"recorded elapsed_s={result.elapsed_s:.3f}s < fast-pass floor "
            f"{fast_pass_floor:.3f}s.  This is almost always a framework "
            "crash during setup BEFORE the real measurement ran (build error, "
            "missing input file, exec-path lookup miss).  Recording the sample "
            "would corrupt the result set with a fake fast measurement.  "
            "Investigate the per-run stdout/stderr; re-run after fixing.  "
            "Override with FAST_PASS_FLOOR_S env var if a sub-second run is "
            "legitimate for this scenario.  (F-6 anti-fast-pass guard.)",
            output_dir=run_output_dir,
        )

    # CRIT-2 guard (F-11): if the scenario was supposed to inject failures but
    # NO injection actually fired during the resilient run, the recorded
    # numbers are pure failure-free elapsed mislabeled as failure-injected.
    # This silently happened on HPCG_reference: cached vanilla baseline was
    # 119.66s (pre-workload-pin), generator computed injection_delay=59.8s,
    # reference (with HPCG_FIXED_SETS=180) ran ~53s — injection point past
    # the run's end, `injected=False`, and the cell appeared as a normal
    # measurement.  Refuse to record; raise so the operator fixes the
    # injection_delay (or the upstream nominal_runtime cache) before the bad
    # data enters the result set.
    if (
        scenario.inject_failures
        and codebase == "resilient"
        and not result.injected
    ):
        raise ValidationError(
            f"scenario {scenario.name!r} (run {run_index}): inject_failures=True "
            f"but NO injection fired during the resilient run "
            f"(elapsed={result.elapsed_s:.2f}s, "
            f"configured injection_delay={scenario.injection_delay:.2f}s). "
            "Recording this would mislabel a failure-free measurement as "
            "failure-injected.  Fix: either reduce injection_delay below "
            "the actual run elapsed, or invalidate the stale baseline cache "
            "(build/baseline_cache/<APP>/) so the generator re-derives "
            "nominal_runtime from a fresh measurement.  See CRIT-2 / F-11 "
            "in build/_experiment_state/_user_review.md.",
            output_dir=run_output_dir,
        )

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
        checkpoint_per_frame_bytes=(ckpt_metrics or {}).get("per_frame_bytes"),
        checkpoint_frames_on_disk=(ckpt_metrics or {}).get("frames_on_disk"),
        checkpoint_files_count=(ckpt_metrics or {}).get("files_count"),
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


# F-2: workload-parity ceiling for bench cells.  Reference legitimately
# adds checkpoint I/O on top of vanilla compute, so reference_elapsed
# should be >= vanilla_elapsed but bounded.  When it exceeds this cap,
# the two paths are running different workloads (HyPar's stale patch
# raised n_iter 2.5M -> 4.5M, +80% work) and the comparison is invalid.
# Cap is per-app via tests/apps/configs/<APP>.yaml: workload_overhead_cap;
# default 1.50 (50% checkpoint overhead headroom).
_BENCH_WORKLOAD_OVERHEAD_DEFAULT = 1.50


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


def _check_workload_parity(
    summary: dict[str, Any],
    overhead_cap: float = _BENCH_WORKLOAD_OVERHEAD_DEFAULT,
) -> dict[str, dict[str, Any]]:
    """F-2 — flag bench scenarios whose reference vs vanilla elapsed diverge.

    Returns a per-scenario dict ``{scenario_name: {ratio, vanilla_median,
    reference_median, ok, cap}}`` covering only scenarios that have BOTH
    `original` and `resilient` runs.  ``ok=False`` means the workload
    parity ceiling was violated and the cell's comparison numbers are not
    apples-to-apples.

    This is a SOFT check: the function records the verdict in raw_metrics
    but does NOT raise.  Plotting / reporter code is expected to read the
    field and exclude violating cells from aggregate visualisations.  The
    forensic data is still there if someone wants to investigate.
    """
    parity: dict[str, dict[str, Any]] = {}
    for scenario_name, bucket in summary.items():
        orig = bucket.get("original", {}).get("elapsed_s", {})
        res = bucket.get("resilient", {}).get("elapsed_s", {})
        van_med = orig.get("median") if isinstance(orig, dict) else None
        ref_med = res.get("median") if isinstance(res, dict) else None
        if van_med is None or ref_med is None or van_med <= 0:
            continue
        ratio = ref_med / van_med
        parity[scenario_name] = {
            "vanilla_median_s": van_med,
            "reference_median_s": ref_med,
            "ratio_reference_over_vanilla": ratio,
            "overhead_cap": overhead_cap,
            "ok": ratio <= overhead_cap,
        }
    return parity


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


# Top-level dir-name prefixes that ARE checkpoints: deleted recursively.
# AMReX (chk*, plt*), CLAMR (checkpoint_output), SAMRAI (restart_*), and the
# generic "checkpoints"-named dirs an app may emit.  The forensic snapshot
# dir written by `validate._capture_checkpoint_artifacts` is also literally
# named "checkpoints" but lives under correctness/, NOT under per-bench-run
# dirs — so this list is safe for the bench cleanup path.
_BENCH_CKPT_DIR_PREFIXES = (
    "chk", "plt", "checkpoint_output", "restart_",
    "dmtcp_ckpt", "ckpt", "veloc",
)

# File-name patterns that are checkpoint outputs.  Mirrors
# `_measure_posix_checkpoint_metrics` PATTERNS; kept narrow so we don't
# accidentally delete app inputs / logs / metric JSON.
_BENCH_CKPT_FILE_PATTERNS = (
    "ckpt", "veloc", ".rst", "checkpoint", "_state-",
    "restart.", "comd_state", "prk_stencil_state", ".sstcpt",
    ".cont.xml", "dump-", ".crx", "backup", "op_0",
    "dump.ising", "restore.", ".sw4checkpoint",
)
# Files that match a pattern above but must NOT be deleted (recorded
# metrics, logs, configs, app input templates).
_BENCH_CKPT_FILE_EXCLUDE = (
    "stdout", "stderr", ".gitkeep",
    ".log", ".yaml", ".cfg", ".json",
    "checkpoint_metrics.json", "resilience_proof.json",
    "test_results.json", "benchmark_progress.json",
    "athinput", "in.", ".vtk", ".tab", ".hst",
    "injection_success.flag", "_validate",
)


def _delete_posix_checkpoints(run_cwd: Path) -> tuple[int, int]:
    """Delete checkpoint dirs and files under *run_cwd*. Best-effort.

    Returns (file_count_deleted, bytes_deleted).
    """
    if not run_cwd.is_dir():
        return (0, 0)
    deleted_count = 0
    deleted_bytes = 0

    # 1. Top-level checkpoint dirs (entire trees).
    try:
        for entry in run_cwd.iterdir():
            try:
                if not entry.is_dir():
                    continue
                low = entry.name.lower()
                if not any(low.startswith(p) for p in _BENCH_CKPT_DIR_PREFIXES):
                    continue
                # Sum size before removing for the log line.
                sz = 0
                fc = 0
                for f in entry.rglob("*"):
                    try:
                        if f.is_file() and not f.is_symlink():
                            sz += f.stat().st_size
                            fc += 1
                    except OSError:
                        pass
                shutil.rmtree(entry, ignore_errors=True)
                deleted_count += fc
                deleted_bytes += sz
            except OSError:
                continue
    except OSError:
        pass

    # 2. Loose checkpoint files at any depth (matched by name pattern).
    try:
        for f in run_cwd.rglob("*"):
            try:
                if not f.is_file() or f.is_symlink():
                    continue
                name = f.name.lower()
                if any(e in name for e in _BENCH_CKPT_FILE_EXCLUDE):
                    continue
                if not any(p in name for p in _BENCH_CKPT_FILE_PATTERNS):
                    continue
                sz = f.stat().st_size
                f.unlink()
                deleted_count += 1
                deleted_bytes += sz
            except OSError:
                continue
    except OSError:
        pass

    return (deleted_count, deleted_bytes)


def _cleanup_checkpoints_post_run(
    run_output_dir: Path,
    veloc_cfg_name: str | None = None,
    veloc_cfg_search_dirs: "list[Path] | None" = None,
) -> None:
    """Delete checkpoint state after a scenario run's metrics are persisted.

    Runs unconditionally for EVERY scenario run, regardless of which
    implementation produced the checkpoints (vanilla, LLM-baseline,
    upstream reference, DMTCP), to:

        (1) reclaim disk space — long sweeps otherwise accumulate gigabytes
            of native checkpoint files (AMReX chk*, CLAMR .crx, SAMRAI
            restart_*, LAMMPS restart.lj.*, …) under each run dir;

        (2) guarantee the next scenario starts fresh — VeloC scratch /
            persistent dirs (typically /tmp/<APP>_persistent) are SHARED
            across runs.  Without cleanup the next scenario could
            short-circuit recovery against a stale checkpoint from a
            previous run, contaminating the resilience proof.

    Cleans:
      * VeloC scratch/persistent dirs from veloc.cfg (if found).
      * Top-level checkpoint-pattern dirs under run_output_dir
        (chk*, plt*, restart_*, checkpoint_output, …).
      * Loose checkpoint-pattern files under run_output_dir.

    Preserves: stdout.txt, stderr.txt, every .json (metrics & progress),
    every .log, app input/config files.

    Suppress with PRESERVE_CHECKPOINTS_AFTER_RUN=1 (debugging only).
    """
    if os.environ.get("PRESERVE_CHECKPOINTS_AFTER_RUN", "") in ("1", "true", "yes"):
        return

    veloc_dirs_cleared: list[Path] = []
    if veloc_cfg_name and veloc_cfg_search_dirs:
        cfg_path: Path | None = None
        for d in veloc_cfg_search_dirs:
            cand = d / veloc_cfg_name
            if cand.exists():
                cfg_path = cand
                break
        if cfg_path is not None:
            dirs = extract_checkpoint_dirs_from_veloc_cfg(cfg_path)
            if dirs:
                clear_checkpoint_dirs(dirs)
                veloc_dirs_cleared = dirs

    posix_count, posix_bytes = _delete_posix_checkpoints(run_output_dir)

    if veloc_dirs_cleared or posix_count:
        msg_parts = []
        if veloc_dirs_cleared:
            msg_parts.append(
                f"veloc dirs cleared: {[str(d) for d in veloc_dirs_cleared]}"
            )
        if posix_count:
            msg_parts.append(
                f"posix files deleted: {posix_count} "
                f"({posix_bytes / (1024 * 1024):.1f} MB)"
            )
        print(
            f"[metrics] checkpoint cleanup ({run_output_dir.name}): "
            + "; ".join(msg_parts),
            flush=True,
        )


def _prune_run_artifacts_if_enabled(run_output_dir: Path) -> None:
    """Prune bulk app-emitted artifacts from a per-run dir to bound disk use.

    Opt-in via env var ``PRUNE_BENCH_ARTIFACTS=1`` — used for apps with very
    large per-run output (WarpX writes 30-50 GB of diags/chkpoint* per run;
    keeping all 3 nofail runs concurrently exceeds typical disk budgets).

    The metric values (elapsed_s, checkpoint_size_bytes via veloc_cfg /tmp
    paths, memory samples) are already captured in-memory and persisted to
    benchmark_progress.json by the caller BEFORE this prune runs, so removal
    of run-output bulk does NOT affect any recorded measurement.

    Kept (needed for Phase 5 trust-gate inspection):
      - stdout.txt, stderr.txt
      - any .json metadata file at run-dir top level

    Removed:
      - all subdirectories (diags/, plotfiles/, restart files, dmtcp_ckpt/, …)
      - any non-stdout/stderr file > 10 MB (large app outputs)
    """
    import os
    if os.environ.get("PRUNE_BENCH_ARTIFACTS", "") not in ("1", "true", "yes"):
        return
    if not run_output_dir.exists():
        return
    KEEP_FILES = {"stdout.txt", "stderr.txt"}
    LARGE_FILE_THRESHOLD = 10 * 1024 * 1024  # 10 MB
    for entry in run_output_dir.iterdir():
        try:
            if entry.is_dir():
                shutil.rmtree(entry)
            elif entry.is_symlink():
                entry.unlink()
            elif entry.name in KEEP_FILES or entry.suffix == ".json":
                continue
            elif entry.stat().st_size > LARGE_FILE_THRESHOLD:
                entry.unlink()
        except OSError as exc:
            print(
                f"[metrics] WARNING: prune skipped {entry}: {exc}",
                flush=True,
            )
    print(
        f"[metrics] pruned bulk artifacts under {run_output_dir} "
        f"(PRUNE_BENCH_ARTIFACTS=1)",
        flush=True,
    )


def _save_bench_progress(benchmarks_dir: Path, runs: list[RunMetrics]) -> None:
    """Persist the list of completed runs to *benchmark_progress.json*."""
    from . import FRAMEWORK_VERSION  # F-10: stamp partial-run artifacts too
    progress_path = benchmarks_dir / _BENCH_PROGRESS_FILE
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "framework_version": FRAMEWORK_VERSION,
        "runs": [r.to_dict() for r in runs],
    }
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
    original_build_cmd: str | None = None,
    resilient_build_cmd: str | None = None,
    app_input_subdir: str | None = None,
    resilient_priority_source_dirs: list[Path] | None = None,
    skip_original_codebase: bool = False,
    skip_original_inject_scenarios: bool = True,
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

    Skip flags (avoid wasted compute on duplicate measurements):
      - ``skip_original_codebase``: when True, never run the *original*
        codebase at all.  Set this in BENCH-BASELINE mode (--baseline);
        the vanilla baseline is shared from BENCH-REF's measurements.
      - ``skip_original_inject_scenarios``: when True (default), skip
        running the *original* codebase for any scenario where
        ``inject_failures=True`` (vanilla can't recover, so the framework
        would route it to a clean run = duplicate of the nofail measurement).
        Comparison reports use synthetic vanilla.once = vanilla.nofail × 1.5.

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
        elif approach.approach_type == "criu":
            from .criu_runner import check_criu_available
            if check_criu_available():
                verified_approaches.append(approach)
            else:
                print(
                    f"[metrics] WARNING: approach {approach.name!r} skipped – "
                    "CRIU not found. Install via: ./scripts/install_criu.sh",
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
    configure_and_build(original_source_dir, original_build_dir,
                        build_cmd=original_build_cmd)
    print("[metrics] building resilient codebase...", flush=True)
    configure_and_build(resilient_source_dir, resilient_build_dir,
                        run_install=install_resilient if not resilient_build_cmd else False,
                        build_cmd=resilient_build_cmd)

    # Build approach codebases and resolve their build dirs.
    # If MANA is available, build DMTCP approaches with MANA stub so
    # that MPI checkpointing works correctly.
    from .dmtcp_runner import detect_mana_root
    mana_root = detect_mana_root()
    mana_cmake_args: list[str] | None = None
    if mana_root is not None:
        mana_cmake_args = [
            "-DDMTCP_USE_MANA_STUB=ON",
            f"-DMANA_ROOT={mana_root}",
        ]

    approach_build_dirs: dict[str, Path] = {}
    for approach in verified_approaches:
        if approach.approach_type == "criu":
            # CRIU uses the original (unmodified) binary — no special build.
            a_build = original_build_dir
            print(f"[metrics] {approach.name} reuses original build (no special build)", flush=True)
        elif approach.approach_type == "dmtcp" and dmtcp_build_dir is not None and not extra_approaches:
            a_build = dmtcp_build_dir
            print(f"[metrics] building {approach.name} codebase...", flush=True)
            extra_args = mana_cmake_args if approach.approach_type == "dmtcp" else None
            configure_and_build(approach.codebase_dir, a_build, cmake_extra_args=extra_args)
        else:
            a_build = build_root / approach.name
            print(f"[metrics] building {approach.name} codebase...", flush=True)
            extra_args = mana_cmake_args if approach.approach_type == "dmtcp" else None
            configure_and_build(approach.codebase_dir, a_build, cmake_extra_args=extra_args)
        approach_build_dirs[approach.name] = a_build

    total_scenarios = len(scenarios)
    for scenario_idx, scenario in enumerate(scenarios, 1):
        print(
            f"\n[metrics] === scenario {scenario_idx}/{total_scenarios}: {scenario.name!r} "
            f"(num_procs={scenario.num_procs}, inject={scenario.inject_failures}, "
            f"num_runs={scenario.num_runs}) ===",
            flush=True,
        )

        # Decide whether to run the *original* codebase for this scenario.
        # See run_benchmark_sweep docstring for skip-flag semantics.
        skip_original_for_this = (
            skip_original_codebase
            or (skip_original_inject_scenarios and scenario.inject_failures)
        )

        for run_idx in range(1, scenario.num_runs + 1):
            # --- Original run ---
            orig_key = _bench_progress_key(scenario.name, "original", run_idx)
            if skip_original_for_this:
                _why = ("baseline-mode (vanilla measured by BENCH-REF)" if skip_original_codebase
                        else "inject_failures=True (vanilla.once is synthetic = vanilla.nofail × 1.5)")
                print(
                    f"[metrics] --- original run {run_idx}/{scenario.num_runs} "
                    f"[SKIPPED – {_why}] ---",
                    flush=True,
                )
            elif orig_key in completed_keys:
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
                    app_input_subdir=app_input_subdir,
                )
                all_runs.append(orig_metrics)
                completed_keys.add(orig_key)
                _save_bench_progress(benchmarks_dir, all_runs)
                _orig_run_dir = benchmarks_dir / "original" / scenario.name / f"run_{run_idx}"
                _prune_run_artifacts_if_enabled(_orig_run_dir)
                _cleanup_checkpoints_post_run(
                    run_output_dir=_orig_run_dir,
                    veloc_cfg_name=veloc_config_name,
                    veloc_cfg_search_dirs=[original_source_dir, original_build_dir],
                )
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
                    app_input_subdir=app_input_subdir,
                    extra_source_dirs=[original_source_dir],
                    priority_source_dirs=resilient_priority_source_dirs,
                )
                all_runs.append(res_metrics)
                completed_keys.add(res_key)
                _save_bench_progress(benchmarks_dir, all_runs)
                _res_run_dir = benchmarks_dir / "resilient" / scenario.name / f"run_{run_idx}"
                _prune_run_artifacts_if_enabled(_res_run_dir)
                _cleanup_checkpoints_post_run(
                    run_output_dir=_res_run_dir,
                    veloc_cfg_name=veloc_config_name,
                    veloc_cfg_search_dirs=[resilient_source_dir, resilient_build_dir],
                )
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
                        app_input_subdir=app_input_subdir,
                        extra_source_dirs=[original_source_dir],
                    )
                    all_runs.append(a_metrics)
                    completed_keys.add(a_key)
                    _save_bench_progress(benchmarks_dir, all_runs)
                    _appr_run_dir = benchmarks_dir / approach.name / scenario.name / f"run_{run_idx}"
                    _prune_run_artifacts_if_enabled(_appr_run_dir)
                    _cleanup_checkpoints_post_run(
                        run_output_dir=_appr_run_dir,
                        veloc_cfg_name=veloc_config_name,
                        veloc_cfg_search_dirs=[approach.codebase_dir, a_build],
                    )
                    print(
                        f"[metrics] {approach.name} run {run_idx}: "
                        f"elapsed={a_metrics.elapsed_s:.2f}s, "
                        f"injected={a_metrics.injected}",
                        flush=True,
                    )

    summary = _build_summary(all_runs)
    # F-2: workload-parity ceiling per scenario.  Result lives in summary
    # so downstream reporter / plotter can decide whether to exclude
    # violating cells from aggregate views.
    parity = _check_workload_parity(summary)
    if parity:
        summary["_workload_parity"] = parity
        bad = [(k, v) for k, v in parity.items() if not v.get("ok")]
        if bad:
            for k, v in bad:
                print(
                    f"[metrics] WARN F-2 workload parity VIOLATION on {k!r}: "
                    f"reference/vanilla={v['ratio_reference_over_vanilla']:.3f}× "
                    f"> cap {v['overhead_cap']:.2f}× "
                    f"(vanilla={v['vanilla_median_s']:.2f}s, "
                    f"reference={v['reference_median_s']:.2f}s).  "
                    "Cell numbers are not apples-to-apples; exclude from aggregate plots.",
                    flush=True,
                )
    results = BenchmarkResults(scenarios=scenarios, runs=all_runs, summary=summary)

    # Save final raw metrics JSON.
    raw_path = benchmarks_dir / "raw_metrics.json"
    results.save(raw_path)
    print(f"\n[metrics] raw metrics saved to {raw_path}", flush=True)

    return results
