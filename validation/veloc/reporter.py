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
  │   ├── execution_time_comparison.png
  │   ├── resilience_overhead.png
  │   ├── checkpoint_size.png
  │   ├── recovery_time.png
  │   ├── memory_usage.png
  │   └── aggregated_summary.png
  └── summary_report.md

Requires: matplotlib, numpy
"""

from __future__ import annotations

import json
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .comparator import CompareResult
from .metrics_collector import BenchmarkResults, RunMetrics


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

_COLORS = {
    "original": "#2196F3",   # blue
    "resilient": "#FF5722",  # deep orange
}
_FIGSIZE_SINGLE = (8, 5)
_FIGSIZE_MULTI = (14, 10)
_DPI = 150
_STYLE = "seaborn-v0_8-whitegrid"


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
# Data extraction helpers
# ---------------------------------------------------------------------------

def _extract_metric(
    runs: list[RunMetrics],
    scenario_name: str,
    codebase: str,
    metric: str,
) -> list[float]:
    """Return all non-None values of *metric* for the given scenario/codebase."""
    values = []
    for r in runs:
        if r.scenario_name != scenario_name or r.codebase != codebase:
            continue
        val = getattr(r, metric, None)
        if val is not None:
            values.append(float(val))
    return values


def _scenario_names(results: BenchmarkResults) -> list[str]:
    seen: list[str] = []
    for s in results.scenarios:
        if s.name not in seen:
            seen.append(s.name)
    return seen


# ---------------------------------------------------------------------------
# Individual plot functions
# ---------------------------------------------------------------------------

def plot_execution_time(results: BenchmarkResults, output_dir: Path) -> Path:
    """Grouped bar chart: original vs resilient execution time per scenario."""
    plt, np = _import_matplotlib()
    _apply_style(plt)

    scenarios = _scenario_names(results)
    orig_means, orig_stds = [], []
    res_means, res_stds = [], []

    for s in scenarios:
        orig_vals = _extract_metric(results.runs, s, "original", "elapsed_s")
        res_vals = _extract_metric(results.runs, s, "resilient", "elapsed_s")
        orig_means.append(np.mean(orig_vals) if orig_vals else 0.0)
        orig_stds.append(np.std(orig_vals) if len(orig_vals) > 1 else 0.0)
        res_means.append(np.mean(res_vals) if res_vals else 0.0)
        res_stds.append(np.std(res_vals) if len(res_vals) > 1 else 0.0)

    x = np.arange(len(scenarios))
    width = 0.35

    fig, ax = plt.subplots(figsize=_FIGSIZE_SINGLE)
    ax.bar(x - width / 2, orig_means, width, yerr=orig_stds, capsize=4,
           label="Original", color=_COLORS["original"], alpha=0.85)
    ax.bar(x + width / 2, res_means, width, yerr=res_stds, capsize=4,
           label="Resilient", color=_COLORS["resilient"], alpha=0.85)

    ax.set_xlabel("Scenario")
    ax.set_ylabel("Execution Time (s)")
    ax.set_title("Execution Time: Original vs Resilient")
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, rotation=20, ha="right")
    ax.legend()
    fig.tight_layout()

    out = output_dir / "plots" / "execution_time_comparison.png"
    _save_fig(fig, out)
    plt.close(fig)
    return out


def plot_resilience_overhead(results: BenchmarkResults, output_dir: Path) -> Path:
    """Bar chart: relative overhead (resilient - original) / original per scenario."""
    plt, np = _import_matplotlib()
    _apply_style(plt)

    scenarios = _scenario_names(results)
    overheads = []

    for s in scenarios:
        orig_vals = _extract_metric(results.runs, s, "original", "elapsed_s")
        res_vals = _extract_metric(results.runs, s, "resilient", "elapsed_s")
        if orig_vals and res_vals:
            orig_mean = np.mean(orig_vals)
            res_mean = np.mean(res_vals)
            overhead = (res_mean - orig_mean) / orig_mean * 100.0 if orig_mean > 0 else 0.0
        else:
            overhead = 0.0
        overheads.append(overhead)

    x = np.arange(len(scenarios))
    colors = [_COLORS["resilient"] if o >= 0 else _COLORS["original"] for o in overheads]

    fig, ax = plt.subplots(figsize=_FIGSIZE_SINGLE)
    ax.bar(x, overheads, color=colors, alpha=0.85)
    ax.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Scenario")
    ax.set_ylabel("Overhead (%)")
    ax.set_title("Resilience Overhead: (Resilient − Original) / Original")
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, rotation=20, ha="right")
    fig.tight_layout()

    out = output_dir / "plots" / "resilience_overhead.png"
    _save_fig(fig, out)
    plt.close(fig)
    return out


def plot_checkpoint_size(results: BenchmarkResults, output_dir: Path) -> Path:
    """Bar chart: checkpoint storage size per scenario (resilient only)."""
    plt, np = _import_matplotlib()
    _apply_style(plt)

    scenarios = _scenario_names(results)
    sizes_mb = []

    for s in scenarios:
        vals = _extract_metric(results.runs, s, "resilient", "checkpoint_size_bytes")
        sizes_mb.append(np.mean(vals) / (1024 ** 2) if vals else 0.0)

    x = np.arange(len(scenarios))

    fig, ax = plt.subplots(figsize=_FIGSIZE_SINGLE)
    ax.bar(x, sizes_mb, color=_COLORS["resilient"], alpha=0.85)
    ax.set_xlabel("Scenario")
    ax.set_ylabel("Checkpoint Size (MiB)")
    ax.set_title("VeloC Checkpoint Storage Size per Scenario")
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, rotation=20, ha="right")
    fig.tight_layout()

    out = output_dir / "plots" / "checkpoint_size.png"
    _save_fig(fig, out)
    plt.close(fig)
    return out


def plot_recovery_time(results: BenchmarkResults, output_dir: Path) -> Path:
    """Bar chart: estimated recovery time per scenario (resilient only)."""
    plt, np = _import_matplotlib()
    _apply_style(plt)

    scenarios = _scenario_names(results)
    rec_means, rec_stds = [], []

    for s in scenarios:
        vals = _extract_metric(results.runs, s, "resilient", "recovery_time_s")
        rec_means.append(np.mean(vals) if vals else 0.0)
        rec_stds.append(np.std(vals) if len(vals) > 1 else 0.0)

    x = np.arange(len(scenarios))

    fig, ax = plt.subplots(figsize=_FIGSIZE_SINGLE)
    ax.bar(x, rec_means, yerr=rec_stds, capsize=4,
           color=_COLORS["resilient"], alpha=0.85)
    ax.set_xlabel("Scenario")
    ax.set_ylabel("Recovery Time (s)")
    ax.set_title("Estimated Recovery Time per Scenario (Resilient)")
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, rotation=20, ha="right")
    fig.tight_layout()

    out = output_dir / "plots" / "recovery_time.png"
    _save_fig(fig, out)
    plt.close(fig)
    return out


def plot_memory_usage(results: BenchmarkResults, output_dir: Path) -> Path:
    """Grouped bar chart: peak memory usage original vs resilient per scenario."""
    plt, np = _import_matplotlib()
    _apply_style(plt)

    scenarios = _scenario_names(results)
    orig_means, orig_stds = [], []
    res_means, res_stds = [], []

    for s in scenarios:
        orig_vals = [
            v / (1024 ** 2)
            for v in _extract_metric(results.runs, s, "original", "peak_memory_bytes")
        ]
        res_vals = [
            v / (1024 ** 2)
            for v in _extract_metric(results.runs, s, "resilient", "peak_memory_bytes")
        ]
        orig_means.append(np.mean(orig_vals) if orig_vals else 0.0)
        orig_stds.append(np.std(orig_vals) if len(orig_vals) > 1 else 0.0)
        res_means.append(np.mean(res_vals) if res_vals else 0.0)
        res_stds.append(np.std(res_vals) if len(res_vals) > 1 else 0.0)

    x = np.arange(len(scenarios))
    width = 0.35

    fig, ax = plt.subplots(figsize=_FIGSIZE_SINGLE)
    ax.bar(x - width / 2, orig_means, width, yerr=orig_stds, capsize=4,
           label="Original", color=_COLORS["original"], alpha=0.85)
    ax.bar(x + width / 2, res_means, width, yerr=res_stds, capsize=4,
           label="Resilient", color=_COLORS["resilient"], alpha=0.85)
    ax.set_xlabel("Scenario")
    ax.set_ylabel("Peak Memory (MiB)")
    ax.set_title("Peak Memory Usage: Original vs Resilient")
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, rotation=20, ha="right")
    ax.legend()
    fig.tight_layout()

    out = output_dir / "plots" / "memory_usage.png"
    _save_fig(fig, out)
    plt.close(fig)
    return out


def plot_aggregated_summary(results: BenchmarkResults, output_dir: Path) -> Path:
    """Multi-panel figure combining execution time, overhead, checkpoint size,
    and recovery time for a publication-ready overview."""
    plt, np = _import_matplotlib()
    _apply_style(plt)

    scenarios = _scenario_names(results)
    x = np.arange(len(scenarios))
    width = 0.35

    fig, axes = plt.subplots(2, 2, figsize=_FIGSIZE_MULTI)
    fig.suptitle("VeloC Validation – Aggregated Metrics Summary", fontsize=14, y=1.01)

    # --- Panel 1: Execution time ---
    ax = axes[0, 0]
    orig_means = [np.mean(v) if (v := _extract_metric(results.runs, s, "original", "elapsed_s")) else 0.0 for s in scenarios]
    res_means  = [np.mean(v) if (v := _extract_metric(results.runs, s, "resilient", "elapsed_s")) else 0.0 for s in scenarios]
    orig_stds  = [np.std(v) if len(v := _extract_metric(results.runs, s, "original", "elapsed_s")) > 1 else 0.0 for s in scenarios]
    res_stds   = [np.std(v) if len(v := _extract_metric(results.runs, s, "resilient", "elapsed_s")) > 1 else 0.0 for s in scenarios]
    ax.bar(x - width / 2, orig_means, width, yerr=orig_stds, capsize=3,
           label="Original", color=_COLORS["original"], alpha=0.85)
    ax.bar(x + width / 2, res_means, width, yerr=res_stds, capsize=3,
           label="Resilient", color=_COLORS["resilient"], alpha=0.85)
    ax.set_title("Execution Time (s)")
    ax.set_xticks(x); ax.set_xticklabels(scenarios, rotation=15, ha="right", fontsize=8)
    ax.legend(fontsize=8)

    # --- Panel 2: Overhead ---
    ax = axes[0, 1]
    overheads = []
    for s in scenarios:
        ov = _extract_metric(results.runs, s, "original", "elapsed_s")
        rv = _extract_metric(results.runs, s, "resilient", "elapsed_s")
        if ov and rv:
            overheads.append((np.mean(rv) - np.mean(ov)) / np.mean(ov) * 100.0)
        else:
            overheads.append(0.0)
    colors = [_COLORS["resilient"] if o >= 0 else _COLORS["original"] for o in overheads]
    ax.bar(x, overheads, color=colors, alpha=0.85)
    ax.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax.set_title("Resilience Overhead (%)")
    ax.set_xticks(x); ax.set_xticklabels(scenarios, rotation=15, ha="right", fontsize=8)

    # --- Panel 3: Checkpoint size ---
    ax = axes[1, 0]
    sizes_mb = [
        np.mean(v) / (1024 ** 2) if (v := _extract_metric(results.runs, s, "resilient", "checkpoint_size_bytes")) else 0.0
        for s in scenarios
    ]
    ax.bar(x, sizes_mb, color=_COLORS["resilient"], alpha=0.85)
    ax.set_title("Checkpoint Size (MiB)")
    ax.set_xticks(x); ax.set_xticklabels(scenarios, rotation=15, ha="right", fontsize=8)

    # --- Panel 4: Recovery time ---
    ax = axes[1, 1]
    rec_means = [np.mean(v) if (v := _extract_metric(results.runs, s, "resilient", "recovery_time_s")) else 0.0 for s in scenarios]
    rec_stds  = [np.std(v) if len(v := _extract_metric(results.runs, s, "resilient", "recovery_time_s")) > 1 else 0.0 for s in scenarios]
    ax.bar(x, rec_means, yerr=rec_stds, capsize=3, color=_COLORS["resilient"], alpha=0.85)
    ax.set_title("Recovery Time (s)")
    ax.set_xticks(x); ax.set_xticklabels(scenarios, rotation=15, ha="right", fontsize=8)

    fig.tight_layout()
    out = output_dir / "plots" / "aggregated_summary.png"
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

    lines += ["", "---", "", "## 2. Performance Metrics", ""]

    if benchmark_results is None or not benchmark_results.runs:
        lines.append("*No benchmark data collected.*")
    else:
        scenarios = [s.name for s in benchmark_results.scenarios]
        lines += [
            "### Execution Time (seconds)",
            "",
            "| Scenario | Original (mean ± std) | Resilient (mean ± std) | Overhead |",
            "|----------|-----------------------|------------------------|----------|",
        ]
        for s in scenarios:
            orig_vals = _extract_metric_from_results(benchmark_results, s, "original", "elapsed_s")
            res_vals  = _extract_metric_from_results(benchmark_results, s, "resilient", "elapsed_s")
            orig_mean = _mean(orig_vals)
            orig_std  = _std(orig_vals)
            res_mean  = _mean(res_vals)
            res_std   = _std(res_vals)
            if orig_mean and orig_mean > 0 and res_mean:
                overhead = f"{(res_mean - orig_mean) / orig_mean * 100:.1f}%"
            else:
                overhead = "N/A"
            lines.append(
                f"| {s} | {_fmt_opt(orig_mean)} ± {_fmt_opt(orig_std)} | "
                f"{_fmt_opt(res_mean)} ± {_fmt_opt(res_std)} | {overhead} |"
            )

        lines += [
            "",
            "### Checkpoint Storage (MiB, resilient only)",
            "",
            "| Scenario | Mean | Std |",
            "|----------|------|-----|",
        ]
        for s in scenarios:
            vals = [
                v / (1024 ** 2)
                for v in _extract_metric_from_results(benchmark_results, s, "resilient", "checkpoint_size_bytes")
            ]
            lines.append(f"| {s} | {_fmt_opt(_mean(vals))} | {_fmt_opt(_std(vals))} |")

        lines += [
            "",
            "### Recovery Time (seconds, resilient only)",
            "",
            "| Scenario | Mean | Std |",
            "|----------|------|-----|",
        ]
        for s in scenarios:
            vals = _extract_metric_from_results(benchmark_results, s, "resilient", "recovery_time_s")
            lines.append(f"| {s} | {_fmt_opt(_mean(vals))} | {_fmt_opt(_std(vals))} |")

        lines += [
            "",
            "### Peak Memory Usage (MiB)",
            "",
            "| Scenario | Original | Resilient |",
            "|----------|----------|-----------|",
        ]
        for s in scenarios:
            orig_vals = [v / (1024 ** 2) for v in _extract_metric_from_results(benchmark_results, s, "original", "peak_memory_bytes")]
            res_vals  = [v / (1024 ** 2) for v in _extract_metric_from_results(benchmark_results, s, "resilient", "peak_memory_bytes")]
            lines.append(f"| {s} | {_fmt_opt(_mean(orig_vals))} | {_fmt_opt(_mean(res_vals))} |")

    lines += ["", "---", "", "## 3. Plots", ""]

    plot_labels = {
        "execution_time": "Execution Time Comparison",
        "resilience_overhead": "Resilience Overhead",
        "checkpoint_size": "Checkpoint Storage Size",
        "recovery_time": "Recovery Time",
        "memory_usage": "Peak Memory Usage",
        "aggregated_summary": "Aggregated Summary",
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
# Small helpers for the report
# ---------------------------------------------------------------------------

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


def _mean(vals: list[float]) -> float | None:
    if not vals:
        return None
    return sum(vals) / len(vals)


def _std(vals: list[float]) -> float | None:
    if len(vals) < 2:
        return None
    import statistics
    return statistics.stdev(vals)


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
            plot_paths["aggregated_summary"] = plot_aggregated_summary(benchmark_results, output_dir)
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
