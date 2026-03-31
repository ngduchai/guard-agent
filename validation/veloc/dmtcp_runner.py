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
_MANA_TOOLS = ["mana_launch", "mana_restart"]

_MARKER_FILE = Path.home() / ".local" / "share" / "guard-agent" / "dmtcp_prefix"

# Default MANA source directory (written by install_dmtcp_mana.sh).
_MANA_SRC_DIR = Path.home() / ".local" / "share" / "guard-agent" / "dmtcp-src" / "mana"


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


def _resolve_mana_bin() -> Path | None:
    """Find the MANA bin/ directory.

    MANA tools (``mana_launch``, ``mana_restart``) live in the MANA
    source/build tree, not in the DMTCP install prefix.
    """
    candidate = _MANA_SRC_DIR / "bin"
    if candidate.exists() and (candidate / "mana_launch").exists():
        return candidate
    # Fall back to PATH.
    path_result = shutil.which("mana_launch")
    if path_result:
        return Path(path_result).parent
    return None


def detect_mana_root() -> Path | None:
    """Return the MANA source root if available, else None."""
    if _MANA_SRC_DIR.is_dir() and (_MANA_SRC_DIR / "bin" / "mana_launch").exists():
        return _MANA_SRC_DIR
    return None


def check_dmtcp_available(install_prefix: str | None = None) -> bool:
    """Return True if all required DMTCP tools can be found."""
    bin_dir = _resolve_dmtcp_bin(install_prefix)
    if bin_dir is None:
        return False
    return all((bin_dir / t).exists() for t in _DMTCP_TOOLS)


def check_mana_available() -> bool:
    """Return True if MANA tools (mana_launch, mana_restart) are available."""
    mana_bin = _resolve_mana_bin()
    if mana_bin is None:
        return False
    return all((mana_bin / t).exists() for t in _MANA_TOOLS)


