"""Shared two-box legend for the merged overhead figure (Fig. 3).

The walltime panel (3a) and the checkpoint-footprint panel (3b) both
encode the same approaches (Vanilla, Opus 4.7, Sonnet 4.6, GPT-5.5,
Reference), and the walltime panel additionally encodes a stacked
breakdown (failure-free execution + failure-injected overhead).
Rather than repeat a per-panel legend twice in the paper, both panels
suppress their internal legends and this script renders one wide
legend strip containing two boxes:

    [ Approaches: Vanilla, Opus 4.7, Sonnet 4.6, GPT-5.5, Reference ]
    [ Scenarios:  Failure-free Execution, Failure Overhead          ]

Output: ``docs/figs/fast_tier_overhead_legend.{pdf,png}`` (mirrored
into ``docs/paper/eScience/Figures/``).  Width is tuned so the legend
visually centers under the two text-width-wide subfigures in the
merged LaTeX figure.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

from _cells import MODEL_COLORS, MODEL_LABELS

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "docs" / "figs"
PAPER_FIGURES_DIRS = [
    REPO_ROOT / "docs" / "paper" / "eScience" / "Figures",
]
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Match the sibling charts' palette.
COLOR_REF = "#332288"
COLOR_VAN = "#777777"

mpl.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif", "Times New Roman", "Times"],
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


def _approach_handles() -> list[mpatches.Patch]:
    """Five-entry approach legend, ordered to match the chart bar order."""
    handles = [
        mpatches.Patch(facecolor=COLOR_VAN, edgecolor="black", linewidth=0.5,
                       label="Vanilla"),
    ]
    for cell_id in ("opus47", "sonnet46", "gpt55_unified"):
        handles.append(
            mpatches.Patch(facecolor=MODEL_COLORS[cell_id],
                           edgecolor="black", linewidth=0.5,
                           label=MODEL_LABELS[cell_id]))
    handles.append(
        mpatches.Patch(facecolor=COLOR_REF, edgecolor="black", linewidth=0.5,
                       label="Reference"))
    return handles


def _scenario_handles() -> list[mpatches.Patch]:
    """Two-entry scenario legend: solid = failure-free, hatched = overhead."""
    return [
        mpatches.Patch(facecolor="#cccccc", edgecolor="black", linewidth=0.5,
                       label="Failure-free Execution"),
        mpatches.Patch(facecolor="#cccccc", edgecolor="black", linewidth=0.5,
                       hatch="////", label="Failure Overhead"),
    ]


def _mirror_to_papers(stem: str) -> None:
    import shutil
    src = OUT_DIR / f"{stem}.pdf"
    if not src.exists():
        return
    for paper_dir in PAPER_FIGURES_DIRS:
        if paper_dir.exists():
            shutil.copy2(src, paper_dir / f"{stem}.pdf")


def main() -> None:
    # Two side-by-side axes, each hosting one legend.  Width ratio
    # mirrors the legend content widths (approach has 5 chips, scenario
    # has 2) so each axis snugly contains its legend with minimal slack.
    # Both axes are turned off; bbox_inches="tight" then trims everything
    # outside the legend frames, producing a clean two-box strip.
    fig, (ax_a, ax_s) = plt.subplots(
        1, 2, figsize=(9.5, 0.55),
        gridspec_kw={"width_ratios": [5, 2], "wspace": 0.35},
    )
    for ax in (ax_a, ax_s):
        ax.set_axis_off()

    ax_a.legend(
        handles=_approach_handles(),
        loc="center",
        ncol=5,
        fontsize=9,
        frameon=True, fancybox=False, edgecolor="black",
        handlelength=1.2, handletextpad=0.4,
        columnspacing=1.2, borderpad=0.4,
    )
    ax_s.legend(
        handles=_scenario_handles(),
        loc="center",
        ncol=2,
        fontsize=9,
        frameon=True, fancybox=False, edgecolor="black",
        handlelength=1.2, handletextpad=0.4,
        columnspacing=1.2, borderpad=0.4,
    )

    stem = "fast_tier_overhead_legend"
    fig.savefig(OUT_DIR / f"{stem}.pdf", bbox_inches="tight", pad_inches=0.02)
    fig.savefig(OUT_DIR / f"{stem}.png", dpi=300, bbox_inches="tight",
                pad_inches=0.02)
    _mirror_to_papers(stem)
    plt.close(fig)
    print(f"Saved: {OUT_DIR}/{stem}.{{pdf,png}} (and mirrored)")


if __name__ == "__main__":
    main()
