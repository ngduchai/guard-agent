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
                text_lines = [f"  ... ({omitted} lines omitted) ..."] + text_lines[-max_lines:]
            return [f"  {label}:"] + [f"    {l}" for l in text_lines]

        lines += _tail(self.stdout, "STDOUT (tail)")
        lines += _tail(self.stderr, "STDERR (tail)")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class RunResult:
    """Structured result of a single MPI application run."""
    exit_code: int
    stdout: str
    stderr: str
    elapsed_s: float
    injected: bool = False          # True if a failure was injected during this run
    num_attempts: int = 1           # total attempts consumed (>1 for retry runs)
    output_dir: Path = field(default_factory=Path)
    last_attempt_elapsed_s: float = 0.0  # wall-clock time of the final (successful) attempt
    memory_samples_bytes: list[int] = field(default_factory=list)  # RSS samples collected during run

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0


# ---------------------------------------------------------------------------
# Build helpers
# ---------------------------------------------------------------------------

def _run_cmd(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> int:
    """Run a shell command, streaming output to stdout, and return the exit code."""
    print(f"[runner] running: {' '.join(str(c) for c in cmd)}", flush=True)
    proc = subprocess.Popen(cmd, cwd=str(cwd) if cwd else None, env=env)
    proc.wait()
    return proc.returncode


def configure_and_build(
    source_dir: Path,
    build_dir: Path,
    run_install: bool = False,
) -> None:
    """Configure (via CMake) and build the example.

    Skips the configure step if ``CMakeCache.txt`` and a generator build file
    already exist (idempotent).  If *run_install* is True, also runs
    ``cmake --install`` with the install prefix set to *build_dir* so that
    runtime config files (e.g. ``veloc.cfg``) are placed next to the binary.
    """
    build_dir.mkdir(parents=True, exist_ok=True)

    cache = build_dir / "CMakeCache.txt"
    makefile = build_dir / "Makefile"
    ninja_file = build_dir / "build.ninja"
    configured = cache.exists() and (makefile.exists() or ninja_file.exists())

    if not configured:
        code = _run_cmd(["cmake", "-S", str(source_dir), "-B", str(build_dir)])
        if code != 0:
            raise RuntimeError(f"CMake configuration failed for {source_dir}")

    code = _run_cmd(["cmake", "--build", str(build_dir)])
    if code != 0:
        raise RuntimeError(f"Build failed for {source_dir}")

    if run_install:
        code = _run_cmd(
            ["cmake", "--install", str(build_dir), "--prefix", str(build_dir)]
        )
        if code != 0:
            raise RuntimeError(f"Install step failed for {source_dir}")


# ---------------------------------------------------------------------------
# Executable discovery
# ---------------------------------------------------------------------------

def _find_executable(build_dir: Path, executable_name: str) -> Path:
    """Locate the built executable under *build_dir*, searching recursively."""
    candidate = build_dir / executable_name
    if candidate.exists():
        return candidate
    for root, _dirs, files in os.walk(build_dir):
        if executable_name in files:
            return Path(root) / executable_name
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
    if veloc_config_sources:
        cfg_dst = cwd / veloc_config_name
        if not cfg_dst.exists():
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
            print("[runner] clearing VeloC checkpoint directories before run:", flush=True)
            for d in ckpt_dirs:
                print(f"  - {d}", flush=True)
            clear_checkpoint_dirs(ckpt_dirs)

    stdout_path = output_dir / "stdout.txt"
    stderr_path = output_dir / "stderr.txt"

    cmd = ["mpirun", "-np", str(num_procs), str(exe_path), *app_args]
    print(f"[runner] starting MPI run (cwd={cwd}): {' '.join(cmd)}", flush=True)

    t0 = time.monotonic()
    with stdout_path.open("wb") as out_f, stderr_path.open("wb") as err_f:
        proc = subprocess.Popen(
            cmd, cwd=str(cwd), stdout=out_f, stderr=err_f, env=env
        )

        # Start memory monitoring thread if requested.
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

    # Signal memory monitor to stop and wait for it.
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
    )


