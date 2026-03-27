"""
dmtcp_runner.py – DMTCP/MANA checkpoint/restart orchestration for the
VeloC validation framework.

Provides transparent (process-level) checkpointing via DMTCP as a
comparison baseline against VeloC's application-level approach.

Requires:
  - dmtcp_launch, dmtcp_coordinator, dmtcp_command, dmtcp_restart
    (auto-discovered at $HOME/.local, marker file, or PATH)
  - MANA plugin for MPI support (https://github.com/mpickpt/mana)

Key differences from VeloC runner (runner.py):
  - Checkpoint is triggered externally via ``dmtcp_command --checkpoint``
  - Restart restores the full process image via ``dmtcp_restart``
  - A coordinator daemon must run alongside the application
  - No application source code changes required
"""

from __future__ import annotations

import glob
import os
import shutil
import signal
import subprocess
import threading
import time
from dataclasses import field
from pathlib import Path

from .runner import RunResult, ValidationError, configure_and_build, _find_executable


# ---------------------------------------------------------------------------
# DMTCP tool discovery
# ---------------------------------------------------------------------------

_DMTCP_TOOLS = ["dmtcp_launch", "dmtcp_coordinator", "dmtcp_command", "dmtcp_restart"]

_MARKER_FILE = Path.home() / ".local" / "share" / "guard-agent" / "dmtcp_prefix"


def _resolve_dmtcp_bin(install_prefix: str | None = None) -> Path | None:
    """Find the DMTCP bin/ directory using multiple search strategies.

    Priority:
      1. Explicit *install_prefix* argument (from approaches config)
      2. Marker file ``~/.local/share/guard-agent/dmtcp_prefix``
         (written by ``scripts/install_dmtcp_mana.sh``)
      3. Default location ``~/.local/bin``
      4. Legacy location ``~/dmtcp/bin``
      5. System PATH (via ``shutil.which``)

    Returns the bin directory ``Path`` or ``None`` if not found.
    """
    candidates: list[Path] = []

    # 1. Explicit prefix.
    if install_prefix:
        candidates.append(Path(install_prefix) / "bin")

    # 2. Marker file.
    if _MARKER_FILE.exists():
        try:
            marker_prefix = _MARKER_FILE.read_text().strip()
            if marker_prefix:
                candidates.append(Path(marker_prefix) / "bin")
        except OSError:
            pass

    # 3. Default location.
    candidates.append(Path.home() / ".local" / "bin")

    # 4. Legacy location.
    candidates.append(Path.home() / "dmtcp" / "bin")

    for bin_dir in candidates:
        if (bin_dir / "dmtcp_launch").exists():
            return bin_dir

    # 5. Fall back to PATH.
    path_result = shutil.which("dmtcp_launch")
    if path_result:
        return Path(path_result).parent

    return None


def check_dmtcp_available(install_prefix: str | None = None) -> bool:
    """Return True if all required DMTCP tools can be found."""
    bin_dir = _resolve_dmtcp_bin(install_prefix)
    if bin_dir is None:
        return False
    return all((bin_dir / t).exists() for t in _DMTCP_TOOLS)


def require_dmtcp(install_prefix: str | None = None) -> dict[str, str]:
    """Locate all DMTCP tools and return a name → path mapping.

    Raises ``RuntimeError`` if any tool is missing.
    """
    bin_dir = _resolve_dmtcp_bin(install_prefix)
    if bin_dir is None:
        raise RuntimeError(
            "DMTCP tools not found. Install via: ./scripts/install_dmtcp_mana.sh"
        )

    tool_paths: dict[str, str] = {}
    missing: list[str] = []
    for t in _DMTCP_TOOLS:
        p = bin_dir / t
        if p.exists():
            tool_paths[t] = str(p)
        else:
            missing.append(t)

    if missing:
        raise RuntimeError(
            f"DMTCP tools not found in {bin_dir}: {', '.join(missing)}. "
            "Install DMTCP+MANA via scripts/install_dmtcp_mana.sh"
        )
    return tool_paths


# ---------------------------------------------------------------------------
# Coordinator management
# ---------------------------------------------------------------------------

def start_coordinator(
    port: int,
    ckpt_dir: Path,
    tool_paths: dict[str, str] | None = None,
    quiet: bool = True,
) -> subprocess.Popen:
    """Start a ``dmtcp_coordinator`` daemon on *port*."""
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    coordinator = (tool_paths or {}).get("dmtcp_coordinator", "dmtcp_coordinator")
    cmd = [
        coordinator,
        "--daemon",
        "--port", str(port),
        "--ckptdir", str(ckpt_dir),
    ]
    if quiet:
        cmd.append("--quiet")
    print(f"[dmtcp] starting coordinator: {' '.join(cmd)}", flush=True)
    proc = subprocess.Popen(cmd)
    proc.wait()  # --daemon forks; parent exits immediately
    time.sleep(0.5)
    return proc


