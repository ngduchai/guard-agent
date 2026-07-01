"""Combined failure-free + failure-impact stacked-bar walltime chart (multi-model).

Combines what used to be two separate figures (failure-free walltime
and failure-injected walltime) into a single stacked-bar chart where
each per-app slot contains up to FIVE stacked bars (Vanilla / Opus /
Sonnet / GPT-5.5 / Reference).  Each stacked bar has two segments:

    bottom = execution time under failure-free workload
    top    = execution time under failure-injected workload
             minus failure-free time
           = failure impact on execution time

The total bar height therefore equals the failure-injected walltime,
and the bottom-segment height is the failure-free walltime.  Each LLM
cell uses its model color (MODEL_COLORS); Reference uses a dark neutral;
Vanilla is mid-gray.  GPT-5.5 (or any cell with no bench data) renders
a thin gray placeholder bar so the slot stays visible.

Data, trust filtering, app ordering, group separators, and category
helpers are reused verbatim from `_plot_fast_tier_llm_vs_reference.py`
(single source of truth for the fast-tier comparison series).
"""
from __future__ import annotations

import matplotlib as mpl
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

import json
import shutil
from pathlib import Path

from _cells import CELLS, MODEL_COLORS, cell_bench, median_cell_for, trusted_apps
from _plot_fast_tier_llm_vs_reference import (
    COLOR_VAN,
    COMPLETED_APPS,
    DIFFICULTY_ORDER,
    OUT_DIR,
    _scenario_summary,
    load_app,
)


# Complexity groups, mirroring the GROUPS dict in
# scripts/ckpt_size_rebench/plot_fig4_from_corrected.py.  Used to draw
# group separators + italic group labels above the bars in Fig 4a,
# matching Fig 4b's layout so the two panels read consistently.
_FIG4_GROUPS = {
    "Plain Static":  ["PRK_Stencil", "HPCG", "SW4lite", "HyPar"],
    "Plain Dynamic": ["CoMD", "SPARTA", "SPPARKS", "CLAMR", "LAMMPS"],
    "Encapsulated":  ["Athena++", "WarpX", "OpenLB", "Smilei"],
    "Modularized":   ["Nyx", "ROSS", "SAMRAI"],
}


def _draw_group_separators(ax, plotted_apps: list[str]) -> None:
    """Draw vertical group boundaries + italic group labels.

    Mirrors the helper in plot_fig4_from_corrected.py — the imported
    upstream version is a no-op (FlexScience uses a 6-app layout that
    does not warrant bands), so override locally.
    """
    rank = {a: i for i, a in enumerate(plotted_apps)}
    bounds, c = [], 0
    for apps in _FIG4_GROUPS.values():
        c += sum(1 for a in apps if a in rank)
        bounds.append(c)
    for b in bounds[:-1]:
        if 0 < b < len(plotted_apps):
            ax.axvline(b - 0.5, color="#aaaaaa", linewidth=0.5,
                       linestyle="--", zorder=0)
    ymin, ymax = ax.get_ylim()
    band_y = ymax * 0.95
    for label, apps in _FIG4_GROUPS.items():
        idxs = [rank[a] for a in apps if a in rank]
        if not idxs:
            continue
        center = (min(idxs) + max(idxs)) / 2.0
        ax.text(center, band_y, label, fontsize=8, ha="center", va="top",
                style="italic", color="#555555")


# Reference color is OVERRIDDEN here (vs ``COLOR_REF`` in the FlexScience
# module, which is "#D55E00" vermillion) to match the eScience shared
# legend (``_plot_overhead_legend.py`` uses "#332288").  Same hue so the
# Reference bars in the chart visually match the Reference patch in the
# strip legend rendered above the figure in main.tex.
COLOR_REF = "#332288"


# This script backs the eScience paper; mirror outputs there.  (The
# shared ``_mirror_to_papers`` imported from
# ``_plot_fast_tier_llm_vs_reference`` targets the FlexScience paper
# only — re-using it would silently drop the eScience copy and leave the
# paper rebuilt against a stale PDF.)
_ESCIENCE_FIGURES_DIR = (
    Path(__file__).resolve().parents[2]
    / "docs" / "paper" / "eScience" / "Figures"
)


