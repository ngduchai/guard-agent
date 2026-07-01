"""Modified-LoC percentage vs total-tokens scatter — shape by model, color by group.

Companion to ``_plot_loc_vs_tokens.py``: same visual encoding (color =
complexity group, shape = model; no success/failure differentiation),
but the x-axis is the fraction of the source tree the LLM actually
rewrote to make it resilient.  Modified LoC = ``added + removed`` lines
in the unified diff between the vanilla tree
(``tests/apps/vanillas/<APP>/``) and the LLM-modified tree
(``results/models/<cell>/source/<APP>/``); binary files and hunk/file
headers are excluded.  The percentage is ``100 * modified_loc / APP_LOC``.

Saves PDF (vector) + PNG (300 DPI) to docs/figs/ and mirrors the PDF
into each active paper's Figures dir.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.lines as mlines

from _cells import (
    CELLS,
    MODEL_COLORS,
    MODEL_LABELS,
    cell_dnc_dirs,
    cell_dnc_source,
    cell_iter_logs,
    cell_source_root,
    load_result,
    trusted_apps,
)

# --- Inputs ---------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
VANILLA_SOURCE = REPO_ROOT / "tests" / "apps" / "vanillas"
OUT_DIR = REPO_ROOT / "docs" / "figs"
PAPER_FIGURES_DIRS = [
    REPO_ROOT / "docs" / "paper" / "eScience" / "Figures",
]
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Per-app LoC and complexity groups — kept consistent with sibling scripts.
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
# Tol muted palette — visually disjoint from MODEL_COLORS.
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
    res = load_result(source_dir, is_dnc=is_dnc)
    if res is None:
        return None
    return int(res["total_tokens"])


def _load_modified_loc(app: str, llm_dir: Path) -> int | None:
    """Count added+removed lines between vanilla and the LLM tree.

    Runs ``diff -ruN <vanilla> <llm>`` and tallies any line starting
    with ``+`` or ``-`` that is not a file-header line (``+++``/``---``)
    and is not part of a binary-file marker.  Returns None if either
    tree is missing.
    """
    v = VANILLA_SOURCE / app
    if not v.is_dir() or not llm_dir.is_dir():
        return None
    proc = subprocess.run(
        ["diff", "-ruN", str(v), str(llm_dir)],
        capture_output=True, text=True, errors="replace",
    )
    added = removed = 0
    for line in proc.stdout.splitlines():
        if not line:
            continue
        if line.startswith("Binary files"):
            continue
        if line.startswith("+++ ") or line.startswith("--- "):
            continue
        if line[0] == "+":
            added += 1
        elif line[0] == "-":
            removed += 1
    return added + removed


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


def _collect(cell: str):
    """Return (trusted_points, unsuccessful_points, dropped_*).

    Each point tuple = (app, pct, tokens_M, mod_loc).
    """
    trusted = trusted_apps(cell)
    dnc = cell_dnc_dirs(cell)
    iter_logs = cell_iter_logs(cell)
    src_root = cell_source_root(cell)
    points, dnc_points = [], []
    dropped_not_trusted, dropped_no_result, dropped_no_source = [], [], []
    for app, loc in APP_LOC.items():
        if app in dnc:
            tk = _load_tokens(dnc[app], is_dnc=True)
            if tk is None:
                dropped_no_result.append(f"{app}(unsuccessful-missing)")
                continue
            llm_dir = cell_dnc_source(cell, app)
            if llm_dir is None or not llm_dir.is_dir():
                dropped_no_source.append(f"{app}(unsuccessful-source-missing)")
                continue
            mod = _load_modified_loc(app, llm_dir)
            if mod is None:
                dropped_no_source.append(f"{app}(unsuccessful-source-missing)")
                continue
            pct = 100.0 * mod / loc
            dnc_points.append((app, pct, tk / 1e6, mod))
            continue
        if app not in trusted:
            dropped_not_trusted.append(app)
            continue
        if not iter_logs.exists():
            dropped_no_result.append(app)
            continue
        tk = _load_tokens(iter_logs / app, is_dnc=False)
        if tk is None:
            dropped_no_result.append(app)
            continue
        mod = _load_modified_loc(app, src_root / app)
        if mod is None:
            dropped_no_source.append(app)
            continue
        pct = 100.0 * mod / loc
        points.append((app, pct, tk / 1e6, mod))
    return points, dnc_points, dropped_not_trusted, dropped_no_result, dropped_no_source


def main() -> None:
    per_cell: dict[str, dict] = {}
    for cell_id, label, marker in CELLS:
        pts, dnc_pts, dnt, dnr, dns = _collect(cell_id)
        print(f"[{cell_id} = {label}]")
        print(f"  [dropped non-TRUSTED]    {sorted(dnt)}")
        print(f"  [dropped no result.json] {sorted(dnr)}")
        print(f"  [dropped no source dir]  {sorted(dns)}")
        for app, pct, tk_m, mod in sorted(pts + dnc_pts, key=lambda p: p[1]):
            tag = "UNSUCC " if (app, pct, tk_m, mod) in dnc_pts else "TRUSTED"
            print(f"  [{tag}] {app:<12}  mod_loc={mod:>5}  app_loc={APP_LOC[app]:>7,}  "
                  f"pct={pct:6.2f}%  tokens={tk_m:5.1f}M")
        per_cell[cell_id] = {"points": pts, "dnc": dnc_pts,
                             "label": label, "marker": marker}

    all_toks = [p[2] for c in per_cell.values()
                for p in c["points"] + c["dnc"]]
    all_pcts = [p[1] for c in per_cell.values()
                for p in c["points"] + c["dnc"]]

    # --- Figure ----------------------------------------------------------
    fig, ax = plt.subplots(figsize=(3.8, 3.7))
    DOT_SIZE = 50
    for cell_id, label, marker in CELLS:
        cell_data = per_cell[cell_id]
        for app, pct, tk_m, _mod in (cell_data["points"] + cell_data["dnc"]):
            grp = _group_of(app)
            color = GROUP_COLORS.get(grp, "#777777")
            ax.scatter([pct], [tk_m], s=DOT_SIZE, marker=marker,
                       color=color, edgecolor="black", linewidth=0.5,
                       zorder=3)

    # Per-app labels at the average pct/tokens across both cells.
    by_app: dict[str, list[tuple[float, float]]] = {}
    for cell_id in (c[0] for c in CELLS):
        for app, pct, tk_m, _m in (per_cell[cell_id]["points"]
                                   + per_cell[cell_id]["dnc"]):
            by_app.setdefault(app, []).append((pct, tk_m))
    for app, vals in by_app.items():
        ax_pct = sum(p for p, _ in vals) / len(vals)
        ax_tk = sum(t for _, t in vals) / len(vals)
        ax.annotate(
            app,
            xy=(ax_pct, ax_tk),
            xytext=(4, 3),
            textcoords="offset points",
            fontsize=6.5,
            color="#222222",
            zorder=4,
        )

    ax.set_xscale("log")
    ax.set_xlabel("Source modified by LLM (% of LoC, log scale)")
    ax.set_ylabel("Total tokens (M)")
    lo = min(all_pcts) if all_pcts else 0.05
    hi = max(all_pcts) if all_pcts else 20.0
    ax.set_xlim(lo / 1.8, hi * 1.8)
    _ymax = max(all_toks) if all_toks else 1.0
    ax.set_ylim(0, _ymax * 1.10)

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

    stem = "modpct_vs_tokens"
    fig.savefig(OUT_DIR / f"{stem}.pdf", bbox_inches="tight",
                bbox_extra_artists=[leg1])
    fig.savefig(OUT_DIR / f"{stem}.png", dpi=300, bbox_inches="tight",
                bbox_extra_artists=[leg1])
    plt.close(fig)
    _mirror_to_papers(stem)
    print(f"\nSaved: {OUT_DIR}/{stem}.{{pdf,png}} (and mirrored)")


if __name__ == "__main__":
    main()
