"""
reporter.py – Visualization and reporting for the VeloC validation framework.

Generates publication-quality matplotlib figures and a human-readable Markdown
summary report from correctness results and benchmark metrics.

Output directory layout
-----------------------
  <output-dir>/
  ├── correctness/
  │   ├── test_results.json
  │   └── correctness_summary.txt
  ├── benchmarks/
  │   └── raw_metrics.json          (written by metrics_collector)
  ├── plots/
  │   ├── execution_time.png
  │   ├── recovery_time.png
  │   ├── checkpoint_size.png
  │   └── memory_usage.png
  └── summary_report.md

Requires: matplotlib, numpy

Design notes
------------
The plotting engine is *config-agnostic*: it inspects the actual set of
BenchmarkScenario objects to discover which parameters vary (num_procs,
injection_delay, app_args positions, …) and maps them to graph elements:

  • y-axis  → the metric being plotted
  • x-axis  → the most-granular varying parameter (e.g. injection_delay)
  • bar-group (column group across x) → second varying parameter (e.g. workload)
  • subplot panel (row of subplots)   → third varying parameter (e.g. num_procs)

For failure-injection metrics (recovery_time, checkpoint_size, overhead) only
scenarios with inject_failures=True are included.

The number of plots is kept minimal: one figure per metric, with all varying
parameters encoded inside that figure.
"""

from __future__ import annotations

import json
import textwrap
from collections import defaultdict
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
from typing import Any

from .comparator import CompareResult
from .metrics_collector import BenchmarkResults, BenchmarkScenario, RunMetrics


# ---------------------------------------------------------------------------
# Matplotlib import guard
# ---------------------------------------------------------------------------

def _import_matplotlib():
    try:
        import matplotlib
        matplotlib.use("Agg")  # non-interactive backend
        import matplotlib.pyplot as plt
        import numpy as np
        return plt, np
    except ImportError as exc:
        raise ImportError(
            "matplotlib and numpy are required for report generation. "
            "Install with: pip install matplotlib numpy"
        ) from exc


# ---------------------------------------------------------------------------
# Plot style helpers
# ---------------------------------------------------------------------------

_DPI = 150
_STYLE = "seaborn-v0_8-whitegrid"

# Colour palette for bar groups (up to 8 groups)
_GROUP_COLORS = [
    "#2196F3",  # blue
    "#FF5722",  # deep orange
    "#4CAF50",  # green
    "#9C27B0",  # purple
    "#FF9800",  # amber
    "#00BCD4",  # cyan
    "#F44336",  # red
    "#795548",  # brown
]

# Hatch patterns for subplot panels (accessibility)
_PANEL_HATCHES = ["", "//", "xx", "\\\\", ".."]


def _apply_style(plt) -> None:
    try:
        plt.style.use(_STYLE)
    except OSError:
        try:
            plt.style.use("seaborn-whitegrid")
        except OSError:
            pass  # fall back to default


def _save_fig(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=_DPI, bbox_inches="tight")


# ---------------------------------------------------------------------------
# Parameter discovery
# ---------------------------------------------------------------------------

def _discover_varying_params(
    scenarios: list[BenchmarkScenario],
    failure_only: bool = False,
) -> dict[str, list]:
    """Inspect *scenarios* and return a dict of parameters that actually vary.

    Parameters
    ----------
    scenarios:
        The full list of BenchmarkScenario objects.
    failure_only:
        When True, only consider scenarios where inject_failures=True.

    Returns
    -------
    A dict mapping parameter name → sorted list of unique values.
    Only parameters with more than one distinct value are included.
    The dict is ordered by "number of distinct values" descending so that
    the caller can assign the most-varying parameter to the x-axis.
    """
    if failure_only:
        scenarios = [s for s in scenarios if s.inject_failures]
    if not scenarios:
        return {}

    candidates: dict[str, set] = {
        "num_procs": set(),
        "injection_delay": set(),
    }

    # Discover varying app_args positions
    max_args = max(len(s.app_args) for s in scenarios)
    for pos in range(max_args):
        candidates[f"app_args[{pos}]"] = set()

    for s in scenarios:
        candidates["num_procs"].add(s.num_procs)
        candidates["injection_delay"].add(s.injection_delay)
        for pos in range(max_args):
            val = s.app_args[pos] if pos < len(s.app_args) else None
            candidates[f"app_args[{pos}]"].add(val)

    # Keep only parameters that actually vary
    varying = {
        k: sorted(v, key=lambda x: (x is None, x))
        for k, v in candidates.items()
        if len(v) > 1
    }

    # Sort by number of distinct values descending (most granular first)
    varying = dict(
        sorted(varying.items(), key=lambda kv: len(kv[1]), reverse=True)
    )
    return varying


