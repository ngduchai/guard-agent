"""
tool_evaluator.py – Evaluate checkpoint tools (baseline, guard-agent) on benchmark apps.

Provides:
  - ToolAdapter protocol   – interface for plugging in checkpoint tools
  - evaluate_tool()        – run a tool on vanilla source, then validate the result
  - NoopAdapter            – passthrough adapter for testing
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Protocol, runtime_checkable

from guard_agent.schemas import AppConfig, ToolEvaluationResult

from .reference_validator import (
    _build_app,
    _compare_outputs,
    _run_app,
    verify_recovery,
)


# ---------------------------------------------------------------------------
# Tool adapter protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class ToolAdapter(Protocol):
    """Interface for checkpoint transformation tools.

    Implementations receive a vanilla source directory and must produce
    a checkpointed version in the output directory.
    """

    @property
    def name(self) -> str:
        """Short identifier for the tool (e.g. ``guard-agent``, ``baseline``)."""
        ...

    def transform(self, vanilla_dir: Path, output_dir: Path, app_config: AppConfig) -> bool:
        """Apply the tool to vanilla source, writing checkpointed code to *output_dir*.

        Returns ``True`` if the transformation succeeded, ``False`` otherwise.
        """
        ...


# ---------------------------------------------------------------------------
# Built-in adapters
# ---------------------------------------------------------------------------

class NoopAdapter:
    """Passthrough adapter that copies vanilla source unchanged (for testing)."""

    @property
    def name(self) -> str:
        return "noop"

    def transform(self, vanilla_dir: Path, output_dir: Path, app_config: AppConfig) -> bool:
        if output_dir.exists():
            shutil.rmtree(output_dir)
        shutil.copytree(vanilla_dir, output_dir)
        return True


class PrebuiltAdapter:
    """Adapter that uses a pre-existing checkpointed directory (for reference comparison)."""

    def __init__(self, checkpointed_dir: Path, label: str = "prebuilt") -> None:
        self._dir = checkpointed_dir
        self._label = label

    @property
    def name(self) -> str:
        return self._label

    def transform(self, vanilla_dir: Path, output_dir: Path, app_config: AppConfig) -> bool:
        if not self._dir.is_dir():
            return False
        if output_dir.exists():
            shutil.rmtree(output_dir)
        shutil.copytree(self._dir, output_dir)
        return True


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate_tool(
    tool: ToolAdapter,
    vanilla_dir: Path,
    app_config: AppConfig,
    golden_stdout: str,
    work_dir: Path,
) -> ToolEvaluationResult:
    """Run a tool on vanilla source, build result, inject failure, compare output.

    Steps:
    1. Run tool.transform() on vanilla → produces checkpointed code
    2. Build the tool's checkpointed code
    3. Run with failure injection → verify recovery
    4. Compare output against golden stdout
    5. Collect metrics (build time, transform time, etc.)
    """
    start = time.monotonic()
    result = ToolEvaluationResult(
        app_name=app_config.name,
        tool_name=tool.name,
    )

    # Step 1: Transform
    tool_output = work_dir / f"tool_{tool.name}"
    transform_start = time.monotonic()
    try:
        transform_ok = tool.transform(vanilla_dir, tool_output, app_config)
    except Exception as e:
        result.error_message = f"Tool transform failed: {e}"
        result.elapsed_seconds = time.monotonic() - start
        return result

    transform_time = time.monotonic() - transform_start
    result.tool_output_dir = str(tool_output)

    if not transform_ok:
        result.error_message = "Tool transform returned False"
        result.elapsed_seconds = time.monotonic() - start
        return result

    # Step 2: Build
    build_dir = work_dir / f"build_{tool.name}"
    success, output = _build_app(tool_output, build_dir, app_config.build.cmd)
    result.build_success = success
    if not success:
        result.error_message = f"Build failed after tool transform: {output[-500:]}"
        result.elapsed_seconds = time.monotonic() - start
        return result

    # Step 3: Verify recovery
    recovered, recovery_run = verify_recovery(
        checkpointed_dir=build_dir,
        app_config=app_config,
        work_dir=work_dir,
    )
    result.recovery_verified = recovered

    # Step 4: Compare output
    if recovered:
        result.output_match = _compare_outputs(
            golden_stdout=golden_stdout,
            test_stdout=recovery_run.stdout,
            method=app_config.comparison.method,
            tolerance=app_config.comparison.tolerance,
        )

    # Step 5: Metrics
    result.metrics = {
        "transform_time_s": transform_time,
        "total_time_s": time.monotonic() - start,
    }

    result.elapsed_seconds = time.monotonic() - start
    return result
