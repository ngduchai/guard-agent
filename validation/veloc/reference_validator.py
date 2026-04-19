"""
reference_validator.py – Validate the reference pair (vanilla + checkpointed).

Verifies resilience through time-based analysis:
1. Golden run: error-free execution, measures T_golden
2. Vanilla kill+restart: kills at 90% of T_golden, restarts from scratch
   → T_vanilla > T_golden + kill_after (all pre-kill work wasted)
3. Checkpointed kill+restart: kills at 90% of T_golden, restarts from checkpoint
   → T_ckpt < T_golden * 1.4 (checkpoint saves most pre-kill work)
4. Output match: checkpointed output ≈ golden (correctness preserved)

This module reuses ``runner.py`` for build/run and ``comparator.py`` for comparison.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path

from guard_agent.schemas import AppConfig, ComparisonResult, ReferenceResult

from .comparator import CompareResult, make_comparator
from .runner import RunResult, configure_and_build, run_once


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BUILD_TIMEOUT = 1200  # 20 minutes


def _build_app(source_dir: Path, build_dir: Path, build_cmd: str) -> tuple[bool, str]:
    """Build an application. Returns (success, output)."""
    build_dir.mkdir(parents=True, exist_ok=True)

    if source_dir != build_dir:
        if build_dir.exists():
            shutil.rmtree(build_dir)
        shutil.copytree(source_dir, build_dir, symlinks=True,
                        ignore_dangling_symlinks=True)

    try:
        result = subprocess.run(
            build_cmd,
            shell=True,
            cwd=str(build_dir),
            capture_output=True,
            text=True,
            timeout=_BUILD_TIMEOUT,
        )
        output = result.stdout + "\n" + result.stderr
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, f"Build timed out after {_BUILD_TIMEOUT} seconds"
    except Exception as e:
        return False, f"Build failed: {e}"


def _run_app(
    build_dir: Path,
    run_cmd: str,
    timeout: int = 120,
    mpi_ranks: int = 4,
) -> RunResult:
    """Run an MPI application and capture output to files (avoids pipe deadlock)."""
    cmd = run_cmd.replace("{mpi_ranks}", str(mpi_ranks))
    stdout_file = build_dir / "_run_stdout.txt"
    stderr_file = build_dir / "_run_stderr.txt"

    try:
        start = time.monotonic()
        with open(stdout_file, "w") as fout, open(stderr_file, "w") as ferr:
            result = subprocess.run(
                cmd, shell=True, cwd=str(build_dir),
                stdout=fout, stderr=ferr, timeout=timeout,
            )
        elapsed = time.monotonic() - start
        return RunResult(
            exit_code=result.returncode,
            stdout=stdout_file.read_text(errors="replace"),
            stderr=stderr_file.read_text(errors="replace"),
            elapsed_s=elapsed,
            output_dir=build_dir,
        )
    except subprocess.TimeoutExpired:
        return RunResult(
            exit_code=-1,
            stdout=stdout_file.read_text(errors="replace") if stdout_file.exists() else "",
            stderr=f"Process timed out after {timeout} seconds",
            elapsed_s=float(timeout),
            output_dir=build_dir,
        )


def _run_with_kill(
    build_dir: Path,
    run_cmd: str,
    kill_after: float = 5.0,
    timeout: int = 120,
    mpi_ranks: int = 4,
    restart_cmd: str | None = None,
) -> RunResult:
    """Start an MPI app, kill it after ``kill_after`` seconds, then restart.

    Returns a RunResult with ``injection_fired=True`` only if the kill signal
    was sent while the process was still alive.
    """
    cmd = run_cmd.replace("{mpi_ranks}", str(mpi_ranks))
    restart = (restart_cmd or run_cmd).replace("{mpi_ranks}", str(mpi_ranks))

    # Phase 1: Start and kill (file-based stdout for debugging)
    phase1_stdout = build_dir / "_kill_stdout.txt"
    phase1_stderr = build_dir / "_kill_stderr.txt"
    injection_fired = False

    try:
        start = time.monotonic()
        with open(phase1_stdout, "w") as fout, open(phase1_stderr, "w") as ferr:
            proc = subprocess.Popen(
                cmd, shell=True, cwd=str(build_dir),
                stdout=fout, stderr=ferr,
                preexec_fn=os.setsid,
            )
        time.sleep(kill_after)

        # Check if process is still alive before killing
        poll = proc.poll()
        if poll is None:
            # Process still running → kill it
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            proc.wait(timeout=10)
            injection_fired = True
            print(f"  [injection] killed process group at {kill_after:.1f}s")
        else:
            # Process already exited before kill_after
            print(f"  [warning] app exited (code={poll}) before kill_after={kill_after:.1f}s — injection did NOT fire")
    except Exception as e:
        print(f"  [warning] Phase 1 kill failed: {e}")

    # Clean up any zombie MPI processes
    subprocess.run("pkill -9 -f 'mpirun|orted' 2>/dev/null || true",
                    shell=True, timeout=5)
    time.sleep(1)  # brief pause for OS cleanup

    # Phase 2: Restart (file-based stdout to avoid pipe deadlock)
    stdout_file = build_dir / "_restart_stdout.txt"
    stderr_file = build_dir / "_restart_stderr.txt"
    try:
        with open(stdout_file, "w") as fout, open(stderr_file, "w") as ferr:
            result = subprocess.run(
                restart, shell=True, cwd=str(build_dir),
                stdout=fout, stderr=ferr, timeout=timeout,
            )
        elapsed = time.monotonic() - start
        return RunResult(
            exit_code=result.returncode,
            stdout=stdout_file.read_text(errors="replace"),
            stderr=stderr_file.read_text(errors="replace"),
            elapsed_s=elapsed,
            injected=True,
            injection_fired=injection_fired,
            num_attempts=2,
            output_dir=build_dir,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - start
        return RunResult(
            exit_code=-1,
            stdout=stdout_file.read_text(errors="replace") if stdout_file.exists() else "",
            stderr=f"Restart timed out after {timeout}s",
            elapsed_s=elapsed,
            injected=True,
            injection_fired=injection_fired,
            num_attempts=2,
            output_dir=build_dir,
        )


def _filter_lines(
    text: str,
    ignore_patterns: list[str],
    keep_patterns: list[str] | None = None,
) -> str:
    """Filter output lines for comparison.

    If ``keep_patterns`` is non-empty, only lines matching at least one
    keep pattern survive (allowlist).  ``ignore_patterns`` is ignored in
    this case (with a warning if both are specified).
    """
    lines = text.splitlines()
    if keep_patterns and ignore_patterns:
        pass  # keep_patterns takes precedence; ignore_patterns silently skipped
    if keep_patterns:
        lines = [ln for ln in lines if any(pat in ln for pat in keep_patterns)]
    elif ignore_patterns:
        lines = [ln for ln in lines if not any(pat in ln for pat in ignore_patterns)]
    return "\n".join(lines)


def _compare_outputs(
    golden_stdout: str,
    test_stdout: str,
    method: str = "text",
    tolerance: float = 1e-6,
    golden_file: str | None = None,
    test_file: str | None = None,
    ignore_patterns: list[str] | None = None,
    keep_patterns: list[str] | None = None,
) -> ComparisonResult:
    """Compare golden output against test output."""
    if golden_file and test_file:
        comparator = make_comparator(method, atol=tolerance, rtol=tolerance)
        result = comparator.compare(Path(golden_file), Path(test_file))
        return ComparisonResult(
            method=result.method, passed=result.passed,
            details=result.message, score=result.score,
        )

    patterns = ignore_patterns or []
    keeps = keep_patterns or []
    golden_filtered = _filter_lines(golden_stdout, patterns, keeps or None)
    test_filtered = _filter_lines(test_stdout, patterns, keeps or None)

    if method == "text":
        passed = golden_filtered.strip() == test_filtered.strip()
        return ComparisonResult(
            method="text", passed=passed,
            details="" if passed else "Stdout differs from golden output",
        )

    if method == "numeric":
        import re
        golden_nums = [float(x) for x in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", golden_filtered)]
        test_nums = [float(x) for x in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", test_filtered)]
        if not golden_nums and not test_nums:
            return ComparisonResult(method="numeric", passed=True, details="No numbers to compare")
        if not golden_nums or not test_nums:
            return ComparisonResult(
                method="numeric", passed=False,
                details=f"One side has no numbers: {len(golden_nums)} vs {len(test_nums)}",
            )
        n = min(len(golden_nums), len(test_nums))
        length_note = ""
        if len(golden_nums) != len(test_nums):
            length_note = f" (lengths differ: {len(golden_nums)} vs {len(test_nums)})"
        max_diff = 0.0
        for g, t in zip(golden_nums[:n], test_nums[:n]):
            diff = abs(g - t)
            denom = max(abs(g), 1e-10)  # avoid division by zero
            diff = diff / denom
            max_diff = max(max_diff, diff)
        passed = max_diff <= tolerance
        return ComparisonResult(
            method="numeric", passed=passed,
            details=f"Max relative diff: {max_diff:.2e}{length_note}",
            score=1.0 - max_diff if passed else max_diff,
        )

    # Fallback: hash comparison
    import hashlib
    h1 = hashlib.sha256(golden_filtered.encode()).hexdigest()
    h2 = hashlib.sha256(test_filtered.encode()).hexdigest()
    passed = h1 == h2
    return ComparisonResult(
        method="hash", passed=passed,
        details="" if passed else f"Hash mismatch: {h1[:16]}... vs {h2[:16]}...",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def verify_no_recovery(
    vanilla_dir: Path,
    app_config: AppConfig,
    golden_elapsed: float,
    kill_after: float,
    work_dir: Path,
) -> tuple[bool, float]:
    """Verify vanilla app wastes time on restart (no checkpoint recovery).

    Returns (passed, T_vanilla).
    Pass criteria: T_vanilla > T_golden + kill_after
    (vanilla restarts from scratch, wasting all pre-kill computation).
    """
    build_dir = work_dir / "vanilla_kill"
    result = _run_with_kill(
        build_dir=build_dir if build_dir.exists() else vanilla_dir,
        run_cmd=app_config.run.cmd,
        kill_after=kill_after,
        timeout=app_config.run.timeout,
        mpi_ranks=app_config.mpi_ranks,
    )

    t_vanilla = result.elapsed_s
    threshold = golden_elapsed + kill_after
    passed = t_vanilla > threshold

    if not result.injection_fired:
        print(f"  [no_recovery] injection did NOT fire (app finished before kill)")
        passed = False

    print(f"  [no_recovery] T_vanilla={t_vanilla:.1f}s, threshold={threshold:.1f}s (T_golden={golden_elapsed:.1f}s + kill={kill_after:.1f}s) → {'PASS' if passed else 'FAIL'}")
    return passed, t_vanilla


def verify_recovery(
    checkpointed_dir: Path,
    app_config: AppConfig,
    golden_elapsed: float,
    kill_after: float,
    work_dir: Path,
) -> tuple[bool, RunResult, float]:
    """Verify checkpointed app recovers efficiently from failure.

    Returns (passed, run_result, T_ckpt).
    Pass criteria: T_ckpt < T_golden * 1.4 AND app exits successfully.
    """
    build_dir = work_dir / "checkpointed_kill"
    run_cfg = app_config.ckpt_run or app_config.run
    result = _run_with_kill(
        build_dir=build_dir if build_dir.exists() else checkpointed_dir,
        run_cmd=run_cfg.cmd,
        kill_after=kill_after,
        timeout=run_cfg.timeout,
        mpi_ranks=app_config.mpi_ranks,
        restart_cmd=run_cfg.restart_cmd,
    )

    t_ckpt = result.elapsed_s
    threshold = golden_elapsed * 1.4
    time_passed = t_ckpt < threshold
    recovered = result.succeeded and time_passed

    if not result.injection_fired:
        print(f"  [recovery] injection did NOT fire (app finished before kill)")
    if not result.succeeded:
        print(f"  [recovery] restart failed: exit_code={result.exit_code}")
        if result.stderr:
            print(f"  [recovery] stderr (last 300 chars): {result.stderr[-300:]}")

    print(f"  [recovery] T_ckpt={t_ckpt:.1f}s, threshold={threshold:.1f}s (T_golden={golden_elapsed:.1f}s × 1.4) → {'PASS' if recovered else 'FAIL'}")
    return recovered, result, t_ckpt


# ---------------------------------------------------------------------------
# Step caching
# ---------------------------------------------------------------------------

def _step_done(work_dir: Path, step: str) -> bool:
    marker = work_dir / ".steps" / step
    return marker.is_file()


def _mark_step(work_dir: Path, step: str, value: str = "") -> None:
    marker = work_dir / ".steps" / step
    marker.parent.mkdir(parents=True, exist_ok=True)
    content = value or time.strftime("%Y-%m-%dT%H:%M:%S")
    marker.write_text(content)


def _read_step(work_dir: Path, step: str) -> str:
    marker = work_dir / ".steps" / step
    return marker.read_text() if marker.is_file() else ""


def _clear_steps(work_dir: Path) -> None:
    steps_dir = work_dir / ".steps"
    if steps_dir.is_dir():
        shutil.rmtree(steps_dir)


# ---------------------------------------------------------------------------
# Main validation pipeline
# ---------------------------------------------------------------------------

def validate_reference(
    vanilla_dir: Path,
    checkpointed_dir: Path,
    app_config: AppConfig,
    work_dir: Path | None = None,
    fresh: bool = False,
) -> ReferenceResult:
    """Run the full reference validation pipeline for one app.

    Steps:
    1. Build vanilla
    2. Run vanilla (error-free) → golden output + T_golden
    3. Build checkpointed
    4. Verify vanilla has no recovery (T_vanilla > T_golden + kill_after)
    5. Verify checkpointed has recovery (T_ckpt < T_golden * 1.4)
    6. Compare checkpointed output vs golden output
    """
    start = time.monotonic()

    if work_dir is None:
        work_dir = Path(tempfile.mkdtemp(prefix=f"ref_{app_config.name}_"))
    work_dir.mkdir(parents=True, exist_ok=True)

    if fresh:
        _clear_steps(work_dir)

    result = ReferenceResult(app_name=app_config.name)
    van_build = work_dir / "vanilla_build"
    ckpt_build = work_dir / "checkpointed_build"
    golden_path = work_dir / "golden_stdout.txt"
    timing_path = work_dir / "timing.json"

    # On resume: clean stale build dirs
    if not fresh:
        if not _step_done(work_dir, "vanilla_build") and van_build.exists():
            print(f"  [resume] cleaning stale vanilla_build")
            shutil.rmtree(van_build)
        if not _step_done(work_dir, "checkpointed_build") and ckpt_build.exists():
            print(f"  [resume] cleaning stale checkpointed_build")
            shutil.rmtree(ckpt_build)

    # Step 1: Build vanilla
    if _step_done(work_dir, "vanilla_build"):
        print(f"  [resume] reusing vanilla build")
        result.vanilla_build_success = True
    else:
        success, output = _build_app(vanilla_dir, van_build, app_config.build.cmd)
        result.vanilla_build_success = success
        if not success:
            result.error_message = f"Vanilla build failed: {output[-500:]}"
            result.elapsed_seconds = time.monotonic() - start
            return result
        _mark_step(work_dir, "vanilla_build")

    # Step 2: Run vanilla (error-free) → golden output + T_golden
    golden_elapsed = 0.0
    if _step_done(work_dir, "golden_run") and golden_path.is_file():
        print(f"  [resume] reusing golden output")
        result.golden_run_success = True
        result.golden_output_path = str(golden_path)
        # Load cached T_golden
        if timing_path.is_file():
            golden_elapsed = json.loads(timing_path.read_text()).get("T_golden", 0.0)
    else:
        golden = _run_app(
            build_dir=van_build,
            run_cmd=app_config.run.cmd,
            timeout=app_config.run.timeout,
            mpi_ranks=app_config.mpi_ranks,
        )
        result.golden_run_success = golden.succeeded
        if not golden.succeeded:
            result.error_message = f"Golden run failed (exit {golden.exit_code}): {golden.stderr[-500:]}"
            result.elapsed_seconds = time.monotonic() - start
            return result
        golden_path.write_text(golden.stdout)
        golden_elapsed = golden.elapsed_s
        # Save T_golden for resume
        timing_path.write_text(json.dumps({"T_golden": golden_elapsed}))
        result.golden_output_path = str(golden_path)
        _mark_step(work_dir, "golden_run")

    golden_stdout = golden_path.read_text()

    # Auto-compute kill_after: 90% of T_golden, with app.yaml as floor
    kill_after = max(golden_elapsed * 0.9, app_config.run.kill_after)
    print(f"  [timing] T_golden={golden_elapsed:.1f}s, kill_after={kill_after:.1f}s (90% of golden or app.yaml floor)")

    # Step 3: Build checkpointed
    if _step_done(work_dir, "checkpointed_build"):
        print(f"  [resume] reusing checkpointed build")
        result.checkpointed_build_success = True
    else:
        ckpt_cmd = app_config.ckpt_build.cmd if app_config.ckpt_build else app_config.build.cmd
        success, output = _build_app(checkpointed_dir, ckpt_build, ckpt_cmd)
        result.checkpointed_build_success = success
        if not success:
            result.error_message = f"Checkpointed build failed: {output[-500:]}"
            result.elapsed_seconds = time.monotonic() - start
            return result
        _mark_step(work_dir, "checkpointed_build")

    # Step 4: Verify vanilla has no recovery (time-based)
    if _step_done(work_dir, "no_recovery"):
        print(f"  [resume] reusing no-recovery result")
        result.vanilla_no_recovery_verified = _read_step(work_dir, "no_recovery") == "True"
    else:
        passed, t_vanilla = verify_no_recovery(
            vanilla_dir=van_build,
            app_config=app_config,
            golden_elapsed=golden_elapsed,
            kill_after=kill_after,
            work_dir=work_dir,
        )
        result.vanilla_no_recovery_verified = passed
        _mark_step(work_dir, "no_recovery", str(passed))

    # Step 5: Verify checkpointed has recovery (time-based)
    recovery_stdout_path = work_dir / "recovery_stdout.txt"
    if _step_done(work_dir, "recovery"):
        print(f"  [resume] reusing recovery result")
        result.checkpointed_recovery_verified = _read_step(work_dir, "recovery") == "True"
        recovery_stdout = recovery_stdout_path.read_text() if recovery_stdout_path.is_file() else ""
    else:
        recovered, recovery_run, t_ckpt = verify_recovery(
            checkpointed_dir=ckpt_build,
            app_config=app_config,
            golden_elapsed=golden_elapsed,
            kill_after=kill_after,
            work_dir=work_dir,
        )
        result.checkpointed_recovery_verified = recovered
        recovery_stdout = recovery_run.stdout if recovery_run else ""
        # Cache step 5
        _mark_step(work_dir, "recovery", str(recovered))
        if recovery_stdout:
            recovery_stdout_path.write_text(recovery_stdout)
        # Save timing
        timing = json.loads(timing_path.read_text()) if timing_path.is_file() else {}
        timing["T_ckpt"] = t_ckpt
        timing["kill_after_used"] = kill_after
        timing_path.write_text(json.dumps(timing))

    # Step 6: Compare checkpointed output vs golden
    if result.checkpointed_recovery_verified:
        result.output_match = _compare_outputs(
            golden_stdout=golden_stdout,
            test_stdout=recovery_stdout,
            method=app_config.comparison.method,
            tolerance=app_config.comparison.tolerance,
            ignore_patterns=app_config.comparison.ignore_patterns,
            keep_patterns=app_config.comparison.keep_patterns,
        )

    result.elapsed_seconds = time.monotonic() - start
    return result