def _scenario_param_value(s: BenchmarkScenario, param: str):
    """Return the value of *param* for scenario *s*."""
    if param == "num_procs":
        return s.num_procs
    if param == "injection_delay":
        return s.injection_delay
    if param.startswith("app_args["):
        pos = int(param[len("app_args["):-1])
        return s.app_args[pos] if pos < len(s.app_args) else None
    return None


def _param_label(param: str) -> str:
    """Human-readable label for a parameter name."""
    if param == "num_procs":
        return "# Processes"
    if param == "injection_delay":
        return "Failure Delay (s)"
    if param.startswith("app_args["):
        pos = int(param[len("app_args["):-1])
        # Common positional meanings for art_simple-style apps
        _pos_names = {
            0: "Input File",
            1: "Center",
            2: "Num Iterations",
            3: "Num Threads",
            4: "Start Angle",
            5: "Num Angles",
        }
        return _pos_names.get(pos, f"app_args[{pos}]")
    return param


def _assign_roles(varying: dict[str, list]) -> tuple[str | None, str | None, str | None]:
    """Assign x-axis, group, and panel roles to the top-3 varying parameters.

    Strategy
    --------
    • x-axis  → parameter with the most distinct values (most granular sweep)
    • group   → parameter with the second-most distinct values
    • panel   → parameter with the third-most distinct values

    Returns (x_param, group_param, panel_param); any may be None if fewer
    than 3 parameters vary.
    """
    keys = list(varying.keys())
    x_param = keys[0] if len(keys) >= 1 else None
    group_param = keys[1] if len(keys) >= 2 else None
    panel_param = keys[2] if len(keys) >= 3 else None
    return x_param, group_param, panel_param


# ---------------------------------------------------------------------------
# Generic grouped-bar plot engine
# ---------------------------------------------------------------------------

def _collect_metric_values(
    runs: list[RunMetrics],
    scenario_name: str,
    metric: str,
    codebase: str | None = None,
) -> list[float]:
    """Return all non-None values of *metric* for the given scenario (and optional codebase)."""
    values = []
    for r in runs:
        if r.scenario_name != scenario_name:
            continue
        if codebase is not None and r.codebase != codebase:
            continue
        val = getattr(r, metric, None)
        if val is not None:
            values.append(float(val))
    return values


def _mean_std(vals: list[float]):
    """Return (mean, std) or (0.0, 0.0) for an empty list."""
    if not vals:
        return 0.0, 0.0
    import statistics as _stats
    mean = sum(vals) / len(vals)
    std = _stats.stdev(vals) if len(vals) > 1 else 0.0
    return mean, std


