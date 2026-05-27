#!/usr/bin/env python3
"""run_parallel_queue.py — parallel LLM-gen + serialized executor orchestrator.

Speeds up multi-app iter+bench experiments by running up to W (default 3)
OpenCode code-generation processes concurrently while serializing ALL
mpirun-bearing work (validation + benchmark) through a single executor
thread.  Host-wide OP-8 (one mpirun at a time) is preserved.

Per-app pipeline (state machine):

    NOT_STARTED
        |  (enqueue at startup)
        v
    READY_FOR_GEN  <-----------------------------------+
        |  (gen worker claims a slot)                  |
        v                                              |
    GENERATING                                         |
        |  (gen worker submits to executor queue,      |
        |   releases its slot the moment it submits)   |
        v                                              |
    QUEUED_FOR_EXECUTOR                                |
        |  (executor dequeues, runs build + validate)  |
        v                                              |
    EXECUTING ----> FAIL && iter<max --> next iter ----+
        | PASS
        v
    QUEUED_FOR_BENCH
        |  (executor dequeues, runs benchmark)
        v
    BENCHING --> DONE_PASSED

    Stall or max_iters with no PASS triggers D3 retry (up to
    1 + OPENCODE_RETRIES loop attempts); exhausting that budget -> DONE_FAILED.

Time accounting (per-app, per the user's spec):
    app_wall_s = sum over iters of (gen_wall_s + val_wall_s)
    bench_wall_s and queue_wait_s are recorded SEPARATELY for forensics
    but are NOT in app_wall_s.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import enum
import json
import os
import queue
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# --- Paths --------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent
BUILD_DIR = REPO_ROOT / "build"
ITERATIVE_LOGS = BUILD_DIR / "iterative_logs"
EXP_STATE_DIR = BUILD_DIR / "_experiment_state"
RUN_LOGS_DIR = BUILD_DIR / "run_logs"

HELPER_SH = SCRIPT_DIR / "_iter_gen.sh"
VALIDATE_SH = SCRIPT_DIR / "run_validate.sh"

# --- Control-plane files (see run_parallel_queue_ctl.py for the client) ------
# The orchestrator reads new lines appended to CONTROL_FILE during its main
# wait loop (~2s polling cadence) and writes one ack record per command to
# CONTROL_ACK_FILE.  Both files are append-only JSONL so a crash mid-write
# never corrupts past records.  Sibling files keep the control plane in the
# same dir as the pid file so dynamic-queue and orchestrator state live
# together under build/_experiment_state/.
CONTROL_FILE = EXP_STATE_DIR / "queue_control.jsonl"
CONTROL_ACK_FILE = EXP_STATE_DIR / "queue_control.ack.jsonl"

VANILLA_ROOTS = [
    REPO_ROOT / "tests" / "apps" / "vanillas",
    REPO_ROOT / "tests" / "ecp" / "vanillas",
    REPO_ROOT / "tests" / "examples" / "original",
]


# --- Per-worker opencode-DB isolation ----------------------------------------
# opencode 1.4.0 keeps its session/message store in a single SQLite DB at
# ~/.local/share/opencode/opencode.db.  Two concurrent `opencode run`
# invocations against that shared DB produce intermittent "Error: database is
# locked" crashes that exit silently with rc=0.  We sidestep this by giving
# each gen worker its own XDG_DATA_HOME (and therefore its own opencode.db)
# under /tmp/opencode_worker_<slot>/.  Shared config + vendored language
# servers are unaffected because they live under XDG_CONFIG_HOME and
# XDG_CACHE_HOME (untouched).
WORKER_DATA_ROOT_TMPL = "/tmp/opencode_worker_{slot}"

_slot_lock = threading.Lock()
_thread_slots: dict[int, int] = {}
_next_slot = [0]


def _get_worker_slot() -> int:
    """Assign each gen thread a unique slot 0..N-1, monotonically.

    ThreadPoolExecutor reuses the same N threads, so each thread calls this
    exactly once at first use and keeps its slot for the run.  The lock makes
    the dict insert + counter increment atomic across concurrent first-uses.
    """
    tid = threading.get_ident()
    with _slot_lock:
        if tid not in _thread_slots:
            _thread_slots[tid] = _next_slot[0]
            _next_slot[0] += 1
        return _thread_slots[tid]


def _cleanup_stale_worker_dirs() -> None:
    """Remove /tmp/opencode_worker_* from prior orchestrator runs at startup.

    Single-instance pid-file guarantees no other orchestrator is using these
    dirs.  Each dir is ~700MB of opencode SQLite state we no longer need.
    """
    tmp = Path("/tmp")
    if not tmp.is_dir():
        return
    for entry in tmp.iterdir():
        if entry.name.startswith("opencode_worker_") and entry.is_dir():
            with contextlib.suppress(Exception):
                shutil.rmtree(entry)


def _prewarm_worker_db(slot: int) -> None:
    """Trigger opencode's one-time DB migration for a slot's XDG_DATA_HOME.

    Without this, the first `opencode run` per slot pays a ~1s migration cost
    serialized with the others — not catastrophic but noisier in metrics.  We
    pre-warm in the main thread before the gen pool spawns so all slots are
    migration-clean before any real iter starts.
    """
    data_root = Path(WORKER_DATA_ROOT_TMPL.format(slot=slot)) / ".local" / "share"
    (data_root / "opencode").mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["XDG_DATA_HOME"] = str(data_root)
    with contextlib.suppress(Exception):
        subprocess.run(
            ["opencode", "db", "path"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=60,
        )


# --- ANTI_GAMING_DIRECTIVE ---------------------------------------------------
# KEEP IN SYNC with validation/veloc/scripts/run_iterative.sh lines 282-316.
# Both drivers must show the LLM the same highest-priority rule.  When this
# text changes, update BOTH places in the same commit.  Long-term TODO: extract
# to validation/veloc/scripts/anti_gaming_directive.txt and have both drivers
# `cat` it; deferred to keep the serial driver untouched in this commit.
ANTI_GAMING_DIRECTIVE = """================================================================================
TASK
================================================================================
This application has no checkpoint/restart support. Add one, using the
VeloC runtime library (libveloc) for persistence.

================================================================================
YOU MAY
================================================================================
- Modify any file inside this codebase directory tree (the current
  working directory and everything under it).
- Call into libveloc.
- Use read, list, glob, grep, edit, write tools directly.
- Read (read-only) any file under this external directory — it holds
  the previous attempt(s) validator output and your build logs, and you
  MUST consult it to understand exactly how/why the previous attempt
  was rejected before you start editing code:
    * /home/ndhai/diaspora/guard-agent/build/iterative_logs/
      (per-iter prompt.txt, build_output.txt, opencode_stdout.txt,
       validate_stdout.txt, validate_stderr.txt, metrics.json —
       validate_stdout.txt holds the ACTUAL failure cause: crash
       trace, recovery exit code, ratio, gate decisions; read it
       first. validate_stderr.txt is mostly resume-help boilerplate.)

================================================================================
YOU MAY NOT
================================================================================
- Modify any file outside this codebase directory tree.
- Delegate work to sub-agents.
- Take any action whose purpose is to make a validator gate pass
  without performing real state capture on checkpoint and real state
  load on restart.

================================================================================
REQUIRED RUNTIME CONFIG FILE (infrastructure, not the resilience task)
================================================================================
The VeloC runtime needs a `veloc.cfg` text file in the SOURCE TREE ROOT
(your current working directory) BEFORE the binary is launched.  The
validator parses this file BEFORE invoking mpirun to know which
directories to poll for checkpoint files.  If the file is absent, or
its scratch/persistent values are NOT absolute filesystem paths, the
validator immediately FATALs with "No VeloC checkpoint directories
resolved from veloc.cfg" and you get zero credit for the iteration.

Create it as a STATIC FILE in the tree at iteration start.  DO NOT
generate it at runtime from inside the binary (e.g. via a
`writeVelocConfig()` function called from main() before VELOC_Init):
that approach cannot pass this validator because the cfg is parsed
before mpirun launches the binary.

Concrete requirements:
  Path:          ./veloc.cfg   (in your current working directory)
  Required keys: scratch, persistent, mode
  Path rule:     scratch and persistent MUST be absolute /tmp paths
                 and MUST differ from each other.

Working example (substitute <app> with a short lowercase identifier;
the exact subdirectory names are unconstrained as long as the two
absolute paths differ):

  scratch = /tmp/<app>_veloc_scratch
  persistent = /tmp/<app>_veloc_persistent
  mode = sync

This is plumbing, not part of the resilience challenge.  Get it in
place on iteration 1 and spend your iteration budget on actual
checkpoint state capture and recovery logic instead.
================================================================================"""


# --- State machine -----------------------------------------------------------
class AppState(enum.Enum):
    NOT_STARTED = "not_started"
    READY_FOR_GEN = "ready_for_gen"
    GENERATING = "generating"
    QUEUED_FOR_EXECUTOR = "queued_for_executor"
    EXECUTING = "executing"
    QUEUED_FOR_BENCH = "queued_for_bench"
    BENCHING = "benching"
    DONE_PASSED = "done_passed"
    DONE_FAILED = "done_failed"


# An app is "active" when it owns a slot in either queue OR is currently
# being processed by a gen worker / the executor.  Adding to the same queue
# again is refused unless the user passes force=true on the ctl command —
# this is the duplicate-detection rule the dynamic-queue spec requires.
ACTIVE_APP_STATES = frozenset({
    AppState.READY_FOR_GEN,
    AppState.GENERATING,
    AppState.QUEUED_FOR_EXECUTOR,
    AppState.EXECUTING,
    AppState.QUEUED_FOR_BENCH,
    AppState.BENCHING,
})
TERMINAL_APP_STATES = frozenset({AppState.DONE_PASSED, AppState.DONE_FAILED})


@dataclasses.dataclass
class IterMetrics:
    iter: int
    gen_wall_s: float = 0.0
    val_wall_s: float = 0.0
    tokens_input: int = 0
    tokens_output: int = 0
    tokens_total: int = 0
    validation_passed: bool = False
    stall_aborted: bool = False
    # Number of in-iter stall retries that preceded THIS gen attempt
    # (0 on the first attempt of an iter, N if the prior N attempts
    # were killed by the stall-watcher).  Forensics for the discarded
    # stall attempts live in iter_<N>_stall<retry>/ archive dirs.
    stall_retries: int = 0
    gen_queue_wait_s: float = 0.0      # time from ready->gen_start
    val_queue_wait_s: float = 0.0      # time from submit-to-executor->exec_start
    gen_started_at: Optional[str] = None
    val_started_at: Optional[str] = None
    gen_exit_code: int = 0
    val_exit_code: int = 0


@dataclasses.dataclass
class LoopAttempt:
    attempt: int
    outcome: str            # "pass" | "stall" | "max_iters"
    iters_run: int
    stall_iteration: int = 0


@dataclasses.dataclass
class AppRun:
    name: str
    label: str               # e.g. "baseline" or "baseline_<MODEL_TAG>"
    app_dir: Path            # build/tests_baseline[_TAG]/<APP>
    log_dir: Path            # build/iterative_logs/<APP>_<LABEL>
    vanilla_src: Path        # tests/apps/vanillas/<APP> or alt root
    max_iters: int
    max_loop_attempts: int
    benchmark_num_runs: int

    state: AppState = AppState.NOT_STARTED
    iter: int = 0                              # current iter within active attempt
    loop_attempt: int = 1                      # current attempt number (1-based)
    per_iter: list[IterMetrics] = dataclasses.field(default_factory=list)
    prior_attempts: list[LoopAttempt] = dataclasses.field(default_factory=list)
    loop_stall_count: int = 0
    loop_max_iters_count: int = 0

    # Per-iter stall-retry counter: resets to 0 whenever a non-stall gen
    # completes (i.e. validate is at least attempted).  Each consecutive
    # stall on the same iter increments it; on hitting the cap below the
    # orchestrator transitions the app to DONE_FAILED rather than
    # restarting the loop from vanilla (user directive 2026-05-26).
    iter_stall_retry_count: int = 0
    max_iter_stall_retries: int = 2            # initialized from --opencode-retries

    bench_wall_s: float = 0.0
    bench_queue_wait_s: float = 0.0
    bench_started_at: Optional[str] = None
    bench_exit_code: int = 0

    verdict_passed: bool = False
    final_stall_aborted: bool = False
    final_stall_iteration: int = 0

    queued_for_executor_at: float = 0.0        # epoch s when last enqueued
    queued_for_gen_at: float = 0.0
    queued_for_bench_at: float = 0.0

    app_started_at: float = 0.0                # first ready_for_gen submit
    app_finished_at: float = 0.0               # entry to DONE_* (incl. bench)
    iter_loop_finished_at: float = 0.0         # iter loop concluded (excl. bench)
                                               # — matches serial run_iterative.sh
                                               # EVAL_END semantics for paper data

    def app_wall_s(self) -> float:
        """User spec: sum over iters of (gen + val), excludes bench + queue wait."""
        return sum(m.gen_wall_s + m.val_wall_s for m in self.per_iter)


# --- Subprocess helpers ------------------------------------------------------
# Module-level lock serializing the fork+exec syscall pair across orchestrator
# threads.  Without it, a gen-worker thread launching `_iter_gen.sh` at the
# same instant the executor thread launches `validate.py` produces a
# silent-no-op iter on the gen side: opencode dies in ~1.5s with rc=137, zero
# tokens, no source edits.  Observed n=3 on 2026-05-26 (SAMRAI/Nyx iter_3+
# cascade) — every no-op fired exactly when a gen Popen and a validate Popen
# raced through fork+setsid+execve at the same millisecond.  The lock is held
# only across `Popen()` (sub-millisecond), released before `proc.wait()`, so
# opencode/network-bound work still overlaps with mpirun the rest of the time.
_POPEN_FORK_LOCK = threading.Lock()


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atomic_write_json(path: Path, payload: dict) -> None:
    """Write JSON via tmp file + rename so partial files are never visible."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}.{threading.get_ident()}")
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp, path)


