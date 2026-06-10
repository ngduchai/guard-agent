"""LoC vs total-tokens scatter, shape by model + color by complexity group.

One dot per (cell, TRUSTED-baseline app):
  * x = source-tree LoC (log scale)
  * y = total tokens consumed by the iter loop
  * color = complexity group (Plain Static / Plain Dynamic /
    Encapsulated / Modularized) — Tol muted palette
  * shape = model (Opus 4.7 = circle, Sonnet 4.6 = triangle-up,
    GPT-5.5 = square)

Unsuccessful runs are plotted with the SAME marker convention as
successful ones (color = group, shape = model); their token totals are
capped at the first ``DNC_CAP`` per_iteration entries (see ``_cells.py``).
The figure no longer encodes success/failure visually — every app dot
looks the same regardless of trust verdict.

Saves PDF (vector) + PNG (300 DPI) to docs/figs/ and mirrors the PDF
into each active paper's Figures dir.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.lines as mlines

from _cells import (
    CELLS,
    MODEL_COLORS,
    MODEL_LABELS,
    cell_dnc_dirs,
    cell_iter_logs,
    load_result,
    trusted_apps,
)

# --- Inputs ---------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "docs" / "figs"
PAPER_FIGURES_DIRS = [
    REPO_ROOT / "docs" / "paper" / "eScience" / "Figures",
]
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Per-app LoC and complexity groups — kept consistent with sibling scripts
# (single source of truth: APP_LOC and GROUPS are duplicated across the
# fast_tier_*.py family; any update must land in all of them in lock-step).
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
    "Plain Static":  ["HPCG", "PRK_Stencil", "SW4lite", "HyPar"],
    "Plain Dynamic": ["CoMD", "SPARTA", "SPPARKS", "CLAMR", "LAMMPS"],
    "Encapsulated":  ["Athena++", "WarpX", "OpenLB", "Smilei"],
    "Modularized":   ["Nyx", "ROSS", "SAMRAI", "QMCPACK"],
}
# Tol muted palette — visually disjoint from MODEL_COLORS so the
# group-color encoding does not collide with the per-model bar charts.
GROUP_COLORS = {
    "Plain Static":  "#88CCEE",   # Tol light cyan
    "Plain Dynamic": "#DDCC77",   # Tol sand
    "Encapsulated":  "#CC6677",   # Tol rose
    "Modularized":   "#AA4499",   # Tol violet
}


def _group_of(app: str) -> str | None:
    for label, apps in GROUPS.items():
        if app in apps:
            return label
    return None


def _load_tokens(source_dir: Path, *, is_dnc: bool) -> int | None:
    """Read unsuccessful-run-capped ``total_tokens`` from ``source_dir``."""
    res = load_result(source_dir, is_dnc=is_dnc)
    if res is None:
        return None
    return int(res["total_tokens"])


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


def _collect(cell: str, label: str) -> tuple[list, list, list, list]:
    """Return (successful_points, unsuccessful_points, dropped_not_trusted,
    dropped_no_result).

    Successful-run token totals come from ``cells_for(label, app)``:
    PS/PD/Enc apps average their tokens across all TRUSTED+CONDITIONAL_TRUSTED
    trials; Mod apps use the single first-run cell.  Apps with no
    successful trial fall back to the model anchor's DNC archive (the
    first-run failure data).
    """
    from _cells import cells_for
    dnc = cell_dnc_dirs(cell)
    points, dnc_points = [], []
    dropped_not_trusted, dropped_no_result = [], []
    for app, loc in APP_LOC.items():
        trial_cells = cells_for(label, app)
        if trial_cells:
            tks = []
            for c in trial_cells:
                iter_logs = cell_iter_logs(c)
                if not iter_logs.exists():
                    continue
                tk = _load_tokens(iter_logs / app, is_dnc=False)
                if tk is not None:
                    tks.append(tk)
            if not tks:
                dropped_no_result.append(app)
                continue
            avg_tk = sum(tks) / len(tks)
            points.append((app, loc, avg_tk / 1e6))
            continue
        # No successful trial -> fall back to the model anchor's DNC archive.
        if app in dnc:
            tk = _load_tokens(dnc[app], is_dnc=True)
            if tk is None:
                dropped_no_result.append(f"{app}(unsuccessful-missing)")
                continue
            dnc_points.append((app, loc, tk / 1e6))
            continue
        dropped_not_trusted.append(app)
    return points, dnc_points, dropped_not_trusted, dropped_no_result


def main() -> None:
    per_cell: dict[str, dict] = {}
    for cell_id, label, marker in CELLS:
        pts, dnc_pts, dropped_nt, dropped_nr = _collect(cell_id, label)
        print(f"[{cell_id} = {label}]")
        print(f"  [dropped non-TRUSTED]    {sorted(dropped_nt)}")
        print(f"  [dropped no result.json] {sorted(dropped_nr)}")
        print(f"  trusted={len(pts)}  unsuccessful={len(dnc_pts)}")
        per_cell[cell_id] = {"points": pts, "dnc": dnc_pts,
                             "label": label, "marker": marker}

    all_toks = [p[2] for c in per_cell.values()
                for p in c["points"] + c["dnc"]]

    fig, ax = plt.subplots(figsize=(3.8, 3.7))

    # Per-cell scatter — color encodes the complexity group; shape
    # encodes the model.  Successful and unsuccessful runs use the SAME
    # marker convention (no X-marker special case).  Size and edge stay
    # constant across both so visual encoding is purely (group, model).
    DOT_SIZE = 50
    for cell_id, label, marker in CELLS:
        cell_data = per_cell[cell_id]
        for app, loc, tk_m in (cell_data["points"] + cell_data["dnc"]):
            grp = _group_of(app)
            color = GROUP_COLORS.get(grp, "#777777")
            ax.scatter([loc], [tk_m], s=DOT_SIZE, marker=marker,
                       color=color, edgecolor="black", linewidth=0.5,
                       zorder=3)

    # Per-app text labels: one label per app, placed at the average of
    # whatever cell points exist for it (so the label sits between the
    # markers).  Unsuccessful markers count toward the average so apps
    # that are unsuccessful in one cell and TRUSTED in another still get
    # a single label between the two.
    by_app: dict[str, list[tuple[float, float]]] = {}
    for cell_id in (c[0] for c in CELLS):
        for app, loc, tk_m in (per_cell[cell_id]["points"]
                               + per_cell[cell_id]["dnc"]):
            by_app.setdefault(app, []).append((loc, tk_m))
    for app, locs in by_app.items():
        ax_loc = locs[0][0]  # LoC is the same across cells (same APP_LOC)
        ax_tk = sum(t for _, t in locs) / len(locs)
        ax.annotate(
            app,
            xy=(ax_loc, ax_tk),
            xytext=(4, 3),
            textcoords="offset points",
            fontsize=6.5,
            color="#222222",
            zorder=4,
        )

    ax.set_xscale("log")
    ax.set_xlabel("Source-tree size (LoC, log scale)")
    ax.set_ylabel("Total tokens (M)")
    ax.set_xlim(700, 1.0e6)
    _ymax = max(all_toks) if all_toks else 1.0
    ax.set_ylim(0, _ymax * 1.10)

    # Two-row legend above the plot:
    #   row 1 = group colors (4 entries)
    #   row 2 = model shapes (3 entries)
    # Group handles use a neutral filled circle to display color only;
    # model handles use a neutral gray fill to display shape only.
    group_handles = [
        mlines.Line2D([], [], marker="o", linestyle="",
                      color=GROUP_COLORS[g], markeredgecolor="black",
                      markersize=8, label=g)
        for g in GROUPS.keys()
    ]
    model_handles = []
    for cell_id, label, marker in CELLS:
        cell_data = per_cell[cell_id]
        has_data = bool(cell_data["points"] or cell_data["dnc"])
        # Keep GPT-5.5 (or any pending cell) in the legend with a faded
        # placeholder fill so the model-shape legend still reads the same
        # 3 entries the paper documents.
        face = "#bbbbbb" if has_data else "#cccccc"
        alpha = 1.0 if has_data else 0.30
        lbl = label if has_data else f"{label} (pending)"
        model_handles.append(
            mlines.Line2D([], [], marker=marker, linestyle="",
                          color=face, alpha=alpha,
                          markeredgecolor="black",
                          markersize=8, label=lbl)
        )
    leg1 = ax.legend(handles=group_handles,
                     loc="lower center", bbox_to_anchor=(0.5, 1.13),
                     ncol=len(group_handles), fontsize=7, frameon=False,
                     handletextpad=0.4, columnspacing=1.0)
    ax.add_artist(leg1)
    ax.legend(handles=model_handles,
              loc="lower center", bbox_to_anchor=(0.5, 1.01),
              ncol=len(model_handles), fontsize=7, frameon=False,
              handletextpad=0.4, columnspacing=1.0)

    fig.tight_layout()

    stem = "loc_vs_tokens"
    fig.savefig(OUT_DIR / f"{stem}.pdf", bbox_inches="tight",
                bbox_extra_artists=[leg1])
    fig.savefig(OUT_DIR / f"{stem}.png", dpi=300, bbox_inches="tight",
                bbox_extra_artists=[leg1])
    plt.close(fig)
    _mirror_to_papers(stem)
    print(f"\nSaved: {OUT_DIR}/{stem}.{{pdf,png}} (and mirrored)")


if __name__ == "__main__":
    main()
