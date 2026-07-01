"""Publication-quality bar charts of LLM-iter-loop metrics (multi-model).

Saves PDF (vector) + PNG (300 DPI) for each metric to docs/figs/.

For every TRUSTED-baseline app, one bar per model is drawn side-by-side
in the model's color (Opus blue, Sonnet vermillion, GPT-5.5 green).
Stacked decompositions inside each bar are preserved (e.g. LLM vs
validation time, input vs output tokens) but rendered in tints of the
model color so the model identity stays the dominant visual signal.
Unsuccessful apps use the existing diagonal-hatch overlay as the
unsuccessful-run indicator; per-model fill is the same model color and
metric values are capped at the first ``DNC_CAP`` iterations (see
_cells.py).

The COMPLETED_APPS list is the candidate set; the actual plotted set
is the UNION of cells' TRUSTED-baseline apps (plus unsuccessful apps
with result.json on disk) so an app TRUSTED in only one cell still
appears
(the missing cell renders no bar at that slot).  GPT-5.5 is included
as a placeholder slot — when no result.json exists, a thin gray "N/A"
bar is drawn so readers see the slot reserved.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

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
CONFIGS = REPO_ROOT / "tests" / "apps" / "configs"
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


# 17-app candidate set (MMSP removed per user instruction 2026-05-08).
# Actual plotted set is filtered against _trust.json at runtime.
COMPLETED_APPS = [
    "Athena++", "CLAMR", "CoMD", "HPCG", "HyPar",
    "LAMMPS", "Nyx", "OpenLB", "PRK_Stencil",
    "QMCPACK", "ROSS", "SAMRAI", "Smilei", "SPARTA",
    "SPPARKS", "SW4lite", "WarpX",
]

# Per-app LOC, sourced from the paper's tab:apps (\S\ref{sec:suite}).
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

# X-axis grouping: apps clustered by complexity group; within each group
# apps are ordered by INCREASING LOC (smallest codebase first).
_GROUPS_RAW = {
    "Plain Static":              ["HPCG", "PRK_Stencil", "SW4lite", "HyPar"],
    "Plain Dynamic":        ["CoMD", "SPARTA", "SPPARKS", "CLAMR", "LAMMPS"],
    "Encapsulated":  ["Athena++", "WarpX", "OpenLB", "Smilei"],
    "Modularized":   ["Nyx", "ROSS", "SAMRAI", "QMCPACK"],
}
GROUPS = {
    label: sorted(apps, key=lambda a: APP_LOC.get(a, float("inf")))
    for label, apps in _GROUPS_RAW.items()
}
DIFFICULTY_ORDER = [app for apps in GROUPS.values() for app in apps]


def _group_boundaries(plotted_apps: list[str]) -> list[int]:
    out, c = [], 0
    for apps in GROUPS.values():
        c += sum(1 for a in apps if a in plotted_apps)
        out.append(c)
    return out[:-1]


def _draw_group_separators(ax, plotted_apps: list[str]) -> None:
    n_apps = len(plotted_apps)
    bounds = _group_boundaries(plotted_apps)
    for b in bounds:
        if 0 < b < n_apps:
            ax.axvline(b - 0.5, color="#aaaaaa", linewidth=0.5,
                       linestyle="--", zorder=0)
    ymin, ymax = ax.get_ylim()
    band_y = ymax * 0.95
    rank = {a: i for i, a in enumerate(plotted_apps)}
    for label, apps in GROUPS.items():
        idxs = [rank[a] for a in apps if a in rank]
        if not idxs:
            continue
        center = (min(idxs) + max(idxs)) / 2.0
        ax.text(center, band_y, label, fontsize=11, ha="center", va="top",
                style="italic", color="#555555")


def load_app(app: str, *, source_dir: Path | None = None,
             iter_logs_root: Path | None = None,
             is_dnc: bool = False) -> dict | None:
    """Return per-app metrics or None if no result.json on disk.

    `source_dir` overrides the cell's iter-logs lookup for unsuccessful
    apps whose iter logs live under an archive dir.  Otherwise the
    per-cell iter logs root is used: ``iter_logs_root/<app>/result.json``.

    `is_dnc=True` activates the unsuccessful-run iteration cap on every
    metric (see ``_cells.load_result``).
    """
    if source_dir is not None:
        base = source_dir
    else:
        assert iter_logs_root is not None
        base = iter_logs_root / app
    res = load_result(base, is_dnc=is_dnc)
    if res is None:
        return None

    cfg_path = CONFIGS / f"{app}.yaml"
    category = next(
        (line.split(":", 1)[1].strip() for line in cfg_path.read_text().splitlines()
         if line.startswith("category:")),
        "unknown",
    )
    wall_s = res["wall_elapsed_s"]
    oc_s   = res["total_opencode_elapsed_s"]
    vd_s   = res["total_validation_elapsed_s"]
    if oc_s == 0 and vd_s == 0:
        oc_s = vd_s = wall_s / 2.0
    in_tok  = res["total_input_tokens"]
    out_tok = res["total_output_tokens"]
    if in_tok == 0 and out_tok == 0:
        total = res["total_tokens"]
        in_tok, out_tok = int(total * 0.95), total - int(total * 0.95)
    return {
        "app": app,
        "category": category,
        "wall_min":     wall_s / 60.0,
        "opencode_min": oc_s   / 60.0,
        "validate_min": vd_s   / 60.0,
        "iters": int(res["iterations"]),
        "tokens_M":         res["total_tokens"] / 1e6,
        "input_tokens_M":   in_tok / 1e6,
        "output_tokens_M":  out_tok / 1e6,
    }


def _collect_cell(cell: str) -> tuple[dict[str, dict], set[str]]:
    """Return ``({app: metrics_dict}, hatched_set)`` for ``cell``.

    `hatched_set` contains unsuccessful apps so the renderer can overlay
    the diagonal hatch on their bars.  Returns empty dicts for
    placeholder cells (e.g. GPT-5.5) whose iter_logs dir does not exist.
    """
    out: dict[str, dict] = {}
    hatched: set[str] = set()
    trusted = trusted_apps(cell)
    iter_root = cell_iter_logs(cell)
    dnc = cell_dnc_dirs(cell)
    for app in COMPLETED_APPS:
        if app in dnc:
            m = load_app(app, source_dir=dnc[app], is_dnc=True)
            if m is not None:
                out[app] = m
                hatched.add(app)
            continue
        if app not in trusted:
            continue
        if not iter_root.exists():
            continue
        m = load_app(app, iter_logs_root=iter_root, is_dnc=False)
        if m is not None:
            out[app] = m
    return out, hatched


# --- Plot styling (publication-grade) -------------------------------------
mpl.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif", "Times New Roman", "Times"],
    "font.size": 14,
    "axes.titlesize": 13,
    "axes.labelsize": 14,
    "axes.linewidth": 0.8,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "legend.fontsize": 12,
    "legend.frameon": False,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "grid.alpha": 0.35,
    "grid.linestyle": "--",
    "grid.linewidth": 0.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.08,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


# Unsuccessful-run hatch overlay (independent of model).
DNC_HATCH = "////"
# Placeholder bar height for a missing cell (e.g. GPT-5.5 today).  The bar
# is rendered in the cell's own MODEL_COLORS hue at PLACEHOLDER_ALPHA so the
# reader sees the slot is reserved for that specific model — not confused
# with vanilla's neutral gray.
PLACEHOLDER_ALPHA = 0.30
PLACEHOLDER_HEIGHT_FRAC = 0.015  # 1.5% of axis height — visible but not loud


def _lighten(hex_color: str, frac: float) -> str:
    """Mix ``hex_color`` with white by ``frac`` (0 = original, 1 = white).

    Used to derive the "second segment" tint of stacked bars so both
    segments stay recognisably the model color but the segments are
    distinguishable from each other.
    """
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r = int(r + (255 - r) * frac)
    g = int(g + (255 - g) * frac)
    b = int(b + (255 - b) * frac)
    return f"#{r:02x}{g:02x}{b:02x}"


def plot_metric(
    per_cell_apps: dict[str, dict[str, dict]], *,
    ordered_apps: list[str],
    hatched_per_cell: dict[str, set[str]],
    ylabel: str, fname_stem: str,
    value_key: str | None = None,
    stacked: list[tuple[str, str]] | None = None,   # (key, legend_label)
    integer_yticks: bool = False,
) -> None:
    """Render a multi-model bar chart.

    ``per_cell_apps[cell_id][app]`` -> metrics dict from ``load_app``.
    For each app one bar per model is drawn side-by-side, colored by
    that model.  Missing per-(cell, app) entries render a thin gray
    placeholder bar so the GPT-5.5 slot stays visible while data is
    pending; the legend lists every cell regardless of data presence.
    Stacked decompositions use two tints of the model color (base for
    the bottom segment, lighter for the top).
    """
    assert (value_key is None) ^ (stacked is None), \
        "exactly one of value_key / stacked must be supplied"

    n_cells = len(CELLS)
    # 60% of each app slot is the cluster of n_cells bars; 40% is the gap
    # between consecutive apps so each app's bar group reads as a distinct
    # unit.  Applies uniformly across 2-cell and 3-cell layouts.
    cluster_w = 0.60
    bar_w = cluster_w / n_cells
    cell_offsets = {
        cell_id: (i - (n_cells - 1) / 2) * bar_w
        for i, (cell_id, _label, _marker) in enumerate(CELLS)
    }

    fig_w = max(9.0, 0.55 * len(ordered_apps) + 1.6)
    fig, ax = plt.subplots(figsize=(fig_w, 3.6))

    x_centres = list(range(len(ordered_apps)))
    max_y = 0.0

    # First pass: real bars + track max for placeholder sizing.
    for cell_id, _label, _marker in CELLS:
        cell_apps = per_cell_apps[cell_id]
        base_color = MODEL_COLORS[cell_id]
        light_color = _lighten(base_color, 0.45)
        hatched_dnc = hatched_per_cell[cell_id]
        x_off = cell_offsets[cell_id]
        for xi, app in zip(x_centres, ordered_apps):
            metrics = cell_apps.get(app)
            if metrics is None:
                continue
            h = DNC_HATCH if app in hatched_dnc else None
            x = xi + x_off
            if value_key is not None:
                v = metrics[value_key]
                ax.bar(x, v, width=bar_w, color=base_color,
                       hatch=h, edgecolor="black", linewidth=0.6)
                max_y = max(max_y, v)
            else:
                bottom = 0.0
                for seg_idx, (key, _legend_label) in enumerate(stacked):
                    seg = metrics[key]
                    seg_color = base_color if seg_idx == 0 else light_color
                    ax.bar(x, seg, width=bar_w, bottom=bottom,
                           color=seg_color, hatch=h,
                           edgecolor="black", linewidth=0.6)
                    bottom += seg
                max_y = max(max_y, bottom)

    # Second pass: placeholder bars for missing cells (GPT-5.5 today).
    # Render in the cell's own MODEL_COLORS hue at PLACEHOLDER_ALPHA so the
    # reader sees the slot is reserved for THAT model (the green stays green
    # for GPT-5.5, distinct from vanilla's neutral gray).
    placeholder_h = max_y * PLACEHOLDER_HEIGHT_FRAC if max_y else 0.05
    for cell_id, _label, _marker in CELLS:
        cell_apps = per_cell_apps[cell_id]
        x_off = cell_offsets[cell_id]
        # Only emit placeholders if the cell has NO data anywhere on this
        # chart — otherwise per-app gaps stay silent (existing convention).
        if cell_apps:
            continue
        ph_color = MODEL_COLORS[cell_id]
        for xi, _app in zip(x_centres, ordered_apps):
            ax.bar(xi + x_off, placeholder_h, width=bar_w,
                   color=ph_color, alpha=PLACEHOLDER_ALPHA,
                   edgecolor=ph_color, linewidth=0.5, zorder=1)

    ax.set_xticks(x_centres)
    ax.set_xticklabels(ordered_apps, rotation=20, ha="right", fontsize=11)
    # Italic-red x-tick label when the app is unsuccessful in EVERY
    # cell that has data.
    for tlbl, app in zip(ax.get_xticklabels(), ordered_apps):
        cells_with_data = [c for c, _, _ in CELLS
                           if app in per_cell_apps[c]]
        if cells_with_data and all(app in hatched_per_cell[c]
                                   for c in cells_with_data):
            tlbl.set_color("#990000")
            tlbl.set_fontstyle("italic")

    ax.set_ylabel(ylabel)
    ax.set_ylim(0, max_y * (1.20 if value_key is not None else 1.30))
    ax.set_xlim(-0.6, len(ordered_apps) - 0.4)

    if integer_yticks:
        ax.yaxis.set_major_locator(mpl.ticker.MaxNLocator(integer=True))

    # Legend: stacked-segment swatches (model-agnostic, in the lighter
    # tint of the first model's color so segment ordering is shown) +
    # one swatch per model in its full color + unsuccessful-run overlay.
    handles: list[mpatches.Patch] = []
    if stacked is not None:
        # Use the first cell with data for the segment-color reference;
        # fall back to the first cell in CELLS if none have data.
        ref_cell = next(
            (cid for cid, _, _ in CELLS if per_cell_apps.get(cid)),
            CELLS[0][0],
        )
        base = MODEL_COLORS[ref_cell]
        light = _lighten(base, 0.45)
        seg_colors = [base, light]
        for (key, legend_label), seg_color in zip(stacked, seg_colors):
            handles.append(
                mpatches.Patch(facecolor=seg_color, edgecolor="black",
                               linewidth=0.5, label=legend_label))
    for cell_id, cell_label, _marker in CELLS:
        cell_apps = per_cell_apps[cell_id]
        label = cell_label if cell_apps else f"{cell_label} (pending)"
        face = MODEL_COLORS[cell_id]
        alpha = 1.0 if cell_apps else PLACEHOLDER_ALPHA
        handles.append(
            mpatches.Patch(facecolor=face, alpha=alpha,
                           edgecolor="black", linewidth=0.5,
                           label=label))
    any_dnc = any(hatched_per_cell[c[0]] for c in CELLS)
    if any_dnc:
        handles.append(
            mpatches.Patch(facecolor="#dddddd", hatch=DNC_HATCH,
                           edgecolor="black", linewidth=0.5,
                           label="Unsuccessful"))
    # Legend goes ABOVE the plot area so it never collides with the
    # in-plot group-label band (Plain Static / Plain Dynamic / etc.)
    # at the top of the axes.
    ax.legend(handles=handles,
              loc="lower center", bbox_to_anchor=(0.5, 1.02),
              fontsize=11,
              frameon=True, fancybox=False, edgecolor="black",
              handlelength=1.2, handletextpad=0.5,
              labelspacing=0.35, borderpad=0.4,
              columnspacing=1.2,
              ncol=min(len(handles), 5))

    _draw_group_separators(ax, ordered_apps)

    fig.savefig(OUT_DIR / f"{fname_stem}.pdf")
    fig.savefig(OUT_DIR / f"{fname_stem}.png", dpi=300)
    plt.close(fig)
    _mirror_to_papers(fname_stem)


def main() -> None:
    per_cell_apps: dict[str, dict[str, dict]] = {}
    hatched_per_cell: dict[str, set[str]] = {}
    for cell_id, label, _marker in CELLS:
        apps_map, hatched = _collect_cell(cell_id)
        per_cell_apps[cell_id] = apps_map
        hatched_per_cell[cell_id] = hatched
        print(f"[{cell_id} = {label}]  trusted+unsuccessful={len(apps_map)} apps "
              f"(unsuccessful: {sorted(hatched)})")

    # Ordered union of apps appearing in any cell, ranked by difficulty.
    union: set[str] = set()
    for cell_id in (c[0] for c in CELLS):
        union.update(per_cell_apps[cell_id].keys())
    rank = {name: i for i, name in enumerate(DIFFICULTY_ORDER)}
    ordered_apps = sorted(union, key=lambda a: rank.get(a, len(rank)))
    print(f"Plotting {len(ordered_apps)} apps in union order: {ordered_apps}")

    # Wall-clock chart — stacked: code-generation (LLM-side) at the bottom,
    # validation (independent build/run/compare) on top.
    plot_metric(
        per_cell_apps,
        ordered_apps=ordered_apps,
        hatched_per_cell=hatched_per_cell,
        stacked=[
            ("opencode_min", "Code generation"),
            ("validate_min", "Validation"),
        ],
        ylabel="Code generation time (min)",
        fname_stem="fast_tier_iter_walltime",
    )
    # Iter count — single bar.
    plot_metric(
        per_cell_apps,
        ordered_apps=ordered_apps,
        hatched_per_cell=hatched_per_cell,
        value_key="iters",
        ylabel="Iterations to success",
        fname_stem="fast_tier_iter_count",
        integer_yticks=True,
    )
    # Token chart — stacked: input tokens on the bottom, output tokens on top.
    plot_metric(
        per_cell_apps,
        ordered_apps=ordered_apps,
        hatched_per_cell=hatched_per_cell,
        stacked=[
            ("input_tokens_M",  "Input"),
            ("output_tokens_M", "Output"),
        ],
        ylabel="Total tokens (millions)",
        fname_stem="fast_tier_iter_tokens",
    )

    print(f"\nSaved: {OUT_DIR}/")
    for f in sorted(OUT_DIR.glob("fast_tier_iter_*")):
        print(f"  {f.name}  ({f.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