def _run_subprocess(
    cmd: list[str],
    *,
    env: Optional[dict] = None,
    cwd: Optional[Path] = None,
    stdout_log: Optional[Path] = None,
    stderr_log: Optional[Path] = None,
    timeout: Optional[float] = None,
) -> tuple[int, float]:
    """Run a subprocess to completion.  Returns (returncode, wall_s).

    No outer timeout is set unless the caller explicitly asks for one
    (per feedback_no_outer_timeout_on_experiments — only the script's
    OWN internal stops are allowed for experiment-bearing runs).
    """
    started = time.monotonic()
    stdout_fh = open(stdout_log, "w") if stdout_log else subprocess.DEVNULL
    stderr_fh = open(stderr_log, "w") if stderr_log else subprocess.DEVNULL
    try:
        # start_new_session=True puts the child in its own process group so
        # killpg() can reach grandchildren (mpirun → orterun → app ranks).
        # Plain proc.kill() only signals the direct child; if mpirun is the
        # direct child, its rank children survive as orphans and the wait()
        # returns but the deadlocked mpirun can stay alive — observed
        # 2026-05-24 WarpX hang where the validate timed out but mpirun PID
        # remained at ~0% CPU for 4h, wedging the host-wide mpirun lane.
        #
        # Popen is wrapped in _POPEN_FORK_LOCK to serialize fork+exec across
        # the gen-pool and executor threads — see lock declaration above for
        # the 2026-05-26 silent-no-op race.  Lock released before wait() so
        # the long-running child doesn't hold up other launches.
        with _POPEN_FORK_LOCK:
            proc = subprocess.Popen(
                cmd,
                env=env,
                cwd=str(cwd) if cwd else None,
                stdout=stdout_fh,
                stderr=stderr_fh,
                start_new_session=True,
            )
        try:
            rc = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            proc.wait()
            rc = 124
    finally:
        if stdout_fh != subprocess.DEVNULL:
            stdout_fh.close()
        if stderr_fh != subprocess.DEVNULL:
            stderr_fh.close()
    return rc, time.monotonic() - started


# --- Per-iter checkpoint cleanup (port of bash _clean_iter_checkpoints) ------
def _clean_iter_checkpoints(app_dir: Path, app_name: str, label: str) -> None:
    """Remove this iter's bulky checkpoint artefacts after validation.

    Preserves stdout.txt/stderr.txt (needed by next iter's prompt builder),
    LLM source modifications, _build/, baseline_cache/, and benchmarks/.
    Best-effort — all failures are silenced.
    """
    app_lower = app_name.lower()

    # (1) correctness/ ckpt dirs/files
    correctness_dir = BUILD_DIR / "validation_output" / f"{app_name}_{label}" / "correctness"
    if correctness_dir.is_dir():
        ckpt_dir_names = {"chkpt", "restart_", "restore."}
        ckpt_file_exts = {".veloc", ".chk", ".h5", ".hdf5"}
        for root, dirs, files in os.walk(correctness_dir, topdown=False):
            for d in list(dirs):
                # AMReX-style chk?????? / plt?????? (6-digit pad)
                if (len(d) == 9 and d.startswith("chk") and d[3:].isdigit()) \
                   or (len(d) == 9 and d.startswith("plt") and d[3:].isdigit()) \
                   or d.startswith("restart_") or d.startswith("chkpt") or d.startswith("restore."):
                    with contextlib.suppress(Exception):
                        shutil.rmtree(Path(root) / d)
            for f in files:
                p = Path(root) / f
                if (p.suffix in ckpt_file_exts or
                        f == "validation_output.bin" or
                        f.startswith("restart.")):
                    with contextlib.suppress(Exception):
                        p.unlink()

    # (2) /tmp dirs that include the app-name (lowercase) AND a ckpt-like suffix
    tmp_dir = Path("/tmp")
    if tmp_dir.is_dir():
        for entry in tmp_dir.iterdir():
            name = entry.name.lower()
            if app_lower not in name:
                continue
            if not any(s in name for s in
                       ("veloc", "persistent", "scratch", "chk",
                        "restart", "ckpt", "backup")):
                continue
            if entry.is_dir():
                with contextlib.suppress(Exception):
                    shutil.rmtree(entry)

    # (3) In-tree ckpts at app_dir's top level (maxdepth=1)
    if app_dir.is_dir():
        for entry in app_dir.iterdir():
            n = entry.name
            keep = False
            if (len(n) == 9 and n.startswith("chk") and n[3:].isdigit()) \
               or (len(n) == 9 and n.startswith("plt") and n[3:].isdigit()) \
               or n.startswith("restart_") or n.endswith(".veloc") \
               or n == "validation_output.bin":
                keep = True
            if keep:
                with contextlib.suppress(Exception):
                    if entry.is_dir():
                        shutil.rmtree(entry)
                    else:
                        entry.unlink()


def _resolve_vanilla(app_name: str) -> Optional[Path]:
    for root in VANILLA_ROOTS:
        cand = root / app_name
        if cand.is_dir():
            return cand
    return None


# --- Crash-immediate resume classification -----------------------------------
def _metrics_complete(metrics_path: Path) -> bool:
    """True iff iter_N/metrics.json exists and contains a post-validate record.

    The orchestrator writes metrics.json only AFTER validate finishes (rc is
    captured + validation_passed populated; see _do_one_validation). A missing
    file or one lacking ``validation_passed`` signals the iter was interrupted
    mid-validate.
    """
    if not metrics_path.exists():
        return False
    try:
        data = json.loads(metrics_path.read_text())
    except Exception:
        return False
    return isinstance(data, dict) and "iter" in data and "validation_passed" in data


def _gen_metrics_complete(gen_metrics_path: Path) -> bool:
    """True iff iter_N/metrics_gen.json exists and contains a gen-complete record.

    The opencode helper writes metrics_gen.json only AFTER the LLM gen step
    finishes (gen_wall_s populated). A missing file or one lacking
    ``gen_wall_s`` signals the iter was interrupted mid-gen, so the source
    tree under app_dir may be a partial LLM edit and is not safe to reuse.
    """
    if not gen_metrics_path.exists():
        return False
    try:
        data = json.loads(gen_metrics_path.read_text())
    except Exception:
        return False
    return isinstance(data, dict) and "gen_wall_s" in data


def _classify_iter_crash(log_dir: Path) -> dict:
    """Classify the resume disposition of the highest iter_N/ dir in *log_dir*.

    Returns one of:
      {"mode": "clean"}                            — no crash signal
      {"mode": "mid_gen",      "iter": N}          — gen interrupted (no
                                                     metrics_gen.json); source
                                                     tree is suspect, wipe +
                                                     restart iter 1
      {"mode": "mid_validate", "iter": N}          — gen complete, validate
                                                     interrupted (no
                                                     metrics.json); LLM iter
                                                     completed so source tree
                                                     is a valid checkpoint —
                                                     re-queue this iter for
                                                     validation only

    "mid_validate" preserves prior completed iters and the latest gen output.
    "mid_gen" archives ALL logs because we cannot restore the source tree to
    the post-iter-{N-1} state (no snapshotting at iter boundaries).
    """
    if not log_dir.exists():
        return {"mode": "clean"}
    iters: list[int] = []
    for d in log_dir.iterdir():
        if not d.is_dir() or not d.name.startswith("iter_"):
            continue
        try:
            iters.append(int(d.name[len("iter_"):]))
        except ValueError:
            continue
    if not iters:
        return {"mode": "clean"}
    last = max(iters)
    iter_dir = log_dir / f"iter_{last}"
    if _metrics_complete(iter_dir / "metrics.json"):
        return {"mode": "clean"}
    if _gen_metrics_complete(iter_dir / "metrics_gen.json"):
        return {"mode": "mid_validate", "iter": last}
    return {"mode": "mid_gen", "iter": last}


def _archive_crashed_logs(log_dir: Path) -> Optional[Path]:
    """Move *log_dir* to a timestamped CRASHED archive sibling, preserving
    prior iter logs + result.json for forensics + paper data.  Returns the
    archive path, or None if log_dir does not exist.  After the move the
    caller is responsible for re-creating an empty log_dir.
    """
    if not log_dir.exists():
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = log_dir.with_name(f"{log_dir.name}.CRASHED_{stamp}")
    suffix = 1
    while archive.exists():
        archive = log_dir.with_name(f"{log_dir.name}.CRASHED_{stamp}_{suffix}")
        suffix += 1
    shutil.move(str(log_dir), str(archive))
    return archive


def _load_partial_gen_iter(iter_log_dir: Path, iter_n: int) -> "IterMetrics":
    """Reconstruct IterMetrics with only the gen fields populated.  Used on
    mid_validate resume: helper wrote metrics_gen.json but the orchestrator
    never wrote the post-validate metrics.json.
    """
    m = IterMetrics(iter=iter_n)
    gp = iter_log_dir / "metrics_gen.json"
    if gp.exists():
        try:
            data = json.loads(gp.read_text())
            m.gen_wall_s = float(data.get("gen_wall_s", 0.0))
            m.tokens_input = int(data.get("tokens_input", 0))
            m.tokens_output = int(data.get("tokens_output", 0))
            m.tokens_total = int(data.get("tokens_total", 0))
            m.stall_aborted = bool(data.get("stall_aborted", False))
        except Exception:
            pass
    return m


def _reset_app_run_after_wipe(app: "AppRun") -> None:
    """Reset bookkeeping on *app* so the next gen iter behaves like a fresh
    cold-start (iter=0, attempt 1, no per_iter, no prior_attempts, bench
    zeroed).  Does NOT touch app_dir / log_dir / vanilla_src / max_iters /
    max_loop_attempts / benchmark_num_runs (those are immutable config).

    Crashes do NOT burn a retry attempt — per project policy, an
    infrastructure crash is not an LLM-level failure.
    """
    app.state = AppState.NOT_STARTED
    app.iter = 0
    app.loop_attempt = 1
    app.per_iter = []
    app.prior_attempts = []
    app.loop_stall_count = 0
    app.loop_max_iters_count = 0
    app.iter_stall_retry_count = 0
    app.bench_wall_s = 0.0
    app.bench_queue_wait_s = 0.0
    app.bench_started_at = None
    app.bench_exit_code = 0
    app.verdict_passed = False
    app.final_stall_aborted = False
    app.final_stall_iteration = 0
    app.queued_for_executor_at = 0.0
    app.queued_for_gen_at = 0.0
    app.queued_for_bench_at = 0.0
    app.app_started_at = 0.0
    app.app_finished_at = 0.0
    app.iter_loop_finished_at = 0.0


