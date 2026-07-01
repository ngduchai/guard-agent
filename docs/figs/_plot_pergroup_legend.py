"""Shared approach legend for the per-group summary panels (Fig. 3 a/b/c).

Panels (a) end-to-end wall time, (b) token cost, and (c) API cost all
encode the same model approaches (Opus 4.7, Sonnet 4.6, GPT-5.5) via
bar color.  Repeating the legend in every panel wastes space; this
script renders a single horizontal strip the LaTeX side places above
the row in main.tex.

Output: ``docs/figs/fast_tier_pergroup_legend.{pdf,png}`` (mirrored
into the paper's Figures dir).
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

from _cells import CELLS, MODEL_COLORS, MODEL_LABELS

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "docs" / "figs"
PAPER_FIGURES_DIRS = [
    REPO_ROOT / "docs" / "paper" / "eScience" / "Figures",
]
OUT_DIR.mkdir(parents=True, exist_ok=True)

mpl.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif", "Times New Roman", "Times"],
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


def _approach_handles() -> list[mpatches.Patch]:
    handles = []
    for cell_id, _label, _marker in CELLS:
        handles.append(
            mpatches.Patch(facecolor=MODEL_COLORS[cell_id],
                           edgecolor="black", linewidth=0.5,
                           label=MODEL_LABELS[cell_id])
        )
    return handles


def _mirror_to_papers(stem: str) -> None:
    import shutil
    src = OUT_DIR / f"{stem}.pdf"
    if not src.exists():
        return
    for paper_dir in PAPER_FIGURES_DIRS:
        if paper_dir.exists():
            shutil.copy2(src, paper_dir / f"{stem}.pdf")


def main() -> None:
    # Width tuned to cover the (a/b/c) three-panel row in main.tex
    # (~3 * 0.24 * \textwidth = 5.16in); 0.4in tall keeps the strip
    # visually subordinate to the panels themselves.
    fig, ax = plt.subplots(figsize=(5.16, 0.4))
    ax.set_axis_off()
    ax.legend(
        handles=_approach_handles(),
        loc="center",
        ncol=len(CELLS),
        fontsize=9,
        frameon=True, fancybox=False, edgecolor="black",
        handlelength=1.4, handletextpad=0.5,
        columnspacing=1.6, borderpad=0.4,
    )

    stem = "fast_tier_pergroup_legend"
    fig.savefig(OUT_DIR / f"{stem}.pdf", bbox_inches="tight", pad_inches=0.02)
    fig.savefig(OUT_DIR / f"{stem}.png", dpi=300, bbox_inches="tight",
                pad_inches=0.02)
    _mirror_to_papers(stem)
    plt.close(fig)
    print(f"Saved: {OUT_DIR}/{stem}.{{pdf,png}} (and mirrored)")


if __name__ == "__main__":
    main()
