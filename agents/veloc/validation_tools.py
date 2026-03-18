from __future__ import annotations

"""
Validation tools exposing the local resilience validation script to the VeloC agent.

These tools run on the user's machine (same environment as the agent runner) and
invoke the Python validation helpers under the top-level `validation` package to
compare baseline and resilient application outputs.
"""

import os
from pathlib import Path
from typing import Any, Dict, List

from agents.veloc._sdk_loader import function_tool
from agents.veloc.config import get_project_root


def _resolve_path_relative_to_root(path: str) -> str:
    """Resolve a path to an absolute path under the project root, rejecting escapes."""
    root = os.path.abspath(get_project_root())
    if os.path.isabs(path):
        abs_path = os.path.abspath(path)
    else:
        abs_path = os.path.abspath(os.path.join(root, path))
    abs_path = os.path.normpath(abs_path)
    if not abs_path.startswith(root):
        raise PermissionError(f"Path is outside project root: {path}")
    return abs_path


def _read_tail(path: Path, max_bytes: int = 4096) -> str:
    """Best-effort: return up to max_bytes from the end of the file."""
    try:
        size = path.stat().st_size
        with path.open("rb") as f:
            if size > max_bytes:
                f.seek(-max_bytes, os.SEEK_END)
            data = f.read()
        return data.decode("utf-8", errors="replace")
    except OSError:
        return ""


def _collect_error_logs(output_root: Path) -> Dict[str, Any]:
    """Collect known stdout/stderr logs from baseline/resilient runs if present."""
    logs: Dict[str, Any] = {}

    baseline_dir = output_root / "baseline"
    resilient_dir = output_root / "resilient"

    # Baseline logs
    for name in ("stdout_baseline.txt", "stderr_baseline.txt"):
        p = baseline_dir / name
        if p.exists():
            logs[f"baseline_{name}"] = {
                "path": str(p),
                "tail": _read_tail(p),
            }

    # Resilient final logs if run_with_retries succeeded at least once
    for name in ("stdout_success.txt", "stderr_success.txt"):
        p = resilient_dir / name
        if p.exists():
            logs[f"resilient_{name}"] = {
                "path": str(p),
                "tail": _read_tail(p),
            }

    # Per-attempt logs (attempt_*/stdout.txt, stderr.txt)
    if resilient_dir.exists():
        for attempt_dir in sorted(resilient_dir.glob("attempt_*")):
            if not attempt_dir.is_dir():
                continue
            for name in ("stdout.txt", "stderr.txt"):
                p = attempt_dir / name
                if p.exists():
                    key = f"{attempt_dir.name}_{name}"
                    logs[key] = {
                        "path": str(p),
                        "tail": _read_tail(p),
                    }

    return logs


def _cleanup_intermediate_outputs(output_root: Path) -> None:
    """
    Remove intermediate per-attempt directories produced by resilient retries.
    Leaves baseline/resilient summary logs and final output artifacts in place.
    """
    resilient_dir = output_root / "resilient"
    if not resilient_dir.exists():
        return
    for attempt_dir in resilient_dir.glob("attempt_*"):
        try:
            if attempt_dir.is_dir():
                import shutil

                shutil.rmtree(attempt_dir, ignore_errors=True)
        except OSError:
            pass


@function_tool
def validate_resilient_output(
    baseline_source_dir: str,
    baseline_build_dir: str,
    baseline_executable_name: str,
    resilient_source_dir: str,
    resilient_build_dir: str,
    resilient_executable_name: str,
    output_dir: str,
    baseline_args: str = "",
    resilient_args: str = "",
    num_procs: int = 4,
    max_attempts: int = 10,
    injection_delay: float = 5.0,
    output_file_name: str = "recon.h5",
    comparison_method: str = "ssim",
    ssim_threshold: float = 0.9999,
    hdf5_dataset: str = "data",
    install_resilient: bool = False,
    veloc_config_name: str = "veloc.cfg",
) -> Dict[str, Any]:
    """Run baseline and resilient applications and validate that outputs match.

    This is a thin wrapper around `validation.run_resilience_validation.main`.
    All paths may be absolute or relative to the GUARD_AGENT_PROJECT_ROOT.

    On any build or execution error, this tool returns status 'error' and
    includes the paths and tail contents of any stdout/stderr logs produced
    by the validation scripts.
    """
    from validation import run_resilience_validation

    output_root = Path(_resolve_path_relative_to_root(output_dir))

    try:
        baseline_source = _resolve_path_relative_to_root(baseline_source_dir)
        baseline_build = _resolve_path_relative_to_root(baseline_build_dir)
        resilient_source = _resolve_path_relative_to_root(resilient_source_dir)
        resilient_build = _resolve_path_relative_to_root(resilient_build_dir)

        argv: List[str] = [
            "--baseline-source-dir",
            baseline_source,
            "--baseline-build-dir",
            baseline_build,
            "--baseline-executable-name",
            baseline_executable_name,
            "--baseline-args",
            baseline_args,
            "--resilient-source-dir",
            resilient_source,
            "--resilient-build-dir",
            resilient_build,
            "--resilient-executable-name",
            resilient_executable_name,
            "--resilient-args",
            resilient_args,
            "--num-procs",
            str(num_procs),
            "--output-dir",
            str(output_root),
            "--max-attempts",
            str(max_attempts),
            "--injection-delay",
            str(injection_delay),
            "--output-file-name",
            output_file_name,
            "--comparison-method",
            comparison_method,
            "--ssim-threshold",
            str(ssim_threshold),
            "--hdf5-dataset",
            hdf5_dataset,
            "--veloc-config-name",
            veloc_config_name,
        ]

        if install_resilient:
            argv.append("--install-resilient")

        exit_code = run_resilience_validation.main(argv)
        logs = _collect_error_logs(output_root)

        if exit_code == 0:
            _cleanup_intermediate_outputs(output_root)
            return {
                "status": "success",
                "exit_code": exit_code,
                "output_dir": str(output_root),
                "baseline_source_dir": baseline_source,
                "baseline_build_dir": baseline_build,
                "resilient_source_dir": resilient_source,
                "resilient_build_dir": resilient_build,
                "output_file_name": output_file_name,
                "comparison_method": comparison_method,
                "logs": logs,
            }

        return {
            "status": "error",
            "exit_code": exit_code,
            "message": "Validation script returned non-zero exit code.",
            "output_dir": str(output_root),
            "logs": logs,
        }
    except Exception as exc:
        logs = _collect_error_logs(output_root)
        return {
            "status": "error",
            "exit_code": None,
            "message": str(exc),
            "output_dir": str(output_root),
            "logs": logs,
        }

