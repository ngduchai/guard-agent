"""Vanilla / LLM-modified comparison bar charts for the fast tier.

Three figures, one per metric:
  1. Failure-free wall-clock      (small-nofail elapsed_s mean)
  2. Failure-injected wall-clock  (small-once  elapsed_s mean)
  3. Per-frame checkpoint size    (`checkpoint_per_frame_bytes` mean)

The upstream-reference series is loaded by `load_app()` (so the data is
available to anyone importing this module) but is **deliberately excluded
from all three plots**: the reference benchmark cells were collected under
the wrong settings (mismatched app args / cadence / build flags) and are
not directly comparable to the LLM-modified runs.  Re-add the Reference
series to `time_series_ff` / `time_series_once` / the checkpoint chart's
series list once the reference benchmark is re-run with the correct
settings.

Data sources are catalogued in `docs/data_locations.md`:

  * Vanilla failure-free elapsed   — `<APP>_reference` summary[`small-nofail`]
                                     [`original`].elapsed_s.mean
                                     (§3.3 schema; vanilla-as-no-resilience
                                     floor measured at the same workload size
                                     as the LLM/Reference bars).
  * Vanilla failure-injected       — **synthesised** as
                                     `vanilla_nofail × (1 + once.delay_fraction)`
                                     per §4.4 of data_locations.md.  The
                                     coefficient comes from
                                     `tests/apps/configs/_frequencies.yaml`
                                     (`once.delay_fraction = 0.5`).  Vanilla
                                     cannot recover from an injected fault, so
                                     the only valid interpretation is "partial
                                     work to the injection point + a full
                                     restart from scratch".  Reading raw
                                     `original`/`small-once` rows directly was
                                     wrong even where they exist (CoMD, HPCG)
                                     because the runner does not actually
                                     inject for codebase=`original`, so those
                                     rows are just nofail timing relabelled.
  * LLM-modified elapsed + ckpt    — `<APP>_baseline`  summary[scenario]
                                     [`resilient`] (§3.3 schema).
  * Reference elapsed + ckpt       — `<APP>_reference` summary[scenario]
                                     [`resilient`] (§3.3 schema).

Visual marker:  synthesised bars (vanilla failure-injected) are drawn with a
diagonal hatch pattern and footnoted in the legend as "(synthetic)" so the
reader can see at a glance which bars are measured and which are modelled.

Re-uses the rcParams + Wong palette + PDF/PNG-300dpi conventions of the
sibling `_plot_fast_tier_iter_metrics.py`.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

# --- Inputs ---------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS = REPO_ROOT / "results"
CONFIGS = REPO_ROOT / "tests" / "apps" / "configs"
OUT_DIR = REPO_ROOT / "docs" / "figs"
# Mirror PDFs into the FlexScience paper's figures dir (this script is the
# 3-bar Vanilla/LLM-modified/Reference 6-app generator that backs that
# paper's main results figures; the eScience paper uses its own
# multi-model script).
PAPER_FIGURES_DIRS = [
    REPO_ROOT / "docs" / "paper" / "FlexScience" / "figures",
]
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _bench_dir(app: str, suffix: str) -> Path:
    """Map (app, suffix) to the post-2026-05 results/ data layout.

    suffix="baseline"  -> results/models/opus47/bench/<APP>/
    suffix="reference" -> results/reference/<APP>/
    """
    if suffix == "baseline":
        return RESULTS / "models" / "opus47" / "bench" / app
    if suffix == "reference":
        return RESULTS / "reference" / app
    raise ValueError(f"unknown bench suffix: {suffix!r}")


def _mirror_to_papers(stem: str) -> None:
    """Copy <stem>.pdf from OUT_DIR into each active paper's Figures dir."""
    import shutil
    src = OUT_DIR / f"{stem}.pdf"
    if not src.exists():
        return
    for paper_dir in PAPER_FIGURES_DIRS:
        if paper_dir.exists():
            shutil.copy2(src, paper_dir / f"{stem}.pdf")

