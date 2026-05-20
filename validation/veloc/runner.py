"""
runner.py – Build and run orchestration for the VeloC validation framework.

Provides:
  - configure_and_build()        – CMake configure + build (idempotent)
  - run_once()                   – single MPI run with timing
  - run_baseline()               – build + single clean run of the original codebase
  - run_with_failure_injection() – retry loop: inject failures until the resilient
                                   app completes successfully with >= 1 injection
  - RunResult                    – structured result dataclass

This module replaces the monolithic run_validation.py and the run-related
portions of run_resilience_validation.py.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# HyPar Fix B (2026-05-03) — bounded stdout/stderr capture for memory safety.
#
# Some apps (HyPar with n_iter=2.5M) produce 375 MB of stdout per run.  After
# the run, we read the full stdout file into a Python string for the
# `RunResult.stdout` field.  That string × multiple runs in a bench loop has
# OOM-killed the runner / validate.py process.
#
# Fix: a tail-bounded reader that returns only the LAST N lines (or full
# file when N is 0/unset).  On-disk file is left intact — the streaming
# comparator reads from disk, not from RunResult.stdout.
#
# Activation: opt-in via env var BENCH_STDOUT_TRUNCATE_LINES=N.  Default
# behavior unchanged (full read) when the var is unset or 0.  Per-app
# enablement happens in run_validate.sh's case statement (export the var
# only for HyPar, similar to how PRUNE_BENCH_ARTIFACTS=1 is HyPar/WarpX
# only).

def _read_text_tailed(
    path: "Path",
    encoding: str = "utf-8",
    errors: str = "replace",
) -> str:
    """Read text from *path*.  When BENCH_STDOUT_TRUNCATE_LINES env var is
    set to a positive integer N, return only the LAST N lines (memory-
    bounded).  Otherwise read the full file (legacy behavior)."""
    n_str = os.environ.get("BENCH_STDOUT_TRUNCATE_LINES", "").strip()
    try:
        n = int(n_str) if n_str else 0
    except ValueError:
        n = 0
    if n <= 0:
        return path.read_text(encoding=encoding, errors=errors)
    # Tail-N read: walk file from end in 64 KB chunks, accumulate until
    # we have N+1 newlines (the +1 to discard the partial-leading-line).
    try:
        size = path.stat().st_size
    except OSError:
        return ""
    if size == 0:
        return ""
    chunk = 65536
    needed = n + 1  # extra to discard partial first line
    buf = bytearray()
    nl_count = 0
    with path.open("rb") as f:
        pos = size
        while pos > 0 and nl_count < needed:
            read_size = min(chunk, pos)
            pos -= read_size
            f.seek(pos)
            data = f.read(read_size)
            buf[0:0] = data  # prepend
            nl_count = buf.count(b"\n")
    text = buf.decode(encoding, errors=errors)
    # Slice to last N lines (drop the partial leading line if file > N lines).
    lines = text.splitlines()
    if len(lines) > n:
        lines = lines[-n:]
        return (
            f"[BENCH_STDOUT_TRUNCATE_LINES={n}: showing last {n} of "
            f"~{nl_count} lines, {size} bytes total on disk]\n"
            + "\n".join(lines)
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class ValidationError(RuntimeError):
    """Raised when a run fails and we want to surface stdout/stderr to the caller.

    Attributes
    ----------
    message     : human-readable summary of what went wrong
    stdout      : captured stdout of the failed run (may be empty)
    stderr      : captured stderr of the failed run (may be empty)
    exit_code   : process exit code (or -1 if unknown)
    output_dir  : directory where stdout.txt / stderr.txt were saved
    """

    def __init__(
        self,
        message: str,
        stdout: str = "",
        stderr: str = "",
        exit_code: int = -1,
        output_dir: Path | None = None,
    ) -> None:
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.output_dir = output_dir

    def debug_report(self, max_lines: int = 40) -> str:
        """Return a formatted debug report with stdout/stderr tails."""
        lines = [str(self)]
        if self.output_dir:
            lines.append(f"  Output directory : {self.output_dir}")
        if self.exit_code != -1:
            lines.append(f"  Exit code        : {self.exit_code}")

        def _tail(text: str, label: str) -> list[str]:
            if not text.strip():
                return [f"  {label}: (empty)"]
            text_lines = text.splitlines()
            if len(text_lines) > max_lines:
                omitted = len(text_lines) - max_lines
                text_lines = [f"  ... ({omitted} lines omitted) ..."] + text_lines[
                    -max_lines:
                ]
            return [f"  {label}:"] + [f"    {l}" for l in text_lines]

        lines += _tail(self.stdout, "STDOUT (tail)")
        lines += _tail(self.stderr, "STDERR (tail)")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


def _resolve_and_apply_perturbation(
    perturbation_spec,
    perturbation_seed,
    source_dir,
    output_dir,
    app_args,
    env,
):
    """Resolve a perturbation value from seed and apply all three slots
    (input file, app_args, env) consistently.

    Returns ``(new_app_args, new_env, resolved_value_or_None)``. When
    ``perturbation_spec`` is ``None`` or marked ``disabled``, this is a
    no-op that returns the inputs unchanged with ``value=None``.

    Callers should invoke this after :func:`_symlink_input_data` since
    regex_replace perturbations need to overwrite the freshly-created
    symlink in ``output_dir``.
    """
    from .app_config import resolve_perturbation_value, apply_perturbation
    if perturbation_spec is None or getattr(perturbation_spec, "method", None) == "disabled":
        return list(app_args), dict(env), None
    if perturbation_seed is None:
        raise ValueError(
            "perturbation_spec provided but perturbation_seed is None — "
            "caller must supply a seed for deterministic perturbation"
        )
    value = resolve_perturbation_value(perturbation_spec, perturbation_seed)
    new_args, new_env, _ = apply_perturbation(
        perturbation_spec, value,
        cwd=output_dir, source_dir=source_dir,
        app_args=app_args, env=env,
    )
    return new_args, new_env, value


@dataclass
class RunResult:
    """Structured result of a single MPI application run."""

    exit_code: int
    stdout: str
    stderr: str
    elapsed_s: float
    injected: bool = False  # True if a failure was injected during this run
    injection_fired: bool = False  # True if kill signal was sent while process was still alive
    num_attempts: int = 1  # total attempts consumed (>1 for retry runs)
    output_dir: Path = field(default_factory=Path)
    last_attempt_elapsed_s: float = (
        0.0  # wall-clock time of the final (successful) attempt
    )
    memory_samples_bytes: list[int] = field(
        default_factory=list
    )  # RSS samples collected during run

    # Set by run_with_checkpoint_observed_injection only.  None means the
    # checkpoint-observed strategy was not used (legacy fixed-delay path).
    # True = at least one checkpoint file appeared during the kill attempt;
    # False = the kill attempt finished (cleanly or via safety timeout)
    # without any checkpoint ever being written.  validate.py's production
    # enforcement treats False as an automatic FAILED verdict.
    checkpoint_observed: bool | None = None
    # Per-attempt elapsed for the new strategy: kill_attempt_elapsed_s holds
    # the wall-clock from process start until the moment we issued SIGKILL
    # (or until natural exit if no checkpoint was observed); recovery_attempt_elapsed_s
    # holds the wall-clock for the second mpirun (the recovery attempt) only.
    # None when the legacy strategy is used.
    kill_attempt_elapsed_s: float | None = None
    recovery_attempt_elapsed_s: float | None = None
    # F-20 (2026-05-15): files in /tmp/ that were created or modified
    # during ANY attempt of this run (kill attempt + recovery attempt).
    # Empty list = nothing touched.  Used by validate.py F-20 gate to
    # content-check binary outputs against the baseline (gaming-6
    # detection: side-car cache outside VeloC dirs).  Does NOT include
    # files inside the VeloC scratch / persistent dirs declared in
    # veloc.cfg (those are legitimate ckpts, not side-cars).  Path
    # strings, NOT Paths, for cheap JSON serialization.
    files_modified_in_scope: list[str] = field(default_factory=list)
    # Perturbation tracking (2026-05-17 cold-replay detector): when the
    # validator applied a random input perturbation before the run, these
    # fields record what was applied for forensic reproducibility. Both
    # None when perturbation is inactive (legacy path / app has no
    # perturbation: spec). The seed alone is enough to reproduce the value
    # via app_config.resolve_perturbation_value.
    perturbation_seed: int | None = None
    perturbation_value: float | int | None = None

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0


# ---------------------------------------------------------------------------
# External tool resolution
# ---------------------------------------------------------------------------


def _resolve_tool(name: str) -> str:
    """Resolve the full path of an external tool (e.g. ``cmake``, ``mpirun``).

    Uses :func:`shutil.which` to search the current ``PATH``.  If the tool
    cannot be found, raises :class:`FileNotFoundError` with a helpful message
    that includes the ``PATH`` value so the user can diagnose the issue on
    remote / HPC machines where tools may live in non-standard locations.
    """
    path = shutil.which(name)
    if path is None:
        env_path = os.environ.get("PATH", "(unset)")
        raise FileNotFoundError(
            f"Required tool '{name}' was not found on PATH.\n"
            f"  PATH = {env_path}\n"
            f"  Hint: ensure '{name}' is installed and available in your shell "
            f"before activating the virtualenv, or set the full path via the "
            f"{name.upper()}_PATH environment variable."
        )
    return path


# ---------------------------------------------------------------------------
# Build helpers
# ---------------------------------------------------------------------------


def _run_cmd(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> int:
    """Run a shell command, streaming output to stdout, and return the exit code."""
    print(f"[runner] running: {' '.join(str(c) for c in cmd)}", flush=True)
    proc = subprocess.Popen(cmd, cwd=str(cwd) if cwd else None, env=env)
    proc.wait()
    return proc.returncode


def _detect_veloc_dir() -> str | None:
    """Auto-detect the VeloC installation prefix.

    Resolution order:
    1. ``VELOC_DIR`` environment variable (explicit override).
    2. Search ``LD_LIBRARY_PATH`` for a directory containing ``libveloc-client.so``
       and derive the prefix (parent of ``lib`` or ``lib64``).
    3. Check well-known prefixes: ``~/.local``, ``~/usr``, ``/usr/local``.

    Returns the prefix path (e.g. ``/home/user/.local``) or *None* if VeloC
    cannot be found.
    """
    # 1. Explicit env var
    env_dir = os.environ.get("VELOC_DIR")
    if env_dir:
        p = Path(env_dir)
        if p.is_dir():
            print(f"[runner] VELOC_DIR from environment: {p}", flush=True)
            return str(p)

    # 2. Search LD_LIBRARY_PATH
    ld_path = os.environ.get("LD_LIBRARY_PATH", "")
    for entry in ld_path.split(":"):
        entry = entry.strip()
        if not entry:
            continue
        lib_dir = Path(entry)
        if (lib_dir / "libveloc-client.so").is_file():
            prefix = lib_dir.parent  # e.g. /home/user/.local/lib64 -> /home/user/.local
            print(
                f"[runner] VeloC detected via LD_LIBRARY_PATH: prefix={prefix}",
                flush=True,
            )
            return str(prefix)

    # 3. Well-known prefixes
    home = Path.home()
    for candidate in [home / ".local", home / "usr", Path("/usr/local")]:
        for libsub in ["lib", "lib64"]:
            if (candidate / libsub / "libveloc-client.so").is_file():
                print(
                    f"[runner] VeloC detected at well-known prefix: {candidate}",
                    flush=True,
                )
                return str(candidate)

    return None


def _veloc_lib_dir(veloc_prefix: str) -> str | None:
    """Return the library subdirectory (lib or lib64) under a VeloC prefix.

    Checks ``lib64`` first (common on RHEL/SUSE-based HPC systems), then ``lib``.
    Returns the full path to the library directory, or *None* if neither exists.
    """
    p = Path(veloc_prefix)
    for subdir in ["lib64", "lib"]:
        candidate = p / subdir
        if (candidate / "libveloc-client.so").is_file():
            return str(candidate)
    return None


def configure_and_build(
    source_dir: Path,
    build_dir: Path,
    run_install: bool = False,
    cmake_extra_args: list[str] | None = None,
    build_cmd: str | None = None,
) -> None:
    """Configure and build the example.

    If *build_cmd* is provided, the source tree is copied to *build_dir*
    and the shell command is executed there (matching the approach used by
    ``reference_validator.py``).  This supports Make, Meson, and any other
    build system — the command comes directly from ``app.yaml``.

    Otherwise, falls back to the original CMake-based flow: configure via
    ``cmake -S ... -B ...``, build via ``cmake --build``, and optionally
    install via ``cmake --install``.

    *cmake_extra_args* are appended to the ``cmake -S ... -B ...`` command.
    """
    import shutil

    build_dir.mkdir(parents=True, exist_ok=True)

    # Marker file written after a successful shell-command build.
    # When configure_and_build is called again (e.g. by run_baseline or
    # run_with_failure_injection) without build_cmd, it detects the marker
    # and skips the build instead of falling through to CMake.
    _shell_build_marker = build_dir / ".shell_build_done"

    # ── Shell-command build (from app.yaml build.cmd) ────────────────────
    if build_cmd is not None:
        # Copy source to build directory (same as reference_validator._build_app)
        if source_dir != build_dir:
            if build_dir.exists():
                # Restore u+w on every entry before rmtree.  Source trees
                # under iter+bench may carry F-15 read-only locks on
                # vendored subprojects (set by run_iterative.sh's
                # _lock_vendored helper) which propagate to the build_dir
                # on first --install-resilient copy.  Without this, the
                # second iter cycle's rmtree fails with PermissionError on
                # files inside the locked dir (e.g. amrex/Tools/C_scripts/
                # describe_sources.py — directory perms 555 prevent
                # unlink even though the file itself is readable).  Note:
                # F-15 is reapplied to the LLM source tree after each iter
                # by run_iterative.sh, so this only relaxes the build_dir
                # copy, not the LLM-facing source.
                _sp_chmod = __import__("subprocess")
                _sp_chmod.run(
                    ["chmod", "-R", "u+w", str(build_dir)],
                    check=False, capture_output=True,
                )
                shutil.rmtree(build_dir)
            shutil.copytree(source_dir, build_dir, symlinks=True,
                            ignore_dangling_symlinks=True)

        import subprocess as _sp
        result = _sp.run(
            build_cmd, shell=True, cwd=str(build_dir),
            capture_output=True, text=True, timeout=1200,
        )
        if result.returncode != 0:
            output = (result.stdout + "\n" + result.stderr)[-1000:]
            raise RuntimeError(
                f"Build failed for {source_dir}:\n{output}"
            )
        _shell_build_marker.write_text(build_cmd)
        return

    # If a previous shell build already populated this directory, skip CMake.
    if _shell_build_marker.exists():
        return

    # ── CMake-based build (original flow) ────────────────────────────────
    cmake = os.environ.get("CMAKE_PATH") or _resolve_tool("cmake")

    cache = build_dir / "CMakeCache.txt"
    makefile = build_dir / "Makefile"
    ninja_file = build_dir / "build.ninja"
    configured = cache.exists() and (makefile.exists() or ninja_file.exists())

    if not configured:
        configure_cmd = [cmake, "-S", str(source_dir), "-B", str(build_dir)]

        # Auto-detect VeloC and pass its prefix to CMake so the generated
        # CMakeLists.txt can find the library and all its dependencies.
        veloc_dir = _detect_veloc_dir()
        if veloc_dir:
            configure_cmd.append(f"-DVELOC_DIR={veloc_dir}")
            # Also pass CMAKE_PREFIX_PATH so find_package / find_library
            # can locate VeloC's transitive dependencies.
            veloc_lib = _veloc_lib_dir(veloc_dir)
            if veloc_lib:
                configure_cmd.append(f"-DCMAKE_PREFIX_PATH={veloc_dir}")

        if cmake_extra_args:
            configure_cmd.extend(cmake_extra_args)

        code = _run_cmd(configure_cmd)
        if code != 0:
            raise RuntimeError(f"CMake configuration failed for {source_dir}")

    code = _run_cmd([cmake, "--build", str(build_dir)])
    if code != 0:
        raise RuntimeError(f"Build failed for {source_dir}")

    if run_install:
        code = _run_cmd(
            [cmake, "--install", str(build_dir), "--prefix", str(build_dir)]
        )
        if code != 0:
            raise RuntimeError(f"Install step failed for {source_dir}")


# ---------------------------------------------------------------------------
# Executable discovery
# ---------------------------------------------------------------------------


def _find_executable(build_dir: Path, executable_name: str) -> Path:
    """Locate the built executable under *build_dir*.

    Prefers canonical build locations (`_build/bin/`, `_build/`, `bin/`) over
    a top-level or recursive match: wrapper scripts (e.g. HPCG's xhpcg_run)
    can appear at multiple paths in a build tree but only function when their
    sibling binary is alongside them in `_build/bin/`.

    Skips dangling symlinks: ``os.walk`` lists symlink entries in ``files``
    regardless of whether the target resolves, so a stale top-level symlink
    in ``build_dir`` (e.g. a pre-strip artifact pointing into the vanilla
    source tree whose binary was later removed) would otherwise shadow the
    real binary deeper in ``_build/<subdir>/``. ``Path.exists()`` returns
    False for a dangling symlink, and ``os.access(..., X_OK)`` ensures the
    candidate is actually runnable rather than a same-named data file.
    """
    def _runnable(p: Path) -> bool:
        return p.exists() and os.access(str(p), os.X_OK)

    for canonical in (
        build_dir / "_build" / "bin" / executable_name,
        build_dir / "_build" / executable_name,
        build_dir / "bin" / executable_name,
    ):
        if _runnable(canonical):
            return canonical
    candidate = build_dir / executable_name
    if _runnable(candidate):
        return candidate
    for root, _dirs, files in os.walk(build_dir):
        if executable_name in files:
            hit = Path(root) / executable_name
            if _runnable(hit):
                return hit
    raise FileNotFoundError(
        f"Executable {executable_name!r} not found under {build_dir}"
    )


# ---------------------------------------------------------------------------
# Single MPI run
# ---------------------------------------------------------------------------


def run_once(
    build_dir: Path,
    executable_name: str,
    num_procs: int,
    app_args: list[str],
    output_dir: Path,
    run_cwd: Path | None = None,
    env: dict | None = None,
    veloc_config_sources: list[Path] | None = None,
    veloc_config_name: str = "veloc.cfg",
    memory_monitor_fn: "callable | None" = None,
    memory_stop_event: "threading.Event | None" = None,
    memory_samples_holder: "list | None" = None,
    timeout_s: float | None = None,
) -> RunResult:
    """Run the application once under mpirun, capturing stdout/stderr and timing.

    If *veloc_config_sources* is provided, the function searches those directories
    for *veloc_config_name* (default ``veloc.cfg``) and copies the first one found
    into the run CWD so that VeloC can locate it at runtime.  This is a no-op when
    the config is already present in the CWD or when *veloc_config_sources* is None.

    If *memory_monitor_fn* is provided along with *memory_stop_event* and
    *memory_samples_holder*, a background thread is started to monitor memory
    usage of the subprocess.

    Returns a :class:`RunResult` with ``injected=False`` (callers that perform
    failure injection should set this field themselves).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    exe_path = _find_executable(build_dir, executable_name)
    cwd = run_cwd if run_cwd is not None else build_dir
    cwd.mkdir(parents=True, exist_ok=True)

    # Ensure veloc.cfg is present in the CWD so VeloC can find it.
    # Always overwrite from the source list — a stale cfg from a prior run in
    # the same cwd (e.g. resilient_clean/) would otherwise win.  Matches
    # _copy_veloc_cfg's unconditional-copy semantics.
    if veloc_config_sources:
        cfg_dst = cwd / veloc_config_name
        for src_dir in veloc_config_sources:
            cfg_src = src_dir / veloc_config_name
            if cfg_src.exists():
                shutil.copy2(cfg_src, cfg_dst)
                print(f"[runner] copied {cfg_src} → {cfg_dst}", flush=True)
                break

    # Clear VeloC checkpoint/scratch directories before running so that leftover
    # checkpoints from a previous run cannot be accidentally picked up.
    cfg_in_cwd = cwd / veloc_config_name
    if cfg_in_cwd.exists():
        ckpt_dirs = extract_checkpoint_dirs_from_veloc_cfg(cfg_in_cwd)
        if ckpt_dirs:
            print(
                "[runner] clearing VeloC checkpoint directories before run:", flush=True
            )
            for d in ckpt_dirs:
                print(f"  - {d}", flush=True)
            clear_checkpoint_dirs(ckpt_dirs)

    stdout_path = output_dir / "stdout.txt"
    stderr_path = output_dir / "stderr.txt"

    # Ensure LD_LIBRARY_PATH includes the VeloC library directory so that
    # libveloc-client.so can find its transitive dependencies (libveloc-modules,
    # liber, libredset, libshuffile, libkvtree, librankstr, libaxl, etc.) at
    # runtime.  This is especially important on Cray/PALS systems where mpirun
    # may not forward the login-node environment to compute nodes.
    run_env = dict(env) if env else dict(os.environ)
    # Ensure LD_LIBRARY_PATH includes paths for checkpoint libraries
    # (VeloC, FTI, SCR, jemalloc) so MPI-launched processes can find them.
    existing_ld = run_env.get("LD_LIBRARY_PATH", "")
    extra_lib_dirs: list[str] = []

    veloc_dir = _detect_veloc_dir()
    if veloc_dir:
        veloc_lib = _veloc_lib_dir(veloc_dir)
        if veloc_lib and veloc_lib not in existing_ld.split(":"):
            extra_lib_dirs.append(veloc_lib)

    # Also add $HOME/.local/lib for FTI, SCR, jemalloc if present
    home_local_lib = os.path.join(os.path.expanduser("~"), ".local", "lib")
    if os.path.isdir(home_local_lib) and home_local_lib not in existing_ld.split(":"):
        extra_lib_dirs.append(home_local_lib)

    if extra_lib_dirs:
        new_ld = ":".join(extra_lib_dirs + ([existing_ld] if existing_ld else []))
        run_env["LD_LIBRARY_PATH"] = new_ld

    mpirun = os.environ.get("MPIRUN_PATH") or _resolve_tool("mpirun")
    cmd = [mpirun, "-np", str(num_procs), str(exe_path), *app_args]
    print(f"[runner] starting MPI run (cwd={cwd}): {' '.join(cmd)}", flush=True)

    t0 = time.monotonic()
    with stdout_path.open("wb") as out_f, stderr_path.open("wb") as err_f:
        proc = subprocess.Popen(
            cmd, cwd=str(cwd), stdout=out_f, stderr=err_f, env=run_env
        )

        # Start memory monitoring thread if requested.
        mem_thread = None
        if (
            memory_monitor_fn
            and memory_stop_event
            and memory_samples_holder is not None
        ):
            mem_thread = threading.Thread(
                target=memory_monitor_fn,
                args=(proc.pid, memory_samples_holder, memory_stop_event),
                daemon=True,
            )
            mem_thread.start()

        # Hard wallclock cap so a runaway LLM solution (infinite recovery
        # loop, deadlocked recovery, runaway checkpoint cadence) cannot hang
        # the harness indefinitely.  Without this, the failure-free check
        # could spin at 100% CPU for hours.  When the cap fires we kill the
        # process group and return exit_code=-9 (matches the SIGKILL convention
        # the rest of the harness uses).
        timeout_hit = False
        if timeout_s and timeout_s > 0:
            try:
                exit_code = proc.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                timeout_hit = True
                print(
                    f"[runner] run_once: TIMEOUT after {timeout_s:.1f}s — "
                    f"terminating mpirun (pid={proc.pid}). Likely a runaway "
                    "loop or deadlock in the application.",
                    flush=True,
                )
                proc.terminate()
                try:
                    exit_code = proc.wait(timeout=10.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    try:
                        exit_code = proc.wait(timeout=5.0)
                    except subprocess.TimeoutExpired:
                        exit_code = -9
        else:
            exit_code = proc.wait()

    elapsed = time.monotonic() - t0

    # Signal memory monitor to stop and wait for it.
    if mem_thread is not None and memory_stop_event is not None:
        memory_stop_event.set()
        mem_thread.join(timeout=5.0)

    stdout_text = _read_text_tailed(stdout_path)
    stderr_text = _read_text_tailed(stderr_path)

    return RunResult(
        exit_code=exit_code,
        stdout=stdout_text,
        stderr=stderr_text,
        elapsed_s=elapsed,
        injected=False,
        num_attempts=1,
        output_dir=output_dir,
        last_attempt_elapsed_s=elapsed,
    )


# ---------------------------------------------------------------------------
# Failure injector launcher
# ---------------------------------------------------------------------------


def _start_failure_injector(
    target_parent_pid: int,
    executable_name: str,
    injection_flag_path: Path,
    delay_seconds: float,
    nodes: str | None = None,
    hostfile: str | None = None,
) -> subprocess.Popen:
    """Launch the failure_injector.py subprocess.

    Parameters
    ----------
    nodes:
        Comma-separated list of hostnames participating in the MPI job.
        Passed as ``--nodes`` to the injector so it can target processes
        across multiple nodes via SSH.
    hostfile:
        Path to a hostfile (one hostname per line).  Passed as
        ``--hostfile`` to the injector.  Ignored when *nodes* is given.
    """
    script_path = Path(__file__).with_name("failure_injector.py")
    cmd = [
        sys.executable,
        str(script_path),
        "--parent-pid",
        str(target_parent_pid),
        "--executable-name",
        executable_name,
        "--flag-path",
        str(injection_flag_path),
        "--delay-seconds",
        str(delay_seconds),
    ]
    if nodes:
        cmd.extend(["--nodes", nodes])
    elif hostfile:
        cmd.extend(["--hostfile", str(hostfile)])
    print(f"[runner] starting failure injector: {' '.join(cmd)}", flush=True)
    return subprocess.Popen(cmd)


# ---------------------------------------------------------------------------
# VeloC checkpoint directory helpers
# ---------------------------------------------------------------------------


def extract_checkpoint_dirs_from_veloc_cfg(cfg_path: Path) -> list[Path]:
    """Parse a VeloC config file and return the scratch/persistent directories."""
    keys = {"scratch", "persistent"}
    dirs: list[Path] = []
    try:
        text = cfg_path.read_text(encoding="utf-8")
    except OSError:
        return dirs
    for line in text.splitlines():
        if "#" in line:
            line = line.split("#", 1)[0]
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip().lower()
        if key not in keys:
            continue
        for token in val.split(","):
            token = token.strip()
            if not token:
                continue
            p = Path(token)
            if p.is_absolute():
                dirs.append(p)
    return dirs


def clear_checkpoint_dirs(dirs: list[Path]) -> None:
    """Remove all contents from the given directories (best-effort)."""
    for d in dirs:
        try:
            if not d.exists() or not d.is_dir():
                continue
            if str(d) in {"/", ""}:
                continue
            for child in d.iterdir():
                if child.is_dir():
                    shutil.rmtree(child, ignore_errors=True)
                else:
                    try:
                        child.unlink()
                    except OSError:
                        pass
        except OSError:
            pass


def measure_checkpoint_dirs(dirs: list[Path]) -> dict:
    """Walk each directory and return a structured size+file-count summary.

    Returned dict shape::

        {
          "total_size_bytes": int,
          "total_file_count": int,
          "per_dir": [
            {"path": "/tmp/comd_persistent",
             "size_bytes": 1234,
             "file_count": 5,
             "exists": True},
            ...
          ]
        }
    """
    out: dict = {"total_size_bytes": 0, "total_file_count": 0, "per_dir": []}
    for d in dirs:
        entry = {"path": str(d), "size_bytes": 0, "file_count": 0,
                 "exists": d.exists() and d.is_dir()}
        if entry["exists"]:
            try:
                for f in d.rglob("*"):
                    if f.is_file() and not f.is_symlink():
                        try:
                            entry["size_bytes"] += f.stat().st_size
                            entry["file_count"] += 1
                        except OSError:
                            pass
            except OSError:
                pass
        out["per_dir"].append(entry)
        out["total_size_bytes"] += entry["size_bytes"]
        out["total_file_count"] += entry["file_count"]
    return out


def snapshot_checkpoint_dirs(dirs: list[Path], dest: Path) -> dict:
    """Copy each ckpt dir into *dest*/<dir-basename>/ so the artifact survives
    after the next app's run wipes /tmp paths or after VeloC's own version
    rotation removes older checkpoints.

    Best-effort: skips files that disappear mid-copy (e.g. symlinks to
    /tmp/<scratch> that get cleaned by the runtime).  Returns a summary
    dict with the bytes copied and any failures.
    """
    dest.mkdir(parents=True, exist_ok=True)
    summary: dict = {"snapshot_dir": str(dest), "copied_dirs": [], "errors": []}
    for d in dirs:
        if not d.exists() or not d.is_dir():
            continue
        target = dest / d.name
        try:
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)
            shutil.copytree(d, target, symlinks=True, ignore_dangling_symlinks=True)
            summary["copied_dirs"].append({"src": str(d), "dst": str(target)})
        except (OSError, shutil.Error) as e:
            summary["errors"].append(f"{d}: {e}")
    return summary


def _resolve_dynamic_recovery_args(args: "list[str]", search_dirs: "list[Path]") -> "list[str]":
    """Replace dynamic tokens in recovery args with values computed from
    on-disk state at recovery time.  Used so per-app bench configs don't
    hardcode restore-numbers that only happen to work for one
    `restart_interval` value.

    Supported tokens (must be the ENTIRE argument string, not embedded):
      {LATEST_RESTORE:<subdir>}
        Search each `search_dir` for `<subdir>/restore.NNNNNN` directories
        (SAMRAI convention) or `<subdir>/chk*` (AMReX convention) and
        replace with the highest NNNNNN found.  If none exist, returns "0".

    Example (SAMRAI LinAdv):
      _extra_args_recovery.txt:
          validation_inputs/linadv.2d.input
          restart_linadv
          {LATEST_RESTORE:restart_linadv}
      At recovery time, the runner inspects search_dirs (mpirun cwd =
      output_dir) for `restart_linadv/restore.NNNNNN`, picks the highest
      NNNNNN, and substitutes that string.  Recovery then reads from
      restart_linadv/restore.NNNNNN/nodes.M/proc.K/ and resumes
      integration.  Works for ANY restart_interval value.
    """
    import re
    pat = re.compile(r"^\{LATEST_RESTORE:([^}]+)\}$")
    resolved: list[str] = []
    for arg in args:
        m = pat.match(str(arg))
        if not m:
            resolved.append(arg)
            continue
        subdir_name = m.group(1)
        best = -1
        for root in search_dirs:
            sub = Path(root) / subdir_name
            if not sub.is_dir():
                continue
            try:
                for child in sub.iterdir():
                    if not child.is_dir():
                        continue
                    name = child.name
                    # SAMRAI convention: restore.NNNNNN
                    if name.startswith("restore."):
                        try:
                            n = int(name.split(".", 1)[1])
                            if n > best:
                                best = n
                        except ValueError:
                            pass
            except OSError:
                continue
        replacement = str(best) if best >= 0 else "0"
        resolved.append(replacement)
        print(
            f"[runner] dynamic recovery arg: {{LATEST_RESTORE:{subdir_name}}} -> {replacement}",
            flush=True,
        )
    return resolved


def _copy_veloc_cfg(
    source_dir: Path,
    build_dir: Path,
    dest_dir: Path,
    veloc_config_name: str,
) -> None:
    """Copy veloc.cfg into dest_dir so VeloC can find it at runtime."""
    for cfg_src_dir in (source_dir, build_dir):
        cfg_src = cfg_src_dir / veloc_config_name
        if cfg_src.exists():
            cfg_dst = dest_dir / veloc_config_name
            shutil.copy2(cfg_src, cfg_dst)
            print(f"[runner] copied {cfg_src} → {cfg_dst}", flush=True)
            return


def _symlink_input_data(
    source_dir: Path,
    build_dir: Path,
    run_cwd: Path,
    app_args: list[str],
    extra_source_dirs: list[Path] | None = None,
    input_subdir: str | None = None,
    priority_source_dirs: list[Path] | None = None,
) -> None:
    """Create symlinks in *run_cwd* for input data directories referenced by *app_args*.

    Many applications reference input files via relative paths (e.g.
    ``test/sedovsmall/sedovsmall.pnt``).  When the run CWD differs from the
    source or build directory, these paths do not resolve.  This helper
    identifies the top-level directory component of each arg that looks like a
    relative path and, if a matching directory exists in the source tree (or
    build tree, e.g. via an existing symlink), creates a symlink in the run CWD
    so the application can find its input data.

    extra_source_dirs:
        Additional source directories searched as fallbacks when an input file
        is not present under *source_dir*.  Used by the resilient run to fall
        back to the original/vanilla source for input files that the reference
        codebase does not ship (e.g. LAMMPS' ``bench/in.lj_long``).

    priority_source_dirs:
        Source directories searched BEFORE *source_dir* / *build_dir*.  Used
        by the audit's reference-baseline run to force vanilla input files
        to override the reference codebase's own input files, so the
        accuracy comparison runs both the vanilla and the reference on
        bit-identical inputs (otherwise SW4lite vanilla ``time t=15.0`` vs
        reference ``time t=2.0`` and Athena++ vanilla 200x200 AMR vs
        reference 50x100 produce divergent outputs even when the algorithms
        are equivalent).

    input_subdir:
        Path component (relative to *source_dir*) extracted from a stripped
        ``cd <subdir> &&`` prefix in the app's ``run.cmd``.  When provided, the
        full contents of ``source_dir/input_subdir`` (and the same path under
        each fallback dir) are symlinked into *run_cwd* so apps that expect to
        run from that subdirectory (SPARTA, SPPARKS, HyPar) find their input
        files via simple cwd-relative names.
    """
    if run_cwd == source_dir or run_cwd == build_dir:
        return  # no symlink needed

    search_roots: list[Path] = []
    if priority_source_dirs:
        for p in priority_source_dirs:
            if p not in search_roots:
                search_roots.append(p)
    for r in (source_dir, build_dir):
        if r not in search_roots:
            search_roots.append(r)
    if extra_source_dirs:
        for extra in extra_source_dirs:
            if extra not in search_roots:
                search_roots.append(extra)

    # Defensive filter: skip files that look like leftover checkpoint /
    # restart artifacts from an earlier in-place run.  Symlinking these into
    # the per-run cwd would let the app silently load a stale state — e.g.
    # PRK_Stencil's prk_stencil_state-N.bin files left in
    # tests/apps/checkpointed/PRK_Stencil/Stencil/ from a past invocation,
    # which made every resilient attempt resume at the final iteration in
    # ~0.2 s and starve the failure injector.
    _SKIP_PATTERNS = (
        "prk_stencil_state-",  # PRK_Stencil POSIX checkpoint
        "veloc_ckpts",         # VeloC scratch dirs accidentally checked in
        "ckpt_iter",           # generic POSIX checkpoint naming
    )
    _SKIP_SUFFIXES = (
        ".ckpt",               # generic checkpoint suffix
        ".veloc",              # VeloC payload suffix
    )

    def _is_stale_checkpoint(name: str) -> bool:
        return (
            any(name.startswith(p) for p in _SKIP_PATTERNS)
            or any(name.endswith(s) for s in _SKIP_SUFFIXES)
        )

    # Flatten the input subdirectory's contents into run_cwd when set.
    if input_subdir:
        for root in search_roots:
            subdir = root / input_subdir
            if subdir.is_dir():
                for child in subdir.iterdir():
                    if _is_stale_checkpoint(child.name):
                        print(
                            f"[runner] skipping stale checkpoint artifact: {child}",
                            flush=True,
                        )
                        continue
                    sibling = run_cwd / child.name
                    if sibling.exists() or sibling.is_symlink():
                        continue
                    try:
                        sibling.symlink_to(child.resolve())
                    except OSError:
                        pass
                break

    def _materialize_top_dir(top: str) -> Path | None:
        """Realize *run_cwd/top* as a real directory whose entries are
        per-file symlinks merged across every search root that contains a
        ``top/`` directory.  Returns the materialized path, or None if no
        search root has *top*.
        """
        link_dst = run_cwd / top
        # Already a real directory we created earlier — reuse it.
        if link_dst.is_dir() and not link_dst.is_symlink():
            return link_dst
        # Symlink to an external dir from a previous call — replace with a
        # real dir + per-file symlinks so we can mix in fallback files.
        if link_dst.is_symlink():
            existing_target = link_dst.resolve()
            link_dst.unlink()
            link_dst.mkdir()
            if existing_target.is_dir():
                for child in existing_target.iterdir():
                    if _is_stale_checkpoint(child.name):
                        continue
                    sibling = link_dst / child.name
                    if sibling.exists() or sibling.is_symlink():
                        continue
                    try:
                        sibling.symlink_to(child.resolve())
                    except OSError:
                        pass
        elif not link_dst.exists():
            # No existing entry — find the first search root that has it.
            found = False
            for candidate_dir in search_roots:
                candidate = candidate_dir / top
                if candidate.is_dir():
                    link_dst.mkdir()
                    for child in candidate.iterdir():
                        if _is_stale_checkpoint(child.name):
                            continue
                        sibling = link_dst / child.name
                        try:
                            sibling.symlink_to(child.resolve())
                        except OSError:
                            pass
                    found = True
                    break
            if not found:
                return None
        # Merge in per-file symlinks from any later search roots that have
        # files the primary source lacks.
        for candidate_dir in search_roots[1:]:
            candidate = candidate_dir / top
            if not candidate.is_dir():
                continue
            for child in candidate.iterdir():
                if _is_stale_checkpoint(child.name):
                    continue
                sibling = link_dst / child.name
                if sibling.exists() or sibling.is_symlink():
                    continue
                try:
                    sibling.symlink_to(child.resolve())
                except OSError:
                    pass
        return link_dst

    for arg in app_args:
        # Skip flags and absolute paths.
        if arg.startswith("-") or os.path.isabs(arg):
            continue
        # Extract the top-level directory component (e.g. "test" from
        # "test/sedovsmall/sedovsmall.pnt").
        top = arg.split("/")[0].split(os.sep)[0]
        if not top or top == "." or top == "..":
            continue
        # When fallbacks are configured AND the arg references something inside
        # a directory (i.e. has a path separator), materialize the top dir as
        # real + per-file symlinks so we can merge files from multiple sources.
        if extra_source_dirs and ("/" in arg or os.sep in arg):
            _materialize_top_dir(top)
        else:
            link_dst = run_cwd / top
            if not (link_dst.exists() or link_dst.is_symlink()):
                for candidate_dir in search_roots:
                    candidate = candidate_dir / top
                    if candidate.exists() or candidate.is_symlink():
                        link_dst.symlink_to(candidate.resolve())
                        print(
                            f"[runner] symlinked {link_dst} → {candidate.resolve()}",
                            flush=True,
                        )
                        break

        # When the arg is a multi-component path (e.g. "examples/free/in.validation"),
        # the input file usually references its sibling files via cwd-relative
        # paths (e.g. SPARTA's in.validation does `species ar.species`).
        # The top-dir symlink alone leaves those siblings at the WRONG cwd
        # depth.  Flatten the immediate-parent directory's contents into
        # run_cwd so cwd-relative references resolve.
        parts = [p for p in arg.replace(os.sep, "/").split("/") if p and p != "."]
        if len(parts) > 1:
            parent_rel = "/".join(parts[:-1])
            for candidate_root in search_roots:
                parent_dir = candidate_root / parent_rel
                if parent_dir.is_dir():
                    for child in parent_dir.iterdir():
                        if _is_stale_checkpoint(child.name):
                            continue
                        sibling = run_cwd / child.name
                        if sibling.exists() or sibling.is_symlink():
                            continue
                        try:
                            sibling.symlink_to(child.resolve())
                        except OSError:
                            pass
                    break


# ---------------------------------------------------------------------------
# Baseline run
# ---------------------------------------------------------------------------


def run_baseline(
    source_dir: Path,
    build_dir: Path,
    output_dir: Path,
    executable_name: str,
    num_procs: int,
    app_args: list[str],
    run_install: bool = False,
    build_cmd: str | None = None,
    app_input_subdir: str | None = None,
    extra_source_dirs: list[Path] | None = None,
    priority_source_dirs: list[Path] | None = None,
) -> RunResult:
    """Build and run the baseline (original) application once without failure injection.

    If *build_cmd* is provided, the shell-command build path in
    :func:`configure_and_build` is used (matches the per-app ``build.cmd`` from
    ``app.yaml``).  Otherwise CMake-based build is attempted — only correct
    for apps that ship a working ``CMakeLists.txt``.

    *app_input_subdir*, *extra_source_dirs* and *priority_source_dirs* are
    forwarded to :func:`_symlink_input_data` so apps whose ``run.cmd`` uses
    a ``cd <subdir> && ...`` prefix find their input files in the per-run
    cwd.  *priority_source_dirs* lets the caller force input files from a
    different source tree to take precedence over the build's own (used by
    the audit's reference baseline to align inputs with the vanilla).
    """
    configure_and_build(source_dir, build_dir, run_install=run_install,
                        build_cmd=build_cmd)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Ensure input data referenced by relative paths in app_args is accessible
    # from the run CWD (which differs from the build directory).
    _symlink_input_data(
        source_dir, build_dir, output_dir, app_args,
        extra_source_dirs=extra_source_dirs,
        input_subdir=app_input_subdir,
        priority_source_dirs=priority_source_dirs,
    )

    result = run_once(
        build_dir=build_dir,
        executable_name=executable_name,
        num_procs=num_procs,
        app_args=app_args,
        output_dir=output_dir,
        run_cwd=output_dir,
    )

    if not result.succeeded:
        raise ValidationError(
            f"Baseline run failed with exit code {result.exit_code}",
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
            output_dir=output_dir,
        )
    return result


# ---------------------------------------------------------------------------
# Resilient run with failure injection and retry loop
# ---------------------------------------------------------------------------


def run_with_failure_injection(
    source_dir: Path,
    build_dir: Path,
    output_dir: Path,
    executable_name: str,
    num_procs: int,
    app_args: list[str],
    max_attempts: int | None = 10,
    injection_delay: float = 5.0,
    target_failures: int = 1,
    run_install: bool = False,
    success_output_filename: str | None = None,
    veloc_config_name: str = "veloc.cfg",
    require_injection: bool = True,
    memory_monitor_fn: "callable | None" = None,
    memory_stop_event: "threading.Event | None" = None,
    memory_samples_holder: "list | None" = None,
    injection_nodes: str | None = None,
    injection_hostfile: str | None = None,
    build_cmd: str | None = None,
    app_input_subdir: str | None = None,
    extra_source_dirs: list[Path] | None = None,
    attempt_timeout_s: float | None = None,
    recovery_app_args: list[str] | None = None,
    priority_source_dirs: list[Path] | None = None,
    perturbation_spec: "object | None" = None,
    perturbation_seed: int | None = None,
) -> RunResult:
    """Inject *target_failures* failures into a single resilient run.

    Each attempt = one ``mpirun`` invocation.  The injector fires once per
    attempt at ``injection_delay`` seconds.  A successful kill counts toward
    ``total_injections``; the run is considered complete once the app exits 0
    AND ``total_injections >= target_failures``.  After the target is reached
    the next attempt is started **without an injector** so the app can run to
    natural completion.

    Parameters
    ----------
    target_failures:
        Total number of distinct successful injections required for the run
        to be considered complete.  Default ``1`` reproduces correctness-mode
        behavior (one kill + one recovery).  Set to N>1 for benchmark mode
        (Interpretation C: failure rate inside a single run).
    require_injection:
        When ``True`` (default, used for correctness validation), the loop
        retries until at least ``target_failures`` injections have succeeded.
        If the app finishes before the injector fires, the run is retried
        (after wiping the checkpoint dirs so the app actually runs again).

        When ``False`` (used for benchmarking), a successful exit (code 0) is
        accepted even if fewer than ``target_failures`` injections fired —
        this happens when ``injection_delay × (target_failures+1)`` exceeds
        the app's total runtime.  The returned :class:`RunResult` will report
        the actual injection count via ``num_attempts``.

    injection_nodes:
        Comma-separated list of hostnames where MPI rank processes may be
        running.  Forwarded to the failure injector so it can target
        processes across multiple nodes via SSH.  When ``None`` the
        injector auto-discovers nodes from SLURM/PBS environment variables
        or falls back to localhost.

    injection_hostfile:
        Path to a hostfile (one hostname per line) used by the failure
        injector for multi-node targeting.  Ignored when *injection_nodes*
        is provided.

    attempt_timeout_s:
        Per-attempt wallclock cap (seconds).  When set, each ``mpirun``
        invocation is killed (SIGTERM, escalating to SIGKILL after 10 s)
        if it has not exited within this many seconds, and the function
        raises :class:`ValidationError` immediately rather than retrying.
        Use this to bound runaway recoveries (e.g. checkpoint cadence so
        aggressive that the app never makes net progress).  Pass ``None``
        (default) for unbounded behavior.

    Returns a :class:`RunResult` for the final successful attempt, with
    ``injected`` reflecting whether at least one failure was actually injected
    and ``num_attempts`` set to the total number of MPI invocations.
    """
    if target_failures < 1:
        raise ValueError(f"target_failures must be >= 1, got {target_failures}")
    # Need at least one extra attempt past the target failures so the app
    # has a chance to run to completion without being killed.
    if max_attempts is not None and max_attempts <= target_failures:
        raise ValueError(
            f"max_attempts ({max_attempts}) must be > target_failures "
            f"({target_failures}) to leave room for the final clean run"
        )
    configure_and_build(source_dir, build_dir, run_install=run_install,
                        build_cmd=build_cmd)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Clear VeloC checkpoint dirs once before the retry loop starts.  This
    # guarantees a clean slate for the very first attempt of this run.
    # Subsequent attempts within the same run intentionally reuse the
    # checkpoints written by the previous (killed) attempt — that is the
    # whole point of the resilience retry loop.
    for cfg_candidate in (
        build_dir / veloc_config_name,
        source_dir / veloc_config_name,
    ):
        if cfg_candidate.exists():
            ckpt_dirs = extract_checkpoint_dirs_from_veloc_cfg(cfg_candidate)
            if ckpt_dirs:
                print(
                    "[runner] clearing VeloC checkpoint/scratch directories before run:",
                    flush=True,
                )
                for d in ckpt_dirs:
                    print(f"  - {d}", flush=True)
                clear_checkpoint_dirs(ckpt_dirs)
            break

    attempt = 0
    total_injections = 0
    total_elapsed = 0.0
    all_mem_samples: list[int] = []
    last_stdout = ""
    last_stderr = ""
    last_exit_code = -1
    # Holds the resolved perturbation value (None when perturbation_spec is
    # absent). Updated per attempt by _resolve_and_apply_perturbation; same
    # seed across attempts means the value is stable.
    perturbation_value = None
    _perturbed_env_override: dict = {}

    while True:
        attempt += 1
        if max_attempts is not None and attempt > max_attempts:
            raise ValidationError(
                f"Maximum number of attempts ({max_attempts}) reached without a "
                "successful resilient run. "
                f"Last attempt exit code: {last_exit_code}. "
                f"Injection succeeded on {total_injections} attempt(s). "
                "Check stdout/stderr below for details.",
                stdout=last_stdout,
                stderr=last_stderr,
                exit_code=last_exit_code,
                output_dir=output_dir,
            )

        attempt_dir = output_dir / f"attempt_{attempt}"
        if attempt_dir.exists():
            shutil.rmtree(attempt_dir)
        attempt_dir.mkdir(parents=True, exist_ok=True)

        # Per-attempt args.  attempt_1 always uses the original *app_args*
        # (writes checkpoints).  attempt_2+ uses *recovery_app_args* when set
        # (so upstream binaries that need different flags / a different input
        # file to read a checkpoint — LAMMPS, SPARTA, SW4lite, Athena++,
        # QMCPACK, Smilei — actually restore instead of starting fresh).
        # Falling back to *app_args* preserves previous behaviour for apps
        # whose binary auto-detects checkpoints (HPCG, MMSP, OpenLB, CoMD).
        if attempt > 1 and recovery_app_args is not None:
            # Resolve dynamic tokens like {LATEST_RESTORE:<subdir>} against
            # the on-disk state.  Search the shared run cwd (output_dir)
            # where checkpoints from attempt_1 were written.
            attempt_args = _resolve_dynamic_recovery_args(
                list(recovery_app_args),
                [output_dir],
            )
            args_source = "recovery"
        else:
            attempt_args = list(app_args)
            args_source = "primary"

        # veloc.cfg + input-data symlinks live in output_dir (the shared cwd
        # for all attempts), not in the per-attempt artifact dir.  Apps look
        # for these via cwd-relative paths.
        _copy_veloc_cfg(source_dir, build_dir, output_dir, veloc_config_name)
        _symlink_input_data(
            source_dir, build_dir, output_dir, attempt_args,
            extra_source_dirs=extra_source_dirs,
            input_subdir=app_input_subdir,
            priority_source_dirs=priority_source_dirs,
        )
        # 2026-05-17 cold-replay detector: apply random input perturbation
        # AFTER the symlink step (regex_replace needs to overwrite the
        # freshly-created symlink). app_arg_override and env_var_set
        # mutate the local attempt_args / run_env captures below.
        # Same perturbation_seed across all attempts of one run, so both
        # the kill leg and the recovery leg see the same perturbed input.
        attempt_args, _perturbed_env_override, _pv = _resolve_and_apply_perturbation(
            perturbation_spec, perturbation_seed,
            source_dir=source_dir, output_dir=output_dir,
            app_args=attempt_args, env={},
        )
        if _pv is not None:
            perturbation_value = _pv

        # Pre-attempt-2 hook: if a `_recovery_hook.sh` exists in the overlay
        # or source tree, run it from the cwd before launching attempt_2.
        # This is the extension point for apps whose binary needs cwd-side
        # setup before it can restore from a checkpoint — e.g. HyPar, where
        # restart_iter only adjusts iteration counters but the binary still
        # reads `initial.bin` for state, so the hook must copy the latest
        # `op_NNNNN.bin` over `initial.bin` before launch.
        if attempt > 1:
            hook_path = None
            search_roots = []
            if priority_source_dirs:
                search_roots.extend(priority_source_dirs)
            search_roots.extend([source_dir, build_dir])
            for root in search_roots:
                # Hook may live at the top of the overlay, or under
                # input_subdir if the app uses one (HyPar runs from
                # Examples/1D/FPDoubleWell, the hook lives there).
                candidates = [Path(root) / "_recovery_hook.sh"]
                if app_input_subdir:
                    candidates.append(Path(root) / app_input_subdir / "_recovery_hook.sh")
                for c in candidates:
                    if c.exists():
                        hook_path = c
                        break
                if hook_path:
                    break
            if hook_path:
                print(
                    f"[runner] attempt {attempt}: running recovery hook {hook_path}",
                    flush=True,
                )
                try:
                    hook_rc = subprocess.call(
                        ["bash", str(hook_path)],
                        cwd=str(output_dir),
                    )
                    print(
                        f"[runner] recovery hook exited with rc={hook_rc}",
                        flush=True,
                    )
                except Exception as e:
                    print(f"[runner] recovery hook failed to launch: {e}", flush=True)

        stdout_path = attempt_dir / "stdout.txt"
        stderr_path = attempt_dir / "stderr.txt"
        injection_flag_path = attempt_dir / "injection_success.flag"

        exe_path = _find_executable(build_dir, executable_name)
        mpirun = os.environ.get("MPIRUN_PATH") or _resolve_tool("mpirun")
        cmd = [mpirun, "-np", str(num_procs), str(exe_path), *attempt_args]
        print(
            f"[runner] attempt {attempt} ({args_source}): starting MPI run "
            f"(cwd={attempt_dir}): {' '.join(cmd)}",
            flush=True,
        )

        # Ensure LD_LIBRARY_PATH includes checkpoint library directories
        # (VeloC, FTI, SCR, jemalloc) — same logic as in run_once.
        run_env = dict(os.environ)
        # Apply env_var_set perturbation overrides on top of inherited env.
        if _perturbed_env_override:
            run_env.update(_perturbed_env_override)
        _existing_ld = run_env.get("LD_LIBRARY_PATH", "")
        _extra_libs: list[str] = []
        _veloc_prefix = _detect_veloc_dir()
        if _veloc_prefix:
            _vlib = _veloc_lib_dir(_veloc_prefix)
            if _vlib and _vlib not in _existing_ld.split(":"):
                _extra_libs.append(_vlib)
        _home_local_lib = os.path.join(os.path.expanduser("~"), ".local", "lib")
        if os.path.isdir(_home_local_lib) and _home_local_lib not in _existing_ld.split(":"):
            _extra_libs.append(_home_local_lib)
        if _extra_libs:
            run_env["LD_LIBRARY_PATH"] = ":".join(
                _extra_libs + ([_existing_ld] if _existing_ld else [])
            )

        # All attempts of one run share the same cwd (= output_dir, the run_X/
        # dir).  Per-attempt artifacts (stdout.txt, stderr.txt, injection
        # flag) are still written into attempt_N/ via explicit paths, but
        # the working directory is shared so apps that write checkpoint
        # files to relative paths (e.g. CoMD's "./CoMD_state-N.txt") have
        # those files persist across attempts and the restart can find them.
        # Note: many apps have small fixed-size buffers for checkpoint
        # paths, so passing a long absolute path via $CHKPT_DIR would
        # overflow them; cwd-sharing avoids that entirely.
        t0 = time.monotonic()
        with stdout_path.open("wb") as out_f, stderr_path.open("wb") as err_f:
            mpi_proc = subprocess.Popen(
                cmd,
                cwd=str(output_dir),
                stdout=out_f,
                stderr=err_f,
                env=run_env,
            )

        # Start per-attempt memory monitoring if requested.
        mem_thread = None
        if (
            memory_monitor_fn
            and memory_stop_event
            and memory_samples_holder is not None
        ):
            memory_stop_event.clear()
            memory_samples_holder[0] = []
            mem_thread = threading.Thread(
                target=memory_monitor_fn,
                args=(mpi_proc.pid, memory_samples_holder, memory_stop_event),
                daemon=True,
            )
            mem_thread.start()

        # Only start the injector if we still need more failures.  Once the
        # target is reached, the next attempt runs to natural completion.
        injector_proc = None
        if total_injections < target_failures:
            injector_proc = _start_failure_injector(
                target_parent_pid=mpi_proc.pid,
                executable_name=executable_name,
                injection_flag_path=injection_flag_path,
                delay_seconds=injection_delay,
                nodes=injection_nodes,
                hostfile=injection_hostfile,
            )
        else:
            print(
                f"[runner] attempt {attempt}: injector skipped "
                f"(target_failures={target_failures} reached); "
                "letting app run to completion.",
                flush=True,
            )

        timeout_hit = False
        if attempt_timeout_s and attempt_timeout_s > 0:
            try:
                mpi_return = mpi_proc.wait(timeout=attempt_timeout_s)
            except subprocess.TimeoutExpired:
                timeout_hit = True
                print(
                    f"[runner] attempt {attempt}: TIMEOUT after "
                    f"{attempt_timeout_s:.1f}s (~3x baseline) — terminating "
                    f"mpirun (pid={mpi_proc.pid}). Likely a runaway recovery "
                    "loop or excessive checkpoint cadence in modified code.",
                    flush=True,
                )
                mpi_proc.terminate()
                try:
                    mpi_return = mpi_proc.wait(timeout=10.0)
                except subprocess.TimeoutExpired:
                    print(
                        f"[runner] attempt {attempt}: mpirun (pid={mpi_proc.pid}) "
                        "still alive after SIGTERM; sending SIGKILL.",
                        flush=True,
                    )
                    mpi_proc.kill()
                    try:
                        mpi_return = mpi_proc.wait(timeout=5.0)
                    except subprocess.TimeoutExpired:
                        mpi_return = -9
        else:
            mpi_return = mpi_proc.wait()
        elapsed = time.monotonic() - t0
        total_elapsed += elapsed

        # Stop memory monitor for this attempt.
        if mem_thread is not None and memory_stop_event is not None:
            memory_stop_event.set()
            mem_thread.join(timeout=5.0)
            # Accumulate samples from this attempt.
            all_mem_samples.extend(memory_samples_holder[0])

        # Ensure injector has finished (if we started one this attempt).
        if injector_proc is not None:
            try:
                injector_proc.wait(timeout=10.0)
            except subprocess.TimeoutExpired:
                print("[runner] injector still running; terminating", flush=True)
                injector_proc.terminate()
                try:
                    injector_proc.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    injector_proc.kill()

        injected = injection_flag_path.exists()
        if injected:
            total_injections += 1

        last_stdout = _read_text_tailed(stdout_path)
        last_stderr = _read_text_tailed(stderr_path)
        last_exit_code = mpi_return

        print(
            f"[runner] attempt {attempt}: exit={mpi_return}, injected={injected}, "
            f"total_injections={total_injections}, elapsed={elapsed:.2f}s"
            f"{' [TIMEOUT]' if timeout_hit else ''}",
            flush=True,
        )

        # Per-attempt timeout: do not retry — every retry would hang the
        # same way (e.g. checkpoint cadence too aggressive to make net
        # progress).  Surface the failure with full context so the LLM
        # iteration loop can diagnose and try a different approach.
        if timeout_hit:
            raise ValidationError(
                f"Attempt {attempt} exceeded the per-attempt wallclock cap of "
                f"{attempt_timeout_s:.1f}s (~3x baseline). The modified "
                "application is not making net forward progress — typical "
                "causes: checkpoint cadence so frequent the app spends all "
                "its time writing checkpoints; an infinite restart loop; or "
                "deadlock during recovery. Tail of stdout/stderr below.",
                stdout=last_stdout,
                stderr=last_stderr,
                exit_code=mpi_return,
                output_dir=output_dir,
            )

        # SUCCESS: app exited cleanly AND we have enough injections.
        if mpi_return == 0 and total_injections >= target_failures:
            final_stdout = output_dir / "stdout_success.txt"
            final_stderr = output_dir / "stderr_success.txt"
            shutil.copy2(stdout_path, final_stdout)
            shutil.copy2(stderr_path, final_stderr)
            if success_output_filename:
                src = attempt_dir / success_output_filename
                if src.exists():
                    dst = output_dir / success_output_filename
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
            print(
                f"[runner] successful resilient run after {attempt} attempt(s) "
                f"({total_injections}/{target_failures} injection(s) delivered). "
                f"Output saved under {output_dir}",
                flush=True,
            )
            return RunResult(
                exit_code=0,
                stdout=last_stdout,
                stderr=last_stderr,
                elapsed_s=total_elapsed,
                injected=total_injections > 0,
                num_attempts=attempt,
                output_dir=output_dir,
                last_attempt_elapsed_s=elapsed,
                memory_samples_bytes=all_mem_samples,
                perturbation_seed=perturbation_seed,
                perturbation_value=perturbation_value,
            )

        # App finished cleanly BUT we are still short of target_failures.
        if mpi_return == 0 and total_injections < target_failures:
            if not require_injection:
                # Benchmark mode: accept the partial run, but warn so the
                # operator can re-tune injection_delay or load size.
                final_stdout = output_dir / "stdout_success.txt"
                final_stderr = output_dir / "stderr_success.txt"
                shutil.copy2(stdout_path, final_stdout)
                shutil.copy2(stderr_path, final_stderr)
                if success_output_filename:
                    src = attempt_dir / success_output_filename
                    if src.exists():
                        dst = output_dir / success_output_filename
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dst)
                print(
                    f"[runner] run completed with exit 0 but only "
                    f"{total_injections}/{target_failures} failures landed "
                    f"(injection_delay={injection_delay}s likely too long for "
                    f"the remaining work). Accepted under require_injection=False.",
                    flush=True,
                )
                return RunResult(
                    exit_code=0,
                    stdout=last_stdout,
                    stderr=last_stderr,
                    elapsed_s=total_elapsed,
                    injected=total_injections > 0,
                    num_attempts=attempt,
                    output_dir=output_dir,
                    last_attempt_elapsed_s=elapsed,
                    memory_samples_bytes=all_mem_samples,
                    perturbation_seed=perturbation_seed,
                    perturbation_value=perturbation_value,
                )
            # Correctness mode: must have at least target_failures injections.
            # Clear checkpoint dirs so the next attempt actually runs the app
            # again instead of restoring from a completed checkpoint.
            for cfg_candidate in (
                build_dir / veloc_config_name,
                source_dir / veloc_config_name,
            ):
                if cfg_candidate.exists():
                    ckpt_dirs = extract_checkpoint_dirs_from_veloc_cfg(cfg_candidate)
                    if ckpt_dirs:
                        print(
                            "[runner] clearing VeloC checkpoints before retry "
                            f"({total_injections}/{target_failures} injections so far):",
                            flush=True,
                        )
                        for d in ckpt_dirs:
                            print(f"  - {d}", flush=True)
                        clear_checkpoint_dirs(ckpt_dirs)
                    break
            print(
                f"[runner] run completed with exit 0 but only "
                f"{total_injections}/{target_failures} injections delivered; "
                "retrying.",
                flush=True,
            )
        else:
            # mpi_return != 0 — typically because the injector killed the app.
            # Restart from the most recent checkpoint on the next attempt.
            print(
                f"[runner] MPI run did not complete successfully "
                f"(exit={mpi_return}, total_injections={total_injections}/{target_failures}); "
                "restarting from checkpoint.",
                flush=True,
            )

        time.sleep(1.0)


