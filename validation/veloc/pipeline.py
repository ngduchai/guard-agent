"""
pipeline.py – End-to-end benchmark validation pipeline.

Orchestrates:
  1. Reference phase  – validate vanilla/checkpointed pairs
  2. Tool evaluation  – run tools (baseline, guard-agent) on vanilla, validate results
  3. Reporting        – generate per-app and cross-app summary reports

Usage::

    from validation.veloc.pipeline import BenchmarkPipeline
    from validation.veloc.app_registry import AppRegistry

    registry = AppRegistry(project_root)
    pipeline = BenchmarkPipeline(registry, project_root, output_dir)
    pipeline.run_reference_phase()
    pipeline.run_tool_phase([guard_agent_adapter])
    pipeline.generate_report()
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from guard_agent.schemas import AppConfig, PipelineResult, ReferenceResult

from .app_registry import AppRegistry
from .reference_validator import validate_reference
from .tool_evaluator import ToolAdapter, evaluate_tool


# ---------------------------------------------------------------------------
# Pipeline state persistence
# ---------------------------------------------------------------------------

def _load_state(state_path: Path) -> dict:
    if state_path.is_file():
        with open(state_path) as f:
            return json.load(f)
    return {}


def _save_state(state_path: Path, state: dict) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2, default=str)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class BenchmarkPipeline:
    """Orchestrates the full benchmark validation pipeline."""

    def __init__(
        self,
        registry: AppRegistry,
        project_root: Path,
        output_dir: Path,
    ) -> None:
        self._registry = registry
        self._root = project_root
        self._output = output_dir
        self._output.mkdir(parents=True, exist_ok=True)
        self._state_path = output_dir / "pipeline_state.json"
        self._state = _load_state(self._state_path)
        self._results: dict[str, PipelineResult] = {}

    # -----------------------------------------------------------------------
    # Reference phase
    # -----------------------------------------------------------------------

    def run_reference_phase(
        self,
        apps: list[str] | None = None,
        skip_completed: bool = True,
    ) -> dict[str, ReferenceResult]:
        """Run reference validation for all (or selected) apps.

        Parameters
        ----------
        apps : list of app names, or None for all discovered apps.
        skip_completed : if True, skip apps already validated in a prior run.

        Returns
        -------
        dict mapping app name → ReferenceResult.
        """
        targets = self._resolve_targets(apps)
        results: dict[str, ReferenceResult] = {}

        for cfg in targets:
            if skip_completed and self._is_phase_done("reference", cfg.name):
                print(f"[pipeline] skipping {cfg.name} (already validated)")
                continue

            print(f"\n{'='*60}")
            print(f"[pipeline] Reference validation: {cfg.name}")
            print(f"{'='*60}")

            van = self._registry.vanilla_path(cfg.name)
            ckpt = self._registry.checkpointed_path(cfg.name)

            if not van.is_dir():
                print(f"[pipeline] WARNING: vanilla dir missing for {cfg.name}, skipping")
                continue
            if not ckpt.is_dir():
                print(f"[pipeline] WARNING: checkpointed dir missing for {cfg.name}, skipping")
                continue

            work = self._output / "work" / cfg.name
            ref_result = validate_reference(van, ckpt, cfg, work)
            results[cfg.name] = ref_result

            # Update pipeline result
            if cfg.name not in self._results:
                self._results[cfg.name] = PipelineResult(app=cfg, reference=ref_result)
            else:
                self._results[cfg.name].reference = ref_result

            # Persist state
            self._mark_phase_done("reference", cfg.name, ref_result.model_dump())
            self._save()

            # Summary
            self._print_reference_summary(cfg.name, ref_result)

        return results

    # -----------------------------------------------------------------------
    # Tool evaluation phase
    # -----------------------------------------------------------------------

    def run_tool_phase(
        self,
        tools: list[ToolAdapter],
        apps: list[str] | None = None,
    ) -> dict[str, list]:
        """Run tool evaluation for all (or selected) apps.

        Each tool is applied to each app's vanilla source, then the result
        is built, tested with failure injection, and compared against golden output.
        """
        targets = self._resolve_targets(apps)
        all_results: dict[str, list] = {}

        for cfg in targets:
            ref_data = self._state.get("reference", {}).get(cfg.name, {})
            golden_path = ref_data.get("golden_output_path")
            if not golden_path or not Path(golden_path).is_file():
                print(f"[pipeline] WARNING: no golden output for {cfg.name}, run reference first")
                continue

            golden_stdout = Path(golden_path).read_text()
            van = self._registry.vanilla_path(cfg.name)
            tool_results = []

            for tool in tools:
                print(f"\n[pipeline] Tool '{tool.name}' on {cfg.name}")
                work = self._output / "work" / cfg.name
                result = evaluate_tool(tool, van, cfg, golden_stdout, work)
                tool_results.append(result)

                if cfg.name in self._results:
                    self._results[cfg.name].tool_evaluations.append(result)

            all_results[cfg.name] = tool_results

        return all_results

    # -----------------------------------------------------------------------
    # Reporting
    # -----------------------------------------------------------------------

    def generate_report(self) -> Path:
        """Generate a summary report for all pipeline results."""
        report_path = self._output / "benchmark_report.md"
        lines = [
            "# Benchmark Validation Report\n",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n",
            f"Apps validated: {len(self._results)}\n",
            "",
            "## Reference Phase Results\n",
            "| App | Category | Vanilla Build | Golden Run | No Recovery | Ckpt Build | Recovery | Output Match |",
            "|-----|----------|---------------|------------|-------------|------------|----------|--------------|",
        ]

        for name, pr in sorted(self._results.items()):
            r = pr.reference
            match_str = "N/A"
            if r.output_match:
                match_str = "PASS" if r.output_match.passed else "FAIL"
            lines.append(
                f"| {name} | {pr.app.category} "
                f"| {'OK' if r.vanilla_build_success else 'FAIL'} "
                f"| {'OK' if r.golden_run_success else 'FAIL'} "
                f"| {'OK' if r.vanilla_no_recovery_verified else 'FAIL'} "
                f"| {'OK' if r.checkpointed_build_success else 'FAIL'} "
                f"| {'OK' if r.checkpointed_recovery_verified else 'FAIL'} "
                f"| {match_str} |"
            )

        # Tool evaluation section
        any_tools = any(pr.tool_evaluations for pr in self._results.values())
        if any_tools:
            lines.extend([
                "",
                "## Tool Evaluation Results\n",
                "| App | Tool | Build | Recovery | Output Match | Transform Time |",
                "|-----|------|-------|----------|--------------|----------------|",
            ])
            for name, pr in sorted(self._results.items()):
                for te in pr.tool_evaluations:
                    match_str = "N/A"
                    if te.output_match:
                        match_str = "PASS" if te.output_match.passed else "FAIL"
                    t_time = te.metrics.get("transform_time_s", "N/A")
                    if isinstance(t_time, float):
                        t_time = f"{t_time:.1f}s"
                    lines.append(
                        f"| {name} | {te.tool_name} "
                        f"| {'OK' if te.build_success else 'FAIL'} "
                        f"| {'OK' if te.recovery_verified else 'FAIL'} "
                        f"| {match_str} "
                        f"| {t_time} |"
                    )

        report_path.write_text("\n".join(lines) + "\n")
        print(f"\n[pipeline] Report written to {report_path}")
        return report_path

    # -----------------------------------------------------------------------
    # Internals
    # -----------------------------------------------------------------------

    def _resolve_targets(self, apps: list[str] | None) -> list[AppConfig]:
        if apps is None:
            return list(self._registry)
        return [self._registry.get(a) for a in apps if self._registry.get(a)]

    def _is_phase_done(self, phase: str, app_name: str) -> bool:
        return app_name in self._state.get(phase, {})

    def _mark_phase_done(self, phase: str, app_name: str, data: dict) -> None:
        self._state.setdefault(phase, {})[app_name] = data

    def _save(self) -> None:
        _save_state(self._state_path, self._state)

    def _print_reference_summary(self, name: str, r: ReferenceResult) -> None:
        checks = [
            ("Vanilla build", r.vanilla_build_success),
            ("Golden run", r.golden_run_success),
            ("No recovery (vanilla)", r.vanilla_no_recovery_verified),
            ("Ckpt build", r.checkpointed_build_success),
            ("Recovery (ckpt)", r.checkpointed_recovery_verified),
        ]
        if r.output_match:
            checks.append(("Output match", r.output_match.passed))

        print(f"\n[pipeline] {name} reference results:")
        for label, ok in checks:
            status = "PASS" if ok else "FAIL"
            print(f"  {label}: {status}")
        if r.error_message:
            print(f"  Error: {r.error_message[:200]}")