# 6 apps where the reference's failure-injected cell exhibits REAL recovery
# (once/nofail ratio < 1.30x — i.e. attempt_2 actually restores from a
# checkpoint instead of restarting from scratch).  These are the only apps
# where a Reference bar on the failure-injected chart is methodologically
# honest.  See data_locations.md §4.1 for the broader pattern; the previous
# 12-app set had 8 apps where reference attempt_2 silently re-ran from
# scratch, producing the misleading 1.5x ratio identical to synthetic vanilla.
#
# Athena++ and LAMMPS were re-collected with proper restart flags but only
# the small-once cell was re-run; their small-nofail (vanilla + reference
# nofail) data is sourced from the archived `*_reference.UNTRUSTED_pre_bench_
# recovery_*` bench, where those nofail measurements are uncontaminated by
# the recovery-flag issue.  See `_load_archived_nofail_fallback` below.
# 16 apps with complete trusted data per the latest status table.
# Excluded: HyPar (UNTRUSTED — friendly-fire bug killed it, needs re-run) and
# PRK_Stencil (UNTRUSTED — wallclock cap fired during reference once-cell).
# SAMRAI is listed but its _baseline bench is UNTRUSTED so the comparison
# charts' missing-data filter will drop it automatically (LLM bars require
# baseline bench data).
# FlexScience paper covers exactly these 6 apps in the displayed order
# (matches the prose in docs/paper/FlexScience/main.tex lines 280-298,
# ordered by increasing checkpointing difficulty).
COMPLETED_APPS = ["HPCG", "CoMD", "OpenLB", "SPARTA", "Athena++", "LAMMPS"]
DIFFICULTY_ORDER = list(COMPLETED_APPS)
# Group separators are intentionally absent in the FlexScience layout: 6
# apps don't warrant complexity-band labels.
GROUPS: dict[str, list[str]] = {}


def _draw_group_separators(ax, n_apps: int) -> None:
    """No-op for the FlexScience 6-app layout (no complexity bands)."""
    return

# Trust filter: comparison charts need BOTH _baseline AND _reference
# TRUSTED, since each bar shows LLM-vs-reference side-by-side.
TRUST = REPO_ROOT / "build" / "_experiment_state" / "_trust.json"


def _trust_partition_comparison(apps):
    """Return (all_apps, untrusted_baseline_set, untrusted_ref_set).

    All apps stay on the x-axis.  The two sets identify which sides should
    be blanked out (reader sees an "n/a" annotation in place of the bar).
    """
    if not TRUST.exists():
        print(f"  [warn] no _trust.json at {TRUST}; treating all apps as TRUSTED")
        return apps, set(), set()
    import json as _json
    trust = _json.loads(TRUST.read_text())
    untrusted_b, untrusted_r = set(), set()
    for app in apps:
        b = trust.get(f"{app}_baseline", {}).get("status", "MISSING")
        r = trust.get(f"{app}_reference", {}).get("status", "MISSING")
        if b != "TRUSTED":
            untrusted_b.add(app)
        if r != "TRUSTED":
            untrusted_r.add(app)
    if untrusted_b:
        print(f"  [partition] LLM bars blanked (baseline UNTRUSTED): {sorted(untrusted_b)}")
    if untrusted_r:
        print(f"  [partition] Ref bars blanked (reference UNTRUSTED): {sorted(untrusted_r)}")
    return apps, untrusted_b, untrusted_r

# Palette: Wong 2011 (color-blind safe). LLM = blue, Reference = vermillion,
# Vanilla = neutral gray (chosen because vanilla is the no-resilience floor —
# a reference baseline rather than a competing implementation).
COLOR_LLM = "#0072B2"
COLOR_REF = "#D55E00"
COLOR_VAN = "#777777"
# Category abbreviations rendered under each app's x-tick label.
CATEGORY_ABBREV = {
    "iterative_fixed":    "sync-fixed",
    "iterative_variable": "sync-variable",
    "iterative_adaptive": "sync-adaptive",
    "asynchronous":       "asynchronous",
}
CAT_ORDER = list(CATEGORY_ABBREV.keys())


# --- Data ----------------------------------------------------------------

def _read_category(app: str) -> str:
    cfg = CONFIGS / f"{app}.yaml"
    for line in cfg.read_text().splitlines():
        if line.startswith("category:"):
            return line.split(":", 1)[1].strip()
    return "unknown"