def _plot_metric_figure(
    results: BenchmarkResults,
    metric: str,
    y_label: str,
    title: str,
    output_path: Path,
    failure_only: bool,
    scale: float = 1.0,
    codebase: str | None = None,
) -> Path:
    """Generic figure generator.

    Discovers varying parameters, assigns them to x-axis / bar-group / panel,
    and draws a grouped-bar chart (one panel per panel-param value, or a single
    panel if fewer than 3 parameters vary).

    Parameters
    ----------
    results:
        Full BenchmarkResults object.
    metric:
        Attribute name on RunMetrics to plot.
    y_label:
        Y-axis label string.
    title:
        Figure suptitle.
    output_path:
        Where to save the PNG.
    failure_only:
        If True, only include scenarios with inject_failures=True.
    scale:
        Multiply raw metric values by this factor (e.g. 1/1024**2 for bytes→MiB).
    codebase:
        If set, filter runs to this codebase ("original" or "resilient").
    """
    plt, np = _import_matplotlib()
    _apply_style(plt)

    # Filter scenarios
    scenarios = results.scenarios
    if failure_only:
        scenarios = [s for s in scenarios if s.inject_failures]
    if not scenarios:
        return output_path  # nothing to plot

    # Discover varying parameters among the filtered scenarios
    varying = _discover_varying_params(scenarios, failure_only=False)
    x_param, group_param, panel_param = _assign_roles(varying)

    if x_param is None:
        # Only one scenario – single bar
        x_vals = [scenarios[0].name]
        group_vals = [None]
        panel_vals = [None]
    else:
        x_vals = varying[x_param]
        group_vals = varying[group_param] if group_param else [None]
        panel_vals = varying[panel_param] if panel_param else [None]

    n_panels = len(panel_vals)
    n_groups = len(group_vals)
    n_x = len(x_vals)

    # Figure layout: one subplot per panel value
    fig_width = max(6, 2.5 * n_x * n_groups + 1.5) * min(n_panels, 3)
    fig_height = 5
    if n_panels > 1:
        ncols = min(n_panels, 3)
        nrows = (n_panels + ncols - 1) // ncols
        fig, axes = plt.subplots(nrows, ncols,
                                 figsize=(fig_width / min(n_panels, 3) * ncols, fig_height * nrows),
                                 sharey=True, squeeze=False)
        axes_flat = axes.flatten()
    else:
        fig, ax_single = plt.subplots(figsize=(max(7, 2.5 * n_x * n_groups + 1.5), fig_height))
        axes_flat = [ax_single]

    width = 0.8 / max(n_groups, 1)
    x_positions = np.arange(n_x)

    for panel_idx, panel_val in enumerate(panel_vals):
        if panel_idx >= len(axes_flat):
            break
        ax = axes_flat[panel_idx]

        for g_idx, group_val in enumerate(group_vals):
            means = []
            stds = []
            for x_val in x_vals:
                # Find matching scenario(s)
                matched = []
                for s in scenarios:
                    if x_param and _scenario_param_value(s, x_param) != x_val:
                        continue
                    if group_param and _scenario_param_value(s, group_param) != group_val:
                        continue
                    if panel_param and _scenario_param_value(s, panel_param) != panel_val:
                        continue
                    matched.append(s)

                vals = []
                for s in matched:
                    raw = _collect_metric_values(results.runs, s.name, metric, codebase)
                    vals.extend([v * scale for v in raw])

                m, sd = _mean_std(vals)
                means.append(m)
                stds.append(sd)

            offset = (g_idx - (n_groups - 1) / 2) * width
            color = _GROUP_COLORS[g_idx % len(_GROUP_COLORS)]
            hatch = _PANEL_HATCHES[panel_idx % len(_PANEL_HATCHES)]

            label = None
            if group_param:
                label = f"{_param_label(group_param)}={group_val}"
            elif panel_param:
                label = f"{_param_label(panel_param)}={panel_val}"

            bars = ax.bar(
                x_positions + offset, means, width,
                yerr=stds, capsize=4,
                color=color, alpha=0.85,
                hatch=hatch,
                label=label,
                error_kw={"elinewidth": 1.2},
            )

        ax.set_xticks(x_positions)
        ax.set_xticklabels(
            [str(v) for v in x_vals],
            rotation=30 if n_x > 4 else 0,
            ha="right" if n_x > 4 else "center",
        )
        if x_param:
            ax.set_xlabel(_param_label(x_param))
        ax.set_ylabel(y_label)

        panel_subtitle = ""
        if panel_param and panel_val is not None:
            panel_subtitle = f"{_param_label(panel_param)} = {panel_val}"
        ax.set_title(panel_subtitle)

        if group_param or (not group_param and not panel_param):
            ax.legend(fontsize="small", loc="best")

    # Hide unused axes
    for idx in range(len(panel_vals), len(axes_flat)):
        axes_flat[idx].set_visible(False)

    # Panel legend (if panel_param is used and there are multiple panels)
    if panel_param and n_panels > 1:
        # Add a figure-level note
        fig.text(
            0.5, 0.01,
            f"Each panel: {_param_label(panel_param)}",
            ha="center", fontsize="small", style="italic",
        )

    fig.suptitle(title, fontsize=13, fontweight="bold", y=1.01 if n_panels > 1 else 1.0)
    fig.tight_layout()

    _save_fig(fig, output_path)
    plt.close(fig)
    return output_path


