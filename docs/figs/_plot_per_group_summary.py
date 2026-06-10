"""Per-group aggregate of LLM iter-loop API cost, code-gen time, tokens.

Three side-by-side panels: API cost / LLM code-gen time / token cost.
Within each panel, every complexity group renders N adjacent bars (one
per model in CELLS), each colored by the model — Opus blue, Sonnet
vermillion, GPT-5.5 green.  Individual app values are overlaid as
scatter dots so within-group spread stays visible per cell.  The group
identity is encoded by the x-axis label only (no group color); the
shared model legend sits below the figure.

Panel (a) "API cost" multiplies per-app capped input/output tokens by
``MODEL_PRICING`` (USD per million tokens, Anthropic standard tier as
of 2026-05).  GPT-5.5 has no published rate yet so the placeholder bars
render with an "N/A" tag instead of a dollar figure.

Saves PDF + PNG to docs/figs/ and mirrors the PDF into each active
paper's Figures dir.
"""
from __future__ import annotations

import statistics
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
OUT_DIR = REPO_ROOT / "docs" / "figs"
PAPER_FIGURES_DIRS = [
    REPO_ROOT / "docs" / "paper" / "eScience" / "Figures",
]
OUT_DIR.mkdir(parents=True, exist_ok=True)


# USD per million tokens, current Anthropic pricing as of 2026-05.
# Verified against the paper's "$70-$1,200 per app" range at line 396 of main.tex:
# HPCG (4.7 M tokens, 99% input) ≈ $70 (matches lower bound), ROSS (81.5 M)
# ≈ $1,225 (matches upper bound). Anthropic standard-tier pricing for Opus
# 4.7 = $15 input / $75 output per million tokens; Sonnet 4.6 is 1/5 of
# those rates. GPT-5.5 placeholder pricing left at None (no public rate yet).
MODEL_PRICING: dict[str, dict[str, float] | None] = {
    # Verified 2026-05-30 from vendor docs.
    # Opus 4.7 (https://platform.claude.com/docs/en/docs/about-claude/
    # models/overview): $5 input / $25 output per M tokens (standard tier).
    # The older Opus 4 / 4.1 rate of $15/$75 was retired before this paper's
    # data was collected; the paper's "$70-$1,200 per app" range in
    # \S\ref{sec:findings} was derived from the retired rate and must be
    # updated to reflect the current Opus 4.7 rate.
    # Sonnet 4.6: $3 input / $15 output per M tokens (standard tier).
    # GPT-5.5 (https://developers.openai.com/api/docs/pricing): standard
    # short-context tier = $5 input / $30 output per M tokens.
    "opus47":   {"input_per_m":  5.0, "output_per_m": 25.0},
    "sonnet46": {"input_per_m":  3.0, "output_per_m": 15.0},
    "gpt55_unified": {"input_per_m":  5.0, "output_per_m": 30.0},
}


def _cost_usd(cell_id: str, input_tokens: int, output_tokens: int) -> float | None:
    """Return per-app USD cost or None if the cell has no published rate."""
    rate = MODEL_PRICING.get(cell_id)
    if rate is None:
        return None
    return (input_tokens * rate["input_per_m"]
            + output_tokens * rate["output_per_m"]) / 1e6


# Per-group x-tick labels are too long for the narrow 0.24*\textwidth
# panel: rotated text overlaps, two-line splits still kiss adjacent
# ticks at fontsize 5+.  Use single-line abbreviations instead; the
# caption + paper prose spell out the full group names.
_SHORT_LABELS = {
    "Plain Static":     "PS",
    "Plain Dynamic":    "PD",
    "Encapsulated":     "Enc",
    "Modularized":      "Mod",
    "Did Not Complete": "DNC",
}


def _two_line_labels(labels: list[str]) -> list[str]:
    return [_SHORT_LABELS.get(lbl, lbl) for lbl in labels]


def _mirror_to_papers(stem: str) -> None:
    import shutil
    src = OUT_DIR / f"{stem}.pdf"
    if not src.exists():
        return
    for paper_dir in PAPER_FIGURES_DIRS:
        if paper_dir.exists():
            shutil.copy2(src, paper_dir / f"{stem}.pdf")