def _load_once_delay_fraction() -> float:
    """Return the `once.delay_fraction` from `_frequencies.yaml`.

    Used to synthesise the vanilla failure-injected bar per
    data_locations.md §4.4.  Tiny ad-hoc parser keeps the script
    PyYAML-free (matches the convention in `_plot_fast_tier_iter_metrics.py`).
    """
    fp = CONFIGS / "_frequencies.yaml"
    in_once = False
    for raw in fp.read_text().splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if indent == 2 and stripped.startswith("once:"):
            in_once = True
            continue
        if in_once and indent <= 2 and stripped.endswith(":"):
            break  # next sibling key — leave the once block
        if in_once and stripped.startswith("delay_fraction:"):
            return float(stripped.split(":", 1)[1].strip())
    raise RuntimeError("once.delay_fraction not found in _frequencies.yaml")


# Per data_locations.md §4.4: vanilla.once = vanilla.nofail × (1 + delay_fraction).
ONCE_DELAY_FRACTION = _load_once_delay_fraction()
VANILLA_ONCE_MULT = 1.0 + ONCE_DELAY_FRACTION


def _scenario_summary(raw: dict, scenario: str, codebase: str) -> dict | None:
    """Return the summary block for (scenario, codebase) or None.

    2026-05-09: also augments the elapsed_s sub-block with `median` computed
    on-the-fly from runs[].  This is robust against stale summary blocks
    (which can drift when a bench is extended via --resume without the
    summary being regenerated — observed for OpenLB_baseline once-cell
    after v40b).  Callers can read either `mean` or `median` from the
    returned dict; for high-variance cells (CV > 10%) median is the
    statistically honest summary.
    """
    block = raw.get("summary", {}).get(scenario, {}).get(codebase)
    if block is None:
        return None
    elapsed = [r["elapsed_s"] for r in raw.get("runs", [])
               if r.get("scenario_name") == scenario and r.get("codebase") == codebase]
    if elapsed:
        import statistics as _stats
        if "elapsed_s" not in block:
            block["elapsed_s"] = {}
        # Always overwrite with run-derived stats so a stale summary block
        # cannot mislead the chart.  Mean and median both computed fresh.
        block["elapsed_s"]["n"] = len(elapsed)
        block["elapsed_s"]["mean"] = _stats.mean(elapsed)
        block["elapsed_s"]["median"] = _stats.median(elapsed)
        block["elapsed_s"]["min"] = min(elapsed)
        block["elapsed_s"]["max"] = max(elapsed)
        if len(elapsed) > 1:
            block["elapsed_s"]["std"] = _stats.stdev(elapsed)
            block["elapsed_s"]["cv"] = _stats.stdev(elapsed) / _stats.mean(elapsed)
        else:
            block["elapsed_s"]["std"] = 0.0
            block["elapsed_s"]["cv"] = 0.0
    return block


def _load_archived_nofail_fallback(app: str, scenario: str, codebase: str) -> float | None:
    """When the active `_reference` benchmark was re-run with --skip-correctness
    and dropped the small-nofail cells (e.g. Athena++, LAMMPS post-recovery-fix
    re-collection), fall back to the most-recent
    `_reference.UNTRUSTED_pre_bench_recovery_*` archive for the requested cell.

    Only nofail cells are recovered this way — the once-cell measurements in the
    archive are the very ones marked UNTRUSTED and must not be reused.
    """
    if "nofail" not in scenario:
        return None
    archives = sorted(
        (RESULTS / "reference").glob(f"{app}.UNTRUSTED_pre_bench_recovery_*"),
        key=lambda p: p.stat().st_mtime, reverse=True
    )
    for arc in archives:
        p = arc / "benchmarks" / "raw_metrics.json"
        if not p.exists(): continue
        d = json.loads(p.read_text())
        cell = d.get("summary", {}).get(scenario, {}).get(codebase, {})
        m = cell.get("elapsed_s", {}).get("mean")
        if m is not None:
            return m
    return None


