import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path


def run_cmd(cmd, cwd=None, env=None) -> int:
    """Run a shell command, streaming output, and return the exit code."""
    print(f"[validation] running: {' '.join(cmd)}", flush=True)
    proc = subprocess.Popen(cmd, cwd=cwd, env=env)
    proc.wait()
    return proc.returncode


def configure_and_build(source_dir: Path, build_dir: Path, run_install: bool = False) -> None:
    """Configure (via CMake) and build the example, if needed.

    If run_install is True, also run `cmake --install` with the install
    prefix set to the build directory. This is useful for examples that
    install runtime configuration files (e.g., veloc.cfg).
    """
    build_dir.mkdir(parents=True, exist_ok=True)

    # Consider the build "configured" only if CMakeCache.txt and a generator
    # build file (e.g., Makefile or build.ninja) exist. This handles cases
    # where the cache remains but the build files were cleaned.
    cache = build_dir / "CMakeCache.txt"
    makefile = build_dir / "Makefile"
    ninja_file = build_dir / "build.ninja"
    configured = cache.exists() and (makefile.exists() or ninja_file.exists())

    if not configured:
        code = run_cmd(["cmake", "-S", str(source_dir), "-B", str(build_dir)])
        if code != 0:
            raise RuntimeError("CMake configuration failed")

    code = run_cmd(["cmake", "--build", str(build_dir)])
    if code != 0:
        raise RuntimeError("Build failed")

    if run_install:
        code = run_cmd(
            ["cmake", "--install", str(build_dir), "--prefix", str(build_dir)]
        )
        if code != 0:
            raise RuntimeError("Install step failed")


def start_mpi_run(
    build_dir: Path,
    executable_name: str,
    num_procs: int,
    app_args: list[str],
    stdout_path: Path,
    stderr_path: Path,
    run_cwd: Path | None = None,
) -> subprocess.Popen:
    exe_path = build_dir / executable_name
    if not exe_path.exists():
        # CMake may place executables in subdirectories; fall back to searching.
        for root, _dirs, files in os.walk(build_dir):
            if executable_name in files:
                exe_path = Path(root) / executable_name
                break
        else:
            raise FileNotFoundError(f"Executable {executable_name!r} not found under {build_dir}")

    stdout_f = stdout_path.open("wb")
    stderr_f = stderr_path.open("wb")

    cmd = ["mpirun", "-np", str(num_procs), str(exe_path), *app_args]
    cwd = run_cwd if run_cwd is not None else build_dir
    print(
        f"[validation] starting MPI run (cwd={cwd}): {' '.join(cmd)}",
        flush=True,
    )
    proc = subprocess.Popen(cmd, cwd=str(cwd), stdout=stdout_f, stderr=stderr_f)
    return proc