def stop_coordinator(
    port: int,
    tool_paths: dict[str, str] | None = None,
) -> None:
    """Send a quit command to the coordinator on *port*."""
    dmtcp_command = (tool_paths or {}).get("dmtcp_command", "dmtcp_command")
    try:
        subprocess.run(
            [dmtcp_command, "--port", str(port), "--quit"],
            timeout=10,
            capture_output=True,
        )
    except Exception:
        pass


def _dmtcp_checkpoint(
    port: int,
    tool_paths: dict[str, str] | None = None,
    timeout: float = 120.0,
) -> bool:
    """Trigger a checkpoint and wait for it to complete."""
    dmtcp_command = (tool_paths or {}).get("dmtcp_command", "dmtcp_command")
    print(f"[dmtcp] triggering checkpoint on port {port} ...", flush=True)
    try:
        result = subprocess.run(
            [dmtcp_command, "--port", str(port), "--checkpoint"],
            timeout=timeout,
            capture_output=True,
            text=True,
        )
        ok = result.returncode == 0
        if ok:
            print("[dmtcp] checkpoint completed", flush=True)
        else:
            print(
                f"[dmtcp] checkpoint command returned {result.returncode}: "
                f"{result.stderr.strip()}",
                flush=True,
            )
        return ok
    except subprocess.TimeoutExpired:
        print("[dmtcp] checkpoint timed out", flush=True)
        return False
    except Exception as exc:
        print(f"[dmtcp] checkpoint error: {exc}", flush=True)
        return False


# ---------------------------------------------------------------------------
# Checkpoint size measurement
# ---------------------------------------------------------------------------

def _prepare_dmtcp_env(env: dict | None) -> dict:
    """Prepare environment variables for DMTCP-launched processes.

    Ensures ``HWLOC_COMPONENTS=-linuxio`` is set so that hwloc (used by
    Open MPI for topology discovery) does not enumerate block devices
    like ``/dev/nvme*``.  Without this, DMTCP's file-connection handler
    crashes with "Unimplemented file type" when it intercepts the
    ``openat`` call on the block device.
    """
    run_env = dict(os.environ if env is None else env)
    # Disable hwloc Linux I/O component to avoid block-device enumeration.
    hwloc = run_env.get("HWLOC_COMPONENTS", "")
    if "-linuxio" not in hwloc:
        run_env["HWLOC_COMPONENTS"] = (
            f"{hwloc},-linuxio" if hwloc else "-linuxio"
        )
    return run_env


def measure_checkpoint_size(ckpt_dir: Path) -> int | None:
    """Sum the sizes of all ``ckpt_*.dmtcp`` files in *ckpt_dir*."""
    total = 0
    count = 0
    for root, _dirs, files in os.walk(ckpt_dir):
        for fname in files:
            if fname.startswith("ckpt_") and fname.endswith(".dmtcp"):
                try:
                    total += (Path(root) / fname).stat().st_size
                    count += 1
                except OSError:
                    pass
    return total if count > 0 else None


# ---------------------------------------------------------------------------
# Clean run (no failure injection)
# ---------------------------------------------------------------------------

def dmtcp_run_once(
    build_dir: Path,
    executable_name: str,
    num_procs: int,
    app_args: list[str],
    output_dir: Path,
    ckpt_dir: Path,
    coord_port: int,
    run_cwd: Path | None = None,
    env: dict | None = None,
    install_prefix: str | None = None,
    memory_monitor_fn: "callable | None" = None,
    memory_stop_event: "threading.Event | None" = None,
    memory_samples_holder: "list | None" = None,
) -> RunResult:
    """Launch the application once under DMTCP, without failure injection."""
    tool_paths = require_dmtcp(install_prefix)
    output_dir.mkdir(parents=True, exist_ok=True)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    exe_path = _find_executable(build_dir, executable_name)
    cwd = run_cwd if run_cwd is not None else build_dir
    cwd.mkdir(parents=True, exist_ok=True)

    stdout_path = output_dir / "stdout.txt"
    stderr_path = output_dir / "stderr.txt"

    start_coordinator(coord_port, ckpt_dir, tool_paths)

    # Prepare environment with HWLOC_COMPONENTS=-linuxio to prevent
    # hwloc from opening block devices (e.g. /dev/nvme*) which causes
    # DMTCP to crash with "Unimplemented file type".
    run_env = _prepare_dmtcp_env(env)

    # Launch mpirun with dmtcp_launch wrapping only the application,
    # NOT mpirun itself.  Wrapping mpirun causes DMTCP to intercept
    # mpirun's internal hwloc/libudev file operations on block devices.
    cmd = [
        "mpirun", "-np", str(num_procs),
        tool_paths["dmtcp_launch"], "--coord-port", str(coord_port),
        str(exe_path), *app_args,
    ]
    print(f"[dmtcp] starting MPI run (cwd={cwd}): {' '.join(cmd)}", flush=True)

    t0 = time.monotonic()
    with stdout_path.open("wb") as out_f, stderr_path.open("wb") as err_f:
        proc = subprocess.Popen(cmd, cwd=str(cwd), stdout=out_f, stderr=err_f, env=run_env)

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

    stop_coordinator(coord_port, tool_paths)

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
# Run with failure injection (checkpoint → kill → restart)
# ---------------------------------------------------------------------------