def _mirror_to_papers(stem: str) -> None:
    src = OUT_DIR / f"{stem}.pdf"
    if src.exists() and _ESCIENCE_FIGURES_DIR.exists():
        shutil.copy2(src, _ESCIENCE_FIGURES_DIR / f"{stem}.pdf")

# Shared 16-app app list used by both Fig 4 panels so the two stacked
# subfigures align vertically in the final PDF (same x-tick positions,
# same y-axis left margin).  Mirrors GROUPS in
# scripts/ckpt_size_rebench/plot_fig4_from_corrected.py — keep the two
# lists in sync.  Apps without bench data render empty slots in this
# panel (Fig 4a); per-checkpoint sizes still appear in Fig 4b.
FIG4_APPS_FULL = [
    "PRK_Stencil", "HPCG", "SW4lite", "HyPar",
    "CoMD", "SPARTA", "SPPARKS", "CLAMR", "LAMMPS",
    "Athena++", "WarpX", "OpenLB", "Smilei",
    "Nyx", "ROSS", "SAMRAI",
]

# Shared layout parameters for cross-subfigure alignment.  Both Fig 4a
# (this script) and Fig 4b (plot_fig4_from_corrected.py) must use these
# exact values; otherwise the y-axes drift and the columns slide apart
# in the final PDF.
FIG4_WIDTH_IN = 12.0
FIG4_MARGIN_LEFT = 0.050
FIG4_MARGIN_RIGHT = 0.998

# Apps that were in-flight or queued at a previous snapshot.  The
# upstream module dropped this set after all apps finished benching;
# keep an empty placeholder so the filter below remains a no-op
# without requiring further edits.
IN_FLIGHT_OR_QUEUED: set[str] = set()

# Placeholder bar styling for cells with no data in this panel.  The
# constants used to live in the sibling LLM-vs-Reference module but
# were retired upstream; keep local copies so this script remains
# self-contained.
PLACEHOLDER_ALPHA = 0.30
PLACEHOLDER_HEIGHT_FRAC = 0.015

mpl.rcParams.setdefault("savefig.bbox", "tight")
# Extra pad so long rotated y-axis labels (e.g. "Execution time
# (normalized to vanilla failure-free)") on the normalized chart are
# not clipped at the left figure edge.
mpl.rcParams.setdefault("savefig.pad_inches", 0.20)

# rcParams above (and the upstream module's rcParams that we inherit on
# import) set savefig.bbox="tight".  For the Fig 4 normalized panel we
# want the saved PDF width to equal FIG4_WIDTH_IN exactly so the panel
# aligns with Fig 4b; "tight" trims each PDF based on label widths,
# breaking that.  Override unconditionally here — this script only saves
# Fig 4-style charts so the override is safe for every render path.
mpl.rcParams["savefig.bbox"] = None


def _pick_elapsed(block: dict | None) -> float | None:
    """Mirror ``load_app``'s mean-vs-median rule for one summary block.

    For high-variance cells (CV > 10%) the median is the honest summary;
    for low-variance cells mean and median agree closely.  Returns None
    when the block (or its elapsed_s sub-block) is missing.
    """
    if block is None:
        return None
    es = block.get("elapsed_s") or {}
    if not es:
        return None
    cv = es.get("cv", 0)
    return es["median"] if cv > 0.10 else es["mean"]


def _load_cell_walltime(cell_id: str, app: str) -> tuple[float | None, float | None]:
    """Return (failure-free, failure-injected) elapsed_s for one (cell, app).

    Reads ``results/models/<cell>/bench/<app>/benchmarks/raw_metrics.json``
    via ``cell_bench`` and ``_scenario_summary`` (which augments the
    summary block with run-derived statistics, matching ``load_app``'s
    behavior).  Returns ``(None, None)`` when bench data is missing.
    """
    path = cell_bench(cell_id, app) / "benchmarks" / "raw_metrics.json"
    if not path.exists():
        return None, None
    raw = json.loads(path.read_text())
    ff = _pick_elapsed(_scenario_summary(raw, "small-nofail", "resilient"))
    once = _pick_elapsed(_scenario_summary(raw, "small-once",  "resilient"))
    return ff, once