def start_failure_injector(
    target_parent_pid: int,
    executable_name: str,
    injection_flag_path: Path,
    delay_seconds: float,
) -> subprocess.Popen:
    """
    Launch a separate Python process that will attempt to kill one child MPI rank
    of the target_parent_pid whose command includes executable_name.
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
    print(f"[validation] starting failure injector: {' '.join(cmd)}", flush=True)
    return subprocess.Popen(cmd)


def run_with_retries(
    source_dir: Path,
    build_dir: Path,
    output_dir: Path,
    executable_name: str,
    num_procs: int,
    app_args: list[str],
    max_attempts: int,
    injection_delay: float,
    run_install: bool = False,
    success_output_filename: str | None = None,
) -> None:
    configure_and_build(source_dir, build_dir, run_install=run_install)
    output_dir.mkdir(parents=True, exist_ok=True)

    attempt = 0
    total_injections = 0
    while True:
        attempt += 1
        if max_attempts is not None and attempt > max_attempts:
            raise RuntimeError("Maximum number of attempts reached without a successful run")

        attempt_dir = output_dir / f"attempt_{attempt}"
        if attempt_dir.exists():
            shutil.rmtree(attempt_dir)
        attempt_dir.mkdir(parents=True, exist_ok=True)

        stdout_path = attempt_dir / "stdout.txt"
        stderr_path = attempt_dir / "stderr.txt"
        injection_flag_path = attempt_dir / "injection_success.flag"

        if injection_flag_path.exists():
            injection_flag_path.unlink()

        mpi_proc = start_mpi_run(
            build_dir=build_dir,
            executable_name=executable_name,
            num_procs=num_procs,
            app_args=app_args,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            run_cwd=attempt_dir,
        )

        injector_proc = start_failure_injector(
            target_parent_pid=mpi_proc.pid,
            executable_name=executable_name,
            injection_flag_path=injection_flag_path,
            delay_seconds=injection_delay,
        )

        # Wait for MPI run to finish.
        mpi_return = mpi_proc.wait()

        # Ensure injector has also finished (or terminate it after a grace period).
        try:
            injector_return = injector_proc.wait(timeout=10.0)
        except subprocess.TimeoutExpired:
            print("[validation] injector still running; terminating", flush=True)
            injector_proc.terminate()
            try:
                injector_proc.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                injector_proc.kill()
            injector_return = None

        injected = injection_flag_path.exists()
        if injected:
            total_injections += 1
        print(
            f"[validation] attempt {attempt}: mpi_return={mpi_return}, "
            f"injected={injected}, total_injections={total_injections}, "
            f"injector_return={injector_return}",
            flush=True,
        )

        # Success: at least one injection accumulated and this run exited 0.
        if mpi_return == 0 and total_injections >= 1:
            final_stdout = output_dir / "stdout_success.txt"
            final_stderr = output_dir / "stderr_success.txt"
            shutil.copy2(stdout_path, final_stdout)
            shutil.copy2(stderr_path, final_stderr)
            if success_output_filename:
                src = attempt_dir / success_output_filename
                if src.exists():
                    shutil.copy2(src, output_dir / success_output_filename)
            print(
                f"[validation] successful resilient run after {attempt} attempt(s) "
                f"({total_injections} injection(s) total). Output saved under {output_dir}",
                flush=True,
            )
            break

        if mpi_return == 0 and total_injections == 0:
            print(
                "[validation] run completed with exit 0 but no injection yet; "
                "retrying to ensure at least one failure is injected.",
                flush=True,
            )
        else:
            print(
                "[validation] MPI run did not complete successfully; restarting.",
                flush=True,
            )
        time.sleep(1.0)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build and validate an MPI example by repeatedly injecting process failures "
            "until the application completes successfully."
        )
    )
    parser.add_argument(
        "--source-dir",
        required=True,
        help="Path to the example source directory containing CMakeLists.txt",
    )
    parser.add_argument(
        "--build-dir",
        required=True,
        help="Path to the build directory for CMake",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where per-attempt outputs and final success logs are stored",
    )
    parser.add_argument(
        "--executable-name",
        required=True,
        help="Name of the built executable to run under mpirun",
    )
    parser.add_argument(
        "--num-procs",
        type=int,
        default=4,
        help="Number of MPI processes (ranks) to launch with mpirun",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=None,
        help="Maximum number of attempts before giving up (default: unlimited)",
    )
    parser.add_argument(
        "--injection-delay",
        type=float,
        default=5.0,
        help="Seconds to wait before injecting a failure into the MPI run",
    )
    parser.add_argument(
        "app_args",
        nargs=argparse.REMAINDER,
        help="Arguments passed through to the MPI application after '--'",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    # Support the common pattern: ... -- <app-args>
    if "--" in argv:
        idx = argv.index("--")
        fixed, rest = argv[:idx], argv[idx + 1 :]
        argv = fixed + rest

    args = parse_args(argv)

    source_dir = Path(args.source_dir).resolve()
    build_dir = Path(args.build_dir).resolve()
    output_dir = Path(args.output_dir).resolve()

    try:
        run_with_retries(
            source_dir=source_dir,
            build_dir=build_dir,
            output_dir=output_dir,
            executable_name=args.executable_name,
            num_procs=args.num_procs,
            app_args=args.app_args,
            max_attempts=args.max_attempts,
            injection_delay=args.injection_delay,
        )
    except Exception as exc:
        print(f"[validation] ERROR: {exc}", file=sys.stderr, flush=True)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

