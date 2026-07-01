"""LoC vs average-tokens-per-iteration scatter, colored by complexity class.

Companion to ``_plot_loc_vs_tokens.py``: same layout (one dot per
TRUSTED-baseline app, color=group, "X" marker for unsuccessful runs,
log-scale x-axis, per-point app labels, legend above the plot), but
the y-axis is average tokens consumed per iteration instead of the
cumulative total.  This isolates how expensive each iteration was
from how many iterations the loop took to terminate.

Saves PDF (vector) + PNG (300 DPI) to docs/figs/ and mirrors the PDF
into each active paper's Figures dir.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

# --- Inputs ---------------------------------------------------------------
# Paper data lives under `results/` (frozen, out of `build/` to survive
# orchestrator wipes).  `PAPER_MODEL` selects which model cell to read;
# default is the paper baseline (Opus 4.7, 128k).  See results/README.md.
REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS = REPO_ROOT / "results"
PAPER_MODEL = os.environ.get("PAPER_MODEL", "opus47")
ITER_LOGS = RESULTS / "models" / PAPER_MODEL / "iter_logs"
TRUST = REPO_ROOT / "build" / "_experiment_state" / "_trust.json"
OUT_DIR = REPO_ROOT / "docs" / "figs"
PAPER_FIGURES_DIRS = [
    REPO_ROOT / "docs" / "paper" / "eScience" / "Figures",
]
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Unsuccessful apps whose per-iter cost is still cited in the paper
# (kept in sync with _plot_loc_vs_tokens.py / _plot_fast_tier_iter_metrics.py).
# Live iter logs were wiped on re-launch; the canonical unsuccessful-run
# archive lives under results/archives/.
FAILED_APP_ARCHIVES = {
    "Nyx":    RESULTS / "archives" / "opus47_nyx_samrai_dnc" / "Nyx_baseline",
    "SAMRAI": RESULTS / "archives" / "opus47_nyx_samrai_dnc" / "SAMRAI_baseline",
}

# Single source of truth: APP_LOC and GROUPS are duplicated across the
# fast_tier_*.py family; any update must land in all of them in lock-step.
APP_LOC = {
    "PRK_Stencil":   1_000,
    "CoMD":          5_600,
    "HPCG":          6_200,
    "ROSS":         15_000,
    "SPPARKS":      52_000,
    "SW4lite":      57_000,
    "HyPar":        63_000,
    "CLAMR":        81_000,
    "Athena++":    132_000,
    "Smilei":      153_000,
    "SPARTA":      174_000,
    "OpenLB":      338_000,
    "Nyx":         441_000,
    "QMCPACK":     532_000,
    "WarpX":       553_000,
    "SAMRAI":      598_000,
    "LAMMPS":      627_000,
}

GROUPS = {
    "Plain Static":              ["HPCG", "PRK_Stencil", "SW4lite", "HyPar"],
    "Plain Dynamic":        ["CoMD", "SPARTA", "SPPARKS", "CLAMR", "LAMMPS"],
    "Encapsulated":  ["Athena++", "WarpX", "OpenLB", "Smilei"],
    "Modularized":   ["Nyx", "ROSS", "SAMRAI", "QMCPACK"],
}
GROUP_COLORS = {
    "Plain Static":              "#0072B2",
    "Plain Dynamic":        "#E69F00",
    "Encapsulated":  "#009E73",
    "Modularized":   "#CC79A7",
}


def _group_of(app: str) -> str | None:
    for label, apps in GROUPS.items():
        if app in apps:
            return label
    return None


def _trusted_baseline_apps() -> set[str]:
    if not TRUST.exists():
        return set()
    d = json.loads(TRUST.read_text())
    return {
        k[: -len("_baseline")]
        for k, v in d.items()
        if k.endswith("_baseline")
        and isinstance(v, dict)
        and v.get("status") == "TRUSTED"
    }


def _load_avg_tokens_per_iter(app: str, *, source_dir: Path | None = None) -> float | None:
    """Average tokens-per-iteration (millions) for `app`.

    Average = total_tokens / iterations, computed from `result.json`.
    Returns None if the result file or its fields are missing.
    """
    base = source_dir if source_dir is not None else (ITER_LOGS / app)
    p = base / "result.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    tot = d.get("total_tokens")
    n = d.get("iterations") or len(d.get("per_iteration", []) or [])
    if tot is None or not n:
        return None
    return (tot / n) / 1e6


# --- Plot styling (publication-grade, matches sibling fast_tier_*.py) ----
mpl.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif", "Times New Roman", "Times"],
    "font.size": 11,
    "axes.titlesize": 12,
    "axes.labelsize": 12,
    "axes.linewidth": 0.8,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "legend.fontsize": 8,
    "legend.frameon": False,
    "axes.grid": True,
    "grid.alpha": 0.35,
    "grid.linestyle": "--",
})


def _mirror_to_papers(stem: str) -> None:
    import shutil
    src = OUT_DIR / f"{stem}.pdf"
    if not src.exists():
        return
    for paper_dir in PAPER_FIGURES_DIRS:
        if paper_dir.exists():
            shutil.copy2(src, paper_dir / f"{stem}.pdf")


def main() -> None:
    trusted = _trusted_baseline_apps()
    points: list[tuple[str, int, float, str]] = []  # (app, loc, avg_M, group)
    failed_points: list[tuple[str, int, float, str]] = []
    dropped_not_trusted: list[str] = []
    dropped_no_result: list[str] = []
    for app, loc in APP_LOC.items():
        if app in FAILED_APP_ARCHIVES:
            avg = _load_avg_tokens_per_iter(app, source_dir=FAILED_APP_ARCHIVES[app])
            if avg is None:
                dropped_no_result.append(f"{app}(unsuccessful-archive-missing)")
                continue
            grp = _group_of(app) or "unknown"
            failed_points.append((app, loc, avg, grp))
            continue
        if app not in trusted:
            dropped_not_trusted.append(app)
            continue
        avg = _load_avg_tokens_per_iter(app)
        if avg is None:
            dropped_no_result.append(app)
            continue
        grp = _group_of(app) or "unknown"
        points.append((app, loc, avg, grp))

    print(f"  [dropped non-TRUSTED]    {sorted(dropped_not_trusted)}")
    print(f"  [dropped no result.json] {sorted(dropped_no_result)}")
    print(f"Plotting {len(points)} TRUSTED apps + "
          f"{len(failed_points)} unsuccessful")
    for app, loc, avg_m, grp in points + failed_points:
        tag = "TRUSTED" if (app, loc, avg_m, grp) in points else "UNSUCC "
        print(f"  [{tag}] {app:<12}  loc={loc:>7,}  avg={avg_m:5.2f} M/it  group={grp}")

    avgs = [p[2] for p in points] + [p[2] for p in failed_points]

    # --- Figure ----------------------------------------------------------
    fig, ax = plt.subplots(figsize=(3.5, 3.1))
    for label in GROUPS.keys():
        xs = [p[1] for p in points if p[3] == label]
        ys = [p[2] for p in points if p[3] == label]
        if not xs:
            continue
        ax.scatter(
            xs, ys,
            s=46,
            color=GROUP_COLORS[label],
            edgecolor="black",
            linewidth=0.5,
            label=label,
            zorder=3,
        )

    # Unsuccessful points — same group color, "X" marker to flag the
    # measurement is from an unsuccessful loop.
    if failed_points:
        for app, loc, avg_m, grp in failed_points:
            ax.scatter(
                [loc], [avg_m],
                s=70,
                marker="X",
                color=GROUP_COLORS.get(grp, "#990000"),
                edgecolor="black",
                linewidth=0.6,
                zorder=3,
            )
        ax.scatter(
            [], [],
            s=70,
            marker="X",
            color="#bbbbbb",
            edgecolor="black",
            linewidth=0.6,
            label="Unsuccessful",
        )

    # Per-point app labels (small, offset to upper-right for legibility).
    for app, loc, avg_m, _grp in points + failed_points:
        ax.annotate(
            app,
            xy=(loc, avg_m),
            xytext=(4, 3),
            textcoords="offset points",
            fontsize=6.5,
            color="#222222",
            zorder=4,
        )

    ax.set_xscale("log")
    ax.set_xlabel("Source-tree size (LoC, log scale)")
    ax.set_ylabel("Average tokens per iteration (M)")
    ax.set_xlim(700, 1.0e6)
    _ymax = max(avgs) if avgs else 1.0
    ax.set_ylim(0, _ymax * 1.10)

    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.02),
        ncol=2,
        fontsize=7,
        frameon=False,
        handletextpad=0.4,
        columnspacing=1.2,
    )

    fig.tight_layout()

    stem = "tokens_per_iter"
    fig.savefig(OUT_DIR / f"{stem}.pdf")
    fig.savefig(OUT_DIR / f"{stem}.png", dpi=300)
    plt.close(fig)
    _mirror_to_papers(stem)
    print(f"\nSaved: {OUT_DIR}/{stem}.{{pdf,png}} (and mirrored)")


if __name__ == "__main__":
    main()
