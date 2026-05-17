"""Categorical heatmap of cross-app state-coverage decisions.

Rows = state classes (normalised across the 6 fast-tier apps).
Columns = apps.
Each cell is colored by the (LLM, Reference) decision pair:
    Both save    → dark blue        (universal protection)
    LLM only     → orange            (LLM-distinctive: harness-induced or defensive)
    Reference only → green          (Reference-distinctive: trust-deterministic-init gap)
    Both skip    → light gray        (re-derivable, deterministic)
    Not applicable → white w/hatch  (state class does not exist in this app)

Saves PDF (vector) + PNG (300 DPI) to docs/figs/.
Companion analysis page: docs/llm_resilience_report/_state_coverage_matrix.md
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

# --- Inputs ---------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "docs" / "figs"
# Mirror PDFs into each active paper's Figures dir so the paper PDF always
# reflects the newest trusted results without a manual copy step.
PAPER_FIGURES_DIRS = [
    REPO_ROOT / "docs" / "paper" / "eScience" / "Figures",
]
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _mirror_to_papers(stem: str) -> None:
    """Copy <stem>.pdf from OUT_DIR into each active paper's Figures dir."""
    import shutil
    src = OUT_DIR / f"{stem}.pdf"
    if not src.exists():
        return
    for paper_dir in PAPER_FIGURES_DIRS:
        if paper_dir.exists():
            shutil.copy2(src, paper_dir / f"{stem}.pdf")

APPS = ["CoMD", "HPCG", "SPARTA", "Athena++", "CLAMR", "PRK_Stencil"]

# Decision codes:
#   "BB" = both save (☑/☑)
#   "LL" = LLM only saves (☑/☐)
#   "RR" = Reference only saves (☐/☑)
#   "NN" = both skip (☐/☐)
#   "--" = not applicable
ROWS = [
    ("A. Loop progress counter",        ["BB", "BB", "BB", "BB", "BB", "BB"]),
    ("B. Primary mutating arrays",      ["BB", "BB", "BB", "BB", "BB", "BB"]),
    ("C. Per-rank dynamic counts",      ["BB", "BB", "BB", "BB", "BB", "--"]),
    ("D. Sim time / dt",                ["NN", "NN", "BB", "BB", "BB", "NN"]),
    ("E. Conserved/diagnostic scalars", ["BB", "NN", "BB", "NN", "BB", "NN"]),
    ("F. Wall-time accumulators",       ["NN", "BB", "BB", "NN", "BB", "NN"]),
    ("G. RNG state",                    ["--", "--", "BB", "--", "--", "--"]),
    ("H. Solver tunables (defensive)",  ["--", "LL", "--", "--", "--", "--"]),
    ("I. Geometry / decomposition",     ["RR", "NN", "RR", "BB", "RR", "NN"]),
    ("J. Species / material tables",    ["RR", "--", "RR", "--", "--", "--"]),
    ("K. AMR mesh topology",            ["--", "--", "--", "BB", "NN", "--"]),
    ("L. Sparse matrix / multigrid",    ["--", "NN", "--", "--", "--", "--"]),
    ("M. Halo / ghost / MPI buffers",   ["NN", "--", "NN", "NN", "NN", "NN"]),
    ("N. Stdout / harness mirror",      ["NN", "NN", "LL", "NN", "NN", "NN"]),
    ("O. Restart-format header",        ["NN", "NN", "BB", "BB", "LL", "NN"]),
]

# Color-blind-safe palette (Wong 2011) — re-uses the same hex codes as the
# existing fast-tier bar-chart script for visual consistency across figures.
COLOR = {
    "BB": "#0072B2",   # dark blue — Both save (universal protection)
    "LL": "#E69F00",   # orange    — LLM-only (distinctive, often defensive)
    "RR": "#009E73",   # green     — Reference-only (LLM trusts re-init)
    "NN": "#EEEEEE",   # light gray — Both skip (re-derivable)
    "--": "#FFFFFF",   # white w/ hatch — Not applicable
}
LABEL = {
    "BB": "Both save",
    "LL": "LLM only",
    "RR": "Reference only",
    "NN": "Both skip",
    "--": "Not applicable",
}
SYMBOL = {
    "BB": "☑/☑",   # ☑/☑
    "LL": "☑/☐",   # ☑/☐
    "RR": "☐/☑",   # ☐/☑
    "NN": "☐/☐",   # ☐/☐
    "--": "—",            # —
}