def _impact(once: float | None, ff: float | None) -> float | None:
    if once is None or ff is None:
        return None
    diff = once - ff
    if diff < 0:
        print(f"  [warn] negative impact ({diff:.2f}s) clamped to 0")
        return 0.0
    return diff


def _render(apps_sorted, *, normalize: bool, stem: str, ylabel: str,
            fig_height: float = 3.15, with_legend: bool = True) -> None:
    """Render one stacked-bar figure.

    Bar order per app: vanilla, then each LLM cell in MODEL_COLORS,
    then reference.  Cells with no data render a placeholder bar at
    that slot so the GPT-5.5 reservation stays visible.

    ``fig_height`` lets the caller shrink the panel (Figure 3a in the
    paper uses a halved height so the merged figure stays tight).
    ``with_legend=False`` suppresses both legend boxes — the paper
    figure renders a shared legend below both subfigures via a
    standalone ``_plot_overhead_legend.py`` artifact.
    """
    n = len(apps_sorted)
    # Width is pinned (FIG4_WIDTH_IN) so this panel's x-tick positions
    # match Fig 4b's after LaTeX scales both to \textwidth; see the
    # FIG4_* constants at module top.
    fig, ax = plt.subplots(figsize=(FIG4_WIDTH_IN, fig_height))

    # Series tuples = (label, color, tag, is_synthetic, placeholder_ok).
    series: list[tuple[str, str, str, bool, bool]] = [
        ("Vanilla (no resilience)", COLOR_VAN, "van", True, False),
    ]
    for cell_id, cell_label, _marker in CELLS:
        series.append(
            (f"LLM {cell_label}", MODEL_COLORS[cell_id], cell_id, False, True)
        )
    series.append(("Reference", COLOR_REF, "ref", False, False))

    k = len(series)
    # Cluster of k bars fills 55% of each app slot, leaving a 45% gap
    # between adjacent apps — wide enough that horizontal x-tick labels
    # (full app names) clear their neighbors at fontsize 7.
    cluster_w = 0.55
    bar_w = cluster_w / k
    offsets = [(i - (k - 1) / 2) * bar_w for i in range(k)]
    x_centres = list(range(n))

    def _scale(a, v):
        if not normalize or v is None:
            return v
        base = a.get("ff_van")
        return None if not base else v / base

    finite_totals = []
    for a in apps_sorted:
        for _label, _col, tag, _synth, _ph in series:
            ff = _scale(a, a.get(f"ff_{tag}"))
            once = _scale(a, a.get(f"once_{tag}"))
            if ff is not None and once is not None:
                finite_totals.append(max(ff, once))
            elif ff is not None:
                finite_totals.append(ff)
    if finite_totals:
        # 1.35 headroom (vs. 1.18) leaves vertical space for the
        # "Plain Static"/"Plain Dynamic"/... group-band labels drawn at
        # 0.95 * ymax so they don't visually collide with the tallest
        # failure-injected (vanilla) bars that reach ~1.5.
        ax.set_ylim(0, max(finite_totals) * 1.35)

    placeholder_h = (max(finite_totals) * PLACEHOLDER_HEIGHT_FRAC
                     if finite_totals else 0.05)

    for (label, colour, tag, synth, placeholder_ok), x_off in zip(series, offsets):
        # Check if this series has ANY data across every app.
        has_any = any(a.get(f"ff_{tag}") is not None
                      or a.get(f"once_{tag}") is not None
                      for a in apps_sorted)
        if not has_any and placeholder_ok:
            # Pure placeholder series — render a thin stub at every slot,
            # in the CELL'S OWN color at PLACEHOLDER_ALPHA so the reserved
            # slot stays attributable to that model (no gray collision with
            # vanilla).
            for c in x_centres:
                ax.bar(c + x_off, placeholder_h, width=bar_w,
                       color=colour, alpha=PLACEHOLDER_ALPHA,
                       edgecolor=colour, linewidth=0.5, zorder=1)
            continue
        if not has_any:
            continue
        for c, a in zip(x_centres, apps_sorted):
            x = c + x_off
            ff = _scale(a, a.get(f"ff_{tag}"))
            once = _scale(a, a.get(f"once_{tag}"))
            if ff is None and once is None:
                continue  # silent gap (no per-cell data for this app)
            if ff is not None:
                ax.bar(x, ff, width=bar_w, color=colour,
                       edgecolor="black", linewidth=0.5, zorder=2)
            ip = _impact(once, ff)
            if ip is not None and ip > 0:
                # Impact segment: same color, hatched.  Solid vs hatched
                # is the failure-free vs failure-injected-overhead key
                # in the breakdown legend.
                ax.bar(x, ip, width=bar_w, bottom=ff if ff else 0,
                       color=colour,
                       edgecolor="black", linewidth=0.5,
                       hatch="////", zorder=2)

    if normalize:
        ax.axhline(1.0, color="#444444", linewidth=0.7, linestyle=":",
                   zorder=1.5)

    ax.set_ylabel(ylabel)
    ax.set_xticks(x_centres)
    # fontsize bumped 6 -> 8 to improve readability of the app names
    # in the final PDF.  Kept HORIZONTAL (rotation=0) per request — 8pt
    # is the largest size that fits 16 horizontal app names across the
    # 12in source figure without colliding.
    ax.set_xticklabels([a["app"] for a in apps_sorted],
                       rotation=0, ha="center", fontsize=8)
    ax.tick_params(axis="x", which="both", length=0)

    extras: list = []
    if with_legend:
        approach_handles = []
        for label, col, tag, _synth, placeholder_ok in series:
            has_any = any(a.get(f"ff_{tag}") is not None
                          or a.get(f"once_{tag}") is not None
                          for a in apps_sorted)
            if has_any:
                approach_handles.append(
                    mpatches.Patch(facecolor=col, edgecolor="black", linewidth=0.5,
                                   label=label))
            elif placeholder_ok:
                approach_handles.append(
                    mpatches.Patch(facecolor=col, alpha=PLACEHOLDER_ALPHA,
                                   edgecolor="black", linewidth=0.5,
                                   label=f"{label} (pending)"))
        breakdown_handles = [
            mpatches.Patch(facecolor="#cccccc", edgecolor="black", linewidth=0.5,
                           label="Failure-free execution"),
            mpatches.Patch(facecolor="#cccccc", edgecolor="black", linewidth=0.5,
                           hatch="////", label="Failure-injected overhead"),
        ]
        approach_leg = ax.legend(
            handles=approach_handles,
            loc="upper left", bbox_to_anchor=(-0.08, -0.18),
            ncol=3, fontsize=9,
            frameon=True, fancybox=False, edgecolor="black",
            handlelength=1.2, handletextpad=0.5,
            columnspacing=1.0, borderpad=0.4)
        ax.add_artist(approach_leg)
        breakdown_leg = ax.legend(
            handles=breakdown_handles,
            loc="upper right", bbox_to_anchor=(1.0, -0.18),
            ncol=1, fontsize=9,
            frameon=True, fancybox=False, edgecolor="black",
            handlelength=1.2, handletextpad=0.5,
            columnspacing=1.0, borderpad=0.4)
        extras = [approach_leg, breakdown_leg]

    _draw_group_separators(ax, [a["app"] for a in apps_sorted])

    # Fixed fractional margins so the y-axis (plot-area left edge) sits
    # at the same proportional x in the saved PDF for both Fig 4 panels.
    # Save with bbox_inches=None to honor figsize exactly — "tight" would
    # trim each PDF differently depending on label widths, breaking the
    # cross-subfigure alignment.
    # bottom=0.22 (modest bump from original 0.18) accommodates the
    # fontsize=8 horizontal x-tick labels.  Same value used in
    # plot_fig4_from_corrected.py so 4a and 4b share the same
    # axes-frame height after layout.
    fig.subplots_adjust(
        left=FIG4_MARGIN_LEFT, right=FIG4_MARGIN_RIGHT,
        top=0.93, bottom=0.22,
    )
    save_kwargs = {"bbox_inches": None}
    if extras:
        save_kwargs["bbox_extra_artists"] = extras
    fig.savefig(OUT_DIR / f"{stem}.pdf", **save_kwargs)
    fig.savefig(OUT_DIR / f"{stem}.png", dpi=300, **save_kwargs)
    _mirror_to_papers(stem)
    plt.close(fig)
    print(f"  Saved: {OUT_DIR}/{stem}.{{pdf,png}} (and mirrored)")