# ---------------------------------------------------------------------------
# Public plot functions (one per metric)
# ---------------------------------------------------------------------------

def plot_execution_time(results: BenchmarkResults, output_dir: Path) -> Path:
    """Execution time for failure-injection scenarios (resilient codebase only).

    For baseline comparison (no-failure vs failure) a separate grouped-bar
    chart is produced showing both codebases side-by-side.
    """
    plt, np = _import_matplotlib()
    _apply_style(plt)

    # --- Part 1: failure-injection scenarios, resilient codebase ---
    out = output_dir / "plots" / "execution_time.png"
    _plot_metric_figure(
        results=results,
        metric="elapsed_s",
        y_label="Execution Time (s)",
        title="Execution Time under Failure Injection (Resilient)",
        output_path=out,
        failure_only=True,
        scale=1.0,
        codebase="resilient",
    )
    return out


def plot_recovery_time(results: BenchmarkResults, output_dir: Path) -> Path:
    """Recovery time for failure-injection scenarios (resilient only)."""
    out = output_dir / "plots" / "recovery_time.png"
    _plot_metric_figure(
        results=results,
        metric="recovery_time_s",
        y_label="Recovery Time (s)",
        title="Estimated Recovery Time under Failure Injection",
        output_path=out,
        failure_only=True,
        scale=1.0,
        codebase="resilient",
    )
    return out


def plot_checkpoint_size(results: BenchmarkResults, output_dir: Path) -> Path:
    """Checkpoint storage size for failure-injection scenarios (resilient only)."""
    out = output_dir / "plots" / "checkpoint_size.png"
    _plot_metric_figure(
        results=results,
        metric="checkpoint_size_bytes",
        y_label="Checkpoint Size (MiB)",
        title="VeloC Checkpoint Storage Size under Failure Injection",
        output_path=out,
        failure_only=True,
        scale=1.0 / (1024 ** 2),
        codebase="resilient",
    )
    return out


def plot_memory_usage(results: BenchmarkResults, output_dir: Path) -> Path:
    """Peak memory usage for failure-injection scenarios (resilient only)."""
    out = output_dir / "plots" / "memory_usage.png"
    _plot_metric_figure(
        results=results,
        metric="peak_memory_bytes",
        y_label="Peak Memory (MiB)",
        title="Peak Memory Usage under Failure Injection (Resilient)",
        output_path=out,
        failure_only=True,
        scale=1.0 / (1024 ** 2),
        codebase="resilient",
    )
    return out


