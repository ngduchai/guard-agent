"""
criu_runner.py – CRIU checkpoint/restart orchestration for the
VeloC validation framework.

Provides OS-level transparent checkpointing via CRIU as a comparison
baseline against VeloC's application-level approach.

Requires:
  - ``criu`` binary (install via ``scripts/install_criu.sh``)
  - Kernel with ``CONFIG_CHECKPOINT_RESTORE=y``
  - ptrace permission on child processes

Key advantages over DMTCP/MANA:
  - Uses **unmodified application binaries** (no stub libraries)
  - Standard ``mpirun`` launch (no wrapper binaries or coordinator)
  - Kernel-level checkpointing (no MPI library interception needed)
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import threading
import time
from pathlib import Path

from .runner import RunResult, ValidationError, _find_executable


# ---------------------------------------------------------------------------
# CRIU tool discovery
# ---------------------------------------------------------------------------

_MARKER_FILE = Path.home() / ".local" / "share" / "guard-agent" / "criu_prefix"


def _resolve_criu_bin() -> str | None:
    """Find the ``criu`` binary.

    Search order:
      1. Marker file ``~/.local/share/guard-agent/criu_prefix``
      2. Default location ``~/.local/sbin/criu``
      3. System PATH
    """
    # 1. Marker file.
    if _MARKER_FILE.exists():
        try:
            prefix = _MARKER_FILE.read_text().strip()
            for subdir in ("sbin", "bin"):
                candidate = Path(prefix) / subdir / "criu"
                if candidate.exists():
                    return str(candidate)
        except OSError:
            pass

    # 2. Default location.
    default = Path.home() / ".local" / "sbin" / "criu"
    if default.exists():
        return str(default)

    # 3. System PATH.
    result = shutil.which("criu")
    return result


def check_criu_available() -> bool:
    """Return True if ``criu`` binary can be found."""
    return _resolve_criu_bin() is not None


def require_criu() -> str:
    """Return path to ``criu`` binary; raise if not available."""
    criu = _resolve_criu_bin()
    if criu is None:
        raise RuntimeError(
            "CRIU not found. Install via: ./scripts/install_criu.sh"
        )
    return criu


# ---------------------------------------------------------------------------
# Checkpoint size measurement
# ---------------------------------------------------------------------------

def measure_checkpoint_size(ckpt_dir: Path) -> int | None:
    """Sum the sizes of all CRIU image files under *ckpt_dir*."""
    total = 0
    count = 0
    for root, _dirs, files in os.walk(ckpt_dir):
        for fname in files:
            if fname.endswith(".img") or fname.endswith(".log"):
                try:
                    total += (Path(root) / fname).stat().st_size
                    count += 1
                except OSError:
                    pass
    return total if count > 0 else None


# ---------------------------------------------------------------------------
# Process discovery
# ---------------------------------------------------------------------------

def _find_rank_pids(executable_name: str, parent_pid: int) -> list[int]:
    """Find PIDs of MPI rank processes matching *executable_name*."""
    try:
        out = subprocess.check_output(
            ["ps", "-o", "pid,ppid,cmd", "--no-headers", "-e"],
            text=True,
        )
    except Exception:
        return []

    pids = []
    for line in out.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        cmd = parts[2]
        if (executable_name in cmd
                and "mpirun" not in cmd
                and "python" not in cmd
                and "criu" not in cmd):
            pids.append(pid)
    return pids


# ---------------------------------------------------------------------------
# Environment preparation
# ---------------------------------------------------------------------------

def _prepare_criu_env(env: dict | None) -> dict:
    """Prepare environment for CRIU-launched processes."""
    run_env = dict(os.environ if env is None else env)
    # Disable hwloc Linux I/O component (same as DMTCP runner).
    hwloc = run_env.get("HWLOC_COMPONENTS", "")
    if "-linuxio" not in hwloc:
        run_env["HWLOC_COMPONENTS"] = (
            f"{hwloc},-linuxio" if hwloc else "-linuxio"
        )
    return run_env


# ---------------------------------------------------------------------------
# Clean run (no failure injection)
# ---------------------------------------------------------------------------

def criu_run_once(
    build_dir: Path,
    executable_name: str,
    num_procs: int,
    app_args: list[str],
    output_dir: Path,
    ckpt_dir: Path,
    run_cwd: Path | None = None,
    env: dict | None = None,
    memory_monitor_fn: "callable | None" = None,
    memory_stop_event: "threading.Event | None" = None,
    memory_samples_holder: "list | None" = None,
) -> RunResult:
    """Launch the application under mpirun, without failure injection.

    This is essentially a standard MPI run (no CRIU wrapping needed for
    clean runs).  CRIU only acts during checkpoint/restore.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    exe_path = _find_executable(build_dir, executable_name)
    cwd = run_cwd if run_cwd is not None else output_dir
    cwd.mkdir(parents=True, exist_ok=True)

    stdout_path = output_dir / "stdout.txt"
    stderr_path = output_dir / "stderr.txt"

    run_env = _prepare_criu_env(env)

    # Add library paths for VeloC/MPI dependencies.
    veloc_lib = Path.home() / ".local" / "lib64"
    if veloc_lib.exists():
        ld = run_env.get("LD_LIBRARY_PATH", "")
        if str(veloc_lib) not in ld:
            run_env["LD_LIBRARY_PATH"] = f"{veloc_lib}:{ld}" if ld else str(veloc_lib)

    cmd = ["mpirun", "-np", str(num_procs), str(exe_path), *app_args]
    print(f"[criu] starting MPI run (cwd={cwd}): {' '.join(cmd)}", flush=True)

    t0 = time.monotonic()
    with stdout_path.open("wb") as out_f, stderr_path.open("wb") as err_f:
        proc = subprocess.Popen(
            cmd, cwd=str(cwd), stdout=out_f, stderr=err_f, env=run_env,
        )

        mem_thread = None
        if memory_monitor_fn and memory_stop_event and memory_samples_holder is not None:
            mem_thread = threading.Thread(
                target=memory_monitor_fn,
                args=(proc.pid, memory_samples_holder, memory_stop_event),
                daemon=True,
            )
            mem_thread.start()

        exit_code = proc.wait()

    elapsed = time.monotonic() - t0

    if mem_thread is not None and memory_stop_event is not None:
        memory_stop_event.set()
        mem_thread.join(timeout=5.0)

    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")

    return RunResult(
        exit_code=exit_code,
        stdout=stdout_text,
        stderr=stderr_text,
        elapsed_s=elapsed,
        injected=False,
        num_attempts=1,
        output_dir=output_dir,
        last_attempt_elapsed_s=elapsed,
        memory_samples_bytes=(
            memory_samples_holder[0] if memory_samples_holder and memory_samples_holder[0] else []
        ),
    )