def main() -> None:
    # Per-(app, model) cell resolution: each model column's bars for a
    # given app come from the median-iter cell defined in
    # MEDIAN_CELL_MAP (see _cells.py).  The model anchor cell_id from
    # the CELLS catalogue still drives color + legend; the real bench
    # source can differ per app.
    eligible = list(FIG4_APPS_FULL)

    def _has_any_bench(app: str) -> bool:
        for c in CELLS:
            real_cell = median_cell_for(c[1], app)
            if real_cell is None:
                continue
            p = cell_bench(real_cell, app) / "benchmarks" / "raw_metrics.json"
            if p.exists():
                return True
        return False

    no_bench = sorted(a for a in eligible if not _has_any_bench(a))
    in_flight = sorted(a for a in eligible if a in IN_FLIGHT_OR_QUEUED)
    eligible = [a for a in eligible if a not in IN_FLIGHT_OR_QUEUED]

    print(f"Plotting {len(eligible)} apps (shared with Fig 4b for vertical alignment)")
    if no_bench:
        print(f"  no bench data in any cell (slot rendered empty): {no_bench}")
    if in_flight:
        print(f"  dropping in-flight/queued: {in_flight}")

    apps = []
    for a in eligible:
        d = load_app(a)
        for c in CELLS:
            cell_id, cell_label, _marker = c
            real_cell = median_cell_for(cell_label, a)
            if real_cell is None:
                d[f"ff_{cell_id}"] = None
                d[f"once_{cell_id}"] = None
                continue
            # Pull bench from the per-(app, model) median cell, not the
            # fixed model anchor.  Keys still use cell_id so downstream
            # rendering keys (color, legend) stay model-anchored.
            ff_v, once_v = _load_cell_walltime(real_cell, a)
            d[f"ff_{cell_id}"] = ff_v
            d[f"once_{cell_id}"] = once_v
        apps.append(d)

    rank = {name: i for i, name in enumerate(FIG4_APPS_FULL)}
    apps_sorted = sorted(apps, key=lambda a: rank.get(a["app"], len(rank)))

    print("Loaded (failure-free / impact):")
    for a in apps_sorted:
        def _f(v):
            return "    n/a" if v is None else f"{v:6.1f}s"
        line = f"  {a['app']:<12}  V={_f(a['ff_van'])}+{_f(_impact(a['once_van'], a['ff_van']))}"
        for c in CELLS:
            cid = c[0]
            ff = a.get(f"ff_{cid}")
            ip = _impact(a.get(f"once_{cid}"), ff)
            line += f"  {cid}={_f(ff)}+{_f(ip)}"
        ff_r = a.get("ff_ref")
        ip_r = _impact(a.get("once_ref"), ff_r)
        line += f"  R={_f(ff_r)}+{_f(ip_r)}"
        print(line)

    _render(apps_sorted, normalize=False,
            stem="fast_tier_compare_walltime_stacked",
            ylabel="Execution time (s)")
    # Y-axis label is intentionally short; the normalization basis is
    # stated in the figure caption (\\label{fig:walltime-overhead}).
    # Paper figure 3a: half-height + no internal legend (shared legend
    # is rendered separately by _plot_overhead_legend.py and inserted
    # in LaTeX between the two subfigures).
    # fig_height=1.7 (was 1.575 originally, briefly 1.95 with rotated
    # labels; now horizontal so we need less vertical space — a small
    # bump from 1.575 -> 1.7 preserves chart area after bottom margin
    # grew 0.18 -> 0.22).  Keep in sync with plot_fig4_from_corrected.py
    # so 4a + 4b render at the same final PDF height.
    _render(apps_sorted, normalize=True,
            stem="fast_tier_compare_walltime_stacked_normalized",
            ylabel="Time (s)",
            fig_height=1.7, with_legend=False)


if __name__ == "__main__":
    main()
