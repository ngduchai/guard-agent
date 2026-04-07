"""Injection validator — builds, tests, and verifies VeloC checkpoint injection.

Wraps the existing validation framework (validation/veloc/) to:
  1. Build original + resilient code
  2. Run baseline for golden output
  3. Run resilient with simulated failure (kill process mid-run, restart)
  4. Compare outputs
  5. Return detailed pass/fail analysis with suggestions
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from guard_agent.schemas import ComparisonResult, ValidationResult


def validate_injection(
    project_dir: str,
    build_cmd: str,
    run_cmd: str,
    num_procs: int = 2,
    comparison_method: str = "hash",
    output_file: str | None = None,
    timeout: int = 300,
    veloc_cfg_path: str | None = None,
) -> ValidationResult:
    """Validate checkpoint injection by building, running with failure, and comparing.

    Args:
        project_dir: Path to the project directory containing the resilient code.
        build_cmd: Build command (e.g., "cmake --build build").
        run_cmd: Run command (e.g., "mpirun -np 4 ./build/simulation").
        num_procs: Number of MPI processes.
        comparison_method: Output comparison method ("hash", "text", "numeric").
        output_file: Output file to compare (if None, compares stdout).
        timeout: Maximum seconds for each run.
        veloc_cfg_path: Path to veloc.cfg (for cleaning checkpoint dirs).

    Returns:
        ValidationResult with pass/fail and detailed analysis.
    """
    start_time = time.monotonic()
    project = Path(project_dir).resolve()

    # Step 1: Build
    build_result = _run_command(build_cmd, cwd=str(project), timeout=timeout)
    if build_result["returncode"] != 0:
        return ValidationResult(
            passed=False,
            build_success=False,
            error_message=f"Build failed with exit code {build_result['returncode']}",
            error_analysis=_analyze_build_failure(build_result["stderr"]),
            suggestions=_build_failure_suggestions(build_result["stderr"]),
            build_output=build_result["stderr"][:4096],
            elapsed_seconds=time.monotonic() - start_time,
        )

    # Step 2: Clean checkpoint directories
    if veloc_cfg_path:
        _clean_checkpoint_dirs(veloc_cfg_path)

    # Step 3: Baseline run (clean, no failure)
    baseline_result = _run_command(run_cmd, cwd=str(project), timeout=timeout)
    if baseline_result["returncode"] != 0:
        return ValidationResult(
            passed=False,
            build_success=True,
            baseline_run_success=False,
            error_message=f"Baseline run failed with exit code {baseline_result['returncode']}",
            error_analysis=_analyze_run_failure(baseline_result["stderr"]),
            suggestions=_run_failure_suggestions(baseline_result["stderr"]),
            run_output=baseline_result["stderr"][:4096],
            elapsed_seconds=time.monotonic() - start_time,
        )

    baseline_output = baseline_result["stdout"]
    baseline_file_content = None
    if output_file:
        output_path = project / output_file
        if output_path.is_file():
            baseline_file_content = output_path.read_bytes()

    # Step 4: Clean checkpoints, run with simulated failure
    if veloc_cfg_path:
        _clean_checkpoint_dirs(veloc_cfg_path)

    # Run 1: Start and kill after a short time to create checkpoint
    kill_result = _run_with_kill(run_cmd, cwd=str(project), kill_after=5, timeout=timeout)

    # Run 2: Restart from checkpoint
    restart_result = _run_command(run_cmd, cwd=str(project), timeout=timeout)
    if restart_result["returncode"] != 0:
        return ValidationResult(
            passed=False,
            build_success=True,
            baseline_run_success=True,
            resilient_run_success=False,
            failure_injection_success=True,
            restart_success=False,
            error_message=f"Restart run failed with exit code {restart_result['returncode']}",
            error_analysis=_analyze_restart_failure(restart_result["stderr"]),
            suggestions=_restart_failure_suggestions(restart_result["stderr"]),
            run_output=restart_result["stderr"][:4096],
            elapsed_seconds=time.monotonic() - start_time,
        )

    # Step 5: Compare outputs
    resilient_output = restart_result["stdout"]
    resilient_file_content = None
    if output_file:
        output_path = project / output_file
        if output_path.is_file():
            resilient_file_content = output_path.read_bytes()

    comparison = _compare_outputs(
        baseline_output, resilient_output,
        baseline_file_content, resilient_file_content,
        comparison_method,
    )

    return ValidationResult(
        passed=comparison.passed,
        build_success=True,
        baseline_run_success=True,
        resilient_run_success=True,
        failure_injection_success=True,
        restart_success=True,
        comparison=comparison,
        run_output=resilient_output[:4096],
        elapsed_seconds=time.monotonic() - start_time,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run_command(
    cmd: str,
    cwd: str,
    timeout: int = 300,
    env: dict | None = None,
) -> dict:
    """Run a shell command and capture output."""
    run_env = dict(os.environ)
    if env:
        run_env.update(env)

    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=run_env,
        )
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    except subprocess.TimeoutExpired:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout} seconds",
        }
    except Exception as e:
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
        }


def _run_with_kill(
    cmd: str,
    cwd: str,
    kill_after: float = 5.0,
    timeout: int = 300,
) -> dict:
    """Run a command and kill it after kill_after seconds to simulate failure."""
    try:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid,
        )

        try:
            stdout, stderr = proc.communicate(timeout=kill_after)
            return {"returncode": proc.returncode, "stdout": stdout, "stderr": stderr}
        except subprocess.TimeoutExpired:
            # Kill the process group
            import signal
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            proc.wait()
            return {
                "returncode": -9,
                "stdout": "",
                "stderr": f"Process killed after {kill_after}s (simulated failure)",
            }
    except Exception as e:
        return {"returncode": -1, "stdout": "", "stderr": str(e)}


def _clean_checkpoint_dirs(veloc_cfg_path: str) -> None:
    """Parse veloc.cfg and clean scratch/persistent directories."""
    try:
        cfg_path = Path(veloc_cfg_path)
        if not cfg_path.is_file():
            return

        content = cfg_path.read_text()
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("scratch") or line.startswith("persistent"):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    dir_path = Path(parts[1].strip())
                    if dir_path.is_dir():
                        shutil.rmtree(dir_path, ignore_errors=True)
                        dir_path.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def _compare_outputs(
    baseline_stdout: str,
    resilient_stdout: str,
    baseline_file: bytes | None,
    resilient_file: bytes | None,
    method: str,
) -> ComparisonResult:
    """Compare baseline and resilient outputs."""
    if method == "hash":
        if baseline_file is not None and resilient_file is not None:
            baseline_hash = hashlib.sha256(baseline_file).hexdigest()
            resilient_hash = hashlib.sha256(resilient_file).hexdigest()
            passed = baseline_hash == resilient_hash
            return ComparisonResult(
                method="hash",
                passed=passed,
                details=(
                    f"Baseline: {baseline_hash[:16]}... "
                    f"Resilient: {resilient_hash[:16]}..."
                ),
            )
        else:
            # Compare stdout
            passed = baseline_stdout.strip() == resilient_stdout.strip()
            return ComparisonResult(
                method="hash",
                passed=passed,
                details="Compared stdout output" + (
                    "" if passed else "; outputs differ"
                ),
            )

    elif method == "text":
        passed = baseline_stdout.strip() == resilient_stdout.strip()
        if not passed:
            # Show first difference
            b_lines = baseline_stdout.strip().splitlines()
            r_lines = resilient_stdout.strip().splitlines()
            diff_line = None
            for i, (bl, rl) in enumerate(zip(b_lines, r_lines)):
                if bl != rl:
                    diff_line = i + 1
                    break
            if diff_line is None and len(b_lines) != len(r_lines):
                diff_line = min(len(b_lines), len(r_lines)) + 1
            details = f"First difference at line {diff_line}" if diff_line else "Line count differs"
        else:
            details = "Outputs match exactly"
        return ComparisonResult(method="text", passed=passed, details=details)

    elif method == "numeric":
        return _numeric_compare(baseline_stdout, resilient_stdout)

    return ComparisonResult(
        method=method,
        passed=False,
        details=f"Unknown comparison method: {method}",
    )


def _numeric_compare(
    baseline: str,
    resilient: str,
    rtol: float = 1e-5,
    atol: float = 1e-8,
) -> ComparisonResult:
    """Compare numeric outputs with tolerance."""
    import re

    num_re = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")
    b_nums = [float(x) for x in num_re.findall(baseline)]
    r_nums = [float(x) for x in num_re.findall(resilient)]

    if len(b_nums) != len(r_nums):
        return ComparisonResult(
            method="numeric",
            passed=False,
            details=f"Different number of values: {len(b_nums)} vs {len(r_nums)}",
        )

    if not b_nums:
        return ComparisonResult(
            method="numeric",
            passed=True,
            details="No numeric values found in output",
        )

    max_diff = 0.0
    for b, r in zip(b_nums, r_nums):
        diff = abs(b - r)
        threshold = atol + rtol * abs(b)
        if diff > threshold:
            return ComparisonResult(
                method="numeric",
                passed=False,
                details=f"Values differ beyond tolerance: {b} vs {r} (diff={diff})",
            )
        max_diff = max(max_diff, diff)

    return ComparisonResult(
        method="numeric",
        passed=True,
        details=f"All {len(b_nums)} values match within tolerance (max diff={max_diff:.2e})",
        score=1.0 - max_diff,
    )


# ---------------------------------------------------------------------------
# Failure analysis
# ---------------------------------------------------------------------------

def _analyze_build_failure(stderr: str) -> str:
    if "veloc.h" in stderr or "veloc.hpp" in stderr:
        return "VeloC header not found. The VeloC library may not be installed or not in the include path."
    if "veloc-client" in stderr or "veloc::client" in stderr:
        return "VeloC library not found during linking. Check that VeloC is installed and find_package(veloc) is in CMakeLists.txt."
    if "undefined reference" in stderr:
        return f"Linker error — undefined references found. Check that all required libraries are linked."
    return "Build failed. Review the build output for error details."


def _build_failure_suggestions(stderr: str) -> list[str]:
    suggestions = []
    if "veloc" in stderr.lower():
        suggestions.append("Ensure VeloC is installed: check with `veloc-config --version`")
        suggestions.append("Add `find_package(veloc REQUIRED)` to CMakeLists.txt")
        suggestions.append("Add `veloc-client` to target_link_libraries")
    if "undefined reference" in stderr:
        suggestions.append("Check that all VeloC API calls use the correct function signatures")
    return suggestions


def _analyze_run_failure(stderr: str) -> str:
    if "veloc.cfg" in stderr.lower():
        return "VeloC configuration file not found or invalid."
    if "segfault" in stderr.lower() or "segmentation" in stderr.lower():
        return "Segmentation fault during execution. Likely a memory access error in VeloC calls."
    return "Runtime failure. Review stderr output."


def _run_failure_suggestions(stderr: str) -> list[str]:
    suggestions = []
    if "veloc.cfg" in stderr.lower():
        suggestions.append("Ensure veloc.cfg is in the working directory or use --veloc-cfg")
    if "segmentation" in stderr.lower():
        suggestions.append("Check VELOC_Mem_protect calls — verify pointer, count, and sizeof are correct")
    return suggestions


def _analyze_restart_failure(stderr: str) -> str:
    if "checkpoint" in stderr.lower() and "not found" in stderr.lower():
        return "No checkpoint found for restart. The initial run may not have created a checkpoint before being killed."
    return "Restart failed. The checkpoint may be corrupted or incompatible."


def _restart_failure_suggestions(stderr: str) -> list[str]:
    return [
        "Increase the kill_after time to allow at least one checkpoint to complete",
        "Verify VELOC_Checkpoint is called inside the main loop",
        "Check that the checkpoint name matches between checkpoint and restart_test calls",
        "Ensure scratch and persistent directories exist and are writable",
    ]
