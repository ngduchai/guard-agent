"""
reference_validator.py – Validate the reference pair (vanilla + checkpointed).

Verifies three properties:
1. Vanilla has NO recovery: after failure injection, it cannot produce correct output
2. Checkpointed HAS recovery: after failure injection, it recovers and completes
3. Checkpointed output matches error-free vanilla output (golden output)

This module reuses ``runner.py`` for build/run and ``comparator.py`` for comparison.
"""

from __future__ import annotations

import shutil
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

def _build_app(source_dir: Path, build_dir: Path, build_cmd: str) -> tuple[bool, str]:
    """Build an application. Returns (success, output)."""
    build_dir.mkdir(parents=True, exist_ok=True)

    # Copy source to build directory if needed
    if source_dir != build_dir:
        if build_dir.exists():
            shutil.rmtree(build_dir)
        shutil.copytree(source_dir, build_dir)

    try:
        result = subprocess.run(
            build_cmd,
            shell=True,
            cwd=str(build_dir),
            capture_output=True,
            text=True,
            timeout=300,
        )
        output = result.stdout + "\n" + result.stderr
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "Build timed out after 300 seconds"
    except Exception as e:
        return False, f"Build failed: {e}"


def _run_app(
    build_dir: Path,
    run_cmd: str,
    timeout: int = 120,
    mpi_ranks: int = 4,
) -> RunResult:
    """Run an MPI application and capture output."""
    cmd = run_cmd.replace("{mpi_ranks}", str(mpi_ranks))

    try:
        start = time.monotonic()
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=str(build_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = time.monotonic() - start
        return RunResult(
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            elapsed_s=elapsed,
            output_dir=build_dir,
        )
    except subprocess.TimeoutExpired:
        return RunResult(
            exit_code=-1,
            stdout="",
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
) -> RunResult:
    """Start an MPI app, kill it after ``kill_after`` seconds, then restart."""
    cmd = run_cmd.replace("{mpi_ranks}", str(mpi_ranks))

    # Phase 1: Start and kill
    try:
        start = time.monotonic()
        proc = subprocess.Popen(
            cmd,
            shell=True,
            cwd=str(build_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(kill_after)
        proc.kill()
        proc.wait(timeout=10)
    except Exception:
        pass

    # Phase 2: Restart (same command)
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=str(build_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = time.monotonic() - start
        return RunResult(
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            elapsed_s=elapsed,
            injected=True,
            num_attempts=2,
            output_dir=build_dir,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - start
        return RunResult(
            exit_code=-1,
            stdout="",
            stderr=f"Restart timed out after {timeout}s",
            elapsed_s=elapsed,
            injected=True,
            num_attempts=2,
            output_dir=build_dir,
        )


def _compare_outputs(
    golden_stdout: str,
    test_stdout: str,
    method: str = "text",
    tolerance: float = 1e-6,
    golden_file: str | None = None,
    test_file: str | None = None,
) -> ComparisonResult:
    """Compare golden output against test output."""
    if golden_file and test_file:
        comparator = make_comparator(method, atol=tolerance, rtol=tolerance)
        result = comparator.compare(Path(golden_file), Path(test_file))
        return ComparisonResult(
            method=result.method,
            passed=result.passed,
            details=result.message,
            score=result.score,
        )

    # Stdout comparison
    if method == "text":
        passed = golden_stdout.strip() == test_stdout.strip()
        return ComparisonResult(
            method="text",
            passed=passed,
            details="" if passed else "Stdout differs from golden output",
        )

    if method == "numeric":
        # Extract numbers and compare with tolerance
        import re
        golden_nums = [float(x) for x in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", golden_stdout)]
        test_nums = [float(x) for x in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", test_stdout)]
        if len(golden_nums) != len(test_nums):
            return ComparisonResult(
                method="numeric",
                passed=False,
                details=f"Different number of numeric values: {len(golden_nums)} vs {len(test_nums)}",
            )
        max_diff = 0.0
        for g, t in zip(golden_nums, test_nums):
            diff = abs(g - t)
            if g != 0:
                diff = diff / abs(g)
            max_diff = max(max_diff, diff)
        passed = max_diff <= tolerance
        return ComparisonResult(
            method="numeric",
            passed=passed,
            details=f"Max relative diff: {max_diff:.2e}",
            score=1.0 - max_diff if passed else max_diff,
        )

    # Fallback: hash comparison of stdout
    import hashlib
    h1 = hashlib.sha256(golden_stdout.encode()).hexdigest()
    h2 = hashlib.sha256(test_stdout.encode()).hexdigest()
    passed = h1 == h2
    return ComparisonResult(
        method="hash",
        passed=passed,
        details="" if passed else f"Hash mismatch: {h1[:16]}... vs {h2[:16]}...",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def verify_no_recovery(
    vanilla_dir: Path,
    app_config: AppConfig,
    golden_stdout: str,
    work_dir: Path,
) -> bool:
    """Verify that a vanilla app CANNOT recover from failure.

    Returns True if the vanilla app correctly fails to recover (expected),
    False if it unexpectedly produces correct output after failure.
    """
    build_dir = work_dir / "vanilla_kill"
    result = _run_with_kill(
        build_dir=build_dir if build_dir.exists() else vanilla_dir,
        run_cmd=app_config.run.cmd,
        kill_after=3.0,
        timeout=app_config.run.timeout,
        mpi_ranks=app_config.mpi_ranks,
    )

    if not result.succeeded:
        return True  # App failed → no recovery, as expected

    # App succeeded after restart; check if output matches golden
    comparison = _compare_outputs(
        golden_stdout=golden_stdout,
        test_stdout=result.stdout,
        method=app_config.comparison.method,
        tolerance=app_config.comparison.tolerance,
    )
    # If output does NOT match golden, vanilla has no recovery (expected)
    return not comparison.passed


def verify_recovery(
    checkpointed_dir: Path,
    app_config: AppConfig,
    work_dir: Path,
) -> tuple[bool, RunResult]:
    """Verify that a checkpointed app CAN recover from failure.

    Returns (recovered: bool, run_result: RunResult).
    """
    build_dir = work_dir / "checkpointed_kill"
    result = _run_with_kill(
        build_dir=build_dir if build_dir.exists() else checkpointed_dir,
        run_cmd=app_config.run.cmd,
        kill_after=5.0,
        timeout=app_config.run.timeout,
        mpi_ranks=app_config.mpi_ranks,
    )
    return result.succeeded, result


def _step_done(work_dir: Path, step: str) -> bool:
    """Check if a validation step was completed in a previous run."""
    marker = work_dir / ".steps" / step
    return marker.is_file()


def _mark_step(work_dir: Path, step: str) -> None:
    """Mark a validation step as completed."""
    marker = work_dir / ".steps" / step
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(time.strftime("%Y-%m-%dT%H:%M:%S"))


def _clear_steps(work_dir: Path) -> None:
    """Remove all step markers (for fresh re-validation)."""
    steps_dir = work_dir / ".steps"
    if steps_dir.is_dir():
        shutil.rmtree(steps_dir)


def validate_reference(
    vanilla_dir: Path,
    checkpointed_dir: Path,
    app_config: AppConfig,
    work_dir: Path | None = None,
    fresh: bool = False,
) -> ReferenceResult:
    """Run the full reference validation pipeline for one app.

    Steps are individually cached in ``work_dir/.steps/`` so that a
    partially-completed validation resumes from where it left off.
    Pass ``fresh=True`` to discard cached steps and re-validate from scratch.

    Steps:
    1. Build vanilla
    2. Run vanilla (error-free) → golden output
    3. Build checkpointed
    4. Verify vanilla has no recovery
    5. Verify checkpointed has recovery
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

    # Step 1: Build vanilla (skip if build dir exists from a prior run)
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

    # Step 2: Run vanilla (error-free) → golden output
    if _step_done(work_dir, "golden_run") and golden_path.is_file():
        print(f"  [resume] reusing golden output")
        result.golden_run_success = True
        result.golden_output_path = str(golden_path)
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
        result.golden_output_path = str(golden_path)
        _mark_step(work_dir, "golden_run")

    golden_stdout = golden_path.read_text()

    # Step 3: Build checkpointed
    if _step_done(work_dir, "checkpointed_build"):
        print(f"  [resume] reusing checkpointed build")
        result.checkpointed_build_success = True
    else:
        success, output = _build_app(checkpointed_dir, ckpt_build, app_config.build.cmd)
        result.checkpointed_build_success = success
        if not success:
            result.error_message = f"Checkpointed build failed: {output[-500:]}"
            result.elapsed_seconds = time.monotonic() - start
            return result
        _mark_step(work_dir, "checkpointed_build")

    # Step 4: Verify vanilla has no recovery
    if _step_done(work_dir, "no_recovery"):
        print(f"  [resume] reusing no-recovery result")
        result.vanilla_no_recovery_verified = True
    else:
        result.vanilla_no_recovery_verified = verify_no_recovery(
            vanilla_dir=van_build,
            app_config=app_config,
            golden_stdout=golden_stdout,
            work_dir=work_dir,
        )
        if result.vanilla_no_recovery_verified:
            _mark_step(work_dir, "no_recovery")

    # Step 5: Verify checkpointed has recovery
    recovered, recovery_run = verify_recovery(
        checkpointed_dir=ckpt_build,
        app_config=app_config,
        work_dir=work_dir,
    )
    result.checkpointed_recovery_verified = recovered

    # Step 6: Compare checkpointed output vs golden
    if recovered:
        result.output_match = _compare_outputs(
            golden_stdout=golden_stdout,
            test_stdout=recovery_run.stdout,
            method=app_config.comparison.method,
            tolerance=app_config.comparison.tolerance,
        )

    result.elapsed_seconds = time.monotonic() - start
    return result