# --- Plot styling (publication-grade) -------------------------------------
mpl.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif", "Times New Roman", "Times"],
    # Standalone panels (a/b/c) are rendered at native width = 0.24*\textwidth
    # = 1.72in, so matplotlib pt values map 1:1 to the rendered PDF.  10pt
    # axes labels match the IEEEtran body text; 8pt ticks match captions.
    "font.size": 8,
    "axes.titlesize": 8,
    "axes.labelsize": 8,
    "axes.linewidth": 0.5,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "legend.fontsize": 6,
    "legend.frameon": False,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "grid.alpha": 0.35,
    "grid.linestyle": "--",
    "grid.linewidth": 0.5,
    # Keep all 4 spines so Fig 3a-c are visually boxed identically to Fig 3d
    # (which draws full top + right spines via the loc_vs_wall_and_tokens
    # script's default rcParams).  Equivalent top + bottom borders are what
    # the paper figure layout needs for visual alignment.
    "axes.spines.top": True,
    "axes.spines.right": True,
    # Default to None so standalone panels (a/b/c) honor figsize exactly,
    # which is required for Fig 3 top/bottom alignment in main.tex.  The
    # composite figure savefig explicitly overrides this with
    # bbox_inches="tight" — see line ~455.
    "savefig.bbox": None,
    "savefig.pad_inches": 0.0,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


# Same grouping used by the per-app charts.
GROUPS = {
    "Plain Static":              ["HPCG", "PRK_Stencil", "SW4lite", "HyPar"],
    "Plain Dynamic":        ["CoMD", "SPARTA", "SPPARKS", "CLAMR", "LAMMPS"],
    "Encapsulated":  ["Athena++", "WarpX", "OpenLB", "Smilei"],
    "Modularized":   ["Nyx", "ROSS", "SAMRAI", "QMCPACK"],
}

# Placeholder bar for a missing cell (e.g. GPT-5.5 today): a thin stub at a
# fixed fraction of the panel's y-range, rendered in the cell's MODEL_COLORS
# hue at PLACEHOLDER_ALPHA so the GPT-5.5 slot stays distinguishable from
# vanilla's neutral gray.
PLACEHOLDER_ALPHA = 0.30
PLACEHOLDER_HEIGHT_FRAC = 0.015


def _load_app(
    iter_logs_root: Path, app: str, cell_id: str, *, is_dnc: bool = False,
) -> dict | None:
    """Return a per-app row dict, or None if the result.json is missing.

    Keys returned (None when the rate is missing for ``cost_usd``):
        cost_usd         — USD billed for this app's iter loop
        tokens_M         — total tokens (input + output) in millions
        input_tokens_M   — input-token component in millions
        output_tokens_M  — output-token component in millions
        codegen_min      — total OpenCode wall time in minutes
        validation_min   — total validator wall time in minutes

    Cost is computed from the capped ``total_input_tokens`` /
    ``total_output_tokens`` exposed by ``_cells.load_result`` using
    ``MODEL_PRICING[cell_id]``.  When the cell has no published rate
    (``MODEL_PRICING[cell_id] is None``), cost is ``None`` so the panel
    can render a placeholder bar instead of a dollar figure.

    Aggregates ALL apps (successful + unsuccessful) so the means
    reflect every app the agent attempted in the group, not just the
    ones that succeeded.  The 10-iter cap in ``load_result`` keeps
    successful and unsuccessful runs comparable.
    """
    res = load_result(iter_logs_root / app, is_dnc=is_dnc)
    if res is None:
        return None
    return _row_from_result(res, cell_id)


def _row_from_result(res: dict, cell_id: str) -> dict:
    """Project a loaded result.json into the per-app row dict the panels read.

    The Argo proxy for GPT-5.5 reports cache-read tokens inside
    ``total_tokens`` but not inside ``total_input_tokens``, so for GPT-5.5
    only, ``total_tokens > total_input_tokens + total_output_tokens``.
    Anthropic's tokenizer already folds cache reads into
    ``total_input_tokens``.  To keep the input bar in Fig 3c and the cost
    in Fig 3d apples-to-apples across models, we derive a unified
    "effective input" = ``total_tokens - total_output_tokens`` for both
    the input column and the billing input rate.  For Opus/Sonnet this
    is a no-op (total = input + output already).
    """
    input_tokens_eff = res["total_tokens"] - res["total_output_tokens"]
    cost_usd = _cost_usd(cell_id,
                        input_tokens_eff,
                        res["total_output_tokens"])
    return {
        "cost_usd":        cost_usd,
        "tokens_M":        res["total_tokens"] / 1e6,
        "input_tokens_M":  input_tokens_eff / 1e6,
        "output_tokens_M": res["total_output_tokens"] / 1e6,
        "codegen_min":     res["total_opencode_elapsed_s"] / 60.0,
        "validation_min":  res["total_validation_elapsed_s"] / 60.0,
    }