# ---------------------------------------------------------------------------
# Checkpoint-observed failure injection (production correctness validation)
# ---------------------------------------------------------------------------


def _count_checkpoint_files(dirs: "list[Path]") -> int:
    """Recursively count regular files under each VeloC scratch/persistent dir.

    Used by the checkpoint-observed injection strategy to detect when the
    application has actually written checkpoint state to disk.  Empty dirs,
    missing dirs, and pure metadata (subdirectories with no files) do not
    count — only real files indicate the application performed a checkpoint
    write.
    """
    total = 0
    for d in dirs:
        if not d.exists() or not d.is_dir():
            continue
        try:
            for child in d.rglob("*"):
                if child.is_file():
                    total += 1
        except OSError:
            continue
    return total


# F-20 helpers (2026-05-15): track files the LLM-modified binary
# creates or modifies under /tmp/ AND build/ during a kill+recovery
# cycle, so validate.py can content-check them against the baseline
# output (gaming-6 detection — side-car cache outside VeloC dirs OR
# tampering with the cached baseline file inside build/).
#
# Tracking both roots is required because the LLM has filesystem
# write access via the binary it controls.  Likely targets:
#   - /tmp/<exe>_signature_cache.bin       (sibling sidecar; v48d)
#   - build/baseline_cache/<APP>/...       (tampering with cached baseline)
#   - build/validation_output/.../...      (sibling files outside attempt dirs)
#   - build/tests_baseline/<APP>/...       (writes to the LLM's source tree)
_F20_SKIP_TMP_PREFIXES = (
    "/tmp/.X11-unix",
    "/tmp/.font-unix",
    "/tmp/.ICE-unix",
    "/tmp/.Test-unix",
    "/tmp/.XIM-unix",
    "/tmp/systemd-",
    "/tmp/snap-private-tmp",
    "/tmp/pmix-",
    "/tmp/openmpi-",
    "/tmp/ompi.",
    "/tmp/ssh-",
    "/tmp/dbus-",
    "/tmp/claude-",
    "/tmp/cargo-",
)
# Inside build/ we skip compiler intermediate dirs and vendored
# sources — the LLM doesn't typically tamper with these from inside
# the running binary, and snapshotting them is expensive.  These
# names are matched as ANY path component (so "build/foo/_build/bar"
# is skipped via "_build").
_F20_SKIP_BUILD_DIR_NAMES = frozenset({
    "_build",          # CMake build dir (compiler intermediates)
    "CMakeFiles",      # CMake intermediate
    "subprojects",     # vendored sources (e.g. AMReX inside Nyx)
    "_deps",           # CMake fetched deps
    "third_party",
    "vendor",
    "thirdparty",
    "node_modules",
    ".git",
    "__pycache__",
})


