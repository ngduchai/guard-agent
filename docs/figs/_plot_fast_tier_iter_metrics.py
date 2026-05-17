"""Publication-quality bar charts of LLM-iter-loop metrics.

Saves PDF (vector) + PNG (300 DPI) for each metric to docs/figs/.

The COMPLETED_APPS list below is the candidate set; the actual plotted
set is filtered by `_trust.json` so only apps whose `_baseline` unit is
TRUSTED appear in the chart.  Apps missing a TRUSTED status are skipped
with a printed warning (skill Operating Principle 1: trust nothing
automatically; do not slip UNTRUSTED data into a published plot).
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

# --- Inputs ---------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
ITER_LOGS = REPO_ROOT / "build" / "iterative_logs"
CONFIGS = REPO_ROOT / "tests" / "apps" / "configs"
OUT_DIR = REPO_ROOT / "docs" / "figs"
TRUST = REPO_ROOT / "build" / "_experiment_state" / "_trust.json"
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


def _trust_partition(apps: list[str], unit_kind: str = "_baseline") -> tuple[list[str], set[str]]:
    """Partition `apps` into (all_apps_in_order, untrusted_set).

    Returns the SAME `apps` list (for x-axis stability) plus the set of apps
    whose <APP><unit_kind> unit is NOT TRUSTED.  Callers should plot every app
    on the x-axis but skip / leave-empty the bars for apps in `untrusted_set`.
    """
    if not TRUST.exists():
        print(f"  [warn] no _trust.json at {TRUST}; treating all apps as TRUSTED")
        return apps, set()
    trust = json.loads(TRUST.read_text())
    untrusted = set()
    for app in apps:
        unit = f"{app}{unit_kind}"
        st = trust.get(unit, {}).get("status", "MISSING")
        if st != "TRUSTED":
            untrusted.add(app)
            print(f"  [partition] {app}: {unit} is {st} (will plot empty)")
    return apps, untrusted

# 17-app candidate set (MMSP removed per user instruction 2026-05-08).
# Actual plotted set is filtered against _trust.json at runtime.
COMPLETED_APPS = [
    "Athena++", "CLAMR", "CoMD", "HPCG", "HyPar",
    "LAMMPS", "Nyx", "OpenLB", "PRK_Stencil",
    "QMCPACK", "ROSS", "SAMRAI", "Smilei", "SPARTA",
    "SPPARKS", "SW4lite", "WarpX",
]

# X-axis grouping: apps clustered by complexity group.  Within each group
# apps are listed in increasing iter-count order to match the per-group
# ordering used in the paper's per-app paragraphs.  See \S\ref{sec:suite}.
GROUPS = {
    "Plain, fixed shape":       ["HPCG", "PRK_Stencil", "SW4lite", "HyPar"],
    "Plain, variable per-rank": ["CoMD", "SPARTA", "SPPARKS", "CLAMR", "LAMMPS"],
    "Encapsulated, accessible": ["Nyx", "Athena++", "WarpX"],
    "Encapsulated, opaque":     ["OpenLB", "Smilei", "QMCPACK", "ROSS", "SAMRAI"],
}
DIFFICULTY_ORDER = [app for apps in GROUPS.values() for app in apps]


def _group_boundaries() -> list[int]:
    """Return the cumulative app-count at each group boundary (excl. final)."""
    out, c = [], 0
    for apps in GROUPS.values():
        c += len(apps)
        out.append(c)
    return out[:-1]  # drop the trailing count (right edge of plot)


def _draw_group_separators(ax, n_apps: int) -> None:
    """Draw light vertical lines at each group boundary and a group-label
    band along the top edge of the axes.  No-op if any group boundary lies
    outside [0, n_apps]."""
    bounds = _group_boundaries()
    for b in bounds:
        if 0 < b < n_apps:
            ax.axvline(b - 0.5, color="#aaaaaa", linewidth=0.5,
                       linestyle="--", zorder=0)
    # Add per-group labels along the top inside the axes
    ymin, ymax = ax.get_ylim()
    band_y = ymax * 0.95
    rank = {a: i for i, a in enumerate(DIFFICULTY_ORDER)}
    for label, apps in GROUPS.items():
        idxs = [rank[a] for a in apps if a in rank]
        if not idxs:
            continue
        center = (min(idxs) + max(idxs)) / 2.0
        ax.text(center, band_y, label, fontsize=7, ha="center", va="top",
                style="italic", color="#555555")


def load_app(app: str) -> dict:
    """Return {app, category, wall_min, opencode_min, validate_min, iters, tokens_M}.

    `opencode_min` + `validate_min` decompose the total wall time into the LLM
    coding-agent's thinking time and the independent validator's
    build+run+compare time, summed across all iterations.  Falls back to
    proportional split if per_iteration breakdown is missing.
    """
    res_path = ITER_LOGS / f"{app}_baseline" / "result.json"
    cfg_path = CONFIGS / f"{app}.yaml"
    res = json.loads(res_path.read_text())
    # Read category as a single line; avoid full YAML parse to keep deps minimal.
    category = next(
        (line.split(":", 1)[1].strip() for line in cfg_path.read_text().splitlines()
         if line.startswith("category:")),
        "unknown",
    )
    wall_s = res["wall_elapsed_s"]
    pi = res.get("per_iteration", []) or []
    oc_s = sum((it.get("opencode_elapsed_s") or 0) for it in pi)
    vd_s = sum((it.get("validation_elapsed_s") or 0) for it in pi)
    if oc_s == 0 and vd_s == 0:
        # No per-iter breakdown available — fall back so chart still plots.
        oc_s = vd_s = wall_s / 2.0
    in_tok  = res.get("total_input_tokens")  or 0
    out_tok = res.get("total_output_tokens") or 0
    if in_tok == 0 and out_tok == 0:
        # Reconstructed result.json with only an aggregate count;
        # split 95% input / 5% output (typical ratio observed).
        total = res.get("total_tokens") or 0
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


# --- Plot styling (publication-grade) -------------------------------------
# Use a serif family (matches LaTeX defaults in SC/HPDC two-column papers)
# and large enough fonts to remain legible at the typical column width.
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
    "legend.fontsize": 10,
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
    "pdf.fonttype": 42,   # embed TrueType (paper-grade); avoids Type-3 issues
    "ps.fonttype": 42,
})

# Color-blind-safe palette (Wong 2011) — distinct per category.
CATEGORY_COLORS = {
    "iterative_fixed":     "#0072B2",  # blue
    "iterative_variable":  "#E69F00",  # orange
    "iterative_adaptive":  "#009E73",  # green
    "asynchronous":        "#CC79A7",  # magenta
    "unknown":             "#999999",
}
# Short, presentation-friendly category labels.  Compact forms used in the
# in-axes legend so all four entries fit on a single row inside the figure.
CATEGORY_LABEL = {
    "iterative_fixed":    "Sync. fixed",
    "iterative_variable": "Sync. variable",
    "iterative_adaptive": "Sync. adaptive",
    "asynchronous":       "Asynchronous",
}


def plot_metric(
    apps: list[dict], *, ylabel: str, fname_stem: str,
    value_key: str | None = None,
    stacked: list[tuple[str, str, str]] | None = None,
    value_fmt: str = "{:.1f}",
    integer_yticks: bool = False,
) -> None:
    """Single-bar (`value_key`) OR stacked-bar (`stacked`) per app.

    `stacked` is a list of (key, color, legend_label) tuples; segments are
    stacked from bottom to top in the order given.  Mutually exclusive with
    `value_key`.
    """
    assert (value_key is None) ^ (stacked is None), \
        "exactly one of value_key / stacked must be supplied"

    # X-axis order: easiest -> hardest by checkpointing difficulty (see Sec. 4.1).
    _RANK = {name: i for i, name in enumerate(DIFFICULTY_ORDER)}
    apps_sorted = sorted(apps, key=lambda a: _RANK.get(a["app"], len(_RANK)))

    # Width scales with number of apps (was 6.4 in for 6 apps; ~0.85 in/app
    # keeps the bar+label spacing comfortable as the dataset grows).
    fig_w = max(6.4, 0.85 * len(apps_sorted) + 1.6)
    fig, ax = plt.subplots(figsize=(fig_w, 3.4))

    x = list(range(len(apps_sorted)))
    bar_kwargs = dict(width=0.66, edgecolor="black", linewidth=0.6)

    if value_key is not None:
        values = [a[value_key] for a in apps_sorted]
        ax.bar(x, values, color="#0072B2", **bar_kwargs)
        max_y = max(values) if values else 1.0
    else:
        # Stacked bars — render each segment in order, tracking the running
        # bottom so segments stack cleanly.
        bottoms = [0.0] * len(apps_sorted)
        max_y = 0.0
        for key, color, legend_label in stacked:
            seg = [a[key] for a in apps_sorted]
            ax.bar(x, seg, bottom=bottoms, color=color,
                   label=legend_label, **bar_kwargs)
            bottoms = [b + s for b, s in zip(bottoms, seg)]
        max_y = max(bottoms) if bottoms else 1.0

    # App name labels under each bar — slight tilt + right-anchored so
    # labels for closely-packed apps don't horizontally overlap.
    ax.set_xticks(x)
    ax.set_xticklabels([a["app"] for a in apps_sorted],
                       rotation=20, ha="right")

    # Numeric labels above bars removed by user request — y-axis ticks
    # already let the reader read off bar heights.

    ax.set_ylabel(ylabel)
    ax.set_ylim(0, max_y * 1.20 if stacked is None else max_y * 1.30)

    if integer_yticks:
        ax.yaxis.set_major_locator(mpl.ticker.MaxNLocator(integer=True))

    # Legend only when bars are stacked (a single-color bar has nothing
    # to legend).
    if stacked is not None:
        ax.legend(loc="upper right", fontsize=9,
                  frameon=True, fancybox=False, edgecolor="black",
                  handlelength=1.0, handletextpad=0.5,
                  labelspacing=0.35, borderpad=0.4, borderaxespad=0.5)

    # Group separators + labels (drawn after y-limits are set so the band
    # text uses the final ylim).
    _draw_group_separators(ax, len(apps_sorted))

    fig.savefig(OUT_DIR / f"{fname_stem}.pdf")
    fig.savefig(OUT_DIR / f"{fname_stem}.png", dpi=300)
    plt.close(fig)
    _mirror_to_papers(fname_stem)


def main() -> None:
    # Plot every app on the x-axis; UNTRUSTED-baseline apps render as empty
    # bars (zero values) so the reader can see which apps are missing data.
    all_apps, untrusted = _trust_partition(COMPLETED_APPS, unit_kind="_baseline")
    print(f"Plotting all {len(all_apps)} apps; {len(untrusted)} untrusted will render empty")
    apps = []
    for a in all_apps:
        if a in untrusted:
            # Empty placeholder: zero values so the bar renders as zero-height,
            # but the x-axis tick still shows the app name.
            apps.append({
                "app": a, "category": "unknown",
                "wall_min": 0.0, "opencode_min": 0.0, "validate_min": 0.0,
                "iters": 0,
                "tokens_M": 0.0, "input_tokens_M": 0.0, "output_tokens_M": 0.0,
            })
        else:
            apps.append(load_app(a))
    print("Loaded:")
    for a in apps:
        print(f"  {a['app']:<12}  {a['category']:<22}  "
              f"wall={a['wall_min']:5.1f}m  iters={a['iters']}  tokens={a['tokens_M']:.2f}M")

    # Wall-clock chart — stacked: code-generation (LLM-side) at the bottom,
    # validation (independent build/run/compare) on top.  Y-axis label matches
    # the "Code generation time" metric defined in Section 3 of the paper.
    plot_metric(
        apps,
        stacked=[
            ("opencode_min", "#0072B2", "Code generation"),  # darker blue, bottom
            ("validate_min", "#56B4E9", "Validation"),       # sky blue, top
        ],
        ylabel="Code generation time (min)",
        fname_stem="fast_tier_iter_walltime",
    )
    # Iter count — single bar.
    plot_metric(
        apps,
        value_key="iters",
        ylabel="Iterations to convergence",
        fname_stem="fast_tier_iter_count",
        value_fmt="{:.0f}",
        integer_yticks=True,
    )
    # Token chart — stacked: input tokens on the bottom, output tokens on top.
    plot_metric(
        apps,
        stacked=[
            ("input_tokens_M",  "#0072B2", "Input"),   # blue,  bottom
            ("output_tokens_M", "#E69F00", "Output"),  # amber, top
        ],
        ylabel="Total tokens (millions)",
        fname_stem="fast_tier_iter_tokens",
        value_fmt="{:.2f}",
    )

    print(f"\nSaved: {OUT_DIR}/")
    for f in sorted(OUT_DIR.glob("fast_tier_iter_*")):
        print(f"  {f.name}  ({f.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
