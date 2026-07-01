"""Shared approach legend strip for Figure 3 (per-group resource panels).

The four subfigures in Fig 3 — code-gen+validation time (a), tokens (b),
API cost (c), and tokens-vs-LoC scatter (d) — all encode the same three
approaches by color (Opus 4.7, Sonnet 4.6, GPT-5.5).  Instead of
repeating a per-panel legend in each subfigure, this script renders one
horizontal three-entry legend that sits above the row of panels in
``main.tex`` (mirrors the pattern used by ``fast_tier_overhead_legend``
above Fig 4).

Output: ``docs/figs/fast_tier_approach_legend.{pdf,png}`` (mirrored
into ``docs/paper/eScience/Figures/``).
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
    """One patch per model in CELLS order, color-keyed to MODEL_COLORS."""
    return [
        mpatches.Patch(facecolor=MODEL_COLORS[cell_id],
                       edgecolor="black", linewidth=0.5,
                       label=MODEL_LABELS[cell_id])
        for cell_id, _label, _marker in CELLS
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
    fig, ax = plt.subplots(figsize=(6.5, 0.45))
    ax.set_axis_off()
    ax.legend(
        handles=_approach_handles(),
        loc="center",
        ncol=len(CELLS),
        fontsize=9,
        frameon=True, fancybox=False, edgecolor="black",
        handlelength=1.2, handletextpad=0.4,
        columnspacing=1.5, borderpad=0.4,
    )
    stem = "fast_tier_approach_legend"
    fig.savefig(OUT_DIR / f"{stem}.pdf", bbox_inches="tight", pad_inches=0.02)
    fig.savefig(OUT_DIR / f"{stem}.png", dpi=300, bbox_inches="tight",
                pad_inches=0.02)
    _mirror_to_papers(stem)
    plt.close(fig)
    print(f"Saved: {OUT_DIR}/{stem}.{{pdf,png}} (and mirrored)")


if __name__ == "__main__":
    main()