def _per_frame_bytes(raw: dict, codebase: str) -> float | None:
    """Average `checkpoint_per_frame_bytes` over the small-nofail runs of
    the given codebase that recorded a non-null value.  Falls back to
    None if no run did.

    Uses NOFAIL-only data because the once (post-injection) cell measures
    the residual scratch dir AFTER attempt_2 finishes — which for some
    apps (notably QMCPACK_baseline: nofail 800 B vs once 40 B) is much
    smaller than the steady-state per-write checkpoint cost recorded by
    nofail.  Averaging both gives a meaningless mid-value (e.g. 420 B
    for QMCPACK) that doesn't match either lifecycle phase.
    Pre-2026-05-08 this function averaged across both scenarios.
    """
    vals = [
        r.get("checkpoint_per_frame_bytes")
        for r in raw.get("runs", [])
        if r.get("codebase") == codebase
        and r.get("scenario_name") == "small-nofail"
        and r.get("checkpoint_per_frame_bytes")
    ]
    return sum(vals) / len(vals) if vals else None


def load_app(app: str) -> dict:
    """Pull the three metrics for vanilla, LLM (_baseline) and Ref (_reference).

    Returns a dict with keys: app, category,
        ff_van, ff_llm, ff_ref       (failure-free elapsed_s mean; None if missing)
        once_van, once_llm, once_ref (failure-injected elapsed_s mean;
                                      once_van is SYNTHETIC per data_locations.md §4.4)
        frame_llm, frame_ref         (per-frame checkpoint bytes; None if missing)
    """
    out = {"app": app, "category": _read_category(app)}
    for variant, suffix in [("llm", "baseline"), ("ref", "reference")]:
        path = _bench_dir(app, suffix) / "benchmarks" / "raw_metrics.json"
        raw = json.loads(path.read_text()) if path.exists() else None
        if raw is None:
            out[f"ff_{variant}"] = None
            out[f"once_{variant}"] = None
            out[f"frame_{variant}"] = None
            continue
        ff = _scenario_summary(raw, "small-nofail", "resilient")
        on = _scenario_summary(raw, "small-once",  "resilient")
        # 2026-05-09: switched to MEDIAN for high-variance cells (CV>10%)
        # — these are noisy by inherent disk-fsync behavior and the median
        # is the only honest summary statistic.  For low-variance cells
        # (CV<=10%) mean and median agree to <2% so either works.  v40/v40b
        # at n=10/5 confirmed this for PRK_Stencil_ref nofail (CV 19%) and
        # OpenLB_baseline once (CV 59% — one anomaly + 4 tight values).
        def _pick(block: dict | None) -> float | None:
            if block is None:
                return None
            es = block["elapsed_s"]
            cv = es.get("cv", 0)
            return es["median"] if cv > 0.10 else es["mean"]
        out[f"ff_{variant}"]    = _pick(ff)
        out[f"once_{variant}"]  = _pick(on)
        out[f"frame_{variant}"] = _per_frame_bytes(raw, "resilient")
        # OpenLB_baseline once-cell exclusion REMOVED 2026-05-09: summary
        # block was re-aggregated from n=5 runs; chart now reads median
        # 126.23s (per _pick above for CV=59%) which honestly represents
        # the typical run.
        # Recovery fallback: if the active _reference bench dropped the
        # small-nofail/resilient cell (Athena++/LAMMPS after the recovery-fix
        # re-collection), pull it from the archived UNTRUSTED bench where
        # the nofail measurement is uncontaminated by the once-cell issue.
        if suffix == "reference" and out[f"ff_{variant}"] is None:
            v = _load_archived_nofail_fallback(app, "small-nofail", "resilient")
            if v is not None:
                out[f"ff_{variant}"] = v

    # Vanilla failure-free: measured at `_reference/<APP>` summary[small-nofail]
    # [original] (data_locations.md §3.3).  Fall back to `_baseline/<APP>` if
    # the active `_reference/<APP>` doesn't have it, then to the archived
    # UNTRUSTED bench (post-recovery-fix re-collection dropped these cells).
    out["ff_van"] = None
    for suffix in ("reference", "baseline"):
        ref_path = _bench_dir(app, suffix) / "benchmarks" / "raw_metrics.json"
        if not ref_path.exists():
            continue
        ref_raw = json.loads(ref_path.read_text())
        van_ff = _scenario_summary(ref_raw, "small-nofail", "original")
        if van_ff:
            # Use median for high-CV vanilla cells (consistent with _pick policy
            # above for resilient cells).  Vanilla is typically rock-solid
            # (CV<2%) so mean and median agree closely.
            es = van_ff["elapsed_s"]
            out["ff_van"] = es["median"] if es.get("cv", 0) > 0.10 else es["mean"]
            break
    if out["ff_van"] is None:
        out["ff_van"] = _load_archived_nofail_fallback(app, "small-nofail", "original")

    # Vanilla failure-injected: SYNTHESISED, not measured (data_locations.md
    # §4.4).  Vanilla cannot recover from an injected failure; the operational
    # cost is "partial work to the injection point + a full restart from
    # scratch" = nofail × (1 + once.delay_fraction).
    out["once_van"] = (out["ff_van"] * VANILLA_ONCE_MULT
                       if out["ff_van"] is not None else None)
    out["once_van_synthetic"] = True
    return out


