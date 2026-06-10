"""Three single-panel scatters: source-tree LoC versus
(a) iter-loop wall time, (b) total tokens, (c) API cost (USD).

Each panel uses the same color-by-group + shape-by-model encoding as
``_plot_loc_vs_tokens.py`` so all figures share a visual grammar.

One dot per (cell, app):
  * x = source-tree LoC (log scale)
  * y = wall_min / tokens_M / cost_usd depending on panel
  * color = complexity group (Tol muted palette)
  * shape = model (Opus 4.7 = circle, Sonnet 4.6 = triangle-up,
    GPT-5.5 = square)

Unsuccessful runs are plotted with the SAME marker convention as
successful ones; their wall / token / cost totals are capped at the
first ``DNC_CAP`` per_iteration entries (see ``_cells.py``).

The script writes FOUR PDFs (and matching PNGs):
  loc_vs_wall.pdf             — single-panel (a)
  loc_vs_tokens.pdf           — single-panel (b) (overwrites the standalone)
  loc_vs_cost.pdf             — single-panel (c)
  loc_vs_wall_and_tokens.pdf  — three-panel composite (legacy; kept for the
                                  paper subcaption block if desired)

All PDFs mirror into each active paper's Figures dir.
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
# Five-color palette chosen so each pair is unambiguous at marker size 14.
# Earlier choices failed two adjacency tests: pink (#CC79A7) vs dark-purple
# (#7E2F8E) were both purple-tinted, and dark-red (#A2142F) vs dark-gray
# (#333333) both read as "dark blob" at scatter size.  This palette spans
# yellow → cyan → magenta → brown → black, so consecutive groups always
# differ in hue family AND brightness.  None collide with MODEL_COLORS
# (Opus blue #0072B2, Sonnet orange #d35d2a, GPT green #009E73) used on
# panels a/b/c.
GROUP_COLORS = {
    "Plain Static":     "#FFC107",   # amber/yellow
    "Plain Dynamic":    "#00BCD4",   # cyan/teal
    "Encapsulated":     "#E91E63",   # vivid magenta/pink
    "Modularized":      "#FF6F00",   # deep orange — bright, distinct from black
    "Did Not Complete": "#000000",   # pure black — DNC
}
# Single-line abbreviations used in panel (d)'s group legend so it
# matches the x-tick labels on panels a/b/c (PS / PD / Enc / Mod / DNC).
# Kept in sync with _plot_per_group_summary.py::_SHORT_LABELS.
GROUP_SHORT_LABELS = {
    "Plain Static":     "PS",
    "Plain Dynamic":    "PD",
    "Encapsulated":     "Enc",
    "Modularized":      "Mod",
    "Did Not Complete": "DNC",
}

# Bottom margin shared with the bar panels in _plot_per_group_summary.py
# so the x-axis lines of Fig 3a/b/c/d sit at the SAME fractional y in
# the saved PDFs and therefore align in the rendered paper figure.  Size
# picked to fit panel (d)'s x-axis tick row + "Source LoC (log)" label.
FIG3_BOTTOM_MARGIN = 0.20
# Per-group marker shape — primary encoding for the scatter panel (d)
# in Figure 3.  Model is encoded via MODEL_COLORS so that panel (d) can
# share the approach color legend with the bar panels (a/b/c); the
# group-shape legend lives embedded in panel (d) itself.
GROUP_MARKERS = {
    "Plain Static":  "o",   # circle
    "Plain Dynamic": "s",   # square
    "Encapsulated":  "^",   # triangle-up
    "Modularized":   "D",   # diamond
}

# Per-model API pricing — USD per million tokens, verified 2026-05-30 from
# vendor docs.  Kept in sync with _plot_per_group_summary.py::MODEL_PRICING.
MODEL_PRICING: dict[str, dict[str, float] | None] = {
    "opus47":   {"input_per_m":  5.0, "output_per_m": 25.0},
    "sonnet46": {"input_per_m":  3.0, "output_per_m": 15.0},
    "gpt55_unified": {"input_per_m":  5.0, "output_per_m": 30.0},
}


def _cost_usd(cell_id: str, input_tokens: int, output_tokens: int) -> float | None:
    rate = MODEL_PRICING.get(cell_id)
    if rate is None:
        return None
    return (input_tokens * rate["input_per_m"]
            + output_tokens * rate["output_per_m"]) / 1e6


def _group_of(app: str) -> str | None:
    for label, apps in GROUPS.items():
        if app in apps:
            return label
    return None


def _load_app(source_dir: Path, cell_id: str, *, is_dnc: bool):
    """Return (wall_min, tokens_M, cost_usd) or None.  Capped per
    ``_cells.load_result``.  cost is ``None`` for cells with no pricing."""
    res = load_result(source_dir, is_dnc=is_dnc)
    if res is None:
        return None
    return (
        res["wall_elapsed_s"] / 60.0,
        res["total_tokens"] / 1e6,
        _cost_usd(cell_id, res["total_input_tokens"], res["total_output_tokens"]),
    )


# --- Plot styling ---------------------------------------------------------
mpl.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif", "Times New Roman", "Times"],
    # loc_vs_tokens.pdf ships as Figure 3 panel (d) at 0.24*\textwidth =
    # 1.72in.  Native figsize below matches that width so matplotlib pt
    # values map 1:1 to the rendered PDF; sizes match the per-group bar
    # panels in _plot_per_group_summary.py.
    "font.size": 8,
    "axes.titlesize": 8,
    "axes.labelsize": 8,
    "axes.linewidth": 0.5,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.major.width": 0.5,
    "ytick.major.width": 0.5,
    "legend.fontsize": 6,
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


def _collect(cell: str, label: str):
    """Per-cell list of (app, loc, wall_min, tokens_M, cost_usd, is_dnc).

    For PS/PD/Enc apps with one or more TRUSTED + CONDITIONAL_TRUSTED
    trials, ``(wall_min, tokens_M, cost_usd)`` is the AVERAGE across all
    successful trials.  For Mod apps, the single first-run cell's value
    is used (with gpt55_retry fallback for GPT-5.5).  Apps with no
    successful trial fall back to the model anchor's DNC archive
    (the first-run failure data) with ``is_dnc=True``.

    Cost pricing always comes from ``cell`` (the model anchor) so the
    per-token rate is consistent across averaged trials of the same
    model.  See [_cells.py:cells_for] for the routing table.
    """
    from _cells import cells_for
    dnc = cell_dnc_dirs(cell)
    rows = []
    for app, loc in APP_LOC.items():
        trial_cells = cells_for(label, app)
        if trial_cells:
            samples = []
            for c in trial_cells:
                iter_logs = cell_iter_logs(c)
                if not iter_logs.exists():
                    continue
                r = _load_app(iter_logs / app, cell, is_dnc=False)
                if r is not None:
                    samples.append(r)
            if not samples:
                continue
            n = len(samples)
            wall_min = sum(s[0] for s in samples) / n
            tokens_M = sum(s[1] for s in samples) / n
            costs = [s[2] for s in samples if s[2] is not None]
            cost_usd = sum(costs) / len(costs) if costs else None
            rows.append((app, loc, wall_min, tokens_M, cost_usd, False))
            continue
        if app in dnc:
            r = _load_app(dnc[app], cell, is_dnc=True)
            if r is None:
                continue
            wall_min, tokens_M, cost_usd = r
            rows.append((app, loc, wall_min, tokens_M, cost_usd, True))
    return rows


_Y_KEYS = {"wall": 2, "tokens": 3, "cost": 4}
_IS_DNC_IDX = 5


def _draw_panel(ax, per_cell, *, y_key: str, y_label: str):
    """Render one scatter panel.  ``y_key`` selects which value to plot:
    ``"wall"`` / ``"tokens"`` / ``"cost"``.  Dots with y=None (e.g. cost
    when pricing is missing) are silently skipped.

    Color encodes complexity group (or DNC for runs from a DNC archive),
    shape encodes the model.  Disjoint from MODEL_COLORS on panels a/b/c.
    """
    # Smaller markers (was s=50) so dots stay distinct in the narrow
    # 1.72in panel without per-app text labels obscuring them.
    DOT_SIZE = 14
    y_idx = _Y_KEYS[y_key]
    all_y = []
    for cell_id, _label, model_marker in CELLS:
        for row in per_cell[cell_id]:
            app, loc = row[0], row[1]
            y = row[y_idx]
            if y is None:
                continue
            # DNC runs override the complexity-group color so the reader
            # can spot Did-Not-Complete attempts at a glance.
            if row[_IS_DNC_IDX]:
                color = GROUP_COLORS["Did Not Complete"]
            else:
                grp = _group_of(app)
                color = GROUP_COLORS.get(grp, "#888888")
            ax.scatter([loc], [y], s=DOT_SIZE, marker=model_marker,
                       color=color, edgecolor="black", linewidth=0.4,
                       zorder=3)
            all_y.append(y)

    # Per-app text labels intentionally omitted: at 1.72in panel width
    # they overlap each other and the markers.  App identity is
    # recoverable from the (LoC, group-color) combination plus the prose.

    ax.set_xscale("log")
    ax.set_xlabel("Source-tree size (LoC, log scale)")
    ax.set_ylabel(y_label)
    ax.set_xlim(700, 1.0e6)
    ymax = max(all_y) if all_y else 1.0
    # 1.15× headroom (was 1.10) so the rotated topmost y-tick label has
    # vertical room above its tick mark and does not get clipped against
    # the figure boundary.
    ax.set_ylim(0, ymax * 1.15)
    # Rotate y-tick labels 90° so they sit vertically against the axis,
    # saving ~0.15in of left margin in the narrow 1.72in panel.  Setting
    # this via the yaxis tick-params object (persistent property)
    # rather than ax.tick_params or plt.setp on label objects ensures
    # the rotation survives any auto-locator regen triggered by later
    # subplots_adjust / savefig calls.
    ax.tick_params(axis="y", pad=1.5)


def _save_single_panel(per_cell, *, stem: str, y_key: str, y_label: str,
                       with_legend: bool):
    """Render one single-panel scatter to ``<stem>.{pdf,png}`` and mirror.

    Native width = 1.72in matches the IEEEtran 0.24*\\textwidth subfigure
    slot used in Figure 3; matplotlib pt values map 1:1 to the rendered
    PDF.  When ``with_legend`` is True, a compact stacked legend sits
    ABOVE the scatter inside the figure rectangle (groups in 2 columns,
    models in 3 columns) so it never occludes the data AND never makes
    the saved PDF wider than 1.72in (which would force LaTeX to shrink
    the whole figure).  Native height grows from 1.6 to 1.95 to make
    room.
    """
    # All panels at 1.72x1.6 so Figure 3's row of bar panels and the
    # scatter share the same axes-frame height; bottoms and tops align.
    fig, ax = plt.subplots(figsize=(1.72, 1.6))
    _draw_panel(ax, per_cell, y_key=y_key, y_label=y_label)
    ax.yaxis.labelpad = 1
    ax.xaxis.labelpad = 1

    if with_legend:
        # Shorter x-label so the 1.72in panel does not overflow.  The
        # caption in main.tex clarifies the full semantics.
        ax.set_xlabel("Source LoC (log)")
        # Two stacked legends in the top-left, both 1 column with thin
        # black frames.  Model legend (shape key) on top, group legend
        # (color key) directly below — mirrors the (approach, stack)
        # layout used by panels a/b/c.  Group colors come from
        # GROUP_COLORS (high-contrast palette) which is intentionally
        # disjoint from MODEL_COLORS used in panels a/b/c.  DNC is
        # added as a 5th entry so Did-Not-Complete attempts have a
        # legend key as well.
        model_handles = [
            mlines.Line2D([], [], marker=marker, linestyle="",
                          color="#bbbbbb", markeredgecolor="black",
                          markersize=4, label=label)
            for _cid, label, marker in CELLS
        ]
        group_keys = list(GROUPS.keys()) + ["Did Not Complete"]
        group_handles = [
            mlines.Line2D([], [], marker="s", linestyle="",
                          color=GROUP_COLORS[g], markeredgecolor="black",
                          markersize=4, label=GROUP_SHORT_LABELS.get(g, g))
            for g in group_keys
        ]
        # fontsize=6 matches Fig 3a-c standalone legends in
        # _plot_per_group_summary.py — keep in sync so all four Fig 3
        # subpanels show legends at the same rendered text size.
        model_leg = ax.legend(
            handles=model_handles,
            loc="upper left", bbox_to_anchor=(0.01, 0.99),
            ncol=1, fontsize=6,
            frameon=True, fancybox=False, edgecolor="black",
            handlelength=0.8, handletextpad=0.3,
            labelspacing=0.20, borderpad=0.25, borderaxespad=0.0,
        )
        ax.add_artist(model_leg)
        # Group legend lands just below the model legend.  Offset
        # widened to 0.42 (was 0.36) to make room for 5 entries
        # (PS/PD/Enc/Mod/DNC) at the bumped fontsize=6 without
        # colliding with the model legend.
        ax.legend(
            handles=group_handles,
            loc="upper left", bbox_to_anchor=(0.01, 0.99 - 0.42),
            ncol=1, fontsize=6,
            frameon=True, fancybox=False, edgecolor="black",
            handlelength=0.8, handletextpad=0.3,
            labelspacing=0.20, borderpad=0.25, borderaxespad=0.0,
        )
    # Maximize plot area: explicit margins consume only what the labels
    # actually need; right/top edges sit nearly flush with the figure
    # boundary so the scatter occupies as much of the 1.72x1.6in panel
    # as possible.  ``bottom`` is pinned to FIG3_BOTTOM_MARGIN so this
    # panel's x-axis line aligns with Fig 3a-c's (the bar panels share
    # the same value in _plot_per_group_summary.py).  (y-tick rotation
    # is set inside ``_draw_panel`` via the persistent yaxis tick-params
    # property.)
    # right=0.93 (was 0.99) so the rightmost x-tick label (10^6) has room
    # to render its exponent fully without being clipped by the figure
    # boundary.  top/bottom remain at 0.99 / FIG3_BOTTOM_MARGIN so this
    # panel's axes-frame top + bottom still align with Fig 3a-c.
    fig.subplots_adjust(left=0.135, right=0.93, top=0.99,
                        bottom=FIG3_BOTTOM_MARGIN)
    # Rotate y-tick labels 90° by FIXING the locator + formatter to
    # explicit values so savefig's internal redraw cannot regenerate the
    # tick artists with default rotation.  ax.tick_params /
    # plt.setp(get_yticklabels()) BOTH get clobbered by the auto-locator
    # on this matplotlib version; FixedLocator + FixedFormatter is the
    # only path that survives the redraw.
    fig.canvas.draw()
    import matplotlib.ticker as mticker
    yticks = list(ax.get_yticks())
    ylim = ax.get_ylim()
    yticks_in = [y for y in yticks if ylim[0] <= y <= ylim[1]]
    ylabels = [(f"{int(y)}" if float(y).is_integer() else f"{y:g}")
               for y in yticks_in]
    ax.yaxis.set_major_locator(mticker.FixedLocator(yticks_in))
    ax.yaxis.set_major_formatter(mticker.FixedFormatter(ylabels))
    ax.set_yticklabels(ylabels, rotation=90, va="center")
    fig.savefig(OUT_DIR / f"{stem}.pdf", bbox_inches=None)
    fig.savefig(OUT_DIR / f"{stem}.png", dpi=300, bbox_inches=None)
    plt.close(fig)
    _mirror_to_papers(stem)
    print(f"  Saved: {OUT_DIR}/{stem}.{{pdf,png}}")


def _save_legend(per_cell, *, stem: str) -> None:
    """Render a legend-only horizontal strip to ``<stem>.{pdf,png}`` so the
    subcaption block in main.tex can place ONE legend above all three
    panels.  Two rows: group colors on top, model shapes on bottom."""
    fig = plt.figure(figsize=(6.5, 0.6))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")

    group_handles = [
        mlines.Line2D([], [], marker="o", linestyle="",
                      color=GROUP_COLORS[g], markeredgecolor="black",
                      markersize=8, label=g)
        for g in GROUPS.keys()
    ]
    model_handles = []
    for cell_id, label, marker in CELLS:
        has_data = bool(per_cell[cell_id])
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
                     loc="upper center", bbox_to_anchor=(0.5, 1.0),
                     ncol=len(group_handles), fontsize=9, frameon=False,
                     handletextpad=0.4, columnspacing=1.4)
    ax.add_artist(leg1)
    leg2 = ax.legend(handles=model_handles,
                     loc="upper center", bbox_to_anchor=(0.5, 0.45),
                     ncol=len(model_handles), fontsize=9, frameon=False,
                     handletextpad=0.4, columnspacing=1.4)

    fig.savefig(OUT_DIR / f"{stem}.pdf", bbox_inches="tight",
                bbox_extra_artists=[leg1, leg2])
    fig.savefig(OUT_DIR / f"{stem}.png", dpi=300, bbox_inches="tight",
                bbox_extra_artists=[leg1, leg2])
    plt.close(fig)
    _mirror_to_papers(stem)
    print(f"  Saved: {OUT_DIR}/{stem}.{{pdf,png}}")


def main() -> None:
    per_cell: dict[str, list] = {}
    for cell_id, label, _marker in CELLS:
        rows = _collect(cell_id, label)
        per_cell[cell_id] = rows
        print(f"[{cell_id} = {label}] {len(rows)} apps "
              f"({sorted(r[0] for r in rows)})")

    # Three single-panel PDFs + a separate legend-only PDF.  The subcaption
    # block in main.tex places the legend above the three equal-width
    # panels so all three panels render at the same plot-area size.
    print("\nSingle-panel renders:")
    _save_single_panel(per_cell, stem="loc_vs_wall",
                       y_key="wall",
                       y_label="Iter-loop wall time (min)",
                       with_legend=False)
    _save_single_panel(per_cell, stem="loc_vs_tokens",
                       y_key="tokens",
                       y_label="Total tokens (M)",
                       with_legend=True)
    _save_single_panel(per_cell, stem="loc_vs_cost",
                       y_key="cost",
                       y_label="API cost per app (USD)",
                       with_legend=False)
    _save_legend(per_cell, stem="loc_legend")

    print("\nDone.")


if __name__ == "__main__":
    main()