def require_dmtcp(install_prefix: str | None = None) -> dict[str, str]:
    """Locate all DMTCP tools and return a name → path mapping.

    Also includes MANA tools if available (keyed as ``mana_launch``,
    ``mana_restart``).  Raises ``RuntimeError`` if core DMTCP tools are
    missing.
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

    # If MANA is available, prefer ALL tools from MANA's bin directory.
    # MANA has its own embedded DMTCP build (mana/dmtcp/) and the tools
    # must match — mixing standalone DMTCP tools with MANA's launcher
    # causes version mismatches and protocol errors.
    mana_bin = _resolve_mana_bin()
    if mana_bin is not None:
        all_mana_tools = _DMTCP_TOOLS + _MANA_TOOLS
        mana_has_all = all((mana_bin / t).exists() for t in all_mana_tools)
        if mana_has_all:
            for t in all_mana_tools:
                tool_paths[t] = str(mana_bin / t)
            print(
                f"[dmtcp] using MANA tools from {mana_bin}",
                flush=True,
            )
        else:
            # MANA partially available — add what we can.
            for t in _MANA_TOOLS:
                p = mana_bin / t
                if p.exists():
                    tool_paths[t] = str(p)

    return tool_paths


# ---------------------------------------------------------------------------
# Coordinator management
# ---------------------------------------------------------------------------

def start_coordinator(
    port: int,
    ckpt_dir: Path,
    tool_paths: dict[str, str] | None = None,
    quiet: bool = True,
    ckpt_interval: int | None = None,
) -> subprocess.Popen:
    """Start a ``dmtcp_coordinator`` daemon on *port*.

    When MANA tools are available, uses ``mana_start_coordinator`` which
    writes a ``~/.mana.rc`` status file that ``mana_launch`` requires
    to find the coordinator host and port.

    Parameters
    ----------
    ckpt_interval:
        If set, pass ``--interval <seconds>`` to the coordinator so that
        it triggers automatic periodic checkpoints.
    """
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    use_mana = "mana_launch" in (tool_paths or {})
    port_flag = "--coord-port" if use_mana else "--port"

    if use_mana:
        # Use mana_start_coordinator which creates ~/.mana.rc (required
        # by mana_launch to discover the coordinator).  It internally
        # calls dmtcp_coordinator with --status-file and --exit-on-last.
        mana_bin = Path((tool_paths or {})["mana_launch"]).parent
        mana_start = str(mana_bin / "mana_start_coordinator")
        cmd = [mana_start, port_flag, str(port), "--ckptdir", str(ckpt_dir)]
        # Do NOT pass --interval to MANA coordinator.  MANA's split-process
        # architecture needs time to initialise; aggressive periodic
        # checkpoints during startup crash the processes.  We rely on
        # manual checkpoint triggers instead (via dmtcp_command).
        if ckpt_interval is not None and ckpt_interval > 0:
            print(
                f"[dmtcp] NOTE: skipping --interval {ckpt_interval} for MANA "
                f"(using manual checkpoint triggers only)",
                flush=True,
            )
        print(f"[dmtcp] starting coordinator: {' '.join(cmd)}", flush=True)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.wait()
        time.sleep(0.5)
        return proc

    coordinator = (tool_paths or {}).get("dmtcp_coordinator", "dmtcp_coordinator")
    cmd = [
        coordinator,
        "--daemon",
        port_flag, str(port),
        "--ckptdir", str(ckpt_dir),
    ]
    if ckpt_interval is not None and ckpt_interval > 0:
        cmd.extend(["--interval", str(ckpt_interval)])
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
    use_mana = "mana_launch" in (tool_paths or {})
    port_flag = "--coord-port" if use_mana else "--port"
    cmd = [dmtcp_command, port_flag, str(port), "--quit"]
    if use_mana:
        import socket
        cmd = [dmtcp_command, "-h", socket.gethostname(), port_flag, str(port), "--quit"]
    try:
        subprocess.run(cmd, timeout=10, capture_output=True)
    except Exception:
        pass


def _dmtcp_checkpoint(
    port: int,
    tool_paths: dict[str, str] | None = None,
    timeout: float = 120.0,
) -> bool:
    """Trigger a checkpoint and wait for it to complete."""
    dmtcp_command = (tool_paths or {}).get("dmtcp_command", "dmtcp_command")
    use_mana = "mana_launch" in (tool_paths or {})
    port_flag = "--coord-port" if use_mana else "--port"
    cmd = [dmtcp_command, port_flag, str(port), "--checkpoint"]
    if use_mana:
        import socket
        cmd = [dmtcp_command, "-h", socket.gethostname(), port_flag, str(port), "--checkpoint"]
    print(f"[dmtcp] triggering checkpoint on port {port} ...", flush=True)
    try:
        result = subprocess.run(
            cmd,
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

def _prepare_dmtcp_env(
    env: dict | None,
    app_args: list[str] | None = None,
    use_mana: bool = False,
) -> dict:
    """Prepare environment variables for DMTCP-launched processes.

    Ensures ``HWLOC_COMPONENTS=-linuxio`` is set so that hwloc (used by
    Open MPI for topology discovery) does not enumerate block devices
    like ``/dev/nvme*``.  Without this, DMTCP's file-connection handler
    crashes with "Unimplemented file type" when it intercepts the
    ``openat`` call on the block device.

    When *use_mana* is True and *app_args* are provided, sets
    ``MANA_NUM_OUTER_ITER`` and ``MANA_CENTER`` environment variables as
    a workaround for MANA's ``deepCopyStack`` bug that corrupts
    ``argv[3]`` in the upper-half application.
    """
    run_env = dict(os.environ if env is None else env)
    # Disable hwloc Linux I/O component to avoid block-device enumeration.
    hwloc = run_env.get("HWLOC_COMPONENTS", "")
    if "-linuxio" not in hwloc:
        run_env["HWLOC_COMPONENTS"] = (
            f"{hwloc},-linuxio" if hwloc else "-linuxio"
        )
    # MANA argv workaround env flag (config file is written by caller).
    if use_mana:
        run_env["MANA_ACTIVE"] = "1"
    return run_env


def _write_mana_argv_override(cwd: Path, app_args: list[str]) -> None:
    """Write a config file with correct arg values for MANA.

    MANA's ``deepCopyStack`` corrupts ``argv[3]``.  The patched DMTCP
    app reads overrides from ``mana_argv_override.conf`` in its CWD.
    """
    if len(app_args) < 5:
        return
    cfg_path = cwd / "mana_argv_override.conf"
    with open(cfg_path, "w") as f:
        f.write(f"center={app_args[1]}\n")
        f.write(f"num_outer_iter={app_args[2]}\n")
        f.write(f"num_iter={app_args[3]}\n")
        f.write(f"beg_index={app_args[4]}\n")
        if len(app_args) >= 6:
            f.write(f"nslices={app_args[5]}\n")
    print(
        f"[dmtcp] MANA argv workaround: wrote {cfg_path} "
        f"(num_outer_iter={app_args[2]})",
        flush=True,
    )


def _find_ckpt_files(ckpt_dir: Path) -> list[str]:
    """Recursively find all ``ckpt_*.dmtcp`` files under *ckpt_dir*.

    DMTCP may write checkpoint files directly in *ckpt_dir* or in
    subdirectories.  This helper walks the entire tree so that files
    are found regardless of the directory layout.
    """
    found: list[str] = []
    for root, _dirs, files in os.walk(ckpt_dir):
        for fname in files:
            if fname.startswith("ckpt_") and fname.endswith(".dmtcp"):
                found.append(str(Path(root) / fname))
    return sorted(found)


def measure_checkpoint_size(ckpt_dir: Path) -> int | None:
    """Sum the sizes of all ``ckpt_*.dmtcp`` files in *ckpt_dir*."""
    total = 0
    count = 0
    for fpath in _find_ckpt_files(ckpt_dir):
        try:
            total += Path(fpath).stat().st_size
            count += 1
        except OSError:
            pass
    return total if count > 0 else None


# ---------------------------------------------------------------------------
# Clean run (no failure injection)
# ---------------------------------------------------------------------------

def _build_launch_cmd(
    tool_paths: dict[str, str],
    num_procs: int,
    coord_port: int,
    exe_path: Path,
    app_args: list[str],
    ckpt_dir: Path | None = None,
) -> list[str]:
    """Build the mpirun + launcher command.

    Uses ``mana_launch`` if available in *tool_paths* (required for MPI
    checkpoint/restart), otherwise falls back to plain ``dmtcp_launch``.
    """
    import socket
    use_mana = "mana_launch" in tool_paths
    if use_mana:
        coord_host = socket.gethostname()
        launcher_args = [
            tool_paths["mana_launch"],
            "--coord-host", coord_host,
            "--coord-port", str(coord_port),
        ]
        if ckpt_dir is not None:
            launcher_args.extend(["--ckptdir", str(ckpt_dir)])
        launcher_args.append("--no-gzip")
    else:
        launcher_args = [
            tool_paths["dmtcp_launch"], "--coord-port", str(coord_port),
        ]

    return [
        "mpirun", "-np", str(num_procs),
        *launcher_args,
        str(exe_path), *app_args,
    ]


def _build_restart_cmd(
    tool_paths: dict[str, str],
    num_procs: int,
    coord_port: int,
    ckpt_dir: Path,
    ckpt_files: list[str],
) -> list[str]:
    """Build the restart command.

    Uses ``mana_restart`` if available (wraps restart in mpirun),
    otherwise falls back to plain ``dmtcp_restart`` with checkpoint files.
    """
    import socket
    use_mana = "mana_restart" in tool_paths
    if use_mana:
        # MANA restart MUST go through mpirun to provide MPI context.
        # The restart script calls dmtcp_restart directly (no mpirun),
        # causing SIGSEGV because the restored lower-half process has
        # no PMI/MPI runtime environment.
        # Only pass --restartdir (not --ckptdir, --no-gzip, or
        # --coord-host/--coord-port which are not valid restart flags).
        return [
            "mpirun", "-np", str(num_procs),
            tool_paths["mana_restart"],
            "--restartdir", str(ckpt_dir),
        ]
    else:
        restart_script = ckpt_dir / "dmtcp_restart_script.sh"
        if restart_script.exists():
            return ["bash", str(restart_script)]
        return [
            tool_paths["dmtcp_restart"], "--coord-port", str(coord_port),
            *ckpt_files,
        ]


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

    use_mana = "mana_launch" in tool_paths
    run_env = _prepare_dmtcp_env(env, app_args=app_args, use_mana=use_mana)
    if use_mana:
        _write_mana_argv_override(cwd, app_args)

    cmd = _build_launch_cmd(
        tool_paths, num_procs, coord_port, exe_path, app_args, ckpt_dir,
    )
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
            ["ps", "-e", "-o", "pid,ppid,cmd", "--no-headers"],
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
        if (executable_name in cmd
                and "mpirun" not in cmd
                and "python" not in cmd
                and "mana_launch" not in cmd
                and "dmtcp_launch" not in cmd
                and "dmtcp_command" not in cmd
                and "dmtcp_coordinator" not in cmd
                and "dmtcp_restart" not in cmd):
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
    # Always use the minimum periodic checkpoint interval (1s) so that
    # short-running applications get at least one checkpoint before they
    # finish.  The previous formula ``max(1, injection_delay // 2)``
    # produced intervals larger than the application runtime for long
    # injection delays, causing zero checkpoint files.
    ckpt_interval = 1
    start_coordinator(
        coord_port, ckpt_dir, tool_paths, ckpt_interval=ckpt_interval,
    )

    # Prepare environment with HWLOC_COMPONENTS=-linuxio to prevent
    # hwloc from opening block devices (e.g. /dev/nvme*) which causes
    # DMTCP to crash with "Unimplemented file type".
    use_mana = "mana_launch" in tool_paths
    run_env = _prepare_dmtcp_env(env, app_args=app_args, use_mana=use_mana)
    if use_mana:
        _write_mana_argv_override(cwd, app_args)

    cmd = _build_launch_cmd(
        tool_paths, num_procs, coord_port, exe_path, app_args, ckpt_dir,
    )
    print(
        f"[dmtcp] attempt: starting MPI run (cwd={cwd}): {' '.join(cmd)}",
        flush=True,
    )

    t0 = time.monotonic()
    # Open stdout/stderr files outside the `with` block so they remain
    # open for the entire lifetime of the child process.  The previous
    # code used a `with` block that closed the file handles immediately
    # after Popen, which could cause the child to lose its output FDs.
    out_f = stdout_path.open("wb")
    err_f = stderr_path.open("wb")
    try:
        mpi_proc = subprocess.Popen(cmd, cwd=str(cwd), stdout=out_f, stderr=err_f, env=run_env)
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

    # ── Phase 2: secure a checkpoint, then wait for injection delay ─────
    # Strategy: decouple "getting a checkpoint" from "waiting for the
    # injection delay".  First, eagerly obtain a checkpoint (via both the
    # periodic --interval 1 and an explicit manual trigger).  Once
    # checkpoint files exist, wait for the remaining injection_delay to
    # elapse, then proceed to kill a rank.  This ensures short-running
    # applications get checkpointed before they finish.
    # MANA's split-process architecture needs more time to initialise
    # than plain DMTCP (lower-half setup, MPI init, coordinator connect).
    use_mana = "mana_launch" in tool_paths
    _CKPT_INIT_GRACE = 5.0 if use_mana else 1.0
    _CKPT_POLL_TIMEOUT = 30.0
    _CKPT_POLL_INTERVAL = 0.5

    # Brief grace period for DMTCP processes to register with the
    # coordinator before we attempt the first checkpoint.
    _grace_deadline = time.monotonic() + _CKPT_INIT_GRACE
    while time.monotonic() < _grace_deadline:
        if mpi_proc.poll() is not None:
            break
        time.sleep(0.25)

    # Trigger a manual checkpoint immediately (don't rely solely on the
    # periodic interval which may race with app completion).
    ckpt_ready = False
    if mpi_proc.poll() is None:
        print(
            f"[dmtcp] triggering early checkpoint "
            f"(injection_delay={injection_delay}s, periodic interval={ckpt_interval}s) ...",
            flush=True,
        )
        _dmtcp_checkpoint(coord_port, tool_paths)

        # Poll for checkpoint files to appear on disk.
        poll_deadline = time.monotonic() + _CKPT_POLL_TIMEOUT
        while time.monotonic() < poll_deadline:
            if _find_ckpt_files(ckpt_dir):
                ckpt_ready = True
                print(
                    f"[dmtcp] checkpoint files ready "
                    f"({time.monotonic() - t0:.1f}s after launch)",
                    flush=True,
                )
                break
            if mpi_proc.poll() is not None:
                print(
                    f"[dmtcp] app exited (code={mpi_proc.returncode}) "
                    f"while waiting for checkpoint files",
                    flush=True,
                )
                break
            time.sleep(_CKPT_POLL_INTERVAL)

    # If first attempt didn't produce files and app is still alive, retry.
    if not ckpt_ready and mpi_proc.poll() is None:
        print("[dmtcp] retrying manual checkpoint ...", flush=True)
        _dmtcp_checkpoint(coord_port, tool_paths)
        retry_deadline = time.monotonic() + 10.0
        while time.monotonic() < retry_deadline:
            if _find_ckpt_files(ckpt_dir):
                ckpt_ready = True
                print(
                    f"[dmtcp] checkpoint files ready on retry "
                    f"({time.monotonic() - t0:.1f}s after launch)",
                    flush=True,
                )
                break
            if mpi_proc.poll() is not None:
                break
            time.sleep(_CKPT_POLL_INTERVAL)

    # Wait for the remaining injection_delay to elapse (preserving the
    # intended delay semantics for benchmarking).
    elapsed_so_far = time.monotonic() - t0
    remaining = injection_delay - elapsed_so_far
    if remaining > 0 and mpi_proc.poll() is None:
        print(
            f"[dmtcp] checkpoint secured; waiting {remaining:.1f}s "
            f"remaining of {injection_delay}s injection delay ...",
            flush=True,
        )
        wait_until = time.monotonic() + remaining
        while time.monotonic() < wait_until:
            if mpi_proc.poll() is not None:
                break
            time.sleep(min(0.5, wait_until - time.monotonic()))

    # Check if app already finished before we could inject.
    poll = mpi_proc.poll()
    if poll is not None:
        out_f.close()
        err_f.close()
        elapsed = time.monotonic() - t0
        if mem_thread is not None and memory_stop_event is not None:
            memory_stop_event.set()
            mem_thread.join(timeout=5.0)
            all_mem_samples.extend(memory_samples_holder[0])
        early_ckpt = _find_ckpt_files(ckpt_dir)
        stop_coordinator(coord_port, tool_paths)
        stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
        stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
        print(
            f"[dmtcp] app finished before injection (exit={poll}, "
            f"elapsed={elapsed:.2f}s, ckpt_files={len(early_ckpt)})",
            flush=True,
        )
        # Diagnose common DMTCP failures on Aurora / GPU-equipped nodes.
        if poll == 99 and len(early_ckpt) == 0:
            print(
                "[dmtcp] ERROR: exit code 99 with zero checkpoint files "
                "indicates a DMTCP JASSERT assertion failure during\n"
                "[dmtcp]   checkpointing.  On Aurora (Intel GPU nodes), "
                "this is typically caused by:\n"
                "[dmtcp]   1. procselfmaps.cpp parser crash on "
                "'anon_inode:i915.gem' entries in /proc/self/maps\n"
                "[dmtcp]   2. Intel compiler runtime (libintlc.so) "
                "infinite recursion in DMTCP's openat() wrapper\n"
                "[dmtcp]   Fix: rebuild DMTCP with the procselfmaps "
                "patch and GCC:\n"
                "[dmtcp]     bash tests/examples/dmtcp/art_simple/"
                "diagnose_and_fix_mana.sh --force\n"
                "[dmtcp]   or re-run:  ./scripts/install_dmtcp_mana.sh",
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

    # Kill one MPI rank (only if checkpoint files exist).
    rank_pid = _find_rank_pid(executable_name)
    killed = False
    if not _find_ckpt_files(ckpt_dir):
        print(
            "[dmtcp] WARNING: no checkpoint files found; skipping kill "
            "(cannot restart without checkpoints)",
            flush=True,
        )
    elif rank_pid is not None:
        print(f"[dmtcp] killing rank pid={rank_pid} (SIGKILL)", flush=True)
        try:
            os.kill(rank_pid, signal.SIGKILL)
            killed = True
        except ProcessLookupError:
            print("[dmtcp] rank already dead", flush=True)
    else:
        print("[dmtcp] WARNING: could not find rank PID to kill", flush=True)

    # Wait for mpirun to exit.
    mpi_proc.wait()
    out_f.close()
    err_f.close()
    t_kill = time.monotonic()

    # Stop memory monitor for initial phase.
    if mem_thread is not None and memory_stop_event is not None:
        memory_stop_event.set()
        mem_thread.join(timeout=5.0)
        all_mem_samples.extend(memory_samples_holder[0])

    exit_code = mpi_proc.returncode
    print(
        f"[dmtcp] initial phase done (exit={exit_code}, killed={killed}, "
        f"elapsed={t_kill - t0:.2f}s).",
        flush=True,
    )

    # ── Phase 3: restart from checkpoint ─────────────────────────────────
    # Search recursively — DMTCP may place checkpoint files in
    # subdirectories of the checkpoint directory.
    ckpt_files = _find_ckpt_files(ckpt_dir)
    restart_script = ckpt_dir / "dmtcp_restart_script.sh"

    if not ckpt_files and not restart_script.exists():
        # If the app completed normally (all ranks exited) and we never
        # managed to kill a rank, DMTCP may have cleaned up checkpoint
        # files on normal exit.  Treat this as "completed without
        # injection" rather than a fatal error.
        stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
        stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")

        # Log diagnostic information.
        print(
            f"[dmtcp] WARNING: no checkpoint files found in {ckpt_dir} "
            f"(exit_code={exit_code})",
            flush=True,
        )
        try:
            ckpt_contents = list(ckpt_dir.rglob("*"))
            print(
                f"[dmtcp]   ckpt_dir contents ({len(ckpt_contents)} items): "
                f"{[str(p.relative_to(ckpt_dir)) for p in ckpt_contents[:20]]}",
                flush=True,
            )
        except Exception:
            pass
        # Show stderr tail for debugging DMTCP issues.
        stderr_tail = stderr_text.strip().splitlines()[-5:]
        if stderr_tail:
            print(
                f"[dmtcp]   stderr (last {len(stderr_tail)} lines):\n"
                + "\n".join(f"    {line}" for line in stderr_tail),
                flush=True,
            )

        if not killed:
            # App finished before we could inject failure — the
            # checkpoint was taken but DMTCP cleaned up on normal exit.
            print(
                "[dmtcp] App completed before failure could be injected. "
                "Returning result as non-injected run.",
                flush=True,
            )
            stop_coordinator(coord_port, tool_paths)
            elapsed = t_kill - t0
            return RunResult(
                exit_code=exit_code,
                stdout=stdout_text,
                stderr=stderr_text,
                elapsed_s=elapsed,
                injected=False,
                num_attempts=1,
                output_dir=output_dir,
                last_attempt_elapsed_s=elapsed,
                memory_samples_bytes=all_mem_samples,
            )

        # We did kill a rank but still no checkpoint files — this is a
        # genuine error.
        stop_coordinator(coord_port, tool_paths)
        raise ValidationError(
            "DMTCP: no checkpoint files found after checkpoint command. "
            "Cannot restart.",
            stdout=stdout_text,
            stderr=stderr_text,
            exit_code=-1,
            output_dir=output_dir,
        )

    # Restart the coordinator — MANA's mana_start_coordinator uses
    # --exit-on-last, so it exits when the crashed MPI job disconnects.
    # A fresh coordinator is needed for mana_restart.
    stop_coordinator(coord_port, tool_paths)
    time.sleep(0.5)
    start_coordinator(coord_port, ckpt_dir, tool_paths)

    restart_cmd = _build_restart_cmd(
        tool_paths, num_procs, coord_port, ckpt_dir, ckpt_files,
    )

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