# --- Plot styling --------------------------------------------------------

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
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


# --- Plot helper ---------------------------------------------------------

def plot_pair(
    apps: list[dict], *,
    series: list[tuple],
    ylabel: str, fname_stem: str,
    value_fmt=lambda v: f"{v:.1f}",
    log_y: bool = False,
    legend_below: bool = False,
    legend_loc: str = "upper right",
    strict_filter: bool = True,
    fig_height: float = 3.8,
    ylim: float | None = None,
) -> None:
    """Grouped bar chart: per app, one bar per `series` entry side by side.

    `series` = list of (label, hex_color, app_dict_key) OR
               (label, hex_color, app_dict_key, hatch_pattern).
    The 4-tuple form draws bars with a hatch pattern (e.g. "////" for
    synthesised values) and appends "(synthetic)" to the legend label.
    Series are drawn left-to-right in the given order; the legend lists
    them in the same order.  Bar widths and x-offsets are chosen to fit
    `len(series)` bars inside one app slot of unit width.
    """
    # Normalise every entry to a 4-tuple (label, color, key, hatch_or_None).
    series = [(t + (None,)) if len(t) == 3 else t for t in series]

    # Filter behaviour:
    #   strict_filter=True (default) — drop any app missing one or more
    #     series values.  Avoids partial-bar gaps in time-series charts where
    #     each app should have all bars.
    #   strict_filter=False — keep all apps; any missing value renders as
    #     a small "n/a" annotation in place of the bar.  Useful when the
    #     app set is fixed (e.g. a 16-app paper figure) and a missing
    #     reference value should be visible rather than hiding the app.
    series_keys = [key for _, _, key, _ in series]
    if strict_filter:
        kept_names = {a["app"] for a in apps if all(a.get(k) is not None for k in series_keys)}
        skipped = [a["app"] for a in apps if a["app"] not in kept_names]
        apps = [a for a in apps if a["app"] in kept_names]
        if skipped:
            print(f"  [{fname_stem}] skipping (incomplete data): {', '.join(skipped)}")
    else:
        partial = [a["app"] for a in apps if not all(a.get(k) is not None for k in series_keys)]
        if partial:
            print(f"  [{fname_stem}] keeping with n/a bars: {', '.join(partial)}")
    # X-axis order: easiest -> hardest by checkpointing difficulty (see Sec. 4.1).
    _RANK = {name: i for i, name in enumerate(DIFFICULTY_ORDER)}
    apps_sorted = sorted(apps, key=lambda a: _RANK.get(a["app"], len(_RANK)))
    n = len(apps_sorted)
    k = len(series)

    # Width scales with number of apps (was fixed 7.0 in for 6 apps; ~0.85
    # in/app keeps bars + their value labels comfortably spaced as the app
    # set grows past the original fast tier).
    fig_w = max(7.0, 0.85 * n + 1.6)
    fig, ax = plt.subplots(figsize=(fig_w, fig_height))

    # Bars take 80 % of the unit-wide app slot; remaining 20 % is the
    # inter-app gap.  With k bars per app, each bar gets 0.8/k width.
    bar_w = 0.8 / k
    x_centres = list(range(n))
    # Offsets centre the k bars around each x_centre.  For k=2 → ±bar_w/2;
    # for k=3 → -bar_w, 0, +bar_w.
    offsets = [(i - (k - 1) / 2) * bar_w for i in range(k)]
    # Stagger label heights so adjacent value strings don't overlap when
    # bar tops are nearly equal.  Cycle through 3 levels regardless of k.
    label_offsets = [2 + (i * 10) for i in range(k)]

    series_values = [[a.get(key) for a in apps_sorted] for _, _, key, _ in series]

    # Set the y-axis scale FIRST so subsequent ax.bar() calls land on a
    # correctly-scaled axis.  Skipping bars whose value is None avoids the
    # log-scale "height=0 → y=-inf" pathology that previously inflated the
    # saved figure to ~150 000 px tall via bbox_inches="tight".
    finite = [v for series_v in series_values for v in series_v if v]
    if log_y:
        ax.set_yscale("log")
        if finite:
            ax.set_ylim(min(finite) * 0.4, max(finite) * 4.0)
    else:
        if finite:
            ax.set_ylim(0, ylim if ylim is not None else max(finite) * 1.45)

    # Compute the y position to use for "n/a" annotations (just above the
    # axis bottom).  On log scale we walk a decade up; on linear scale we
    # use 5 % of the range.
    y_bottom, y_top = ax.get_ylim()
    y_na = y_bottom * 1.6 if log_y else y_bottom + 0.05 * (y_top - y_bottom)

    def _draw_group(values, x_offset, color, label, label_y_offset, hatch):
        first = True
        for c, v in zip(x_centres, values):
            x = c + x_offset
            if v is None:
                ax.annotate("n/a", xy=(x, y_na),
                            ha="center", va="bottom",
                            fontsize=7.5, color="#777777", style="italic")
                continue
            ax.bar(x, v, width=bar_w,
                   color=color, edgecolor="black", linewidth=0.6,
                   hatch=hatch,
                   label=label if first else None)
            first = False
            # Numeric labels above bars removed by user request.

    for (label, color, _key, hatch), values, x_offset, lyo in zip(
            series, series_values, offsets, label_offsets):
        _draw_group(values, x_offset, color, label, lyo, hatch)

    ax.set_ylabel(ylabel)

    # X-axis: app name + small italic category abbreviation underneath.
    # Anchor the italic label at xy=(i, y_bottom) — using `y=0` would be
    # -inf on a log axis and balloon the tight-bbox to ~500 inches tall.
    # App-name tilt + the category label's pushdown both scale with how
    # tall the tilted labels render (fontsize 10 × 20° ≈ 11 pt vertical run).
    ax.set_xticks(x_centres)
    ax.set_xticklabels([a["app"] for a in apps_sorted],
                       rotation=20, ha="right")
    # Italic class abbreviation under each app temporarily removed
    # (we will regroup later).

    # Legend: in-axes upper-right by default (matches sibling figure); on
    # log-scale plots PRK_Stencil's huge bars push into the corner, so caller
    # passes legend_below=True to relocate it under the plot.
    handles = [
        mpatches.Patch(facecolor=color, edgecolor="black", linewidth=0.6,
                       hatch=hatch, label=label)
        for label, color, _key, hatch in series
    ]
    if legend_below:
        leg = ax.legend(handles=handles,
                  loc="upper center", bbox_to_anchor=(0.5, -0.18),
                  ncol=2, fontsize=9,
                  frameon=True, fancybox=False, edgecolor="black",
                  handlelength=1.2, handletextpad=0.5,
                  columnspacing=1.5, borderpad=0.4)
    else:
        leg = ax.legend(handles=handles, loc=legend_loc,
                  ncol=1, fontsize=9,
                  frameon=True, fancybox=False, edgecolor="black",
                  handlelength=1.0, handletextpad=0.5,
                  labelspacing=0.35, borderpad=0.4, borderaxespad=0.5)
    # Semi-transparent legend background so any value labels behind the box
    # (e.g. PRK_Stencil's 676 s reference bar peeking into the upper-right
    # corner on the time charts) remain visible.
    leg.get_frame().set_alpha(0.85)

    _draw_group_separators(ax, len(apps_sorted))

    fig.savefig(OUT_DIR / f"{fname_stem}.pdf")
    fig.savefig(OUT_DIR / f"{fname_stem}.png", dpi=300)
    _mirror_to_papers(fname_stem)
    plt.close(fig)


