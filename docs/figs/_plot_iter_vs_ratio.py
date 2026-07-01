"""Iteration count vs LLM/reference checkpoint-size ratio.

Tests the hypothesis: does an LLM that struggled (high iter count) tend
to give up on selectivity and dump everything, producing a larger
checkpoint relative to the upstream reference?

One scatter point per (model, app) cell with TRUSTED bench data and a
non-zero reference per-frame size.  X = number of iterations the iter
loop took to converge on that cell (from result.json, capped at the
DNC cap when applicable, matching Table II).  Y = LLM per-frame size /
reference per-frame size, log axis.  Color encodes model; marker shape
encodes complexity group.  Spearman rho is reported per model and
overall in the legend.

Saves PDF + PNG to docs/figs/ and mirrors the PDF into each active
paper's Figures dir.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

from _cells import (
    CELLS,
    MODEL_COLORS,
    MODEL_LABELS,
    cell_bench,
    cell_iter_logs,
    load_result,
    trusted_apps,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "docs" / "figs"
REF_DIR = REPO_ROOT / "build" / "validation_output"
PAPER_FIGURES_DIRS = [
    REPO_ROOT / "docs" / "paper" / "eScience" / "Figures",
]
OUT_DIR.mkdir(parents=True, exist_ok=True)


# Same grouping as the other paper figures.
GROUPS = {
    "Plain Static":    ["HPCG", "PRK_Stencil", "SW4lite", "HyPar"],
    "Plain Dynamic":   ["CoMD", "SPARTA", "SPPARKS", "CLAMR", "LAMMPS"],
    "Encapsulated":    ["Athena++", "WarpX", "OpenLB", "Smilei"],
    "Modularized":     ["Nyx", "ROSS", "SAMRAI", "QMCPACK"],
}
GROUP_MARKERS = {
    "Plain Static":  "o",
    "Plain Dynamic": "s",
    "Encapsulated":  "^",
    "Modularized":   "D",
}
APP_TO_GROUP = {a: g for g, apps in GROUPS.items() for a in apps}


def _per_frame_bytes(raw: dict, codebase: str) -> float | None:
    runs = [r for r in raw.get("runs", [])
            if r.get("codebase") == codebase
            and not r.get("injected")
            and r.get("checkpoint_per_frame_bytes")]
    if not runs:
        return None
    return statistics.median(r["checkpoint_per_frame_bytes"] for r in runs)


def _spearman(xs, ys):
    """Spearman rank correlation; returns rho or None if n < 3."""
    n = len(xs)
    if n < 3:
        return None

    def _rank(vals):
        order = sorted(range(n), key=lambda i: vals[i])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0  # 1-indexed average rank for ties
            for k in range(i, j + 1):
                ranks[order[k]] = avg
            i = j + 1
        return ranks

    rx, ry = _rank(xs), _rank(ys)
    mx = sum(rx) / n
    my = sum(ry) / n
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    dx = (sum((rx[i] - mx) ** 2 for i in range(n))) ** 0.5
    dy = (sum((ry[i] - my) ** 2 for i in range(n))) ** 0.5
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def _mirror_to_papers(stem: str) -> None:
    import shutil
    src = OUT_DIR / f"{stem}.pdf"
    if not src.exists():
        return
    for paper_dir in PAPER_FIGURES_DIRS:
        if paper_dir.exists():
            shutil.copy2(src, paper_dir / f"{stem}.pdf")


mpl.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif", "Times New Roman", "Times"],
    "font.size": 12,
    "axes.titlesize": 11,
    "axes.labelsize": 12,
    "axes.linewidth": 0.8,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "legend.fontsize": 9,
    "legend.frameon": True,
    "legend.fancybox": False,
    "axes.grid": True,
    "grid.alpha": 0.35,
    "grid.linestyle": "--",
    "grid.linewidth": 0.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.10,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


def _collect_points():
    """Yield (cell_id, app, iters, ratio) for each TRUSTED (model, app) cell
    where both an LLM and reference per-frame size are available."""
    trusted_by_cell = {c[0]: trusted_apps(c[0]) for c in CELLS}
    ref_cache: dict[str, float] = {}

    def _ref_for(app: str) -> float | None:
        if app in ref_cache:
            return ref_cache[app]
        p = REF_DIR / f"{app}_reference" / "benchmarks" / "raw_metrics.json"
        if not p.exists():
            ref_cache[app] = None
            return None
        raw = json.loads(p.read_text())
        val = (_per_frame_bytes(raw, "reference")
               or _per_frame_bytes(raw, "resilient"))
        ref_cache[app] = val
        return val

    for cell_id, label, _marker in CELLS:
        iter_root = cell_iter_logs(cell_id)
        if not iter_root.exists():
            continue
        for app in trusted_by_cell[cell_id]:
            # Iter count from this cell's result.json for this app.
            res = load_result(iter_root / app, is_dnc=False)
            if res is None or res.get("iterations") in (None, 0):
                continue
            iters = int(res["iterations"])
            # LLM per-frame bytes from the same cell's bench.
            bp = cell_bench(cell_id, app) / "benchmarks" / "raw_metrics.json"
            if not bp.exists():
                continue
            braw = json.loads(bp.read_text())
            llm_pf = _per_frame_bytes(braw, "resilient")
            ref_pf = _ref_for(app)
            if not llm_pf or not ref_pf:
                continue
            yield (cell_id, app, iters, llm_pf / ref_pf)


def main() -> None:
    points = list(_collect_points())
    if not points:
        print("No data points found.")
        return

    print(f"Collected {len(points)} (model, app) points:")
    by_cell: dict[str, list[tuple[str, int, float]]] = {c[0]: [] for c in CELLS}
    for cell_id, app, iters, ratio in points:
        by_cell[cell_id].append((app, iters, ratio))
        grp = APP_TO_GROUP.get(app, "?")
        print(f"  {cell_id:<14} {app:<14} iters={iters:>2}  "
              f"ratio={ratio:>10.3f}×  group={grp}")

    fig, ax = plt.subplots(figsize=(7.0, 4.5))

    # Scatter per (model, app), colored by model, shaped by group.
    for cell_id, label, _marker in CELLS:
        color = MODEL_COLORS[cell_id]
        for app, iters, ratio in by_cell[cell_id]:
            grp = APP_TO_GROUP.get(app, "Plain Static")
            mk = GROUP_MARKERS[grp]
            ax.scatter(iters, ratio, color=color, marker=mk,
                       s=70, edgecolor="black", linewidth=0.6,
                       zorder=3, alpha=0.85)

    # Per-model Spearman rho (rank correlation) + overall.
    per_model_rho = {}
    for cell_id, label, _marker in CELLS:
        rows = by_cell[cell_id]
        if len(rows) < 3:
            per_model_rho[cell_id] = None
            continue
        per_model_rho[cell_id] = _spearman(
            [r[1] for r in rows], [r[2] for r in rows])
    overall_rho = _spearman(
        [p[2] for p in points], [p[3] for p in points])

    print("\nSpearman rank correlation (iter count vs size ratio):")
    for cell_id, label, _marker in CELLS:
        rho = per_model_rho[cell_id]
        nshow = len(by_cell[cell_id])
        s = f"{rho:+.2f}" if rho is not None else "  n/a"
        print(f"  {MODEL_LABELS[cell_id]:<12} rho={s}  (n={nshow})")
    print(f"  Overall      rho={overall_rho:+.2f}  (n={len(points)})")

    # Parity line at ratio = 1.
    ax.axhline(1.0, color="0.4", linestyle=":", linewidth=0.8, zorder=1)
    ax.text(0.5, 1.15, "Reference parity ($1\\times$)",
            color="0.4", fontsize=8, ha="left")

    ax.set_yscale("log")
    ax.set_xlabel("Iterations to converge")
    ax.set_ylabel("LLM checkpoint size / Reference (log)")
    # X axis: integer ticks 1..10 with a little margin on the left.
    iter_max = max(p[2] for p in points)
    ax.set_xlim(0.5, iter_max + 0.5)
    ax.set_xticks(range(1, iter_max + 1))

    # Legends:  (a) model legend with per-model Spearman in the label;
    #           (b) group-marker legend.
    from matplotlib.lines import Line2D
    model_handles = []
    for cell_id, label, _marker in CELLS:
        rho = per_model_rho[cell_id]
        rho_txt = f"$\\rho={rho:+.2f}$" if rho is not None else "$\\rho$=n/a"
        nshow = len(by_cell[cell_id])
        model_handles.append(Line2D(
            [0], [0], marker="o", color="none",
            markerfacecolor=MODEL_COLORS[cell_id],
            markeredgecolor="black", markeredgewidth=0.6,
            markersize=8,
            label=f"{MODEL_LABELS[cell_id]} ({rho_txt}, n={nshow})"))
    group_handles = [
        Line2D([0], [0], marker=GROUP_MARKERS[g], color="none",
               markerfacecolor="0.7", markeredgecolor="black",
               markeredgewidth=0.6, markersize=8, label=g)
        for g in GROUPS.keys()
    ]
    leg1 = ax.legend(handles=model_handles, loc="upper left",
                     fontsize=9, edgecolor="black", borderpad=0.4,
                     handletextpad=0.5)
    ax.add_artist(leg1)
    ax.legend(handles=group_handles, loc="lower right",
              fontsize=8, edgecolor="black", borderpad=0.4,
              handletextpad=0.5, title="Complexity group",
              title_fontsize=8)

    fig.tight_layout()
    stem = "fast_tier_iter_vs_ckpt_ratio"
    fig.savefig(OUT_DIR / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(OUT_DIR / f"{stem}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    _mirror_to_papers(stem)
    print(f"\nSaved: {OUT_DIR}/{stem}.{{pdf,png}} (and mirrored)")


if __name__ == "__main__":
    main()