# ---------------------------------------------------------------------------
# Failure injector launcher
# ---------------------------------------------------------------------------

def _start_failure_injector(
    target_parent_pid: int,
    executable_name: str,
    injection_flag_path: Path,
    delay_seconds: float,
) -> subprocess.Popen:
    """Launch the failure_injector.py subprocess."""
    script_path = Path(__file__).with_name("failure_injector.py")
    cmd = [
        sys.executable,
        str(script_path),
        "--parent-pid", str(target_parent_pid),
        "--executable-name", executable_name,
        "--flag-path", str(injection_flag_path),
        "--delay-seconds", str(delay_seconds),
    ]
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
) -> RunResult:
    """Build and run the baseline (original) application once without failure injection."""
    configure_and_build(source_dir, build_dir, run_install=run_install)
    output_dir.mkdir(parents=True, exist_ok=True)

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
    run_install: bool = False,
    success_output_filename: str | None = None,
    veloc_config_name: str = "veloc.cfg",
    require_injection: bool = True,
    memory_monitor_fn: "callable | None" = None,
    memory_stop_event: "threading.Event | None" = None,
    memory_samples_holder: "list | None" = None,
) -> RunResult:
    """Retry loop: inject failures until the resilient app completes successfully.

    Parameters
    ----------
    require_injection:
        When ``True`` (default, used for correctness validation), the loop
        retries until at least one failure has been injected before the app
        completes successfully.  If the app finishes before the injector fires,
        the run is retried.

        When ``False`` (used for benchmarking), a successful exit (code 0) is
        accepted even if no failure was injected — this happens when the
        injection delay is longer than the total runtime.  The returned
        :class:`RunResult` will have ``injected=False`` in that case.

    Returns a :class:`RunResult` for the final successful attempt, with
    ``injected`` reflecting whether a failure was actually injected and
    ``num_attempts`` set to the total number of attempts.
    """
    configure_and_build(source_dir, build_dir, run_install=run_install)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Clear VeloC checkpoint dirs once before the retry loop starts.  This
    # guarantees a clean slate for the very first attempt of this run.
    # Subsequent attempts within the same run intentionally reuse the
    # checkpoints written by the previous (killed) attempt — that is the
    # whole point of the resilience retry loop.
    for cfg_candidate in (build_dir / veloc_config_name, source_dir / veloc_config_name):
        if cfg_candidate.exists():
            ckpt_dirs = extract_checkpoint_dirs_from_veloc_cfg(cfg_candidate)
            if ckpt_dirs:
                print("[runner] clearing VeloC checkpoint/scratch directories before run:", flush=True)
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

        _copy_veloc_cfg(source_dir, build_dir, attempt_dir, veloc_config_name)

        stdout_path = attempt_dir / "stdout.txt"
        stderr_path = attempt_dir / "stderr.txt"
        injection_flag_path = attempt_dir / "injection_success.flag"

        exe_path = _find_executable(build_dir, executable_name)
        cmd = ["mpirun", "-np", str(num_procs), str(exe_path), *app_args]
        print(
            f"[runner] attempt {attempt}: starting MPI run (cwd={attempt_dir}): "
            f"{' '.join(cmd)}",
            flush=True,
        )

        t0 = time.monotonic()
        with stdout_path.open("wb") as out_f, stderr_path.open("wb") as err_f:
            mpi_proc = subprocess.Popen(
                cmd, cwd=str(attempt_dir), stdout=out_f, stderr=err_f
            )

        # Start per-attempt memory monitoring if requested.
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

        injector_proc = _start_failure_injector(
            target_parent_pid=mpi_proc.pid,
            executable_name=executable_name,
            injection_flag_path=injection_flag_path,
            delay_seconds=injection_delay,
        )

        mpi_return = mpi_proc.wait()
        elapsed = time.monotonic() - t0
        total_elapsed += elapsed

        # Stop memory monitor for this attempt.
        if mem_thread is not None and memory_stop_event is not None:
            memory_stop_event.set()
            mem_thread.join(timeout=5.0)
            # Accumulate samples from this attempt.
            all_mem_samples.extend(memory_samples_holder[0])

        # Ensure injector has finished.
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

        last_stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
        last_stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
        last_exit_code = mpi_return

        print(
            f"[runner] attempt {attempt}: exit={mpi_return}, injected={injected}, "
            f"total_injections={total_injections}, elapsed={elapsed:.2f}s",
            flush=True,
        )

        if mpi_return == 0 and total_injections >= 1:
            # Success with injection: copy final outputs to the top-level output dir.
            final_stdout = output_dir / "stdout_success.txt"
            final_stderr = output_dir / "stderr_success.txt"
            shutil.copy2(stdout_path, final_stdout)
            shutil.copy2(stderr_path, final_stderr)
            if success_output_filename:
                src = attempt_dir / success_output_filename
                if src.exists():
                    shutil.copy2(src, output_dir / success_output_filename)
            print(
                f"[runner] successful resilient run after {attempt} attempt(s) "
                f"({total_injections} injection(s) total). Output saved under {output_dir}",
                flush=True,
            )
            return RunResult(
                exit_code=0,
                stdout=last_stdout,
                stderr=last_stderr,
                elapsed_s=total_elapsed,
                injected=True,
                num_attempts=attempt,
                output_dir=output_dir,
                last_attempt_elapsed_s=elapsed,
                memory_samples_bytes=all_mem_samples,
            )

        if mpi_return == 0 and total_injections == 0:
            if not require_injection:
                # Benchmarking mode: app completed before injection fired – that's OK.
                # Copy outputs and return success with injected=False.
                final_stdout = output_dir / "stdout_success.txt"
                final_stderr = output_dir / "stderr_success.txt"
                shutil.copy2(stdout_path, final_stdout)
                shutil.copy2(stderr_path, final_stderr)
                if success_output_filename:
                    src = attempt_dir / success_output_filename
                    if src.exists():
                        shutil.copy2(src, output_dir / success_output_filename)
                print(
                    f"[runner] run completed with exit 0 and no injection "
                    f"(injection_delay={injection_delay}s exceeded runtime). "
                    "Accepted as success (require_injection=False).",
                    flush=True,
                )
                return RunResult(
                    exit_code=0,
                    stdout=last_stdout,
                    stderr=last_stderr,
                    elapsed_s=total_elapsed,
                    injected=False,
                    num_attempts=attempt,
                    output_dir=output_dir,
                    last_attempt_elapsed_s=elapsed,
                    memory_samples_bytes=all_mem_samples,
                )
            # Correctness mode: must have injection – retry.
            # Clear checkpoint directories so the next attempt starts from
            # scratch instead of restoring from the completed checkpoint
            # (which would cause it to finish instantly again).
            for cfg_candidate in (build_dir / veloc_config_name, source_dir / veloc_config_name):
                if cfg_candidate.exists():
                    ckpt_dirs = extract_checkpoint_dirs_from_veloc_cfg(cfg_candidate)
                    if ckpt_dirs:
                        print(
                            "[runner] clearing VeloC checkpoints before retry "
                            "(previous run completed without injection):",
                            flush=True,
                        )
                        for d in ckpt_dirs:
                            print(f"  - {d}", flush=True)
                        clear_checkpoint_dirs(ckpt_dirs)
                    break
            print(
                "[runner] run completed with exit 0 but no injection yet; "
                "retrying to ensure at least one failure is injected.",
                flush=True,
            )
        else:
            print("[runner] MPI run did not complete successfully; restarting.", flush=True)

        time.sleep(1.0)