def _load_app_averaged(
    cells_list: list[str], app: str, anchor_cell_id: str,
) -> dict | None:
    """Load this app's row from each cell in ``cells_list`` and return the
    per-key mean.

    ``anchor_cell_id`` drives the pricing rate for cost (so all trials of
    the same model share the same per-token rate).  Cells without a
    loadable ``result.json`` are silently skipped.  Returns ``None`` if
    no cell produced a row.
    """
    rows = []
    for c in cells_list:
        r = _load_app(cell_iter_logs(c), app, anchor_cell_id, is_dnc=False)
        if r is not None:
            rows.append(r)
    if not rows:
        return None
    if len(rows) == 1:
        return rows[0]
    avg: dict = {}
    for key in rows[0].keys():
        vals = [r[key] for r in rows if r.get(key) is not None]
        avg[key] = statistics.mean(vals) if vals else None
    return avg


def main() -> None:
    # Collect per-(cell, group) rows.  ALL apps the agent attempted in
    # the cell are aggregated (successful + unsuccessful) so each model's
    # mean reflects its true per-group resource footprint, not just the
    # successful subset.  Unsuccessful apps are loaded from the cell's
    # DNC archive; the 10-iter cap in load_result keeps them comparable
    # to successful runs.  Placeholder cells with no iter_logs dir
    # silently contribute zero rows.
    per_cell_group: dict[str, dict[str, list[dict]]] = {}
    # Per-(app, model) cell routing — see _cells.py.
    #   PS/PD/Enc apps  -> cells_for() returns the list of all successful
    #                      trials; metrics are AVERAGED across them.
    #   Mod apps        -> cells_for() returns a single first-run cell
    #                      (with gpt55_retry fallback for GPT-5.5).
    # ``cell_id`` is the model anchor (drives color, legend label, cost
    # pricing rate, fallback DNC paths); the real data cells differ per
    # app.  Apps with an empty cells_for() list fall back to the model
    # anchor's DNC archive (first-run failure data).
    from _cells import cells_for
    for cell_id, label, _marker in CELLS:
        dnc_dirs = cell_dnc_dirs(cell_id)
        per_group: dict[str, list[dict]] = {}
        dropped_no_result, dropped_unsucc = [], []
        for grp_label, apps in GROUPS.items():
            rows = []
            for a in apps:
                trial_cells = cells_for(label, a)
                if trial_cells:
                    r = _load_app_averaged(trial_cells, a, cell_id)
                elif a in dnc_dirs:
                    res = load_result(dnc_dirs[a], is_dnc=True)
                    r = _row_from_result(res, cell_id) if res else None
                else:
                    r = None
                if r is None:
                    dropped_no_result.append(a)
                    continue
                rows.append(r)
                if not trial_cells:
                    dropped_unsucc.append(a)
            per_group[grp_label] = rows
        # NEW: "Did Not Complete" group — every app this cell failed on,
        # regardless of complexity bin. Rows come from the cell's DNC
        # archives only, since by construction these apps did not produce
        # an iter_logs result.  Apps that succeed for this cell never appear
        # here.
        dnc_rows = []
        dnc_app_list = []
        for app, dnc_dir in sorted(dnc_dirs.items()):
            res = load_result(dnc_dir, is_dnc=True)
            if res is None:
                continue
            dnc_rows.append(_row_from_result(res, cell_id))
            dnc_app_list.append(app)
        per_group["Did Not Complete"] = dnc_rows
        per_cell_group[cell_id] = per_group
        print(f"[{cell_id} = {label}]")
        print(f"  [included unsuccessful]  {sorted(set(dropped_unsucc))}")
        print(f"  [dropped no result.json] {sorted(set(dropped_no_result))}")
        print(f"  [DNC group apps]         {dnc_app_list}")

    labels = list(GROUPS.keys()) + ["Did Not Complete"]
    # X-tick label = group name only.  Per-cell sample counts (n=X/X/X) are
    # still printed to stdout for inspection but kept off the chart so the
    # x-axis stays visually clean.
    for lbl in labels:
        ns = [len(per_cell_group[c[0]][lbl]) for c in CELLS]
        print(f"  [n] {lbl:30s}  n={'/'.join(str(n) for n in ns)}")
    labels_with_n = [lbl.replace("\n", " ") for lbl in labels]

    # Compute per-(cell, group) means for one row dict key.  Skip None
    # values (e.g. cost when GPT-5.5 has no published rate) so they do not
    # poison the aggregate.  Returns 0 when no rows have a numeric value
    # for the key (consistent with the prior tuple-slot behavior).
    def _mean_at(cell_id, lbl, key):
        vals = [row[key] for row in per_cell_group[cell_id][lbl]
                if row.get(key) is not None]
        return statistics.mean(vals) if vals else 0

    print("Per-group means (" + " / ".join(MODEL_LABELS[c[0]] for c in CELLS) + "):")
    for lbl in labels:
        flat = lbl.replace("\n", " ")
        costs = [_mean_at(c[0], lbl, "cost_usd")        for c in CELLS]
        cg    = [_mean_at(c[0], lbl, "codegen_min")     for c in CELLS]
        vd    = [_mean_at(c[0], lbl, "validation_min")  for c in CELLS]
        tin   = [_mean_at(c[0], lbl, "input_tokens_M")  for c in CELLS]
        tout  = [_mean_at(c[0], lbl, "output_tokens_M") for c in CELLS]
        cost_str = "/".join(
            ("N/A" if MODEL_PRICING.get(c[0]) is None else f"${cost:7.2f}")
            for c, cost in zip(CELLS, costs)
        )
        print(f"  {flat:30s}  "
              f"cost={cost_str}  "
              f"codegen+val={'/'.join(f'{a:5.1f}+{b:4.1f}' for a, b in zip(cg, vd))} min  "
              f"tok in+out={'/'.join(f'{a:.2f}+{b:.2f}' for a, b in zip(tin, tout))} M")

    fig, (ax_w, ax_g, ax_t) = plt.subplots(1, 3, figsize=(12.0, 3.4),
                                           gridspec_kw={"wspace": 0.40})

    n_cells = len(CELLS)
    cluster_w = 0.78
    bar_w = cluster_w / n_cells
    cell_offsets = {
        cell_id: (i - (n_cells - 1) / 2) * bar_w
        for i, (cell_id, _label, _marker) in enumerate(CELLS)
    }
    x = list(range(len(labels)))

    # Hatch used on the TOP segment of stacked bars (validation, output
    # tokens).  Single style across both stacked panels so the per-panel
    # legend reads consistently and the model color stays the dominant
    # encoding.
    TOP_HATCH = "////"
    TOP_ALPHA = 0.70

    def _panel(ax, bottom_key, top_key=None, *, ylabel, title,
               stack_legend=None, ymax=None):
        """Render one panel.

        Single-stack panels pass only ``bottom_key`` (e.g. ``cost_usd``).
        Two-stack panels pass both ``bottom_key`` and ``top_key`` (e.g.
        ``codegen_min`` + ``validation_min``); the top segment renders in
        the same model color with ``TOP_HATCH`` over ``TOP_ALPHA`` so the
        model identity remains visible and the stack component is
        distinguishable.

        ``stack_legend`` (only meaningful when ``top_key`` is set) is a
        ``(bottom_label, top_label)`` pair used to draw a small inset
        legend explaining which segment is which.
        """
        max_v = 0.0

        def _cell_has_numeric(cell_id):
            for lbl in labels:
                for row in per_cell_group[cell_id][lbl]:
                    if row.get(bottom_key) is not None:
                        return True
                    if top_key is not None and row.get(top_key) is not None:
                        return True
            return False

        # Pass 1: real bars.
        for cell_id, _label, _marker in CELLS:
            if not _cell_has_numeric(cell_id):
                continue
            x_off = cell_offsets[cell_id]
            color = MODEL_COLORS[cell_id]
            for i, lbl in enumerate(labels):
                bot = _mean_at(cell_id, lbl, bottom_key)
                top = _mean_at(cell_id, lbl, top_key) if top_key else 0
                if bot == 0 and top == 0:
                    continue
                # Bottom segment: solid model color.
                ax.bar(i + x_off, bot, color=color, width=bar_w,
                       edgecolor="black", linewidth=0.5, zorder=2)
                # Top segment: model color + hatch (only on stacked panels).
                if top_key is not None and top > 0:
                    ax.bar(i + x_off, top, bottom=bot, color=color,
                           hatch=TOP_HATCH, alpha=TOP_ALPHA,
                           width=bar_w, edgecolor="black", linewidth=0.5,
                           zorder=2)
                # Track max bar height (stack total) and per-app outliers
                # for y-axis sizing.
                max_v = max(max_v, bot + top)
                for row in per_cell_group[cell_id][lbl]:
                    bv = row.get(bottom_key) or 0
                    tv = (row.get(top_key) or 0) if top_key else 0
                    max_v = max(max_v, bv + tv)

        # Pass 2: placeholder bars for cells with no numeric data anywhere
        # in this panel.  Same hue at low alpha so the GPT-5.5 reservation
        # reads as faded-color, not generic gray.
        placeholder_h = max_v * PLACEHOLDER_HEIGHT_FRAC if max_v else 0.05
        for cell_id, _label, _marker in CELLS:
            if _cell_has_numeric(cell_id):
                continue
            x_off = cell_offsets[cell_id]
            ph_color = MODEL_COLORS[cell_id]
            for i in range(len(labels)):
                ax.bar(i + x_off, placeholder_h, width=bar_w,
                       color=ph_color, alpha=PLACEHOLDER_ALPHA,
                       edgecolor=ph_color, linewidth=0.5, zorder=1)

        ax.set_ylabel(ylabel)
        ax.set_xticks(x)
        # No rotation per user preference; use short single-line
        # abbreviations so each label fits within its ~0.25in tick slot
        # (axes width 1.25in / 5 ticks).  Caption spells out the full
        # group names.
        ax.set_xticklabels(_two_line_labels(labels_with_n),
                           fontsize=6, rotation=0)
        ax.tick_params(axis="x", which="both", length=0)
        if ymax is not None:
            ax.set_ylim(0, ymax)
        else:
            ax.set_ylim(0, (max_v if max_v else 1.0) * 1.22)

        # Stack legend kept on the axes object so the standalone-panel
        # caller can position it below the approach legend in the top-left
        # corner.  Stored on ``ax`` via a side attribute rather than
        # rendered here so the caller controls both legends' placement
        # without colliding (matplotlib drops earlier ax.legend() calls
        # unless add_artist is used; doing both legends in one place
        # keeps the layout explicit).
        ax._stack_legend_handles = None
        if top_key is not None and stack_legend is not None:
            bot_label, top_label = stack_legend
            # White fill so the rectangle marker reads as a pure
            # solid/hatched key (not "the gray model").  Edge stays
            # black; the hatch lines on the top patch sit on a white
            # background.
            bot_patch = mpatches.Patch(facecolor="white", edgecolor="black",
                                       linewidth=0.5, label=bot_label)
            top_patch = mpatches.Patch(facecolor="white", edgecolor="black",
                                       linewidth=0.5, hatch=TOP_HATCH,
                                       label=top_label)
            ax._stack_legend_handles = [bot_patch, top_patch]

    _panel(ax_w, "cost_usd",
           ylabel="API cost per app (USD)",
           title="(a) API cost",
           ymax=500)
    _panel(ax_g, "codegen_min", "validation_min",
           ylabel="Time per app (min)",
           title="(b) LLM code-gen + validation time",
           stack_legend=("Code Gen.", "Validation"),
           ymax=350)
    _panel(ax_t, "input_tokens_M", "output_tokens_M",
           ylabel="Tokens per app (M)",
           title="(c) Token cost (input + output)",
           stack_legend=("Input", "Output"),
           ymax=120)

    # Single model legend below the figure.  GPT-5.5 (or any pending
    # cell) is rendered in its placeholder color with a "(pending)" tag
    # so the reservation is explicit.
    handles = []
    for cell_id, cell_label, _marker in CELLS:
        has_data_anywhere = any(
            per_cell_group[cell_id][lbl] for lbl in labels
        )
        if has_data_anywhere:
            handles.append(
                mpatches.Patch(facecolor=MODEL_COLORS[cell_id],
                               edgecolor="black", linewidth=0.5,
                               label=cell_label))
        else:
            handles.append(
                mpatches.Patch(facecolor=MODEL_COLORS[cell_id],
                               alpha=PLACEHOLDER_ALPHA,
                               edgecolor="black", linewidth=0.5,
                               label=f"{cell_label} (pending)"))
    fig.legend(handles=handles, loc="lower center",
               bbox_to_anchor=(0.5, -0.12),
               ncol=len(CELLS), fontsize=10,
               frameon=True, fancybox=False, edgecolor="black",
               handlelength=1.2, handletextpad=0.5,
               columnspacing=1.5, borderpad=0.4)

    fig.tight_layout()

    stem = "fast_tier_per_group_summary"
    fig.savefig(OUT_DIR / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(OUT_DIR / f"{stem}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    _mirror_to_papers(stem)
    print(f"\nSaved: {OUT_DIR}/{stem}.{{pdf,png}} (and mirrored)")

    # Standalone per-panel renders.  Each panel becomes its own self-
    # contained PDF (with the same model legend embedded at the bottom)
    # so the LaTeX side can lay them out as referable subfigures via the
    # ``subcaption`` package.  The combined PDF above stays in place for
    # any caller that still wants the bundled view.
    # Every standalone panel hosts its OWN approach (model color) legend
    # in the top-left corner.  Panels b/c stack the per-panel stack key
    # (Code Gen./Validation, Input/Output) BELOW the approach legend in
    # the same top-left corner.
    standalone_specs = [
        ("a", "cost_usd",       None,             None,
         "API cost per app (USD)",
         "(a) API cost", 500, True),
        ("b", "codegen_min",    "validation_min", ("Code Gen.", "Validation"),
         "Time per app (min)",
         "(b) LLM code-gen + validation time", 350, True),
        ("c", "input_tokens_M", "output_tokens_M", ("Input", "Output"),
         "Tokens per app (M)",
         "(c) Token cost (input + output)", 120, True),
    ]
    for tag, bottom_key, top_key, stack_legend, ylabel, title, ymax, with_approach in standalone_specs:
        sfig, sax = plt.subplots(figsize=(1.72, 1.6))
        _panel(sax, bottom_key, top_key,
               ylabel=ylabel, title=title, stack_legend=stack_legend, ymax=ymax)
        # Top-left corner stack of legends inside the plot rectangle:
        # approach legend (model color) above the stack key (hatch),
        # both 1 column, both with a thin black frame.  The stack
        # legend's anchor y drops to sit just below the approach
        # legend when both are present.
        next_y = 0.99
        if with_approach:
            approach_leg = sax.legend(
                handles=handles,
                loc="upper left", bbox_to_anchor=(0.01, next_y),
                ncol=1, fontsize=6,
                frameon=True, fancybox=False, edgecolor="black",
                handlelength=1.0, handletextpad=0.3,
                labelspacing=0.20, borderpad=0.25, borderaxespad=0.0,
            )
            sax.add_artist(approach_leg)
            # Reserve ~0.30 axes-units (3 entries x ~0.10) for the
            # approach legend so the stack legend lands just below it.
            next_y -= 0.32
        stack_handles = getattr(sax, "_stack_legend_handles", None)
        if stack_handles:
            sax.legend(
                handles=stack_handles,
                loc="upper left", bbox_to_anchor=(0.01, next_y),
                ncol=1, fontsize=6,
                frameon=True, fancybox=False, edgecolor="black",
                handlelength=1.0, handletextpad=0.3,
                labelspacing=0.20, borderpad=0.25, borderaxespad=0.0,
            )
        sfig.tight_layout()
        # Pin BOTH top and bottom margins so this bar panel's axes-frame
        # top + bottom align with Fig 3d's scatter panel in the rendered
        # paper figure.  Same values (top=0.99, bottom=FIG3_BOTTOM_MARGIN
        # =0.20) are used in _plot_loc_vs_wall_and_tokens.py — keep in
        # sync.  Saving WITHOUT bbox_inches="tight" so the PDF honors
        # figsize exactly (1.72x1.6in); otherwise the saved PDF dimensions
        # vary per panel based on label widths and the alignment breaks
        # once LaTeX scales each PDF to \linewidth.
        sfig.subplots_adjust(top=0.99, bottom=0.20)
        sstem = f"{stem}_{tag}"
        sfig.savefig(OUT_DIR / f"{sstem}.pdf", bbox_inches=None)
        sfig.savefig(OUT_DIR / f"{sstem}.png", dpi=300, bbox_inches=None)
        plt.close(sfig)
        _mirror_to_papers(sstem)
        print(f"Saved standalone: {OUT_DIR}/{sstem}.{{pdf,png}} (and mirrored)")


if __name__ == "__main__":
    main()