def plot_resilience_overhead(results: BenchmarkResults, output_dir: Path) -> Path:
    """Resilience overhead (%) relative to no-failure baseline.

    For each failure-injection scenario, overhead = (resilient_time - baseline_time)
    / baseline_time * 100.  The baseline is the no-failure scenario with the
    same workload parameters (same app_args and num_procs, inject_failures=False).

    Varying parameters are mapped to x-axis / bar-group / panel as usual.
    """
    plt, np = _import_matplotlib()
    _apply_style(plt)

    failure_scenarios = [s for s in results.scenarios if s.inject_failures]
    baseline_scenarios = [s for s in results.scenarios if not s.inject_failures]
    if not failure_scenarios:
        return output_dir / "plots" / "resilience_overhead.png"

    # Build a lookup: (num_procs, tuple(app_args)) → baseline mean elapsed_s
    def _baseline_key(s: BenchmarkScenario):
        return (s.num_procs, tuple(s.app_args))

    baseline_lookup: dict[tuple, float] = {}
    for bs in baseline_scenarios:
        key = _baseline_key(bs)
        vals = _collect_metric_values(results.runs, bs.name, "elapsed_s", "resilient")
        if not vals:
            vals = _collect_metric_values(results.runs, bs.name, "elapsed_s", "original")
        if vals:
            baseline_lookup[key] = sum(vals) / len(vals)

    # Compute overhead for each failure scenario
    # We'll build a synthetic RunMetrics-like structure by injecting overhead
    # values into a temporary BenchmarkResults so we can reuse _plot_metric_figure.
    # Instead, we compute directly here.

    varying = _discover_varying_params(failure_scenarios, failure_only=False)
    x_param, group_param, panel_param = _assign_roles(varying)

    x_vals = varying[x_param] if x_param else [failure_scenarios[0].name]
    group_vals = varying[group_param] if group_param else [None]
    panel_vals = varying[panel_param] if panel_param else [None]

    n_panels = len(panel_vals)
    n_groups = len(group_vals)
    n_x = len(x_vals)

    fig_width = max(6, 2.5 * n_x * n_groups + 1.5) * min(n_panels, 3)
    fig_height = 5
    if n_panels > 1:
        ncols = min(n_panels, 3)
        nrows = (n_panels + ncols - 1) // ncols
        fig, axes = plt.subplots(nrows, ncols,
                                 figsize=(fig_width / min(n_panels, 3) * ncols, fig_height * nrows),
                                 sharey=True, squeeze=False)
        axes_flat = axes.flatten()
    else:
        fig, ax_single = plt.subplots(figsize=(max(7, 2.5 * n_x * n_groups + 1.5), fig_height))
        axes_flat = [ax_single]

    width = 0.8 / max(n_groups, 1)
    x_positions = np.arange(n_x)

    for panel_idx, panel_val in enumerate(panel_vals):
        if panel_idx >= len(axes_flat):
            break
        ax = axes_flat[panel_idx]

        for g_idx, group_val in enumerate(group_vals):
            means = []
            stds = []
            for x_val in x_vals:
                matched = []
                for s in failure_scenarios:
                    if x_param and _scenario_param_value(s, x_param) != x_val:
                        continue
                    if group_param and _scenario_param_value(s, group_param) != group_val:
                        continue
                    if panel_param and _scenario_param_value(s, panel_param) != panel_val:
                        continue
                    matched.append(s)

                overhead_vals = []
                for s in matched:
                    bkey = _baseline_key(s)
                    base = baseline_lookup.get(bkey)
                    if base is None or base == 0:
                        continue
                    res_vals = _collect_metric_values(results.runs, s.name, "elapsed_s", "resilient")
                    for rv in res_vals:
                        overhead_vals.append((rv - base) / base * 100.0)

                m, sd = _mean_std(overhead_vals)
                means.append(m)
                stds.append(sd)

            offset = (g_idx - (n_groups - 1) / 2) * width
            color = _GROUP_COLORS[g_idx % len(_GROUP_COLORS)]
            hatch = _PANEL_HATCHES[panel_idx % len(_PANEL_HATCHES)]

            label = None
            if group_param:
                label = f"{_param_label(group_param)}={group_val}"

            ax.bar(
                x_positions + offset, means, width,
                yerr=stds, capsize=4,
                color=color, alpha=0.85,
                hatch=hatch,
                label=label,
                error_kw={"elinewidth": 1.2},
            )

        ax.axhline(0, color="black", linewidth=0.8, linestyle="--")
        ax.set_xticks(x_positions)
        ax.set_xticklabels(
            [str(v) for v in x_vals],
            rotation=30 if n_x > 4 else 0,
            ha="right" if n_x > 4 else "center",
        )
        if x_param:
            ax.set_xlabel(_param_label(x_param))
        ax.set_ylabel("Overhead (%)")

        panel_subtitle = ""
        if panel_param and panel_val is not None:
            panel_subtitle = f"{_param_label(panel_param)} = {panel_val}"
        ax.set_title(panel_subtitle)

        if group_param:
            ax.legend(fontsize="small", loc="best")

    for idx in range(len(panel_vals), len(axes_flat)):
        axes_flat[idx].set_visible(False)

    if panel_param and n_panels > 1:
        fig.text(
            0.5, 0.01,
            f"Each panel: {_param_label(panel_param)}",
            ha="center", fontsize="small", style="italic",
        )

    fig.suptitle(
        "Resilience Overhead vs No-Failure Baseline\n"
        "(Resilient − Baseline) / Baseline × 100%",
        fontsize=13, fontweight="bold",
    )
    fig.tight_layout()

    out = output_dir / "plots" / "resilience_overhead.png"
    _save_fig(fig, out)
    plt.close(fig)
    return out