def _snapshot_paths_for_gaming_check(
    roots: "list[Path]",
) -> "dict[str, tuple[int, float]]":
    """Snapshot every regular file under each *roots* dir.  Returns
    {path: (size, mtime)}.  Used to diff before / after each binary
    attempt and identify what the binary touched.

    Skips noisy system entries under /tmp/ (sockets, dbus, etc.) and
    huge compiler intermediates under build/ (subprojects/, _build/,
    CMakeFiles/, _deps/, third_party/).
    """
    snap: "dict[str, tuple[int, float]]" = {}
    for root in roots:
        try:
            if not root.exists():
                continue
            root_str = str(root)
            # /tmp/ has its own skip-prefix list.
            is_tmp_root = root_str == "/tmp" or root_str.startswith("/tmp/")
            for entry in root.iterdir():
                entry_str = str(entry)
                if is_tmp_root and any(entry_str.startswith(p) for p in _F20_SKIP_TMP_PREFIXES):
                    continue
                try:
                    if entry.is_file():
                        st = entry.stat()
                        snap[entry_str] = (st.st_size, st.st_mtime)
                    elif entry.is_dir():
                        # Walk recursively, skipping known compiler /
                        # vendored dir names anywhere in the path.
                        for f in entry.rglob("*"):
                            try:
                                if not f.is_file():
                                    continue
                                # Skip if any path component is a
                                # known noisy/vendored dir name.
                                if any(part in _F20_SKIP_BUILD_DIR_NAMES for part in f.parts):
                                    continue
                                st = f.stat()
                                snap[str(f)] = (st.st_size, st.st_mtime)
                            except OSError:
                                continue
                except OSError:
                    continue
        except OSError:
            continue
    return snap


