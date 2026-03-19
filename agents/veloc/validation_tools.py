"""
Validation tool for the VeloC agent.

Wraps the local resilience validation script to compare baseline and
resilient application outputs after failure injection.

The function is a plain Python callable — no SDK decorator is required.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from agents.veloc.config import get_project_root


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve(path: str) -> str:
    """Resolve *path* to an absolute path under the project root."""
    root = os.path.abspath(get_project_root())
    abs_path = os.path.normpath(
        os.path.abspath(path if os.path.isabs(path) else os.path.join(root, path))
    )
    if not abs_path.startswith(root):
        raise PermissionError(f"Path is outside project root: {path}")
    return abs_path


def _read_tail(path: Path, max_bytes: int = 4096) -> str:
    """Return up to *max_bytes* from the end of *path* (best-effort)."""
    try:
        size = path.stat().st_size
        with path.open("rb") as f:
            if size > max_bytes:
                f.seek(-max_bytes, os.SEEK_END)
            return f.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def _collect_logs(output_root: Path) -> Dict[str, Any]:
    """Collect stdout/stderr tails from baseline and resilient run directories."""
    logs: Dict[str, Any] = {}
    for subdir, names in [
        (output_root / "baseline", ["stdout_baseline.txt", "stderr_baseline.txt"]),
        (output_root / "resilient", ["stdout_success.txt", "stderr_success.txt"]),
    ]:
        for name in names:
            p = subdir / name
            if p.exists():
                logs[name] = {"path": str(p), "tail": _read_tail(p)}

    resilient_dir = output_root / "resilient"
    if resilient_dir.exists():
        for attempt_dir in sorted(resilient_dir.glob("attempt_*")):
            if attempt_dir.is_dir():
                for name in ("stdout.txt", "stderr.txt"):
                    p = attempt_dir / name
                    if p.exists():
                        logs[f"{attempt_dir.name}_{name}"] = {"path": str(p), "tail": _read_tail(p)}
    return logs


# ---------------------------------------------------------------------------
# Tool function
# ---------------------------------------------------------------------------

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
    """Build and run baseline and resilient applications, then compare outputs.

    Wraps ``validation.run_resilience_validation.main``.  All paths may be
    absolute or relative to ``GUARD_AGENT_PROJECT_ROOT``.

    Returns a dict with ``status`` ('success' or 'error'), ``exit_code``,
    ``output_dir``, and ``logs`` (stdout/stderr tails from each run).
    """
    from validation import run_resilience_validation

    output_root = Path(_resolve(output_dir))

    try:
        argv: List[str] = [
            "--baseline-source-dir", _resolve(baseline_source_dir),
            "--baseline-build-dir",  _resolve(baseline_build_dir),
            "--baseline-executable-name", baseline_executable_name,
            "--baseline-args", baseline_args,
            "--resilient-source-dir", _resolve(resilient_source_dir),
            "--resilient-build-dir",  _resolve(resilient_build_dir),
            "--resilient-executable-name", resilient_executable_name,
            "--resilient-args", resilient_args,
            "--num-procs", str(num_procs),
            "--output-dir", str(output_root),
            "--max-attempts", str(max_attempts),
            "--injection-delay", str(injection_delay),
            "--output-file-name", output_file_name,
            "--comparison-method", comparison_method,
            "--ssim-threshold", str(ssim_threshold),
            "--hdf5-dataset", hdf5_dataset,
            "--veloc-config-name", veloc_config_name,
        ]
        if install_resilient:
            argv.append("--install-resilient")

        exit_code = run_resilience_validation.main(argv)
        logs = _collect_logs(output_root)

        if exit_code == 0:
            return {
                "status": "success",
                "exit_code": exit_code,
                "output_dir": str(output_root),
                "logs": logs,
            }
        return {
            "status": "error",
            "exit_code": exit_code,
            "message": "Validation returned non-zero exit code.",
            "output_dir": str(output_root),
            "logs": logs,
        }
    except Exception as exc:
        return {
            "status": "error",
            "exit_code": None,
            "message": str(exc),
            "output_dir": str(output_root),
            "logs": _collect_logs(output_root),
        }