# ---------------------------------------------------------------------------
# Correctness report helpers
# ---------------------------------------------------------------------------

def _write_correctness_files(
    correctness_results: list[CompareResult],
    output_dir: Path,
) -> tuple[Path, Path]:
    """Write correctness/test_results.json and correctness/correctness_summary.txt."""
    corr_dir = output_dir / "correctness"
    corr_dir.mkdir(parents=True, exist_ok=True)

    # JSON
    json_data = [
        {
            "passed": r.passed,
            "method": r.method,
            "score": r.score,
            "message": r.message,
            "details": r.details,
        }
        for r in correctness_results
    ]
    json_path = corr_dir / "test_results.json"
    json_path.write_text(json.dumps(json_data, indent=2), encoding="utf-8")

    # Text summary
    total = len(correctness_results)
    passed = sum(1 for r in correctness_results if r.passed)
    lines = [
        "Correctness Summary",
        "=" * 40,
        f"Total tests : {total}",
        f"Passed      : {passed}",
        f"Failed      : {total - passed}",
        "",
    ]
    for i, r in enumerate(correctness_results, 1):
        status = "PASS" if r.passed else "FAIL"
        lines.append(f"  [{status}] Test {i}: {r}")
    txt_path = corr_dir / "correctness_summary.txt"
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return json_path, txt_path


# ---------------------------------------------------------------------------
# Markdown summary report
# ---------------------------------------------------------------------------

def _fmt_opt(val: float | None, fmt: str = ".2f", suffix: str = "") -> str:
    if val is None:
        return "N/A"
    return f"{val:{fmt}}{suffix}"


def _mean(vals: list[float]) -> float | None:
    if not vals:
        return None
    return sum(vals) / len(vals)


def _std(vals: list[float]) -> float | None:
    if len(vals) < 2:
        return None
    import statistics
    return statistics.stdev(vals)


def _extract_metric_from_results(
    results: BenchmarkResults,
    scenario_name: str,
    codebase: str,
    metric: str,
) -> list[float]:
    values = []
    for r in results.runs:
        if r.scenario_name != scenario_name or r.codebase != codebase:
            continue
        val = getattr(r, metric, None)
        if val is not None:
            values.append(float(val))
    return values