# ---------------------------------------------------------------------------
# Run with failure injection (checkpoint → kill → restore)
# ---------------------------------------------------------------------------

def criu_run_with_failure_injection(
    build_dir: Path,
    executable_name: str,
    num_procs: int,
    app_args: list[str],
    output_dir: Path,
    ckpt_dir: Path,
    injection_delay: float = 5.0,
    run_cwd: Path | None = None,
    env: dict | None = None,
    memory_monitor_fn: "callable | None" = None,
    memory_stop_event: "threading.Event | None" = None,
    memory_samples_holder: "list | None" = None,
) -> RunResult:
    """CRIU failure-injection flow: launch → checkpoint → kill → restore."""
    criu = require_criu()
    output_dir.mkdir(parents=True, exist_ok=True)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    exe_path = _find_executable(build_dir, executable_name)
    cwd = run_cwd if run_cwd is not None else output_dir
    cwd.mkdir(parents=True, exist_ok=True)

    stdout_path = output_dir / "stdout.txt"
    stderr_path = output_dir / "stderr.txt"
    restore_stdout = output_dir / "stdout_restore.txt"
    restore_stderr = output_dir / "stderr_restore.txt"

    all_mem_samples: list[int] = []

    run_env = _prepare_criu_env(env)
    veloc_lib = Path.home() / ".local" / "lib64"
    if veloc_lib.exists():
        ld = run_env.get("LD_LIBRARY_PATH", "")
        if str(veloc_lib) not in ld:
            run_env["LD_LIBRARY_PATH"] = f"{veloc_lib}:{ld}" if ld else str(veloc_lib)

    # ── Phase 1: launch MPI app normally ─────────────────────────────────
    cmd = ["mpirun", "-np", str(num_procs), str(exe_path), *app_args]
    print(
        f"[criu] starting MPI run (cwd={cwd}): {' '.join(cmd)}",
        flush=True,
    )

    t0 = time.monotonic()
    out_f = stdout_path.open("wb")
    err_f = stderr_path.open("wb")
    try:
        mpi_proc = subprocess.Popen(
            cmd, cwd=str(cwd), stdout=out_f, stderr=err_f, env=run_env,
        )
    except Exception:
        out_f.close()
        err_f.close()
        raise

    mem_thread = None
    if memory_monitor_fn and memory_stop_event and memory_samples_holder is not None:
        memory_stop_event.clear()
        memory_samples_holder[0] = []
        mem_thread = threading.Thread(
            target=memory_monitor_fn,
            args=(mpi_proc.pid, memory_samples_holder, memory_stop_event),
            daemon=True,
        )
        mem_thread.start()

    # ── Phase 2: wait, then checkpoint ───────────────────────────────────
    # Wait for the injection delay before checkpointing.
    print(
        f"[criu] waiting {injection_delay}s before checkpoint ...",
        flush=True,
    )
    wait_until = time.monotonic() + injection_delay
    while time.monotonic() < wait_until:
        if mpi_proc.poll() is not None:
            break
        time.sleep(0.5)

    # Check if app already finished.
    if mpi_proc.poll() is not None:
        out_f.close()
        err_f.close()
        elapsed = time.monotonic() - t0
        if mem_thread is not None and memory_stop_event is not None:
            memory_stop_event.set()
            mem_thread.join(timeout=5.0)
            all_mem_samples.extend(memory_samples_holder[0])
        stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
        stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
        print(
            f"[criu] app finished before checkpoint (exit={mpi_proc.returncode}, "
            f"elapsed={elapsed:.2f}s)",
            flush=True,
        )
        return RunResult(
            exit_code=mpi_proc.returncode,
            stdout=stdout_text,
            stderr=stderr_text,
            elapsed_s=elapsed,
            injected=False,
            num_attempts=1,
            output_dir=output_dir,
            last_attempt_elapsed_s=elapsed,
            memory_samples_bytes=all_mem_samples,
        )

    # Checkpoint the mpirun process tree.
    print(
        f"[criu] checkpointing process tree (pid={mpi_proc.pid}) ...",
        flush=True,
    )
    dump_log = ckpt_dir / "dump.log"
    dump_cmd = [
        criu, "dump",
        "--tree", str(mpi_proc.pid),
        "--leave-running",
        "--tcp-established",
        "--shell-job",
        "--file-locks",
        "-D", str(ckpt_dir),
        "-o", str(dump_log),
        "-v4",
    ]
    dump_result = subprocess.run(
        dump_cmd, capture_output=True, text=True, timeout=120,
    )

    if dump_result.returncode != 0:
        print(
            f"[criu] checkpoint failed (exit={dump_result.returncode}): "
            f"{dump_result.stderr.strip()[:200]}",
            flush=True,
        )
        # Try to read dump log for details.
        if dump_log.exists():
            log_tail = dump_log.read_text(errors="replace").strip().splitlines()[-5:]
            print(
                f"[criu] dump.log (last {len(log_tail)} lines):\n"
                + "\n".join(f"  {l}" for l in log_tail),
                flush=True,
            )
        # Let the app continue and return as non-injected.
        mpi_proc.wait()
        out_f.close()
        err_f.close()
        elapsed = time.monotonic() - t0
        if mem_thread is not None and memory_stop_event is not None:
            memory_stop_event.set()
            mem_thread.join(timeout=5.0)
            all_mem_samples.extend(memory_samples_holder[0])
        return RunResult(
            exit_code=mpi_proc.returncode,
            stdout=stdout_path.read_text(encoding="utf-8", errors="replace"),
            stderr=stderr_path.read_text(encoding="utf-8", errors="replace"),
            elapsed_s=elapsed,
            injected=False,
            num_attempts=1,
            output_dir=output_dir,
            last_attempt_elapsed_s=elapsed,
            memory_samples_bytes=all_mem_samples,
        )

    ckpt_size = measure_checkpoint_size(ckpt_dir)
    print(
        f"[criu] checkpoint completed "
        f"({ckpt_size / 1024 / 1024:.1f} MB)" if ckpt_size else
        "[criu] checkpoint completed",
        flush=True,
    )

    # ── Phase 3: kill one rank (failure injection) ───────────────────────
    rank_pids = _find_rank_pids(executable_name, mpi_proc.pid)
    killed = False
    if rank_pids:
        target_pid = rank_pids[0]
        print(f"[criu] killing rank pid={target_pid} (SIGKILL)", flush=True)
        try:
            os.kill(target_pid, signal.SIGKILL)
            killed = True
        except ProcessLookupError:
            print("[criu] rank already dead", flush=True)
    else:
        print("[criu] WARNING: could not find rank PID to kill", flush=True)

    # Wait for mpirun to exit (it should crash due to dead rank).
    mpi_proc.wait()
    out_f.close()
    err_f.close()
    t_kill = time.monotonic()

    if mem_thread is not None and memory_stop_event is not None:
        memory_stop_event.set()
        mem_thread.join(timeout=5.0)
        all_mem_samples.extend(memory_samples_holder[0])

    print(
        f"[criu] initial phase done (exit={mpi_proc.returncode}, "
        f"killed={killed}, elapsed={t_kill - t0:.2f}s)",
        flush=True,
    )

    if not killed:
        stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
        stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
        print(
            "[criu] App completed before failure could be injected.",
            flush=True,
        )
        return RunResult(
            exit_code=mpi_proc.returncode,
            stdout=stdout_text,
            stderr=stderr_text,
            elapsed_s=t_kill - t0,
            injected=False,
            num_attempts=1,
            output_dir=output_dir,
            last_attempt_elapsed_s=t_kill - t0,
            memory_samples_bytes=all_mem_samples,
        )

    # ── Phase 4: restore from checkpoint ─────────────────────────────────
    restore_log = ckpt_dir / "restore.log"
    restore_cmd = [
        criu, "restore",
        "--tcp-established",
        "--shell-job",
        "--file-locks",
        "-d",
        "-D", str(ckpt_dir),
        "-o", str(restore_log),
        "-v4",
    ]
    print(f"[criu] restoring from checkpoint ...", flush=True)

    t_restore = time.monotonic()
    restore_result = subprocess.run(
        restore_cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=120,
        env=run_env,
    )

    if restore_result.returncode != 0:
        print(
            f"[criu] restore failed (exit={restore_result.returncode}): "
            f"{restore_result.stderr.strip()[:200]}",
            flush=True,
        )
        if restore_log.exists():
            log_tail = restore_log.read_text(errors="replace").strip().splitlines()[-5:]
            print(
                f"[criu] restore.log (last {len(log_tail)} lines):\n"
                + "\n".join(f"  {l}" for l in log_tail),
                flush=True,
            )
        stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
        stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
        raise ValidationError(
            "CRIU restore failed. Cannot continue.",
            stdout=stdout_text,
            stderr=stderr_text,
            exit_code=restore_result.returncode,
            output_dir=output_dir,
        )

    # Wait for the restored process to complete.
    # After `criu restore -d`, the process tree is running in background.
    # We need to wait for the mpirun PID to finish.
    print("[criu] restore completed, waiting for app to finish ...", flush=True)

    # Poll for the restored mpirun process to exit.
    _RESTORE_TIMEOUT = 600.0  # 10 minutes max
    poll_deadline = time.monotonic() + _RESTORE_TIMEOUT
    restore_exit = None
    while time.monotonic() < poll_deadline:
        try:
            pid_result = os.waitpid(mpi_proc.pid, os.WNOHANG)
            if pid_result[0] != 0:
                restore_exit = os.WEXITSTATUS(pid_result[1]) if os.WIFEXITED(pid_result[1]) else -1
                break
        except ChildProcessError:
            # Process already reaped or not our child — check if still running.
            try:
                os.kill(mpi_proc.pid, 0)  # signal 0 = check existence
                time.sleep(0.5)
            except ProcessLookupError:
                restore_exit = 0  # Process gone, assume success
                break
        time.sleep(0.5)

    if restore_exit is None:
        print("[criu] WARNING: restored process timed out", flush=True)
        try:
            os.kill(mpi_proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        restore_exit = -1

    t1 = time.monotonic()
    total_elapsed = t1 - t0
    restore_elapsed = t1 - t_restore

    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")

    print(
        f"[criu] completed: exit={restore_exit}, "
        f"restore_elapsed={restore_elapsed:.2f}s, total={total_elapsed:.2f}s",
        flush=True,
    )

    return RunResult(
        exit_code=restore_exit,
        stdout=stdout_text,
        stderr=stderr_text,
        elapsed_s=total_elapsed,
        injected=True,
        num_attempts=1,
        output_dir=output_dir,
        last_attempt_elapsed_s=restore_elapsed,
        memory_samples_bytes=all_mem_samples,
    )