# --- Formatting helpers --------------------------------------------------

def _fmt_seconds(v: float) -> str:
    return f"{v:.0f}s" if v >= 100 else f"{v:.1f}s"


def _fmt_bytes(v: float) -> str:
    if v >= 1e9:
        return f"{v/1e9:.1f}GB"
    if v >= 1e6:
        return f"{v/1e6:.1f}MB"
    if v >= 1e3:
        return f"{v/1e3:.1f}KB"
    return f"{v:.0f}B"


# --- Main ----------------------------------------------------------------

def main() -> None:
    all_apps, untrusted_b, untrusted_r = _trust_partition_comparison(COMPLETED_APPS)
    print(f"Plotting all {len(all_apps)} apps; LLM bars blanked for {len(untrusted_b)}, "
          f"Ref bars blanked for {len(untrusted_r)}")
    apps = []
    for a in all_apps:
        d = load_app(a)
        # Blank the LLM-side fields if baseline is UNTRUSTED.
        if a in untrusted_b:
            for k in ("ff_llm", "once_llm", "frame_llm"):
                d[k] = None
        # Blank the reference-side fields if reference is UNTRUSTED.
        if a in untrusted_r:
            for k in ("ff_ref", "once_ref", "frame_ref"):
                d[k] = None
        apps.append(d)
    print("Loaded:")
    for a in apps:
        def fmt(x, b=False):
            if x is None:
                return "      n/a"
            return _fmt_bytes(x) if b else f"{x:7.1f}s"
        print(f"  {a['app']:<12} {a['category']:<22} "
              f"ff_van={fmt(a['ff_van']):<10} ff_llm={fmt(a['ff_llm']):<10} ff_ref={fmt(a['ff_ref']):<10} "
              f"once_van={fmt(a['once_van']):<10} once_llm={fmt(a['once_llm']):<10} once_ref={fmt(a['once_ref']):<10} "
              f"frame_llm={fmt(a['frame_llm'], True):<10} frame_ref={fmt(a['frame_ref'], True):<10}")

    # Time charts: 3-bar Vanilla / LLM-modified / Reference comparison.
    # Vanilla is the no-resilience floor; on the failure-injected chart it
    # is SYNTHESISED (data_locations.md §4.4) and drawn with a diagonal
    # hatch.  Reference is the upstream's own checkpointed implementation,
    # measured on matched workload args (post Phase B rerun).
    time_series_ff = [
        ("Vanilla (no resilience)", COLOR_VAN, "ff_van"),
        ("LLM-modified",            COLOR_LLM, "ff_llm"),
        ("Reference",               COLOR_REF, "ff_ref"),
    ]
    # Reference series RESTORED for the 6-app set (CoMD, HPCG, MMSP,
    # OpenLB, Athena++, LAMMPS) — these are the only apps where the
    # reference's failure-injected attempt actually recovers from a
    # checkpoint instead of restarting from scratch.  See COMPLETED_APPS
    # comment for the broader pattern.
    time_series_once = [
        ("Vanilla (no resilience)", COLOR_VAN, "once_van", "////"),
        ("LLM-modified",            COLOR_LLM, "once_llm"),
        ("Reference",               COLOR_REF, "once_ref"),
    ]

    plot_pair(apps,
              series=time_series_ff,
              ylabel="Execution time, failure-free (s)",
              fname_stem="fast_tier_compare_walltime_failure_free",
              value_fmt=_fmt_seconds,
              strict_filter=False,
              fig_height=3.04, ylim=210)

    plot_pair(apps,
              series=time_series_once,
              ylabel="Execution time, failure-injected (s)",
              fname_stem="fast_tier_compare_walltime_failure_injected",
              value_fmt=_fmt_seconds,
              strict_filter=False,
              fig_height=3.04, ylim=350)

    # Checkpoint-size chart: 2-bar LLM vs Reference (vanilla has no
    # checkpoint).  Log-scale y-axis spans many orders of magnitude.
    plot_pair(apps,
              series=[
                  ("LLM-modified", COLOR_LLM, "frame_llm"),
                  ("Reference",    COLOR_REF, "frame_ref"),
              ],
              ylabel="Per-frame checkpoint footprint (bytes)",
              fname_stem="fast_tier_compare_checkpoint_per_frame",
              value_fmt=_fmt_bytes,
              log_y=True,
              legend_below=False, legend_loc="upper right",
              strict_filter=False,
              fig_height=3.04)

    print(f"\nSaved: {OUT_DIR}/")
    for f in sorted(OUT_DIR.glob("fast_tier_compare_*")):
        print(f"  {f.name}  ({f.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