def _refresh_app_dir(app: AppRun) -> None:
    """Wipe app_dir and re-copy vanilla.  Matches run_iterative.sh REFRESH."""
    if app.app_dir.exists():
        # Defensive chmod for pre-2026-05-22 read-only locks on subprojects.
        with contextlib.suppress(Exception):
            subprocess.run(["chmod", "-R", "u+w", str(app.app_dir)],
                           check=False, stderr=subprocess.DEVNULL)
        shutil.rmtree(app.app_dir, ignore_errors=True)
    app.app_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(app.vanilla_src, app.app_dir, symlinks=True)


# --- Per-iter git-snapshot helpers ------------------------------------------
# Used to make stall-retries safe: snapshot the tree at iter start, hard-reset
# on stall so the retry begins from a clean iter-N-start state (rolling back
# any partial mid-stall edits the LLM applied before the watchdog killed it).
# The .git dir lives inside app_dir (build/tests_<label>/<APP>/) — vanilla
# source under tests/apps/vanillas/ is never touched.

def _git(app_dir: Path, *args: str) -> tuple[int, str]:
    """Run a `git` subcommand inside app_dir.  Returns (rc, combined_output).

    Output is captured (not streamed) so a long git operation does not pollute
    the orchestrator's stdout log.  Best-effort — any failure is returned to
    the caller rather than raised, so the orchestrator can degrade gracefully
    if git is unavailable or the tree is in an unexpected state.
    """
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(app_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, out
    except FileNotFoundError:
        return 127, "git binary not found"
    except Exception as e:
        return 1, f"git invocation failed: {e!r}"


def _git_init_snapshot(app_dir: Path, message: str) -> bool:
    """Ensure app_dir is a git repo and commit current state as a snapshot.

    Idempotent: safe to call multiple times.  Returns True on success.
    Failures are logged to orchestrator stdout but never raise — the iter
    still runs even if snapshotting fails (the cost is that a subsequent
    stall cannot be cleanly rolled back).
    """
    if not app_dir.exists():
        return False

    # `git init` is idempotent.  Use --quiet to avoid noisy output for the
    # already-initialized case.
    rc, _ = _git(app_dir, "init", "--quiet")
    if rc != 0:
        print(f"[git] {app_dir.name}: init failed (rc={rc})", flush=True)
        return False

    # Set local identity so commits work without relying on global config
    # (CI containers may have no user.name/user.email).
    _git(app_dir, "config", "user.email", "orchestrator@guard-agent.local")
    _git(app_dir, "config", "user.name", "guard-agent orchestrator")

    # Stage everything (including deletions) and commit.  --allow-empty
    # handles the case where nothing changed between two consecutive
    # snapshots (e.g. iter started but LLM made no edits before stall).
    rc, out = _git(app_dir, "add", "-A")
    if rc != 0:
        print(f"[git] {app_dir.name}: add failed (rc={rc}): {out[-200:]}",
              flush=True)
        return False
    rc, out = _git(app_dir, "commit", "--allow-empty", "-q", "-m", message)
    if rc != 0:
        print(f"[git] {app_dir.name}: commit failed (rc={rc}): {out[-200:]}",
              flush=True)
        return False
    return True


def _git_reset_hard(app_dir: Path) -> bool:
    """Hard-reset the working tree to HEAD.  Returns True on success.

    Discards any uncommitted changes (i.e. the LLM's partial mid-stall edits)
    and restores the tree to the most recent _git_init_snapshot.  Untracked
    files are removed via `git clean -fdx` so newly-created files from the
    stalled iter (e.g. an unfinished new source file) also disappear.
    """
    if not (app_dir / ".git").exists():
        print(f"[git] {app_dir.name}: no .git dir — cannot reset", flush=True)
        return False
    rc, out = _git(app_dir, "reset", "--hard", "-q", "HEAD")
    if rc != 0:
        print(f"[git] {app_dir.name}: reset --hard failed (rc={rc}): {out[-200:]}",
              flush=True)
        return False
    rc, out = _git(app_dir, "clean", "-fdx", "-q")
    if rc != 0:
        # Non-fatal: reset already succeeded.  Log so the user notices.
        print(f"[git] {app_dir.name}: clean -fdx failed (rc={rc}): {out[-200:]}",
              flush=True)
    return True


# --- Prompt building (mirrors run_iterative.sh iter-1 + iter-2+ templates) ---
def _build_prompt(app: AppRun, iter_n: int) -> str:
    initial_prompt_path = app.app_dir / "prompt.txt"
    initial_prompt = initial_prompt_path.read_text() if initial_prompt_path.exists() else ""

    if iter_n == 1:
        return f"{ANTI_GAMING_DIRECTIVE}\n\n{initial_prompt}"

    prev_log = app.log_dir / f"iter_{iter_n - 1}"
    body = (
        f"{ANTI_GAMING_DIRECTIVE}\n\n"
        f"Your previous attempt was rejected by the validation pipeline. Inspect\n"
        f"the artifacts under this directory and fix the code:\n\n"
        f"  {prev_log}\n\n"
        f"It contains validate_stdout.txt (the ACTUAL failure cause:\n"
        f"crash trace, recovery exit code, ratio, gate decisions — read it\n"
        f"first), validate_stderr.txt (mostly resume-help boilerplate),\n"
        f"build_output.txt, opencode_stdout.txt, and metrics.json."
    )
    # If the previous iter hit the watchdog timeout, surface the marker
    # contents directly so the LLM cannot miss it.  Standard validate
    # stderr is often truncated mid-stream when SIGKILL fires.
    timeout_marker = prev_log / "_TIMEOUT_KILLED.txt"
    if timeout_marker.exists():
        with contextlib.suppress(Exception):
            body += "\n\n" + timeout_marker.read_text()
    return body


# --- Resume state loader -----------------------------------------------------
def _load_app_resume_state(app: "AppRun") -> dict:
    """Reconstruct AppRun state from on-disk artifacts.  Empty dict if no
    prior data exists for this app+label.

    Sources, in priority order:
      - iter_N/metrics.json   : ground truth for completed iters (written
                                immediately after each validate completes)
      - result.json           : authoritative for loop_attempt_final +
                                prior_loop_attempts (written at every
                                end-of-attempt and at drain)
      - parallel_timing.json  : auxiliary per-iter timing/queue-wait fields,
                                bench fields, and per-iter exit codes

    Returns a dict with keys:
      verdict, completed_iters, loop_attempt, prior_attempts,
      loop_stall_count, loop_max_iters_count, verdict_passed,
      exhausted_retries, bench_wall_s, bench_queue_wait_s,
      bench_started_at, bench_exit_code
    """
    log_dir = app.log_dir
    if not log_dir.exists():
        return {}

    # 1. Scan iter_*/metrics.json — only iters that completed validate are
    #    recorded here, so this is the ground truth for "what's done".
    iter_files = []
    for d in log_dir.iterdir():
        if not d.is_dir() or not d.name.startswith("iter_"):
            continue
        try:
            n = int(d.name[len("iter_"):])
        except ValueError:
            continue
        m = d / "metrics.json"
        if m.exists():
            iter_files.append((n, m))
    iter_files.sort(key=lambda t: t[0])
    if not iter_files:
        return {}

    completed: list[IterMetrics] = []
    for _, f in iter_files:
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue
        completed.append(IterMetrics(
            iter=int(data["iter"]),
            gen_wall_s=float(data.get("opencode_elapsed_s", 0.0)),
            val_wall_s=float(data.get("validation_elapsed_s", 0.0)),
            tokens_input=int(data.get("input_tokens", 0)),
            tokens_output=int(data.get("output_tokens", 0)),
            tokens_total=int(data.get("total_tokens", 0)),
            validation_passed=bool(data.get("validation_passed", False)),
            stall_aborted=bool(data.get("stall_aborted", False)),
            gen_queue_wait_s=float(data.get("gen_queue_wait_s", 0.0)),
            val_queue_wait_s=float(data.get("val_queue_wait_s", 0.0)),
        ))
    if not completed:
        return {}

    # 2. Augment per-iter rows from parallel_timing.json (started_at + exit).
    bench_wall_s = 0.0
    bench_queue_wait_s = 0.0
    bench_started_at: Optional[str] = None
    bench_exit_code = 0
    pt_path = log_dir / "parallel_timing.json"
    if pt_path.exists():
        try:
            pt = json.loads(pt_path.read_text())
            pt_by_iter = {int(p["iter"]): p for p in pt.get("per_iter", [])}
            for m in completed:
                p = pt_by_iter.get(m.iter)
                if p:
                    m.gen_started_at = p.get("gen_started_at")
                    m.val_started_at = p.get("val_started_at")
                    m.gen_exit_code = int(p.get("gen_exit_code", 0))
                    m.val_exit_code = int(p.get("val_exit_code", 0))
            bench_wall_s = float(pt.get("bench_wall_s", 0.0))
            bench_queue_wait_s = float(pt.get("bench_queue_wait_s", 0.0))
            bench_started_at = pt.get("bench_started_at")
            bench_exit_code = int(pt.get("bench_exit_code", 0))
        except Exception:
            pass

    # 3. Read result.json for loop_attempt + prior_attempts + verdict.
    loop_attempt = 1
    prior_attempts: list[LoopAttempt] = []
    loop_stall_count = 0
    loop_max_iters_count = 0
    verdict_passed = False
    verdict = "IN_PROGRESS"
    res_path = log_dir / "result.json"
    if res_path.exists():
        try:
            r = json.loads(res_path.read_text())
            loop_attempt = int(r.get("loop_attempt_final", 1))
            loop_stall_count = int(r.get("loop_stall_count", 0))
            loop_max_iters_count = int(r.get("loop_max_iters_count", 0))
            verdict_passed = bool(r.get("passed", False))
            prior_attempts = [
                LoopAttempt(
                    attempt=int(a["attempt"]),
                    outcome=str(a["outcome"]),
                    iters_run=int(a["iters_run"]),
                    stall_iteration=int(a.get("stall_iteration", 0)),
                )
                for a in r.get("prior_loop_attempts", [])
            ]
            if verdict_passed:
                verdict = "PASS"
            elif loop_attempt >= app.max_loop_attempts and prior_attempts:
                verdict = "FAIL"
        except Exception:
            pass

    exhausted_retries = (verdict == "FAIL") or (loop_attempt > app.max_loop_attempts)

    return {
        "verdict": verdict,
        "completed_iters": completed,
        "loop_attempt": loop_attempt,
        "prior_attempts": prior_attempts,
        "loop_stall_count": loop_stall_count,
        "loop_max_iters_count": loop_max_iters_count,
        "verdict_passed": verdict_passed,
        "exhausted_retries": exhausted_retries,
        "bench_wall_s": bench_wall_s,
        "bench_queue_wait_s": bench_queue_wait_s,
        "bench_started_at": bench_started_at,
        "bench_exit_code": bench_exit_code,
    }


def _apply_context_cap(prompt: str, iter_log: Path) -> str:
    """Mirror run_iterative.sh:423-431 — when OPENCODE_INPUT_TRUNC_TOKENS is
    set, pipe the prompt through validation.veloc.prompt_truncator and write
    the bookkeeping JSON to iter_log/prompt_truncation.json.  Unset env var
    returns the prompt unchanged; truncator failure returns the original
    prompt (do not crash the iter loop)."""
    if not os.environ.get("OPENCODE_INPUT_TRUNC_TOKENS", "").strip():
        return prompt
    try:
        result = subprocess.run(
            ["python3", "-m", "validation.veloc.prompt_truncator"],
            input=prompt,
            capture_output=True,
            text=True,
            env=os.environ.copy(),
            check=False,
        )
    except Exception as exc:
        print(f"[gen] prompt_truncator subprocess error: {exc!r}", flush=True)
        return prompt
    if result.returncode != 0 or not result.stdout:
        print(f"[gen] prompt_truncator rc={result.returncode} "
              f"stdout_empty={not result.stdout} — using untruncated prompt",
              flush=True)
        return prompt
    with contextlib.suppress(Exception):
        (iter_log / "prompt_truncation.json").write_text(result.stderr or "")
    return result.stdout


# --- Orchestrator -------------------------------------------------------------
class Orchestrator:
    def __init__(
        self,
        app_names: list[str],
        max_gen_workers: int,
        max_iters: int,
        benchmark_num_runs: int,
        label: str,
        opencode_retries: int,
        skip_bench: bool,
        validate_timeout_s: float = 900.0,
        resume: bool = False,
    ):
        self.max_gen_workers = max_gen_workers
        self.label = label
        self.skip_bench = skip_bench
        self.validate_timeout_s = validate_timeout_s
        self.resume = resume
        self.experiment_started_at = time.monotonic()
        self.experiment_started_at_wall = _utc_iso()

        # Per-app collision check (lowercase prefix substring containment)
        lower = [a.lower() for a in app_names]
        for i, a in enumerate(lower):
            for j, b in enumerate(lower):
                if i != j and (a in b or b in a):
                    # Same-length identical names already deduped; this catches
                    # genuine prefix collisions like "Foo" vs "FooBar" that
                    # would cause /tmp cleanup of one to wipe the other's
                    # checkpoints.
                    if a != b:
                        raise SystemExit(
                            f"Lowercase app-name prefix collision: "
                            f"'{app_names[i]}' vs '{app_names[j]}' — "
                            f"refusing to launch (would cause /tmp checkpoint cleanup collision)"
                        )

        # Resolve per-app paths + vanilla source.
        self.apps: dict[str, AppRun] = {}
        for name in app_names:
            vanilla = _resolve_vanilla(name)
            if vanilla is None:
                raise SystemExit(f"No vanilla source found for {name} under {VANILLA_ROOTS}")
            app_dir = BUILD_DIR / f"tests_{label}" / name
            log_dir = ITERATIVE_LOGS / f"{name}_{label}"
            self.apps[name] = AppRun(
                name=name,
                label=label,
                app_dir=app_dir,
                log_dir=log_dir,
                vanilla_src=vanilla,
                max_iters=max_iters,
                max_loop_attempts=1 + opencode_retries,
                max_iter_stall_retries=opencode_retries,
                benchmark_num_runs=benchmark_num_runs,
            )

        # Concurrency primitives.  Single RLock guards ALL mutable state on
        # AppRun objects + the timing index dict.  No nested-lock scenarios
        # are introduced; queue.Queue has its own internal lock and is safe
        # to call under or outside our lock.
        self.state_lock = threading.RLock()
        self.ready_for_gen: queue.Queue = queue.Queue()
        self.executor_queue: queue.Queue = queue.Queue()
        # Side-channel queue checked FIRST by the executor loop.  Lets ctl
        # add --queue exec --immediate jump the line without preempting the
        # task already running (OP-0 forbids killing running execution).
        self.executor_priority_queue: queue.Queue = queue.Queue()
        self.stop_event = threading.Event()
        self.all_done_event = threading.Event()
        self.remaining = len(self.apps)
        # Byte offset into CONTROL_FILE — only commands appended AFTER the
        # orchestrator starts are honored.  Historical commands from a
        # previous run are ignored on startup (see run() initialization).
        self._control_file_offset = 0

    # --- Public entry point --------------------------------------------------
    def run(self) -> int:
        EXP_STATE_DIR.mkdir(parents=True, exist_ok=True)
        ITERATIVE_LOGS.mkdir(parents=True, exist_ok=True)
        RUN_LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self._claim_pid_file()

        # Snap the control file offset to current EOF so prior-run commands
        # left in queue_control.jsonl are not re-applied.  The ack file is
        # left intact for forensic browsing.
        if CONTROL_FILE.exists():
            with contextlib.suppress(OSError):
                self._control_file_offset = CONTROL_FILE.stat().st_size

        # Wipe stale /tmp/opencode_worker_* from any prior orchestrator run,
        # then pre-warm one SQLite DB per gen slot so the first concurrent
        # iter does not pay the one-time migration cost in-band.
        _cleanup_stale_worker_dirs()
        for slot in range(self.max_gen_workers):
            _prewarm_worker_db(slot)
        print(f"[orchestrator] pre-warmed {self.max_gen_workers} per-slot "
              f"opencode DBs under /tmp/opencode_worker_*", flush=True)

        try:
            # Initial state dump + per-app log dirs.
            for app in self.apps.values():
                app.log_dir.mkdir(parents=True, exist_ok=True)
                if self.resume and self._apply_resume_state(app):
                    # Already terminal (PASS or exhausted FAIL) — skip enqueue.
                    continue
                with self.state_lock:
                    app.state = AppState.READY_FOR_GEN
                    app.queued_for_gen_at = time.monotonic()
                    app.app_started_at = time.monotonic()
                self.ready_for_gen.put(app.name)

            # If every requested app was already terminal, all_done_event
            # fires inside _mark_app_done; the wait loop exits at once.

            # Install signal handlers in main thread BEFORE spawning workers.
            signal.signal(signal.SIGINT, self._on_signal)
            signal.signal(signal.SIGTERM, self._on_signal)
            signal.signal(signal.SIGHUP, self._on_signal)

            self._write_experiment_timing(status="running")

            # Spawn the executor thread + gen pool.
            executor = threading.Thread(target=self._executor_loop, name="executor", daemon=True)
            executor.start()

            gen_pool = ThreadPoolExecutor(max_workers=self.max_gen_workers,
                                          thread_name_prefix="gen")
            gen_futures = [gen_pool.submit(self._gen_worker) for _ in range(self.max_gen_workers)]

            # Wait for either all done OR a signal.
            while not self.all_done_event.is_set() and not self.stop_event.is_set():
                self.all_done_event.wait(timeout=2.0)
                self._apply_control_commands()
                self._write_experiment_timing(status="running")

            # Drain: tell workers to stop.
            for _ in range(self.max_gen_workers):
                self.ready_for_gen.put(None)
            self.executor_queue.put(None)

            gen_pool.shutdown(wait=True)
            executor.join(timeout=30.0)

            status = "interrupted" if self.stop_event.is_set() else "done"
            self._write_experiment_timing(status=status)
            for app in self.apps.values():
                self._write_per_app_result(app)
                self._write_per_app_parallel_timing(app)
            return 0 if status == "done" else 130
        finally:
            self._release_pid_file()

    # --- Single-instance pid file -------------------------------------------
    @property
    def pid_file(self) -> Path:
        return EXP_STATE_DIR / "parallel_orchestrator.pid"

    def _claim_pid_file(self) -> None:
        if self.pid_file.exists():
            try:
                old = int(self.pid_file.read_text().strip())
            except Exception:
                old = -1
            if old > 0:
                # Liveness probe.
                try:
                    os.kill(old, 0)
                    raise SystemExit(
                        f"Another orchestrator is running (pid {old}, "
                        f"from {self.pid_file}). Refusing to start."
                    )
                except ProcessLookupError:
                    pass  # stale pid — overwrite
        self.pid_file.write_text(str(os.getpid()))

    def _release_pid_file(self) -> None:
        with contextlib.suppress(Exception):
            if self.pid_file.exists() and self.pid_file.read_text().strip() == str(os.getpid()):
                self.pid_file.unlink()

    # --- Resume application -------------------------------------------------
    def _apply_resume_state(self, app: AppRun) -> bool:
        """Restore *app* from on-disk artifacts under crash-immediate safety.

        Returns True iff the caller should SKIP the default READY_FOR_GEN
        enqueue (because we already enqueued elsewhere — terminal, executor,
        or bench — or because the app is done).  Returns False to let the
        caller proceed with the normal READY_FOR_GEN enqueue path.

        Five dispositions:

          mid_gen      — gen helper was interrupted mid-LLM-edit.  Source
                         tree under app_dir may be a partial edit and is
                         not safe to reuse.  Archive all prior logs (still
                         useful for the paper) + wipe app_dir + restage
                         fresh vanilla + reset AppRun.  Crash does NOT
                         burn a retry attempt.  Returns False (caller
                         enqueues at READY_FOR_GEN, iter starts at 1).

          mid_validate — gen completed cleanly (metrics_gen.json present)
                         but validate never wrote metrics.json.  Source
                         tree IS a valid checkpoint per LLM-iter-completion
                         convention.  Restore prior completed iters and a
                         partial IterMetrics for iter N (gen fields only),
                         enqueue ("validate", N) on the executor.  No data
                         lost.  Returns True (skip default enqueue).

          mid_bench    — iter loop reached PASS but bench never reached
                         terminal (no result.json).  Restore all iters,
                         mark verdict_passed, enqueue ("bench", final_iter)
                         on the executor.  Returns True.

          terminal     — prior verdict=PASS or exhausted-retry FAIL.  Mark
                         DONE_*, call _mark_app_done.  Returns True.

          clean        — between iters with all iters complete.  Existing
                         logic: restore bookkeeping, return False so caller
                         enqueues at READY_FOR_GEN for next iter.
        """
        crash = _classify_iter_crash(app.log_dir)

        # --- Branch 1: mid_gen → wipe + restart iter 1 ---------------------
        if crash["mode"] == "mid_gen":
            crashed_iter = crash["iter"]
            archive = _archive_crashed_logs(app.log_dir)
            with self.state_lock:
                _refresh_app_dir(app)
                _reset_app_run_after_wipe(app)
            app.log_dir.mkdir(parents=True, exist_ok=True)
            print(
                f"[orchestrator] {app.name} CRASH-RESUME mid_gen iter={crashed_iter}: "
                f"prior logs archived to {archive.name if archive else '(none)'}, "
                f"vanilla restaged, restarting iter 1 (retry not consumed)",
                flush=True,
            )
            return False

        # --- Branch 2: mid_validate → re-queue executor for validate -------
        if crash["mode"] == "mid_validate":
            partial_iter = crash["iter"]
            prior = _load_app_resume_state(app)
            # prior may be {} if mid_validate hit iter 1 with no completed
            # predecessors — handle by using empty defaults.
            with self.state_lock:
                app.per_iter = prior.get("completed_iters", [])
                app.loop_attempt = prior.get("loop_attempt", 1)
                app.prior_attempts = prior.get("prior_attempts", [])
                app.loop_stall_count = prior.get("loop_stall_count", 0)
                app.loop_max_iters_count = prior.get("loop_max_iters_count", 0)
                app.per_iter.append(
                    _load_partial_gen_iter(app.log_dir / f"iter_{partial_iter}",
                                           partial_iter)
                )
                app.iter = partial_iter
                app.state = AppState.QUEUED_FOR_EXECUTOR
                app.queued_for_executor_at = time.monotonic()
                if app.app_started_at == 0.0:
                    app.app_started_at = time.monotonic()
            self.executor_queue.put((app.name, "validate", partial_iter))
            print(
                f"[orchestrator] {app.name} CRASH-RESUME mid_validate iter={partial_iter}: "
                f"gen complete (source preserved), re-queued for validate "
                f"({len(app.per_iter) - 1} prior iters restored)",
                flush=True,
            )
            return True

        # --- Branch 3: clean — load state, then check for mid_bench --------
        prior = _load_app_resume_state(app)
        if not prior:
            return False

        with self.state_lock:
            app.per_iter = prior["completed_iters"]
            app.iter = app.per_iter[-1].iter if app.per_iter else 0
            app.loop_attempt = prior["loop_attempt"]
            app.prior_attempts = prior["prior_attempts"]
            app.loop_stall_count = prior["loop_stall_count"]
            app.loop_max_iters_count = prior["loop_max_iters_count"]
            app.verdict_passed = prior["verdict_passed"]
            app.bench_wall_s = prior["bench_wall_s"]
            app.bench_queue_wait_s = prior["bench_queue_wait_s"]
            app.bench_started_at = prior["bench_started_at"]
            app.bench_exit_code = prior["bench_exit_code"]

            if prior["verdict"] == "PASS":
                app.state = AppState.DONE_PASSED
                self._mark_app_done(app)
                print(
                    f"[orchestrator] {app.name} RESUME: prior verdict=PASS "
                    f"({len(app.per_iter)} iters, attempt {app.loop_attempt}"
                    f"/{app.max_loop_attempts}) — skipping",
                    flush=True,
                )
                return True
            if prior["exhausted_retries"]:
                app.state = AppState.DONE_FAILED
                self._mark_app_done(app)
                print(
                    f"[orchestrator] {app.name} RESUME: prior verdict=FAIL "
                    f"with exhausted retries ({app.loop_attempt}"
                    f"/{app.max_loop_attempts}) — skipping",
                    flush=True,
                )
                return True

            # --- Branch 4: mid_bench ---------------------------------------
            # Signal: latest iter passed validate, but no result.json on
            # disk (terminal never reached).  Only meaningful when bench is
            # the intended next step (skip_bench=False); with skip_bench=True
            # the orchestrator goes straight to DONE_PASSED + writes
            # result.json, so the "no result.json" condition implies bench.
            result_json = app.log_dir / "result.json"
            last_iter_passed = (app.per_iter and
                                app.per_iter[-1].validation_passed)
            if last_iter_passed and not result_json.exists() and not self.skip_bench:
                final_iter = app.per_iter[-1].iter
                app.verdict_passed = True
                app.iter_loop_finished_at = time.monotonic()
                app.bench_started_at = None
                app.bench_wall_s = 0.0
                app.bench_exit_code = 0
                app.state = AppState.QUEUED_FOR_BENCH
                app.queued_for_bench_at = time.monotonic()
                if app.app_started_at == 0.0:
                    app.app_started_at = time.monotonic()
                self.executor_queue.put((app.name, "bench", final_iter))
                print(
                    f"[orchestrator] {app.name} CRASH-RESUME mid_bench: "
                    f"iter loop passed at iter={final_iter}, no result.json — "
                    f"re-queued for bench",
                    flush=True,
                )
                return True

            # --- Branch 5: clean in-progress between iters -----------------
            print(
                f"[orchestrator] {app.name} RESUME: continuing from "
                f"iter={app.iter} attempt={app.loop_attempt}"
                f"/{app.max_loop_attempts} ({len(app.per_iter)} prior iters "
                f"restored)",
                flush=True,
            )
            return False

    # --- Signal handling ----------------------------------------------------
    def _on_signal(self, signum, frame):
        print(f"\n[orchestrator] received signal {signum} — draining and exiting", flush=True)
        self.stop_event.set()
        # Best-effort kill any in-flight child opencode + mpirun.  Children
        # inherit our process group, so killpg(0, TERM) reaches them all.
        with contextlib.suppress(Exception):
            os.killpg(0, signal.SIGTERM)

    # --- Gen worker loop ----------------------------------------------------
    def _gen_worker(self) -> None:
        while not self.stop_event.is_set():
            try:
                name = self.ready_for_gen.get(timeout=1.0)
            except queue.Empty:
                continue
            if name is None:
                return
            try:
                self._do_one_gen_iter(self.apps[name])
            except Exception as exc:
                print(f"[gen] {name} CRASHED: {exc!r}", flush=True)
                with self.state_lock:
                    self.apps[name].state = AppState.DONE_FAILED
                    self._mark_app_done(self.apps[name])

    def _do_one_gen_iter(self, app: AppRun) -> None:
        with self.state_lock:
            app.iter += 1
            app.state = AppState.GENERATING
            iter_n = app.iter
            gen_started_mono = time.monotonic()
            gen_started_wall = _utc_iso()
            gen_queue_wait_s = gen_started_mono - app.queued_for_gen_at

        # First iter of a loop attempt: re-copy vanilla.  Also for very first
        # iter (loop_attempt=1, iter=1) the existing serial driver always
        # re-copies — we match that behavior.
        if iter_n == 1:
            print(f"[gen] {app.name} attempt {app.loop_attempt}: re-copying vanilla", flush=True)
            _refresh_app_dir(app)

        # Snapshot the tree BEFORE this iter starts.  On stall, a hard-reset
        # to this commit rolls back any partial mid-stall edits so the retry
        # begins from a clean iter-N-start state.  Idempotent — on resume
        # the repo may already exist with a different last-commit; we
        # overwrite by committing the current state.
        _git_init_snapshot(
            app.app_dir,
            f"pre-iter {iter_n} (attempt {app.loop_attempt}, "
            f"stall_retry={app.iter_stall_retry_count})",
        )

        iter_log = app.log_dir / f"iter_{iter_n}"
        iter_log.mkdir(parents=True, exist_ok=True)
        prompt_text = _build_prompt(app, iter_n)
        prompt_text = _apply_context_cap(prompt_text, iter_log)
        prompt_path = iter_log / "prompt.txt"
        prompt_path.write_text(prompt_text)

        worker_slot = _get_worker_slot()
        print(f"[gen] {app.name} iter {iter_n} START (attempt {app.loop_attempt}, "
              f"slot={worker_slot}, queue_wait={gen_queue_wait_s:.1f}s)", flush=True)

        cmd = [
            str(HELPER_SH),
            app.name,
            str(iter_n),
            str(prompt_path),
            str(app.app_dir),
            str(app.log_dir),
            str(worker_slot),
        ]
        env = os.environ.copy()
        # No outer timeout — helper has its own OPENCODE_TIMEOUT + stall watcher.
        rc, _wall = _run_subprocess(cmd, env=env)

        # Defense-in-depth: opencode 1.4.0 may exit silently with rc=0 on a
        # "database is locked" sqlite collision even after per-slot XDG
        # isolation (e.g. if a shared path is unexpectedly locked, or a
        # future opencode version regresses).  Detect the crash signature
        # in stderr and convert it to rc=99 so the existing retry path
        # (rc != 0 in next iter loop) treats this as a failure instead of
        # feeding a no-code result to the validator.
        stderr_path = iter_log / "opencode_stderr.txt"
        if rc == 0 and stderr_path.exists():
            try:
                tail = stderr_path.read_text(errors="replace")[-8192:]
                if "database is locked" in tail or "SQLITE_BUSY" in tail:
                    print(f"[gen] {app.name} iter {iter_n} detected opencode "
                          f"DB-lock crash despite rc=0 — overriding to rc=99 "
                          f"for retry", flush=True)
                    rc = 99
                    with contextlib.suppress(Exception):
                        with stderr_path.open("a") as fh:
                            fh.write("\n[orchestrator] DB-lock crash signature "
                                     "detected; overriding opencode rc 0 -> 99\n")
            except Exception as e:
                print(f"[gen] {app.name} iter {iter_n} stderr scan error: {e}",
                      flush=True)

        # Defense-in-depth (2026-05-26 incident): even with the helper's
        # OC_RC capture fix, opencode 1.4.0 has been observed exiting
        # genuinely cleanly (rc=0) without producing ANY work — 0 tokens,
        # 0 bytes of stdout/stderr, sub-second wall.  Root cause not fully
        # known (suspected slot-reuse race or CLI internal session short-
        # circuit), but the SIGNATURE is unambiguous: a real iter on this
        # workload spends minutes generating and consumes millions of
        # tokens.  We treat (rc=0 AND tokens_total=0 AND gen_wall_s<10) as
        # a silent no-op and override to rc=99 so the orchestrator's retry
        # path fires.  We also surface the helper's diagnostic dump to the
        # orchestrator stdout so each occurrence is visible in real time.
        # Predicate widened 2026-05-26: rc=137 (SIGKILL) and rc=124 (timeout)
        # were observed producing the same silent-no-op signature on SAMRAI+Nyx
        # fresh-vanilla iter_2+.  Root cause NOT yet confirmed — the original
        # stale-slot-DB hypothesis was disproven by the broader history (many
        # apps reached 3-8 iters fine without per-iter wipe).  Treat the
        # signature itself as authoritative: any rc with 0 tokens AND <10s
        # wall on a workload that should take minutes is a no-op regardless
        # of exit code.  Forensic dump still happens via the diagnostic file.
        metrics_path_for_check = iter_log / "metrics_gen.json"
        if rc in (0, 124, 137) and metrics_path_for_check.exists():
            try:
                m_check = json.loads(metrics_path_for_check.read_text())
                _toks = int(m_check.get("tokens_total", 0) or 0)
                _wall = float(m_check.get("gen_wall_s", 999.0) or 999.0)
                _stdout_size = 0
                _stderr_size = 0
                stdout_path = iter_log / "opencode_stdout.txt"
                if stdout_path.exists():
                    _stdout_size = stdout_path.stat().st_size
                if stderr_path.exists():
                    _stderr_size = stderr_path.stat().st_size
                if _toks == 0 and _wall < 10.0:
                    print(
                        f"[gen] {app.name} iter {iter_n} SILENT NO-OP detected "
                        f"(rc=0, tokens=0, gen_wall={_wall:.2f}s, "
                        f"stdout={_stdout_size}B, stderr={_stderr_size}B) — "
                        f"overriding to rc=99 for retry",
                        flush=True,
                    )
                    rc = 99
                    # Surface the helper's diagnostic dump verbatim so the
                    # orchestrator log captures full forensic state for each
                    # no-op occurrence (env, opencode --version, slot DB
                    # state, latest opencode log tail).  Helps root-cause
                    # without re-running.
                    diag_path = iter_log / "opencode_diagnostic.txt"
                    if diag_path.exists():
                        try:
                            diag_text = diag_path.read_text(errors="replace")
                            print(
                                f"[gen] {app.name} iter {iter_n} no-op "
                                f"diagnostic ({diag_path}):\n"
                                f"--- BEGIN opencode_diagnostic.txt ---\n"
                                f"{diag_text}\n"
                                f"--- END opencode_diagnostic.txt ---",
                                flush=True,
                            )
                        except Exception as ex:
                            print(
                                f"[gen] {app.name} iter {iter_n} could not "
                                f"surface diagnostic: {ex}",
                                flush=True,
                            )
                    else:
                        print(
                            f"[gen] {app.name} iter {iter_n} no diagnostic "
                            f"dump at {diag_path} — helper may pre-date the "
                            f"diagnostic patch",
                            flush=True,
                        )
                    # Mark stderr so a human grepping iter_N/opencode_stderr.txt
                    # later sees why this iter was retried.
                    with contextlib.suppress(Exception):
                        with stderr_path.open("a") as fh:
                            fh.write(
                                "\n[orchestrator] silent no-op signature "
                                f"(rc=0, tokens=0, wall={_wall:.2f}s); "
                                "overriding opencode rc 0 -> 99 for retry\n"
                            )
            except Exception as ex:
                print(
                    f"[gen] {app.name} iter {iter_n} no-op detector error: {ex}",
                    flush=True,
                )

        # Read helper's metrics_gen.json (single source of truth for gen wall).
        metrics_path = iter_log / "metrics_gen.json"
        gen_wall_s = 0.0
        tokens_in = tokens_out = tokens_total = 0
        stall_aborted = False
        if metrics_path.exists():
            try:
                data = json.loads(metrics_path.read_text())
                gen_wall_s = float(data.get("gen_wall_s", 0.0))
                tokens_in = int(data.get("tokens_input", 0))
                tokens_out = int(data.get("tokens_output", 0))
                tokens_total = int(data.get("tokens_total", 0))
                stall_aborted = bool(data.get("stall_aborted", False))
            except Exception as e:
                print(f"[gen] {app.name} iter {iter_n} metrics_gen.json read error: {e}",
                      flush=True)

        # Record the iter metrics under lock + transition state.
        with self.state_lock:
            app.per_iter.append(IterMetrics(
                iter=iter_n,
                gen_wall_s=gen_wall_s,
                tokens_input=tokens_in,
                tokens_output=tokens_out,
                tokens_total=tokens_total,
                stall_aborted=stall_aborted,
                stall_retries=app.iter_stall_retry_count,
                gen_queue_wait_s=gen_queue_wait_s,
                gen_started_at=gen_started_wall,
                gen_exit_code=rc,
            ))

            if stall_aborted:
                self._handle_stall(app, iter_n, iter_log)
                return

            # Non-stall gen completed (validate will be attempted): reset the
            # per-iter stall-retry counter so a future stall on a LATER iter
            # gets its own fresh budget.
            app.iter_stall_retry_count = 0
            app.state = AppState.QUEUED_FOR_EXECUTOR
            app.queued_for_executor_at = time.monotonic()

        print(f"[gen] {app.name} iter {iter_n} DONE gen ({gen_wall_s:.1f}s) "
              f"-> queued for executor", flush=True)
        self.executor_queue.put((app.name, "validate", iter_n))

    def _handle_stall(self, app: AppRun, iter_n: int, iter_log: Path) -> None:
        """Handle a mid-iter OpenCode stall.

        Called under ``state_lock`` from ``_do_one_gen_iter`` when the helper
        reports ``stall_aborted=true`` for the current iter.

        Per user directive 2026-05-26: do NOT restart the loop from vanilla
        on stall.  Instead, hard-reset the codebase tree to the snapshot
        taken at iter start (discarding any partial mid-stall edits), bump
        the per-iter stall-retry counter, and re-queue the SAME iter.

        Budget: ``app.max_iter_stall_retries`` (initialized from
        ``--opencode-retries``, default 2) consecutive stalls per iter.
        On exhaustion the app transitions directly to DONE_FAILED — the
        loop-restart fallback is intentionally not used because the user
        wants stall to be terminal once the per-iter budget is gone.

        Forensics: the stalled iter's log dir (containing stall_watch.log,
        opencode_stderr.txt, partial metrics_gen.json) is archived to
        ``iter_<N>_stall<retry>`` BEFORE the retry overwrites it, so a
        post-mortem can still see exactly where each attempt got stuck.
        """
        app.iter_stall_retry_count += 1
        retry_n = app.iter_stall_retry_count

        # Archive the stalled iter dir so the retry starts with a fresh
        # iter_<N>/ directory and the forensics are preserved on disk.
        archive_dir = iter_log.parent / f"iter_{iter_n}_stall{retry_n}"
        with contextlib.suppress(Exception):
            if iter_log.exists() and not archive_dir.exists():
                os.rename(iter_log, archive_dir)

        if retry_n > app.max_iter_stall_retries:
            # Per-iter retries exhausted.  Treat as terminal: do NOT restart
            # the loop from vanilla.  Record the terminal-stall outcome and
            # transition to DONE_FAILED.
            app.prior_attempts.append(LoopAttempt(
                attempt=app.loop_attempt,
                outcome="stall_exhausted",
                iters_run=iter_n,
                stall_iteration=iter_n,
            ))
            app.loop_stall_count += 1
            app.final_stall_aborted = True
            app.final_stall_iteration = iter_n
            app.iter_loop_finished_at = time.monotonic()
            app.state = AppState.DONE_FAILED
            self._mark_app_done(app)
            print(f"[orchestrator] {app.name} iter {iter_n} stall budget "
                  f"exhausted ({retry_n - 1}/{app.max_iter_stall_retries} "
                  f"retries used) — DONE_FAILED (no vanilla restart, per "
                  f"user directive)", flush=True)
            return

        # Pop the just-appended stalled IterMetrics so per_iter stays
        # 1-entry-per-iter (the retried attempt will append its own entry
        # with stall_retries=retry_n).  Forensics for THIS stall are
        # preserved in the archived iter_<N>_stall<retry>/ dir on disk.
        # The terminal-exhaustion path above keeps its stall entry as a
        # visible "this is where we gave up" record.
        if app.per_iter and app.per_iter[-1].iter == iter_n and app.per_iter[-1].stall_aborted:
            app.per_iter.pop()

        # Roll back any partial mid-stall edits before retrying.
        reset_ok = _git_reset_hard(app.app_dir)
        # Re-queue the SAME iter: decrement app.iter so _do_one_gen_iter
        # increments it back to iter_n on the next dispatch.
        app.iter = iter_n - 1
        app.state = AppState.READY_FOR_GEN
        app.queued_for_gen_at = time.monotonic()
        self.ready_for_gen.put(app.name)
        print(f"[orchestrator] {app.name} iter {iter_n} stalled — retry "
              f"{retry_n}/{app.max_iter_stall_retries} (git reset "
              f"{'OK' if reset_ok else 'FAILED'}, archived to "
              f"{archive_dir.name})", flush=True)

    # --- Executor (serialized) loop -----------------------------------------
    def _executor_loop(self) -> None:
        while not self.stop_event.is_set():
            # Priority queue (populated by ctl add --immediate) is drained
            # FIRST so dynamic-queue commands land ahead of normally queued
            # work without preempting the task already in flight.  Falls
            # through to the main queue with a 1s wait when priority is empty.
            item = None
            try:
                item = self.executor_priority_queue.get_nowait()
            except queue.Empty:
                try:
                    item = self.executor_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
            if item is None:
                return
            name, kind, iter_n = item
            app = self.apps[name]
            try:
                if kind == "validate":
                    self._do_one_validation(app, iter_n)
                elif kind == "bench":
                    self._do_one_bench(app)
            except Exception as exc:
                print(f"[exec] {name} {kind} CRASHED: {exc!r}", flush=True)
                with self.state_lock:
                    app.state = AppState.DONE_FAILED
                    self._mark_app_done(app)

    def _do_one_validation(self, app: AppRun, iter_n: int) -> None:
        with self.state_lock:
            app.state = AppState.EXECUTING
            val_started_mono = time.monotonic()
            val_started_wall = _utc_iso()
            val_queue_wait_s = val_started_mono - app.queued_for_executor_at

        iter_log = app.log_dir / f"iter_{iter_n}"
        print(f"[exec] {app.name} iter {iter_n} VALIDATE START "
              f"(queue_wait={val_queue_wait_s:.1f}s)", flush=True)

        # --label routes BOTH the resilient-source directory (tests_<label>/)
        # and the validation-output directory (validation_output/<APP>_<label>/)
        # so non-default labels (smoke probes, secondary sweeps) cannot collide
        # with the canonical baseline cell.  See run_validate.sh comments at
        # the --label parse block.
        cmd = [
            str(VALIDATE_SH),
            "--baseline", app.name,
            "--label", app.label,
            "--skip-benchmarks", "--skip-report",
        ]
        rc, val_wall_s = _run_subprocess(
            cmd,
            env=os.environ.copy(),
            stdout_log=iter_log / "validate_stdout.txt",
            stderr_log=iter_log / "validate_stderr.txt",
            timeout=self.validate_timeout_s,
        )

        # Watchdog tripped: validate exceeded the 15-min cap.  _run_subprocess
        # already SIGKILL'd the entire process group (mpirun + ranks) so the
        # host-wide executor lane is freed.  Drop a marker file the next-iter
        # LLM prompt will see — the standard prompt builder points the LLM at
        # the prev iter dir, and a top-level _TIMEOUT_KILLED.txt is the most
        # legible signal to surface here (vs JSON the LLM has to parse).
        if rc == 124:
            with contextlib.suppress(Exception):
                (iter_log / "_TIMEOUT_KILLED.txt").write_text(
                    f"VALIDATE STAGE TIMED OUT AND WAS KILLED\n"
                    f"========================================\n"
                    f"App:           {app.name}\n"
                    f"Iter:          {iter_n}\n"
                    f"Wall:          {val_wall_s:.1f}s (cap: "
                    f"{self.validate_timeout_s:.0f}s)\n"
                    f"Killed at:     {_utc_iso()}\n"
                    f"Signal:        SIGKILL to the entire validate process "
                    f"group (mpirun + ranks)\n"
                    f"\n"
                    f"Diagnosis (read this carefully):\n"
                    f"\n"
                    f"Your previous iteration's checkpoint/restart code most\n"
                    f"likely contains an MPI deadlock — typically a routine\n"
                    f"that is collective from MPI's perspective but where some\n"
                    f"ranks (often only rank 0) take an early-return path\n"
                    f"BEFORE a downstream collective call (MPI_Barrier,\n"
                    f"MPI_Allreduce, MPI_Bcast, or any MPI-collective I/O).\n"
                    f"The non-returning ranks then block forever at the\n"
                    f"collective, mpirun never exits, and the validator\n"
                    f"watchdog had to kill the entire process tree.\n"
                    f"\n"
                    f"Common shapes of this bug:\n"
                    f"\n"
                    f"  if (rank == 0) {{\n"
                    f"      if (mkdir(...) < 0) return false;   // rank 0 only\n"
                    f"  }}\n"
                    f"  MPI_Barrier(comm);                       // others deadlock\n"
                    f"\n"
                    f"  if (VELOC_Restart(...) != VELOC_SUCCESS) {{\n"
                    f"      return;                              // per-rank rc\n"
                    f"  }}\n"
                    f"  // next collective is unreached on the failing rank\n"
                    f"\n"
                    f"To fix:\n"
                    f"  - Either move the early-return AFTER the next\n"
                    f"    collective (so every rank reaches it), or\n"
                    f"  - Reduce the per-rank decision across all ranks first\n"
                    f"    (MPI_Allreduce with MPI_LAND/MPI_LOR/MPI_MIN) and\n"
                    f"    have every rank act on the reduced value.\n"
                    f"\n"
                    f"The full stdout/stderr from the killed validate are at:\n"
                    f"  validate_stdout.txt\n"
                    f"  validate_stderr.txt\n"
                    f"They were truncated when the watchdog fired.\n"
                )
            # Also append a one-line breadcrumb to validate_stderr.txt so
            # readers who scan that file directly see the timeout without
            # needing to know about the marker file.
            with contextlib.suppress(Exception):
                with (iter_log / "validate_stderr.txt").open("a") as fh:
                    fh.write(
                        f"\n[parallel_queue_watchdog] VALIDATE TIMEOUT after "
                        f"{val_wall_s:.1f}s (cap {self.validate_timeout_s:.0f}s); "
                        f"process group SIGKILLed. See _TIMEOUT_KILLED.txt.\n"
                    )
            print(
                f"[exec] {app.name} iter {iter_n} VALIDATE TIMEOUT_KILL "
                f"({val_wall_s:.1f}s > cap {self.validate_timeout_s:.0f}s) "
                f"— process group killed, lane freed",
                flush=True,
            )

        # Mirror run_iterative.sh:726-728 — extract build/CMake/make error
        # lines (+20 lines of context) from validator output into
        # build_output.txt for downstream visibility.  Raw data lives in
        # validate_{stdout,stderr}.txt regardless; this is a convenience
        # summary the iter-2+ prompt may surface.  Best-effort: missing
        # files / no matches / grep failure all silently produce an empty
        # build_output.txt (matches serial's `|| true` behaviour).
        with contextlib.suppress(Exception):
            with (iter_log / "build_output.txt").open("w") as fh:
                subprocess.run(
                    ["grep", "-A", "20",
                     "Build failed\\|CMake Error\\|make.*Error\\|error:",
                     str(iter_log / "validate_stdout.txt"),
                     str(iter_log / "validate_stderr.txt")],
                    stdout=fh,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )

        # Update the most-recent IterMetrics with validation data.
        with self.state_lock:
            m = next((x for x in reversed(app.per_iter) if x.iter == iter_n), None)
            if m is None:
                m = IterMetrics(iter=iter_n)
                app.per_iter.append(m)
            m.val_wall_s = val_wall_s
            m.val_queue_wait_s = val_queue_wait_s
            m.val_started_at = val_started_wall
            m.val_exit_code = rc
            m.validation_passed = (rc == 0)

            # Mirror to per-iter metrics.json so chart-gen + audit see schema-1
            # output identical to what run_iterative.sh writes (separate from
            # the helper's metrics_gen.json which is gen-only).
            (iter_log / "metrics.json").write_text(json.dumps({
                "iter": iter_n,
                "opencode_elapsed_s": m.gen_wall_s,
                "validation_elapsed_s": m.val_wall_s,
                "total_elapsed_s": m.gen_wall_s + m.val_wall_s,
                "validation_passed": m.validation_passed,
                "input_tokens": m.tokens_input,
                "output_tokens": m.tokens_output,
                "total_tokens": m.tokens_total,
                "stall_aborted": m.stall_aborted,
                "gen_queue_wait_s": m.gen_queue_wait_s,
                "val_queue_wait_s": m.val_queue_wait_s,
            }, indent=2))

        # Cleanup ckpts AFTER validation regardless of pass/fail (matches
        # run_iterative.sh:715).  Outside the lock — it does subprocess+IO.
        with contextlib.suppress(Exception):
            _clean_iter_checkpoints(app.app_dir, app.name, app.label)

        if m.validation_passed:
            print(f"[exec] {app.name} iter {iter_n} VALIDATE PASS ({val_wall_s:.1f}s)",
                  flush=True)
            with self.state_lock:
                app.verdict_passed = True
                # Mark iter-loop finished BEFORE entering bench so wall_elapsed_s
                # excludes bench wall, matching serial run_iterative.sh:756.
                app.iter_loop_finished_at = time.monotonic()
                self._finalize_loop_attempt(app, outcome="pass", iters_run=iter_n)
                if self.skip_bench:
                    app.state = AppState.DONE_PASSED
                    self._mark_app_done(app)
                    return
                app.state = AppState.QUEUED_FOR_BENCH
                app.queued_for_bench_at = time.monotonic()
            self.executor_queue.put((app.name, "bench", iter_n))
            return

        # Validation failed.
        print(f"[exec] {app.name} iter {iter_n} VALIDATE FAIL ({val_wall_s:.1f}s)",
              flush=True)
        with self.state_lock:
            if app.iter < app.max_iters:
                # Try another iter inside this loop attempt.
                app.state = AppState.READY_FOR_GEN
                app.queued_for_gen_at = time.monotonic()
                self.ready_for_gen.put(app.name)
            else:
                # max_iters reached → loop-attempt outcome + D3 decision.
                self._finalize_loop_attempt(app, outcome="max_iters", iters_run=iter_n)

    def _do_one_bench(self, app: AppRun) -> None:
        with self.state_lock:
            app.state = AppState.BENCHING
            bench_started_mono = time.monotonic()
            app.bench_started_at = _utc_iso()
            app.bench_queue_wait_s = bench_started_mono - app.queued_for_bench_at

        print(f"[exec] {app.name} BENCH START "
              f"(n={app.benchmark_num_runs}, queue_wait={app.bench_queue_wait_s:.1f}s)",
              flush=True)
        bench_log_dir = app.log_dir / "_bench_run"
        bench_log_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            str(VALIDATE_SH),
            "--baseline", app.name,
            "--label", app.label,
            "--benchmark-num-runs", str(app.benchmark_num_runs),
        ]
        rc, bench_wall = _run_subprocess(
            cmd,
            env=os.environ.copy(),
            stdout_log=bench_log_dir / "bench_stdout.txt",
            stderr_log=bench_log_dir / "bench_stderr.txt",
        )
        with self.state_lock:
            app.bench_wall_s = bench_wall
            app.bench_exit_code = rc
            app.state = AppState.DONE_PASSED if rc == 0 else AppState.DONE_FAILED
            self._mark_app_done(app)
        print(f"[exec] {app.name} BENCH DONE rc={rc} wall={bench_wall:.1f}s", flush=True)

    # --- Dynamic-queue control plane ----------------------------------------
    # See run_parallel_queue_ctl.py for the CLI client.  Commands are append-
    # only JSONL records (one record per line) in CONTROL_FILE; we read the
    # newly-appended slice each wait tick, apply each command under
    # state_lock, and write one ack record per command to CONTROL_ACK_FILE.
    #
    # Why polling vs IPC: zero new runtime dependency, command history
    # survives orchestrator restarts, the file doubles as an audit trail.
    # Latency is bounded by the wait-loop timeout (~2s, plus current task
    # holding state_lock).
    @staticmethod
    def _snapshot_queue(q: queue.Queue) -> list:
        """Snapshot the FIFO contents of *q* without disturbing it.

        queue.Queue exposes its internal deque as ``.queue`` and its lock as
        ``.mutex``; holding the mutex while copying the deque is the
        canonical safe-iteration pattern documented in the CPython stdlib.
        """
        with q.mutex:
            return list(q.queue)

    def _app_in_queue(self, app_name: str, q: queue.Queue) -> bool:
        for item in self._snapshot_queue(q):
            if item is None:
                continue
            if isinstance(item, str) and item == app_name:
                return True
            if isinstance(item, tuple) and item and item[0] == app_name:
                return True
        return False

    def _filter_queue(self, q: queue.Queue, app_name: str) -> int:
        """Drop every entry for *app_name* from *q* in place, preserving
        order and the shutdown sentinel ``None``.  Returns the count removed.
        """
        removed = 0
        with q.mutex:
            keep: list = []
            for item in q.queue:
                if item is None:
                    keep.append(item)
                    continue
                if isinstance(item, str) and item == app_name:
                    removed += 1
                    continue
                if isinstance(item, tuple) and item and item[0] == app_name:
                    removed += 1
                    continue
                keep.append(item)
            q.queue.clear()
            for k in keep:
                q.queue.append(k)
        return removed

    def _write_ack(self, cmd_id: str, status: str, msg: str) -> None:
        """Append one ack record + mirror to orchestrator stdout."""
        record = {
            "id": cmd_id,
            "ts": _utc_iso(),
            "status": status,
            "msg": msg,
        }
        with contextlib.suppress(Exception):
            CONTROL_ACK_FILE.parent.mkdir(parents=True, exist_ok=True)
            with CONTROL_ACK_FILE.open("a") as fh:
                fh.write(json.dumps(record) + "\n")
        print(f"[ctl] ack {cmd_id} {status}: {msg}", flush=True)

    def _reset_app_for_redo(self, app: AppRun) -> None:
        """Take a terminal app back to a clean READY state for re-enqueue.

        Per-iter history (``per_iter``, ``prior_attempts``) is preserved on
        the object so chart-gen can still see prior runs; new iters append.
        ``remaining`` is bumped and ``all_done_event`` cleared so the main
        wait loop does not exit on a now-incomplete experiment.
        """
        app.iter = 0
        app.loop_attempt = 1
        app.loop_stall_count = 0
        app.loop_max_iters_count = 0
        app.verdict_passed = False
        app.final_stall_aborted = False
        app.final_stall_iteration = 0
        app.app_started_at = time.monotonic()
        app.app_finished_at = 0.0
        app.iter_loop_finished_at = 0.0
        app.bench_wall_s = 0.0
        app.bench_queue_wait_s = 0.0
        app.bench_started_at = None
        app.bench_exit_code = 0
        self.remaining += 1
        self.all_done_event.clear()

    def _ctl_add_gen(self, cmd_id: str, app_name: str, force: bool) -> None:
        with self.state_lock:
            if app_name not in self.apps:
                self._write_ack(cmd_id, "err",
                                f"unknown app '{app_name}' (not in initial --apps list; "
                                f"dynamic enrollment is not supported in this version)")
                return
            app = self.apps[app_name]
            already_queued = self._app_in_queue(app_name, self.ready_for_gen)
            if app.state in ACTIVE_APP_STATES or already_queued:
                if not force:
                    self._write_ack(
                        cmd_id, "duplicate",
                        f"'{app_name}' already active (state={app.state.value}, "
                        f"in_gen_queue={already_queued}) — pass force=true to override",
                    )
                    return
                print(
                    f"[ctl] force-add to gen: {app_name} already active "
                    f"({app.state.value}, in_queue={already_queued}); proceeding",
                    flush=True,
                )
            if app.state in TERMINAL_APP_STATES:
                self._reset_app_for_redo(app)
            app.state = AppState.READY_FOR_GEN
            app.queued_for_gen_at = time.monotonic()
        self.ready_for_gen.put(app_name)
        self._write_ack(cmd_id, "ok", f"'{app_name}' enqueued to gen queue")

    def _ctl_add_exec(self, cmd_id: str, app_name: str, kind: str,
                      iter_n: Optional[int], immediate: bool, force: bool) -> None:
        if kind not in ("validate", "bench"):
            self._write_ack(cmd_id, "err",
                            f"unknown kind '{kind}' (use validate or bench)")
            return
        with self.state_lock:
            if app_name not in self.apps:
                self._write_ack(cmd_id, "err",
                                f"unknown app '{app_name}' (not in initial --apps list)")
                return
            app = self.apps[app_name]
            in_main = self._app_in_queue(app_name, self.executor_queue)
            in_pri = self._app_in_queue(app_name, self.executor_priority_queue)
            # An exec add must lose to ANY active-state app: mid-gen would
            # race the in-flight LLM edit, ready-for-gen would race the
            # upcoming gen, and queued/executing/benching are already in
            # one of the queues we just snapshotted.  Mirror the gen-side
            # rule at _ctl_add_gen (uses ACTIVE_APP_STATES) so semantics
            # are symmetric.
            active = app.state in ACTIVE_APP_STATES
            if active or in_main or in_pri:
                if not force:
                    self._write_ack(
                        cmd_id, "duplicate",
                        f"'{app_name}' already in pipeline "
                        f"(state={app.state.value}, in_exec_queue={in_main}, "
                        f"in_priority_queue={in_pri}) — pass force=true to override",
                    )
                    return
                print(
                    f"[ctl] force-add to exec: {app_name} already present; proceeding",
                    flush=True,
                )
            if app.state in TERMINAL_APP_STATES:
                self._reset_app_for_redo(app)
            if kind == "validate":
                # Default to the most-recently-completed iter; if the app has
                # never run, default to 1.  Callers can override with --iter.
                if iter_n is None or iter_n <= 0:
                    iter_n = app.iter if app.iter > 0 else 1
                app.state = AppState.QUEUED_FOR_EXECUTOR
                app.queued_for_executor_at = time.monotonic()
            else:  # bench
                iter_n = iter_n or 0
                app.state = AppState.QUEUED_FOR_BENCH
                app.queued_for_bench_at = time.monotonic()
        target = self.executor_priority_queue if immediate else self.executor_queue
        target.put((app_name, kind, iter_n))
        where = "priority" if immediate else "main"
        self._write_ack(
            cmd_id, "ok",
            f"'{app_name}' enqueued to {where} executor queue ({kind}, iter={iter_n})",
        )

    def _ctl_remove(self, cmd_id: str, app_name: str, which: str) -> None:
        if which not in ("gen", "exec", "all"):
            self._write_ack(cmd_id, "err",
                            f"unknown queue '{which}' (use gen, exec, or all)")
            return
        details: list[str] = []
        total = 0
        with self.state_lock:
            if which in ("gen", "all"):
                n = self._filter_queue(self.ready_for_gen, app_name)
                if n:
                    details.append(f"gen={n}")
                total += n
            if which in ("exec", "all"):
                n = self._filter_queue(self.executor_queue, app_name)
                if n:
                    details.append(f"executor={n}")
                total += n
                n = self._filter_queue(self.executor_priority_queue, app_name)
                if n:
                    details.append(f"priority={n}")
                total += n
        if total == 0:
            self._write_ack(
                cmd_id, "noop",
                f"'{app_name}' had no pending entries in {which} queue "
                f"(any in-flight task is NOT killed — use SIGINT/SIGTERM on "
                f"the orchestrator for that, with user confirmation)",
            )
        else:
            self._write_ack(
                cmd_id, "ok",
                f"removed {total} pending entr{'y' if total == 1 else 'ies'} "
                f"for '{app_name}' ({', '.join(details)}); in-flight tasks unaffected",
            )

    def _ctl_list(self, cmd_id: str) -> None:
        with self.state_lock:
            gen_snap = self._snapshot_queue(self.ready_for_gen)
            exec_snap = self._snapshot_queue(self.executor_queue)
            pri_snap = self._snapshot_queue(self.executor_priority_queue)
            per_app = {
                name: {"state": app.state.value, "iter": app.iter,
                       "loop_attempt": app.loop_attempt}
                for name, app in self.apps.items()
            }
            remaining = self.remaining
        summary = {
            "gen_queue": [x for x in gen_snap if x is not None],
            "executor_queue": [list(x) for x in exec_snap if x is not None],
            "priority_queue": [list(x) for x in pri_snap if x is not None],
            "per_app": per_app,
            "remaining": remaining,
        }
        self._write_ack(cmd_id, "ok", json.dumps(summary))

    def _dispatch_control_command(self, cmd: dict) -> None:
        cmd_id = str(cmd.get("id") or uuid.uuid4())
        cmd_type = cmd.get("cmd", "")
        try:
            if cmd_type == "add":
                queue_kind = cmd.get("queue", "")
                if queue_kind == "gen":
                    self._ctl_add_gen(cmd_id, cmd["app"],
                                      bool(cmd.get("force", False)))
                elif queue_kind == "exec":
                    self._ctl_add_exec(
                        cmd_id, cmd["app"], cmd.get("kind", "validate"),
                        cmd.get("iter"), bool(cmd.get("immediate", False)),
                        bool(cmd.get("force", False)),
                    )
                else:
                    self._write_ack(cmd_id, "err",
                                    f"unknown queue '{queue_kind}' for add")
            elif cmd_type == "remove":
                self._ctl_remove(cmd_id, cmd["app"], cmd.get("queue", "all"))
            elif cmd_type == "list":
                self._ctl_list(cmd_id)
            else:
                self._write_ack(cmd_id, "err", f"unknown cmd '{cmd_type}'")
        except KeyError as e:
            self._write_ack(cmd_id, "err", f"missing required field: {e}")
        except Exception as e:
            self._write_ack(cmd_id, "err", f"exception applying cmd: {e!r}")

    def _apply_control_commands(self) -> None:
        """Read new lines from CONTROL_FILE since the last poll, dispatch each.

        No-op if the file does not exist or has not grown.  Malformed lines
        are logged and skipped — they do not stall the loop.
        """
        if not CONTROL_FILE.exists():
            return
        try:
            size = CONTROL_FILE.stat().st_size
        except OSError:
            return
        if size <= self._control_file_offset:
            return
        try:
            with CONTROL_FILE.open("r") as fh:
                fh.seek(self._control_file_offset)
                new_data = fh.read()
                self._control_file_offset = fh.tell()
        except Exception as e:
            print(f"[ctl] error reading control file: {e}", flush=True)
            return
        for raw in new_data.splitlines():
            line = raw.strip()
            if not line:
                continue
            try:
                cmd = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[ctl] skipping malformed control line: {e} :: {line!r}",
                      flush=True)
                continue
            if not isinstance(cmd, dict):
                print(f"[ctl] skipping non-object control line: {cmd!r}",
                      flush=True)
                continue
            self._dispatch_control_command(cmd)

    # --- D3 retry decision (called under state_lock) ------------------------
    def _finalize_loop_attempt(self, app: AppRun, *, outcome: str,
                                iters_run: int, stall_iteration: int = 0) -> None:
        app.prior_attempts.append(LoopAttempt(
            attempt=app.loop_attempt,
            outcome=outcome,
            iters_run=iters_run,
            stall_iteration=stall_iteration,
        ))
        if outcome == "stall":
            app.loop_stall_count += 1
            app.final_stall_aborted = True
            app.final_stall_iteration = stall_iteration
        elif outcome == "max_iters":
            app.loop_max_iters_count += 1
        elif outcome == "pass":
            return  # do NOT reset iter — bench follows

        # Decide retry vs. final fail.
        if app.loop_attempt < app.max_loop_attempts:
            app.loop_attempt += 1
            app.iter = 0
            app.state = AppState.READY_FOR_GEN
            app.queued_for_gen_at = time.monotonic()
            self.ready_for_gen.put(app.name)
            print(f"[orchestrator] {app.name} retry-on-{outcome}: starting loop attempt "
                  f"{app.loop_attempt}/{app.max_loop_attempts}", flush=True)
        else:
            # Mark iter-loop finished BEFORE entering DONE_FAILED so
            # wall_elapsed_s captures iter-loop time only (no bench was run
            # on this terminal-fail path).  Matches serial
            # run_iterative.sh:837 EVAL_END semantics.
            app.iter_loop_finished_at = time.monotonic()
            app.state = AppState.DONE_FAILED
            self._mark_app_done(app)
            print(f"[orchestrator] {app.name} EXHAUSTED retry budget "
                  f"({app.loop_attempt}/{app.max_loop_attempts}) — DONE_FAILED",
                  flush=True)

    def _mark_app_done(self, app: AppRun) -> None:
        """Called under state_lock when an app reaches DONE_*."""
        if app.app_finished_at == 0.0:
            app.app_finished_at = time.monotonic()
        self.remaining -= 1
        # Write the per-app result/parallel JSONs early so each app's
        # snapshot is available on disk even if the orchestrator is
        # interrupted before the global drain.
        self._write_per_app_result(app)
        self._write_per_app_parallel_timing(app)
        if self.remaining <= 0:
            self.all_done_event.set()

    # --- JSON writers --------------------------------------------------------
    def _write_per_app_result(self, app: AppRun) -> None:
        """Schema-v2 result.json matching run_iterative.sh output exactly.

        wall_elapsed_s = sum across iters of (LLM-gen wall + validator wall).
        EXCLUDES bench wall AND queue-wait time apps spent waiting for the
        single-threaded executor lock between their own iterations.  In serial
        there is no queue-wait by design (one app at a time), so this sum
        equals serial run_iterative.sh's EVAL_END-EVAL_START byte-equivalent.
        Chart-gen consumers (docs/figs/_plot_per_group_summary.py:86,
        _plot_fast_tier_iter_metrics.py:173) get apples-to-apples wall times
        regardless of which driver produced the result.

        total_opencode_elapsed_s / total_validation_elapsed_s are also
        exposed as top-level fields so consumers can read the breakdown
        without summing per_iteration[] themselves.
        """
        per_iter = [
            {
                "iter": m.iter,
                "opencode_elapsed_s": m.gen_wall_s,
                "validation_elapsed_s": m.val_wall_s,
                "total_elapsed_s": m.gen_wall_s + m.val_wall_s,
                "validation_passed": m.validation_passed,
                "input_tokens": m.tokens_input,
                "output_tokens": m.tokens_output,
                "total_tokens": m.tokens_total,
                **({"stall_aborted": True} if m.stall_aborted else {}),
            }
            for m in app.per_iter
        ]
        total_opencode_elapsed_s = sum(m.gen_wall_s for m in app.per_iter)
        total_validation_elapsed_s = sum(m.val_wall_s for m in app.per_iter)
        wall_elapsed_s = total_opencode_elapsed_s + total_validation_elapsed_s
        total_input = sum(m.tokens_input for m in app.per_iter)
        total_output = sum(m.tokens_output for m in app.per_iter)
        total_tokens = sum(m.tokens_total for m in app.per_iter)
        # State machine guarantees DONE_PASSED is reached only when
        # validation+bench (or skip_bench+validation) genuinely passed
        # (see _do_one_validation pass branch and _do_one_bench rc==0
        # branch).  All other paths end in DONE_FAILED.
        passed = app.verdict_passed and app.state == AppState.DONE_PASSED
        payload = {
            "app_name": app.name,
            "mode": app.label,
            "schema_version": 2,
            "passed": passed,
            "_passed_via": "iter_loop",
            "iterations": (app.per_iter[-1].iter if app.per_iter else 0),
            "max_iters": app.max_iters,
            "total_elapsed_s": app.app_wall_s(),
            "wall_elapsed_s": wall_elapsed_s,
            "total_opencode_elapsed_s": total_opencode_elapsed_s,
            "total_validation_elapsed_s": total_validation_elapsed_s,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_tokens,
            "per_iteration": per_iter,
            "loop_attempt_final": app.loop_attempt,
            "loop_attempts_total": app.loop_attempt,
            "loop_stall_count": app.loop_stall_count,
            "loop_max_iters_count": app.loop_max_iters_count,
            "prior_loop_attempts": [
                {
                    "attempt": a.attempt,
                    "outcome": a.outcome,
                    "iters_run": a.iters_run,
                    "stall_iteration": a.stall_iteration,
                }
                for a in app.prior_attempts
            ],
        }
        if not passed:
            payload["stall_aborted"] = app.final_stall_aborted
            payload["stall_iteration"] = app.final_stall_iteration
        _atomic_write_json(app.log_dir / "result.json", payload)

    def _write_per_app_parallel_timing(self, app: AppRun) -> None:
        payload = {
            "schema": "parallel_timing_v1",
            "app_name": app.name,
            "label": app.label,
            "per_iter": [
                {
                    "iter": m.iter,
                    "gen_wall_s": m.gen_wall_s,
                    "val_wall_s": m.val_wall_s,
                    "tokens_total": m.tokens_total,
                    "validation_passed": m.validation_passed,
                    "stall_aborted": m.stall_aborted,
                    "gen_queue_wait_s": m.gen_queue_wait_s,
                    "val_queue_wait_s": m.val_queue_wait_s,
                    "gen_started_at": m.gen_started_at,
                    "val_started_at": m.val_started_at,
                    "gen_exit_code": m.gen_exit_code,
                    "val_exit_code": m.val_exit_code,
                }
                for m in app.per_iter
            ],
            "app_wall_s": app.app_wall_s(),
            "bench_wall_s": app.bench_wall_s,
            "bench_queue_wait_s": app.bench_queue_wait_s,
            "bench_started_at": app.bench_started_at,
            "bench_exit_code": app.bench_exit_code,
            "loop_attempts_total": app.loop_attempt,
            "loop_stall_count": app.loop_stall_count,
            "loop_max_iters_count": app.loop_max_iters_count,
            "verdict": "PASS" if app.state == AppState.DONE_PASSED else
                       ("FAIL" if app.state == AppState.DONE_FAILED else "IN_PROGRESS"),
        }
        _atomic_write_json(app.log_dir / "parallel_timing.json", payload)

    def _write_experiment_timing(self, *, status: str) -> None:
        now_mono = time.monotonic()
        payload = {
            "schema": "parallel_experiment_timing_v1",
            "started_at": self.experiment_started_at_wall,
            "finished_at": _utc_iso() if status != "running" else None,
            "experiment_wall_clock_s": now_mono - self.experiment_started_at,
            "status": status,
            "max_gen_workers": self.max_gen_workers,
            "n_apps": len(self.apps),
            "skip_bench": self.skip_bench,
            "per_app": {
                name: {
                    "state": app.state.value,
                    "iter": app.iter,
                    "loop_attempt": app.loop_attempt,
                    "app_wall_s": app.app_wall_s(),
                    "bench_wall_s": app.bench_wall_s,
                    "bench_queue_wait_s": app.bench_queue_wait_s,
                    "verdict": ("PASS" if app.state == AppState.DONE_PASSED else
                                "FAIL" if app.state == AppState.DONE_FAILED else
                                "IN_PROGRESS"),
                }
                for name, app in self.apps.items()
            },
        }
        _atomic_write_json(EXP_STATE_DIR / "parallel_experiment_timing.json", payload)