def _diff_path_snapshots(
    before: "dict[str, tuple[int, float]]",
    after: "dict[str, tuple[int, float]]",
    excluded_dir_strs: "list[str]",
) -> "list[str]":
    """Files newly created or modified between snapshots, excluding
    paths inside any directory in *excluded_dir_strs*.  Excluded
    dirs typically include the VeloC scratch / persistent dirs
    (legitimate ckpt locations) and the current attempt's output_dir
    (legitimate run cwd where stdout.txt etc. land).
    """
    out: "list[str]" = []
    excl_prefixes = tuple(d.rstrip("/") + "/" for d in excluded_dir_strs)
    excl_exact = set(excluded_dir_strs)
    for path, (size, mtime) in after.items():
        prev = before.get(path)
        if prev is not None and prev == (size, mtime):
            continue  # unchanged
        if path in excl_exact:
            continue
        if any(path.startswith(p) for p in excl_prefixes):
            continue
        out.append(path)
    return out


# Backwards-compatible aliases (in case anything else imports them).
_snapshot_tmp_file_states = _snapshot_paths_for_gaming_check
_diff_tmp_snapshots = _diff_path_snapshots


def run_with_checkpoint_observed_injection(
    source_dir: "Path",
    build_dir: "Path",
    output_dir: "Path",
    executable_name: str,
    num_procs: int,
    app_args: "list[str]",
    failure_free_elapsed: float,
    *,
    observation_threshold_fraction: float = 0.5,
    poll_interval_s: float = 1.0,
    post_checkpoint_wait_s: float = 5.0,
    recovery_timeout_s: "float | None" = None,
    safety_kill_attempt_timeout_s: "float | None" = None,
    success_output_filename: "str | None" = None,
    veloc_config_name: str = "veloc.cfg",
    run_install: bool = False,
    build_cmd: "str | None" = None,
    app_input_subdir: "str | None" = None,
    extra_source_dirs: "list[Path] | None" = None,
    memory_monitor_fn: "callable | None" = None,
    memory_stop_event: "threading.Event | None" = None,
    memory_samples_holder: "list | None" = None,
    injection_nodes: "str | None" = None,
    injection_hostfile: "str | None" = None,
    perturbation_spec: "object | None" = None,
    perturbation_seed: "int | None" = None,
) -> RunResult:
    """Checkpoint-observed failure injection (single kill + single recovery).

    Used for production correctness validation (Validation B).  Replaces the
    fixed-delay retry loop of :func:`run_with_failure_injection` with a
    strategy that:

      1. Builds, then starts MPI (kill attempt).
      2. Sleeps until ``observation_threshold_fraction × failure_free_elapsed``
         has elapsed.
      3. Polls the VeloC scratch/persistent directories every
         ``poll_interval_s`` seconds for any newly-written checkpoint file.
      4. **No checkpoint observed before the app exited** → returns a
         ``RunResult`` with ``checkpoint_observed=False`` and a non-zero
         ``exit_code``.  validate.py's production enforcement will treat
         this as a FAILED verdict (the application has no working
         checkpoint mechanism).
      5. **Checkpoint observed** → sleeps ``post_checkpoint_wait_s`` (so
         the in-progress write completes), then issues SIGKILL via the
         failure injector.
      6. Waits for the kill attempt to die.
      7. Starts MPI again (recovery attempt) **without clearing the
         checkpoint dirs** — recovery should restore from the just-written
         checkpoint.
      8. Waits for the recovery attempt with ``recovery_timeout_s``
         wallclock cap (default ``failure_free_elapsed × 1.5``).
      9. Returns the combined ``RunResult``: ``elapsed_s`` is the sum of
         the kill attempt and the recovery attempt; ``num_attempts=2``;
         ``checkpoint_observed=True``; ``injected=True``.

    The PASS/FAIL verdict (output correctness + total wallclock cap of
    ``failure_free_elapsed × 1.2``) is enforced in validate.py, not here —
    this function only carries out the kill-and-recover protocol and
    surfaces the timing data for downstream policy enforcement.
    """
    if failure_free_elapsed <= 0:
        raise ValueError(
            f"failure_free_elapsed must be > 0, got {failure_free_elapsed}"
        )
    if not (0.0 < observation_threshold_fraction < 1.0):
        raise ValueError(
            f"observation_threshold_fraction must be in (0, 1), "
            f"got {observation_threshold_fraction}"
        )
    if recovery_timeout_s is None:
        recovery_timeout_s = failure_free_elapsed * 1.5
    if safety_kill_attempt_timeout_s is None:
        # Generous safety net for the kill attempt.  Normally we kill at
        # ~observation_threshold + post_checkpoint_wait so the process
        # never reaches this cap.  It only fires if the polling loop has
        # been running indefinitely without ever seeing a checkpoint AND
        # without the process exiting (an unusual hang).
        safety_kill_attempt_timeout_s = max(
            failure_free_elapsed * 2.0,
            failure_free_elapsed + post_checkpoint_wait_s + 30.0,
        )

    configure_and_build(
        source_dir, build_dir, run_install=run_install, build_cmd=build_cmd,
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    # Resolve VeloC checkpoint directories from the app's veloc.cfg.  The
    # polling loop checks these for newly-written files.
    ckpt_dirs: list[Path] = []
    cfg_path: Path | None = None
    for cfg_candidate in (
        build_dir / veloc_config_name,
        source_dir / veloc_config_name,
    ):
        if cfg_candidate.exists():
            cfg_path = cfg_candidate
            ckpt_dirs = extract_checkpoint_dirs_from_veloc_cfg(cfg_candidate)
            break
    if not ckpt_dirs:
        raise ValidationError(
            f"No VeloC checkpoint directories resolved from {veloc_config_name} "
            f"under {source_dir} or {build_dir}.  The checkpoint-observed "
            "injection strategy needs scratch/persistent paths to poll.  "
            "Either ship a valid veloc.cfg or use the legacy fixed-delay "
            "strategy.",
            stdout="",
            stderr="",
            exit_code=-1,
            output_dir=output_dir,
        )

    # Clean slate before the kill attempt so any newly-observed file is
    # actually written by THIS run, not leftover state from a prior one.
    print(
        "[runner] checkpoint-observed: clearing VeloC scratch/persistent dirs "
        "before kill attempt:",
        flush=True,
    )
    for d in ckpt_dirs:
        print(f"  - {d}", flush=True)
    clear_checkpoint_dirs(ckpt_dirs)

    # Outer-scope perturbation tracking so _launch_attempt can write back to it.
    # The same value is computed on every call (deterministic from seed), so any
    # call sets the same final value. None when perturbation is inactive.
    observed_perturbation_value: "int | float | None" = None

    # Helper to launch one mpirun attempt; returns (proc, attempt_dir,
    # stdout_path, stderr_path, t0_monotonic).
    def _launch_attempt(attempt_idx: int):
        nonlocal observed_perturbation_value
        attempt_dir = output_dir / f"attempt_{attempt_idx}"
        if attempt_dir.exists():
            shutil.rmtree(attempt_dir)
        attempt_dir.mkdir(parents=True, exist_ok=True)

        _copy_veloc_cfg(source_dir, build_dir, output_dir, veloc_config_name)
        _symlink_input_data(
            source_dir, build_dir, output_dir, app_args,
            extra_source_dirs=extra_source_dirs,
            input_subdir=app_input_subdir,
        )
        # 2026-05-17 cold-replay detector: apply random input perturbation
        # after the symlink step. Same seed across kill + recovery attempts
        # of one run, so both legs see the same perturbed input.
        effective_app_args, perturbed_env_override, _pv = (
            _resolve_and_apply_perturbation(
                perturbation_spec, perturbation_seed,
                source_dir=source_dir, output_dir=output_dir,
                app_args=list(app_args), env={},
            )
        )
        if _pv is not None:
            observed_perturbation_value = _pv

        stdout_path = attempt_dir / "stdout.txt"
        stderr_path = attempt_dir / "stderr.txt"

        exe_path = _find_executable(build_dir, executable_name)
        mpirun = os.environ.get("MPIRUN_PATH") or _resolve_tool("mpirun")
        cmd = [mpirun, "-np", str(num_procs), str(exe_path), *effective_app_args]
        print(
            f"[runner] checkpoint-observed attempt {attempt_idx}: launching "
            f"(cwd={attempt_dir}): {' '.join(cmd)}",
            flush=True,
        )

        run_env = dict(os.environ)
        if perturbed_env_override:
            run_env.update(perturbed_env_override)
        _existing_ld = run_env.get("LD_LIBRARY_PATH", "")
        _extra_libs: list[str] = []
        _veloc_prefix = _detect_veloc_dir()
        if _veloc_prefix:
            _vlib = _veloc_lib_dir(_veloc_prefix)
            if _vlib and _vlib not in _existing_ld.split(":"):
                _extra_libs.append(_vlib)
        _home_local_lib = os.path.join(os.path.expanduser("~"), ".local", "lib")
        if (
            os.path.isdir(_home_local_lib)
            and _home_local_lib not in _existing_ld.split(":")
        ):
            _extra_libs.append(_home_local_lib)
        if _extra_libs:
            run_env["LD_LIBRARY_PATH"] = ":".join(
                _extra_libs + ([_existing_ld] if _existing_ld else [])
            )

        t0 = time.monotonic()
        with stdout_path.open("wb") as out_f, stderr_path.open("wb") as err_f:
            proc = subprocess.Popen(
                cmd,
                cwd=str(output_dir),
                stdout=out_f,
                stderr=err_f,
                env=run_env,
            )
        return proc, attempt_dir, stdout_path, stderr_path, t0

    # F-20: snapshot /tmp/ AND build/ state BEFORE the kill attempt
    # so we can diff after each attempt and emit the FULL list of
    # files the LLM-modified binary touches.  Tracking both roots is
    # required because the LLM has filesystem write access via the
    # binary it controls.
    #
    # NOTE on exclusions: the diff DELIBERATELY does NOT exclude any
    # directories.  In particular, VeloC scratch/persistent dirs and
    # the current attempt's output_dir are NOT excluded — the LLM can
    # stash a cache file inside those dirs too (e.g. give it a name
    # that looks like a VeloC ckpt, or drop it next to stdout.txt in
    # the attempt cwd).  F-20's content-check in validate.py is the
    # actual discriminator: legit ckpt files don't match the baseline
    # output bytes (a 40-byte signature won't match 4 MB of field
    # data); gaming caches do.  Whitelisting happens at the F-20
    # stage by file PATH, not directory: the official
    # output_dir/<output_file_name> and its attempt_*/ copies are
    # exempt because they're SUPPOSED to match the baseline (that's
    # the verdict criterion).  Everything else is fair game.
    _f20_excluded_dirs: "list[str]" = []
    # Find the project's build/ dir (for baseline_cache, validation_output,
    # tests_baseline tampering detection).  Walk up from output_dir to
    # find the first ancestor named "build".
    _f20_build_root: "Path | None" = None
    try:
        for parent in output_dir.resolve().parents:
            if parent.name == "build":
                _f20_build_root = parent
                break
    except OSError:
        pass
    _f20_snapshot_roots = [Path("/tmp")]
    if _f20_build_root is not None:
        _f20_snapshot_roots.append(_f20_build_root)
    _f20_snapshot_before_a1 = _snapshot_paths_for_gaming_check(_f20_snapshot_roots)
    _f20_files_modified: "list[str]" = []

    # ---- Attempt 1: kill attempt ----
    mpi_proc, attempt1_dir, a1_stdout_path, a1_stderr_path, t0_a1 = (
        _launch_attempt(1)
    )

    # Start memory monitoring for the kill attempt (will cover both attempts
    # via samples accumulation, mirroring run_with_failure_injection).
    all_mem_samples: list[int] = []
    mem_thread = None
    if (
        memory_monitor_fn
        and memory_stop_event
        and memory_samples_holder is not None
    ):
        memory_stop_event.clear()
        memory_samples_holder[0] = []
        mem_thread = threading.Thread(
            target=memory_monitor_fn,
            args=(mpi_proc.pid, memory_samples_holder, memory_stop_event),
            daemon=True,
        )
        mem_thread.start()

    observation_start_at = t0_a1 + (
        observation_threshold_fraction * failure_free_elapsed
    )
    safety_deadline = t0_a1 + safety_kill_attempt_timeout_s

    # Phase A: wait until observation threshold (50% of failure-free runtime)
    # while watching for unexpectedly-early process exit.
    print(
        f"[runner] checkpoint-observed: waiting until "
        f"{observation_threshold_fraction:.0%} of failure-free runtime "
        f"({observation_threshold_fraction * failure_free_elapsed:.1f}s) "
        "before polling for checkpoints.",
        flush=True,
    )
    early_exit = False
    while time.monotonic() < observation_start_at:
        if mpi_proc.poll() is not None:
            early_exit = True
            break
        time.sleep(min(poll_interval_s, max(0.1, observation_start_at - time.monotonic())))

    checkpoint_observed = False
    if not early_exit:
        # Phase B: poll for checkpoint files.  Exit conditions:
        #   - file count > 0  → checkpoint observed
        #   - process exited  → no checkpoint, treat as failure
        #   - safety_deadline → no checkpoint, treat as failure (hung app)
        print(
            "[runner] checkpoint-observed: starting checkpoint-file poll "
            f"(every {poll_interval_s:.1f}s)",
            flush=True,
        )
        while time.monotonic() < safety_deadline:
            n_files = _count_checkpoint_files(ckpt_dirs)
            if n_files > 0:
                checkpoint_observed = True
                print(
                    f"[runner] checkpoint-observed: detected {n_files} "
                    f"checkpoint file(s) in scratch/persistent dirs.",
                    flush=True,
                )
                break
            if mpi_proc.poll() is not None:
                # App exited before any checkpoint was written.
                break
            time.sleep(poll_interval_s)
        else:
            # Safety deadline hit without observing a checkpoint.
            print(
                "[runner] checkpoint-observed: safety deadline reached "
                f"({safety_kill_attempt_timeout_s:.1f}s) without observing "
                "a checkpoint; killing kill-attempt and reporting failure.",
                flush=True,
            )

    # If no checkpoint was observed, ensure the process is dead and return
    # with checkpoint_observed=False.  validate.py will fail this run.
    if not checkpoint_observed:
        if mpi_proc.poll() is None:
            mpi_proc.terminate()
            try:
                mpi_proc.wait(timeout=10.0)
            except subprocess.TimeoutExpired:
                mpi_proc.kill()
                try:
                    mpi_proc.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    pass
        kill_attempt_elapsed = time.monotonic() - t0_a1
        if mem_thread is not None and memory_stop_event is not None:
            memory_stop_event.set()
            mem_thread.join(timeout=5.0)
            if memory_samples_holder is not None:
                all_mem_samples.extend(memory_samples_holder[0])
        a1_stdout = _read_text_tailed(a1_stdout_path)
        a1_stderr = _read_text_tailed(a1_stderr_path)
        a1_exit = mpi_proc.returncode if mpi_proc.returncode is not None else -1
        # Refresh top-level stdout.txt / stderr.txt from this run so the
        # validate.py comparator reads CURRENT data, not a stale file from
        # a previous iteration that happened to leave files behind.  Without
        # this, the iterative loop's retry feedback mis-describes the failure
        # ("0 vs 40 numbers" when the kill attempt actually produced N lines)
        # and blocks the LLM from making progress.
        try:
            shutil.copy2(a1_stdout_path, output_dir / "stdout.txt")
            shutil.copy2(a1_stderr_path, output_dir / "stderr.txt")
        except OSError as exc:
            print(
                f"[runner] checkpoint-observed: WARNING failed to refresh "
                f"top-level stdout/stderr ({exc}); comparator may read stale "
                "files.",
                flush=True,
            )
        print(
            f"[runner] checkpoint-observed: NO CHECKPOINT detected "
            f"(kill_attempt elapsed={kill_attempt_elapsed:.2f}s, "
            f"exit={a1_exit}). Reporting checkpoint_observed=False.",
            flush=True,
        )
        # F-20: diff /tmp/ snapshots before vs after attempt 1.
        try:
            _f20_snap_after_a1 = _snapshot_paths_for_gaming_check(_f20_snapshot_roots)
            _f20_files_modified = _diff_path_snapshots(
                _f20_snapshot_before_a1, _f20_snap_after_a1, _f20_excluded_dirs
            )
        except Exception:
            _f20_files_modified = []
        return RunResult(
            exit_code=a1_exit if a1_exit != 0 else -1,
            stdout=a1_stdout,
            stderr=a1_stderr,
            elapsed_s=kill_attempt_elapsed,
            injected=False,
            injection_fired=False,
            num_attempts=1,
            output_dir=output_dir,
            last_attempt_elapsed_s=kill_attempt_elapsed,
            memory_samples_bytes=all_mem_samples,
            checkpoint_observed=False,
            kill_attempt_elapsed_s=kill_attempt_elapsed,
            recovery_attempt_elapsed_s=None,
            files_modified_in_scope=_f20_files_modified,
            perturbation_seed=perturbation_seed,
            perturbation_value=observed_perturbation_value,
        )

    # ---- Phase C: post-checkpoint wait, then inject failure ----
    print(
        f"[runner] checkpoint-observed: waiting {post_checkpoint_wait_s:.1f}s "
        "to let the in-flight checkpoint write complete before SIGKILL.",
        flush=True,
    )
    sleep_deadline = time.monotonic() + post_checkpoint_wait_s
    while time.monotonic() < sleep_deadline:
        if mpi_proc.poll() is not None:
            # App finished naturally during the post-checkpoint wait.  We
            # never got to inject — treat as inconclusive (FAIL: cannot
            # validate recovery if the app already finished).
            kill_attempt_elapsed = time.monotonic() - t0_a1
            if mem_thread is not None and memory_stop_event is not None:
                memory_stop_event.set()
                mem_thread.join(timeout=5.0)
                if memory_samples_holder is not None:
                    all_mem_samples.extend(memory_samples_holder[0])
            a1_stdout = _read_text_tailed(a1_stdout_path)
            a1_stderr = _read_text_tailed(a1_stderr_path)
            # Same stdout/stderr refresh as the no-checkpoint path; without
            # it, the comparator reads a stale file from a previous iter.
            try:
                shutil.copy2(a1_stdout_path, output_dir / "stdout.txt")
                shutil.copy2(a1_stderr_path, output_dir / "stderr.txt")
            except OSError as exc:
                print(
                    f"[runner] checkpoint-observed: WARNING failed to refresh "
                    f"top-level stdout/stderr ({exc}); comparator may read stale "
                    "files.",
                    flush=True,
                )
            print(
                "[runner] checkpoint-observed: app finished cleanly during "
                "the post-checkpoint wait window; injection was not delivered. "
                "Cannot validate recovery — reporting failure.",
                flush=True,
            )
            try:
                _f20_snap_after_a1 = _snapshot_paths_for_gaming_check(_f20_snapshot_roots)
                _f20_files_modified = _diff_path_snapshots(
                    _f20_snapshot_before_a1, _f20_snap_after_a1, _f20_excluded_dirs
                )
            except Exception:
                _f20_files_modified = []
            return RunResult(
                exit_code=mpi_proc.returncode if mpi_proc.returncode == 0 else -1,
                stdout=a1_stdout,
                stderr=a1_stderr,
                elapsed_s=kill_attempt_elapsed,
                injected=False,
                injection_fired=False,
                num_attempts=1,
                output_dir=output_dir,
                last_attempt_elapsed_s=kill_attempt_elapsed,
                memory_samples_bytes=all_mem_samples,
                checkpoint_observed=True,
                kill_attempt_elapsed_s=kill_attempt_elapsed,
                recovery_attempt_elapsed_s=None,
                files_modified_in_scope=_f20_files_modified,
                perturbation_seed=perturbation_seed,
                perturbation_value=observed_perturbation_value,
            )
        time.sleep(min(0.5, sleep_deadline - time.monotonic()))

    injection_flag_path = attempt1_dir / "injection_success.flag"
    injector_proc = _start_failure_injector(
        target_parent_pid=mpi_proc.pid,
        executable_name=executable_name,
        injection_flag_path=injection_flag_path,
        delay_seconds=0.0,
        nodes=injection_nodes,
        hostfile=injection_hostfile,
    )

    # Wait for the kill attempt to die after injection.  Generous timeout —
    # MPI ranks usually terminate within seconds of SIGKILL.
    try:
        mpi_proc.wait(timeout=60.0)
    except subprocess.TimeoutExpired:
        print(
            "[runner] checkpoint-observed: kill attempt did not exit within "
            "60 s of injection; sending SIGKILL to mpirun directly.",
            flush=True,
        )
        mpi_proc.kill()
        try:
            mpi_proc.wait(timeout=10.0)
        except subprocess.TimeoutExpired:
            pass

    # Reap the injector.
    try:
        injector_proc.wait(timeout=10.0)
    except subprocess.TimeoutExpired:
        injector_proc.terminate()
        try:
            injector_proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            injector_proc.kill()

    if mem_thread is not None and memory_stop_event is not None:
        memory_stop_event.set()
        mem_thread.join(timeout=5.0)
        if memory_samples_holder is not None:
            all_mem_samples.extend(memory_samples_holder[0])

    kill_attempt_elapsed = time.monotonic() - t0_a1
    injection_fired = injection_flag_path.exists()
    print(
        f"[runner] checkpoint-observed: kill attempt complete "
        f"(elapsed={kill_attempt_elapsed:.2f}s, injection_fired={injection_fired}).",
        flush=True,
    )

    # ---- Attempt 2: recovery attempt ----
    # Do NOT clear checkpoint dirs — the recovery must restore from them.
    print(
        f"[runner] checkpoint-observed: starting recovery attempt "
        f"(timeout {recovery_timeout_s:.1f}s = "
        f"{recovery_timeout_s / failure_free_elapsed:.2f}x failure-free).",
        flush=True,
    )
    rec_proc, attempt2_dir, a2_stdout_path, a2_stderr_path, t0_a2 = (
        _launch_attempt(2)
    )

    # Re-arm memory monitoring for the recovery attempt (cumulative samples).
    rec_mem_thread = None
    if (
        memory_monitor_fn
        and memory_stop_event
        and memory_samples_holder is not None
    ):
        memory_stop_event.clear()
        memory_samples_holder[0] = []
        rec_mem_thread = threading.Thread(
            target=memory_monitor_fn,
            args=(rec_proc.pid, memory_samples_holder, memory_stop_event),
            daemon=True,
        )
        rec_mem_thread.start()

    recovery_timed_out = False
    try:
        rec_return = rec_proc.wait(timeout=recovery_timeout_s)
    except subprocess.TimeoutExpired:
        recovery_timed_out = True
        print(
            f"[runner] checkpoint-observed: recovery TIMEOUT after "
            f"{recovery_timeout_s:.1f}s; killing.",
            flush=True,
        )
        rec_proc.terminate()
        try:
            rec_return = rec_proc.wait(timeout=10.0)
        except subprocess.TimeoutExpired:
            rec_proc.kill()
            try:
                rec_return = rec_proc.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                rec_return = -9

    recovery_elapsed = time.monotonic() - t0_a2

    if rec_mem_thread is not None and memory_stop_event is not None:
        memory_stop_event.set()
        rec_mem_thread.join(timeout=5.0)
        if memory_samples_holder is not None:
            all_mem_samples.extend(memory_samples_holder[0])

    a2_stdout = _read_text_tailed(a2_stdout_path)
    a2_stderr = _read_text_tailed(a2_stderr_path)

    # Surface success_output_filename from the recovery attempt for the
    # caller's downstream comparison logic (mirrors run_with_failure_injection).
    if rec_return == 0 and not recovery_timed_out:
        final_stdout = output_dir / "stdout_success.txt"
        final_stderr = output_dir / "stderr_success.txt"
        shutil.copy2(a2_stdout_path, final_stdout)
        shutil.copy2(a2_stderr_path, final_stderr)
        if success_output_filename:
            src = attempt2_dir / success_output_filename
            if src.exists():
                dst = output_dir / success_output_filename
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

    total_elapsed = kill_attempt_elapsed + recovery_elapsed
    print(
        f"[runner] checkpoint-observed: recovery attempt complete "
        f"(elapsed={recovery_elapsed:.2f}s, exit={rec_return}, "
        f"timed_out={recovery_timed_out}).  "
        f"Total kill+recovery elapsed={total_elapsed:.2f}s "
        f"({total_elapsed / failure_free_elapsed:.2f}x failure-free).",
        flush=True,
    )

    # F-20: diff /tmp/ snapshots before kill vs after recovery
    # (covers both attempts as one window — the LLM may have written
    # the side-car during attempt 1 OR during recovery; either way
    # we see it in the post-recovery snapshot).
    try:
        _f20_snap_after_a2 = _snapshot_paths_for_gaming_check(_f20_snapshot_roots)
        _f20_files_modified = _diff_path_snapshots(
            _f20_snapshot_before_a1, _f20_snap_after_a2, _f20_excluded_dirs
        )
    except Exception:
        _f20_files_modified = []

    return RunResult(
        exit_code=rec_return,
        stdout=a2_stdout,
        stderr=a2_stderr,
        elapsed_s=total_elapsed,
        injected=injection_fired,
        injection_fired=injection_fired,
        num_attempts=2,
        output_dir=output_dir,
        last_attempt_elapsed_s=recovery_elapsed,
        memory_samples_bytes=all_mem_samples,
        checkpoint_observed=True,
        kill_attempt_elapsed_s=kill_attempt_elapsed,
        recovery_attempt_elapsed_s=recovery_elapsed,
        files_modified_in_scope=_f20_files_modified,
        perturbation_seed=perturbation_seed,
        perturbation_value=observed_perturbation_value,
    )
