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
- Read (read-only) any file under these external directories — they hold
  the previous attempt(s) validator output and your build logs, and you
  MUST consult them to understand exactly how/why the previous attempt
  was rejected before you start editing code:
    * /home/ndhai/diaspora/guard-agent/build/iterative_logs/
      (per-iter prompt.txt, build_output.txt, opencode_stdout.txt,
       validate_stdout.txt, validate_stderr.txt, metrics.json)
    * /home/ndhai/diaspora/guard-agent/build/validation_output/
      (validator artifacts: correctness/resilient*, benchmarks/, proof JSON,
       raw_metrics.json — the validator stderr at the previous iter dir
       (validate_stderr.txt) contains the exact gate / fatal that rejected
       the previous attempt; read it first.)

================================================================================
YOU MAY NOT
================================================================================
- Modify any file outside this codebase directory tree.
- Delegate work to sub-agents.
- Take any action whose purpose is to make a validator gate pass
  without performing real state capture on checkpoint and real state
  load on restart.
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


# --- Prompt building (mirrors run_iterative.sh iter-1 + iter-2+ templates) ---
def _build_prompt(app: AppRun, iter_n: int) -> str:
    initial_prompt_path = app.app_dir / "prompt.txt"
    initial_prompt = initial_prompt_path.read_text() if initial_prompt_path.exists() else ""

    if iter_n == 1:
        return f"{ANTI_GAMING_DIRECTIVE}\n\n{initial_prompt}"

    prev_log = app.log_dir / f"iter_{iter_n - 1}"
    app_out_dir = BUILD_DIR / "validation_output" / f"{app.name}_{app.label}" / "correctness"
    body = (
        f"{ANTI_GAMING_DIRECTIVE}\n\n"
        f"Your previous attempt was rejected by the validation pipeline. Inspect\n"
        f"the artifacts under these directories and fix the code.\n\n"
        f"  {prev_log}\n"
        f"  {app_out_dir}/resilient\n"
        f"  {app_out_dir}/resilient_clean"
    )
    # If the previous iter hit the watchdog timeout, surface the marker
    # contents directly so the LLM cannot miss it.  Standard validate
    # stderr is often truncated mid-stream when SIGKILL fires.
    timeout_marker = prev_log / "_TIMEOUT_KILLED.txt"
    if timeout_marker.exists():
        with contextlib.suppress(Exception):
            body += "\n\n" + timeout_marker.read_text()
    return body


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
    ):
        self.max_gen_workers = max_gen_workers
        self.label = label
        self.skip_bench = skip_bench
        self.validate_timeout_s = validate_timeout_s
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
                benchmark_num_runs=benchmark_num_runs,
            )

        # Concurrency primitives.  Single RLock guards ALL mutable state on
        # AppRun objects + the timing index dict.  No nested-lock scenarios
        # are introduced; queue.Queue has its own internal lock and is safe
        # to call under or outside our lock.
        self.state_lock = threading.RLock()
        self.ready_for_gen: queue.Queue = queue.Queue()
        self.executor_queue: queue.Queue = queue.Queue()
        self.stop_event = threading.Event()
        self.all_done_event = threading.Event()
        self.remaining = len(self.apps)

    # --- Public entry point --------------------------------------------------
    def run(self) -> int:
        EXP_STATE_DIR.mkdir(parents=True, exist_ok=True)
        ITERATIVE_LOGS.mkdir(parents=True, exist_ok=True)
        RUN_LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self._claim_pid_file()

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
                with self.state_lock:
                    app.state = AppState.READY_FOR_GEN
                    app.queued_for_gen_at = time.monotonic()
                    app.app_started_at = time.monotonic()
                self.ready_for_gen.put(app.name)

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
                gen_queue_wait_s=gen_queue_wait_s,
                gen_started_at=gen_started_wall,
                gen_exit_code=rc,
            ))

            if stall_aborted:
                # Skip validation; record loop-attempt outcome and decide D3.
                self._finalize_loop_attempt(app, outcome="stall",
                                            iters_run=iter_n,
                                            stall_iteration=iter_n)
                return

            app.state = AppState.QUEUED_FOR_EXECUTOR
            app.queued_for_executor_at = time.monotonic()

        print(f"[gen] {app.name} iter {iter_n} DONE gen ({gen_wall_s:.1f}s) "
              f"-> queued for executor", flush=True)
        self.executor_queue.put((app.name, "validate", iter_n))

    # --- Executor (serialized) loop -----------------------------------------
    def _executor_loop(self) -> None:
        while not self.stop_event.is_set():
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
    )
    return orch.run()


if __name__ == "__main__":
    sys.exit(main())