# --- CLI ----------------------------------------------------------------------
def _parse_apps(arg: str) -> list[str]:
    apps = [a.strip() for a in arg.split(",") if a.strip()]
    if not apps:
        raise argparse.ArgumentTypeError("--apps must list at least one app")
    if len(set(apps)) != len(apps):
        raise argparse.ArgumentTypeError(f"--apps contains duplicates: {apps}")
    return apps


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Parallel LLM-gen + serialized executor orchestrator",
    )
    parser.add_argument("--apps", required=True, type=_parse_apps,
                        help="Comma-separated app names (e.g. Nyx,SAMRAI,HPCG)")
    parser.add_argument("--max-gen-workers", type=int, default=3,
                        help="Concurrent OpenCode generators (default 3)")
    parser.add_argument("--max-iters", type=int, default=50,
                        help="Max iterations per loop attempt (default 50)")
    parser.add_argument("--benchmark-num-runs", type=int, default=3,
                        help="n for the post-PASS benchmark (default 3)")
    parser.add_argument("--label", default="baseline",
                        help="Label used in build/tests_<LABEL>/ and "
                             "build/iterative_logs/<APP>_<LABEL>/ "
                             "(default baseline, honors MODEL_TAG env via wrapper)")
    parser.add_argument("--opencode-retries", type=int, default=2,
                        help="D3 retry budget — max_loop_attempts = 1 + this (default 2)")
    parser.add_argument("--skip-bench", action="store_true",
                        help="Skip the post-PASS benchmark stage")
    parser.add_argument("--resume", action="store_true",
                        help="Resume an interrupted run.  For each --apps "
                             "entry, scan build/iterative_logs/<APP>_<LABEL>/ "
                             "and restore prior state from result.json, "
                             "parallel_timing.json, and iter_*/metrics.json. "
                             "Apps with a PASS verdict or exhausted retry "
                             "budget are skipped; in-progress apps continue "
                             "from iter+1.  Without this flag the prior "
                             "state is ignored and iter dirs may be "
                             "overwritten from iter 1.")
    parser.add_argument("--validate-timeout-s", type=float, default=900.0,
                        help="Per-iter VALIDATE wall cap in seconds (default 900 = "
                             "15 min). On timeout the executor SIGKILLs the entire "
                             "process group (mpirun + ranks) and records VALIDATE "
                             "FAIL so the host-wide mpirun lane cannot wedge on a "
                             "deadlocked LLM-generated checkpoint/restart routine "
                             "(see _TIMEOUT_KILLED.txt for the per-iter marker the "
                             "next-iter LLM prompt surfaces).")
    args = parser.parse_args(argv)

    # Per the MODEL_TAG convention in run_iterative.sh, allow env-driven
    # label sharding without forcing the user to type it on the CLI.
    tag = os.environ.get("MODEL_TAG", "").strip()
    label = args.label
    if tag and not label.endswith(f"_{tag}"):
        label = f"{label}_{tag}"

    orch = Orchestrator(
        app_names=args.apps,
        max_gen_workers=args.max_gen_workers,
        max_iters=args.max_iters,
        benchmark_num_runs=args.benchmark_num_runs,
        label=label,
        opencode_retries=args.opencode_retries,
        skip_bench=args.skip_bench,
        validate_timeout_s=args.validate_timeout_s,
        resume=args.resume,
    )
    return orch.run()


if __name__ == "__main__":
    sys.exit(main())