def _find_rank_pid(executable_name: str) -> int | None:
    """Search the process table for a rank process matching *executable_name*."""
    try:
        out = subprocess.check_output(
            ["ps", "-o", "pid,ppid,cmd", "--no-headers"],
            text=True,
        )
    except Exception:
        return None

    for line in out.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        cmd = parts[2]
        if executable_name in cmd and "mpirun" not in cmd and "python" not in cmd and "dmtcp" not in cmd:
            return pid
    return None


def dmtcp_run_with_failure_injection(
    build_dir: Path,
    executable_name: str,
    num_procs: int,
    app_args: list[str],
    output_dir: Path,
    ckpt_dir: Path,
    coord_port: int,
    injection_delay: float = 5.0,
    run_cwd: Path | None = None,
    env: dict | None = None,
    install_prefix: str | None = None,
    memory_monitor_fn: "callable | None" = None,
    memory_stop_event: "threading.Event | None" = None,
    memory_samples_holder: "list | None" = None,
) -> RunResult:
    """DMTCP failure-injection flow: launch → checkpoint → kill → restart."""
    tool_paths = require_dmtcp(install_prefix)
    output_dir.mkdir(parents=True, exist_ok=True)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    exe_path = _find_executable(build_dir, executable_name)
    cwd = run_cwd if run_cwd is not None else output_dir
    cwd.mkdir(parents=True, exist_ok=True)

    stdout_path = output_dir / "stdout.txt"
    stderr_path = output_dir / "stderr.txt"
    restart_stdout = output_dir / "stdout_restart.txt"
    restart_stderr = output_dir / "stderr_restart.txt"

    all_mem_samples: list[int] = []

    # ── Phase 1: initial launch ──────────────────────────────────────────
    start_coordinator(coord_port, ckpt_dir, tool_paths)

    # Prepare environment with HWLOC_COMPONENTS=-linuxio to prevent
    # hwloc from opening block devices (e.g. /dev/nvme*) which causes
    # DMTCP to crash with "Unimplemented file type".
    run_env = _prepare_dmtcp_env(env)

    # Launch mpirun with dmtcp_launch wrapping only the application,
    # NOT mpirun itself.  Wrapping mpirun causes DMTCP to intercept
    # mpirun's internal hwloc/libudev file operations on block devices.
    cmd = [
        "mpirun", "-np", str(num_procs),
        tool_paths["dmtcp_launch"], "--coord-port", str(coord_port),
        str(exe_path), *app_args,
    ]
    print(
        f"[dmtcp] attempt: starting MPI run (cwd={cwd}): {' '.join(cmd)}",
        flush=True,
    )

    t0 = time.monotonic()
    with stdout_path.open("wb") as out_f, stderr_path.open("wb") as err_f:
        mpi_proc = subprocess.Popen(cmd, cwd=str(cwd), stdout=out_f, stderr=err_f, env=run_env)

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

    # ── Phase 2: wait, checkpoint, kill ──────────────────────────────────
    print(f"[dmtcp] waiting {injection_delay}s before checkpoint ...", flush=True)
    time.sleep(injection_delay)

    # Check if app already finished.
    poll = mpi_proc.poll()
    if poll is not None:
        elapsed = time.monotonic() - t0
        if mem_thread is not None and memory_stop_event is not None:
            memory_stop_event.set()
            mem_thread.join(timeout=5.0)
            all_mem_samples.extend(memory_samples_holder[0])
        stop_coordinator(coord_port, tool_paths)
        stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
        stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
        print(
            f"[dmtcp] app finished before injection (exit={poll}, elapsed={elapsed:.2f}s)",
            flush=True,
        )
        return RunResult(
            exit_code=poll,
            stdout=stdout_text,
            stderr=stderr_text,
            elapsed_s=elapsed,
            injected=False,
            num_attempts=1,
            output_dir=output_dir,
            last_attempt_elapsed_s=elapsed,
            memory_samples_bytes=all_mem_samples,
        )

    # Trigger checkpoint.
    ckpt_ok = _dmtcp_checkpoint(coord_port, tool_paths)
    if not ckpt_ok:
        print("[dmtcp] WARNING: checkpoint may have failed; proceeding with kill", flush=True)

    # Kill one MPI rank.
    rank_pid = _find_rank_pid(executable_name)
    if rank_pid is not None:
        print(f"[dmtcp] killing rank pid={rank_pid} (SIGKILL)", flush=True)
        try:
            os.kill(rank_pid, signal.SIGKILL)
        except ProcessLookupError:
            print("[dmtcp] rank already dead", flush=True)
    else:
        print("[dmtcp] WARNING: could not find rank PID to kill", flush=True)

    # Wait for mpirun to exit.
    mpi_proc.wait()
    t_kill = time.monotonic()

    # Stop memory monitor for initial phase.
    if mem_thread is not None and memory_stop_event is not None:
        memory_stop_event.set()
        mem_thread.join(timeout=5.0)
        all_mem_samples.extend(memory_samples_holder[0])

    print(
        f"[dmtcp] initial phase done (elapsed={t_kill - t0:.2f}s). Restarting ...",
        flush=True,
    )

    # ── Phase 3: restart from checkpoint ─────────────────────────────────
    ckpt_files = sorted(glob.glob(str(ckpt_dir / "ckpt_*.dmtcp")))
    restart_script = ckpt_dir / "dmtcp_restart_script.sh"

    if not ckpt_files and not restart_script.exists():
        stop_coordinator(coord_port, tool_paths)
        raise ValidationError(
            "DMTCP: no checkpoint files found after checkpoint command. "
            "Cannot restart.",
            stdout=stdout_path.read_text(encoding="utf-8", errors="replace"),
            stderr=stderr_path.read_text(encoding="utf-8", errors="replace"),
            exit_code=-1,
            output_dir=output_dir,
        )

    if restart_script.exists():
        restart_cmd = ["bash", str(restart_script)]
    else:
        restart_cmd = [
            tool_paths["dmtcp_restart"], "--coord-port", str(coord_port),
            *ckpt_files,
        ]

    print(f"[dmtcp] restarting: {' '.join(restart_cmd[:5])} ...", flush=True)

    t_restart = time.monotonic()
    with restart_stdout.open("wb") as out_f, restart_stderr.open("wb") as err_f:
        restart_proc = subprocess.Popen(
            restart_cmd, cwd=str(cwd), stdout=out_f, stderr=err_f, env=run_env
        )

        mem_thread_restart = None
        if memory_monitor_fn and memory_stop_event and memory_samples_holder is not None:
            memory_stop_event.clear()
            memory_samples_holder[0] = []
            mem_thread_restart = threading.Thread(
                target=memory_monitor_fn,
                args=(restart_proc.pid, memory_samples_holder, memory_stop_event),
                daemon=True,
            )
            mem_thread_restart.start()

        restart_exit = restart_proc.wait()

    t1 = time.monotonic()

    if mem_thread_restart is not None and memory_stop_event is not None:
        memory_stop_event.set()
        mem_thread_restart.join(timeout=5.0)
        all_mem_samples.extend(memory_samples_holder[0])

    stop_coordinator(coord_port, tool_paths)

    total_elapsed = t1 - t0
    restart_elapsed = t1 - t_restart

    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
    restart_stdout_text = restart_stdout.read_text(encoding="utf-8", errors="replace")
    combined_stdout = stdout_text + "\n--- DMTCP RESTART ---\n" + restart_stdout_text

    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    restart_stderr_text = restart_stderr.read_text(encoding="utf-8", errors="replace")
    combined_stderr = stderr_text + "\n--- DMTCP RESTART ---\n" + restart_stderr_text

    print(
        f"[dmtcp] restart completed: exit={restart_exit}, "
        f"restart_elapsed={restart_elapsed:.2f}s, total={total_elapsed:.2f}s",
        flush=True,
    )

    return RunResult(
        exit_code=restart_exit,
        stdout=combined_stdout,
        stderr=combined_stderr,
        elapsed_s=total_elapsed,
        injected=True,
        num_attempts=1,
        output_dir=output_dir,
        last_attempt_elapsed_s=restart_elapsed,
        memory_samples_bytes=all_mem_samples,
    )