# --- Plot styling (publication-grade) -------------------------------------
mpl.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif", "Times New Roman", "Times"],
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 11,
    "axes.linewidth": 0.8,
    "xtick.labelsize": 10,
    "ytick.labelsize": 9,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "legend.fontsize": 9,
    "legend.frameon": False,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.08,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


def main() -> None:
    n_rows = len(ROWS)
    n_cols = len(APPS)
    fig, ax = plt.subplots(figsize=(7.6, 5.6))

    # Draw cells one by one (avoids needing a colormap)
    for r, (_label, cells) in enumerate(ROWS):
        # Plot top-to-bottom: row 0 at the top.
        y = n_rows - 1 - r
        for c, code in enumerate(cells):
            face = COLOR[code]
            rect = mpatches.Rectangle(
                (c, y), 1, 1,
                facecolor=face, edgecolor="black", linewidth=0.4,
                hatch="////" if code == "--" else None,
            )
            ax.add_patch(rect)
            # Centered text symbol (white on dark blue, black elsewhere).
            # Render in sans-serif so the U+2610/U+2611 ballot-box glyphs
            # resolve (DejaVu Serif lacks them; DejaVu Sans has them).
            text_color = "white" if code == "BB" else "black"
            ax.text(c + 0.5, y + 0.5, SYMBOL[code],
                    ha="center", va="center",
                    fontsize=9, color=text_color,
                    fontfamily="DejaVu Sans")

    # Axes — categorical
    ax.set_xlim(0, n_cols)
    ax.set_ylim(0, n_rows)
    ax.set_xticks([c + 0.5 for c in range(n_cols)])
    ax.set_xticklabels(APPS, rotation=20, ha="right")
    ax.set_yticks([n_rows - 0.5 - r for r in range(n_rows)])
    ax.set_yticklabels([row[0] for row in ROWS])
    ax.tick_params(axis="x", which="both", length=0)
    ax.tick_params(axis="y", which="both", length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    # Legend below the heatmap, single row of five chips
    handles = []
    for code in ["BB", "LL", "RR", "NN", "--"]:
        handles.append(
            mpatches.Patch(
                facecolor=COLOR[code], edgecolor="black", linewidth=0.4,
                hatch="////" if code == "--" else None,
                label=f"{SYMBOL[code]}  {LABEL[code]}",
            )
        )
    legend = ax.legend(
        handles=handles,
        loc="upper center", bbox_to_anchor=(0.5, -0.10),
        ncol=5, frameon=True, fancybox=False, edgecolor="black",
        handlelength=1.4, handletextpad=0.5,
        columnspacing=1.2, borderpad=0.4,
    )
    # Match the in-cell symbol font so legend text contains valid glyphs too.
    for txt in legend.get_texts():
        txt.set_fontfamily("DejaVu Sans")

    fig.savefig(OUT_DIR / "fast_tier_state_coverage.pdf")
    fig.savefig(OUT_DIR / "fast_tier_state_coverage.png", dpi=300)
    plt.close(fig)
    _mirror_to_papers("fast_tier_state_coverage")

    # Console summary
    counts = {code: 0 for code in COLOR}
    for _, cells in ROWS:
        for c in cells:
            counts[c] += 1
    print("Cell counts:")
    for code in ["BB", "LL", "RR", "NN", "--"]:
        print(f"  {LABEL[code]:<18}  {counts[code]:>3d}  ({100*counts[code]/(n_rows*n_cols):.1f}%)")
    print(f"\nSaved: {OUT_DIR}/")
    for f in sorted(OUT_DIR.glob("fast_tier_state_coverage.*")):
        print(f"  {f.name}  ({f.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