def write_summary_report(
    correctness_results: list[CompareResult],
    benchmark_results: BenchmarkResults | None,
    plot_paths: dict[str, Path],
    output_dir: Path,
) -> Path:
    """Write summary_report.md with embedded plot references and tabular metrics."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total = len(correctness_results)
    passed = sum(1 for r in correctness_results if r.passed)
    overall_status = "✅ PASS" if passed == total else "❌ FAIL"

    lines: list[str] = [
        "# VeloC Validation Summary Report",
        "",
        f"Generated: {now}",
        "",
        "---",
        "",
        "## 1. Correctness",
        "",
        f"**Overall status: {overall_status}** ({passed}/{total} tests passed)",
        "",
        "| # | Method | Score | Status | Message |",
        "|---|--------|-------|--------|---------|",
    ]
    for i, r in enumerate(correctness_results, 1):
        status = "✅ PASS" if r.passed else "❌ FAIL"
        score_str = f"{r.score:.6g}" if r.score is not None else "—"
        lines.append(f"| {i} | {r.method} | {score_str} | {status} | {r.message} |")

    lines += ["", "---", "", "## 2. Performance Metrics (Failure-Injection Scenarios)", ""]

    if benchmark_results is None or not benchmark_results.runs:
        lines.append("*No benchmark data collected.*")
    else:
        failure_scenarios = [s for s in benchmark_results.scenarios if s.inject_failures]
        scenario_names = [s.name for s in failure_scenarios]

        lines += [
            "### Execution Time – Resilient (seconds)",
            "",
            "| Scenario | Mean ± Std |",
            "|----------|------------|",
        ]
        for sname in scenario_names:
            vals = _extract_metric_from_results(benchmark_results, sname, "resilient", "elapsed_s")
            lines.append(f"| {sname} | {_fmt_opt(_mean(vals))} ± {_fmt_opt(_std(vals))} |")

        lines += [
            "",
            "### Recovery Time (seconds)",
            "",
            "| Scenario | Mean ± Std |",
            "|----------|------------|",
        ]
        for sname in scenario_names:
            vals = _extract_metric_from_results(benchmark_results, sname, "resilient", "recovery_time_s")
            lines.append(f"| {sname} | {_fmt_opt(_mean(vals))} ± {_fmt_opt(_std(vals))} |")

        lines += [
            "",
            "### Checkpoint Storage (MiB)",
            "",
            "| Scenario | Mean | Std |",
            "|----------|------|-----|",
        ]
        for sname in scenario_names:
            vals = [
                v / (1024 ** 2)
                for v in _extract_metric_from_results(benchmark_results, sname, "resilient", "checkpoint_size_bytes")
            ]
            lines.append(f"| {sname} | {_fmt_opt(_mean(vals))} | {_fmt_opt(_std(vals))} |")

        lines += [
            "",
            "### Peak Memory Usage (MiB)",
            "",
            "| Scenario | Mean | Std |",
            "|----------|------|-----|",
        ]
        for sname in scenario_names:
            vals = [
                v / (1024 ** 2)
                for v in _extract_metric_from_results(benchmark_results, sname, "resilient", "peak_memory_bytes")
            ]
            lines.append(f"| {sname} | {_fmt_opt(_mean(vals))} | {_fmt_opt(_std(vals))} |")

    lines += ["", "---", "", "## 3. Plots", ""]

    plot_labels = {
        "execution_time": "Execution Time (Failure-Injection, Resilient)",
        "resilience_overhead": "Resilience Overhead vs No-Failure Baseline",
        "checkpoint_size": "Checkpoint Storage Size",
        "recovery_time": "Recovery Time",
        "memory_usage": "Peak Memory Usage",
    }
    for key, label in plot_labels.items():
        if key in plot_paths:
            rel = plot_paths[key].relative_to(output_dir)
            lines.append(f"### {label}")
            lines.append("")
            lines.append(f"![{label}]({rel})")
            lines.append("")

    lines += ["---", "", "*End of report.*", ""]

    report_path = output_dir / "summary_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------

def generate_report(
    correctness_results: list[CompareResult],
    benchmark_results: BenchmarkResults | None,
    output_dir: Path,
) -> Path:
    """Generate all plots and the summary report.

    Returns the path to ``summary_report.md``.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write correctness files.
    _write_correctness_files(correctness_results, output_dir)

    # Generate plots (only if benchmark data is available).
    plot_paths: dict[str, Path] = {}
    if benchmark_results is not None and benchmark_results.runs:
        try:
            plot_paths["execution_time"] = plot_execution_time(benchmark_results, output_dir)
            plot_paths["resilience_overhead"] = plot_resilience_overhead(benchmark_results, output_dir)
            plot_paths["checkpoint_size"] = plot_checkpoint_size(benchmark_results, output_dir)
            plot_paths["recovery_time"] = plot_recovery_time(benchmark_results, output_dir)
            plot_paths["memory_usage"] = plot_memory_usage(benchmark_results, output_dir)
            print(f"[reporter] plots saved to {output_dir / 'plots'}", flush=True)
        except ImportError as exc:
            print(f"[reporter] WARNING: could not generate plots: {exc}", flush=True)

    # Write summary report.
    report_path = write_summary_report(
        correctness_results=correctness_results,
        benchmark_results=benchmark_results,
        plot_paths=plot_paths,
        output_dir=output_dir,
    )
    print(f"[reporter] summary report saved to {report_path}", flush=True)
    return report_path
