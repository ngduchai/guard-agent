"""Shared cell-discovery helper for the multi-model plots.

The fast-tier paper figures render every model cell side-by-side on the
same axes.  Each plot script imports `CELLS` here, then asks the helper
for per-cell file locations, trust verdicts, and capped iter metrics;
the helper centralises the small but easy-to-get-wrong differences
between the cell layouts:

  * iter logs live under ``results/models/<cell_id>/iter_logs/<APP>/``
  * LLM source snapshots live under ``results/models/<cell_id>/source/<APP>/``
  * benchmarks live under ``results/models/<cell_id>/bench/<APP>/``
  * unsuccessful-run archives are different per cell (historical DNC
    naming kept on disk for traceability):
      - opus47: ``results/archives/opus47_nyx_samrai_dnc/<APP>_baseline/``
        (result.json directly inside; iter_* siblings; ``source/`` subdir)
      - sonnet46: ``results/models/sonnet46/archive/<APP>/iter_logs/``
        (same shape as the live iter_logs dir, plus a sibling ``source/``)
      - gpt55: placeholder — no data yet; helpers return empty results
  * trust keys are different per cell:
      - opus47: ``<APP>_baseline``
      - sonnet46: ``<APP>_baseline_sonnet46``
      - gpt55: ``<APP>_baseline_gpt55`` (no records yet)

Plot scripts keep their own APP_LOC / GROUPS constants (intentionally
duplicated across the fast_tier family per the existing in-code
rationale); only cell-layout knowledge, MODEL_COLORS/MODEL_LABELS, and
the unsuccessful-run-aware ``load_result`` helper live here.
"""
from __future__ import annotations

import json
from pathlib import Path

# Repo root = three levels up from this file (docs/figs/_cells.py).
REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS = REPO_ROOT / "results"
TRUST = REPO_ROOT / "build" / "_experiment_state" / "_trust.json"

# Public catalogue of cells.  Tuple = (cell_id, display_label, marker_shape).
# `marker_shape` is the matplotlib marker code that scatter plots use to
# distinguish the models on the same axes (kept for back-compat; the
# bar/scatter plots now distinguish primarily by color).
CELLS: list[tuple[str, str, str]] = [
    ("opus47",        "Opus 4.7",     "o"),
    ("sonnet46",      "Sonnet 4.6",   "^"),
    ("gpt55_unified", "GPT-5.5",      "s"),
]

# Per-(app, model) cell map for Fig 3 + Fig 4a.  Each plot script reads
# the data for app X in column model M from the cell named here.  This
# is the FIRST-RUN-ONLY rollback: opus47 + sonnet46 for the two Anthropic
# columns, and gpt55 with gpt55_retry fallback (the historical
# "gpt55_unified" behavior) for GPT-5.5 — i.e., gpt55_retry is used only
# when gpt55 itself FAILed.  Entries set to ``None`` mean the (app, model)
# setting has no TRUSTED trial in any included cell.
MEDIAN_CELL_MAP: dict[str, dict[str, str | None]] = {
    "PRK_Stencil":  {"Opus 4.7": "opus47", "Sonnet 4.6": "sonnet46", "GPT-5.5": "gpt55"},
    "HPCG":         {"Opus 4.7": "opus47", "Sonnet 4.6": "sonnet46", "GPT-5.5": "gpt55"},
    "SW4lite":      {"Opus 4.7": "opus47", "Sonnet 4.6": "sonnet46", "GPT-5.5": "gpt55"},
    "HyPar":        {"Opus 4.7": "opus47", "Sonnet 4.6": "sonnet46", "GPT-5.5": "gpt55"},
    "CoMD":         {"Opus 4.7": "opus47", "Sonnet 4.6": "sonnet46", "GPT-5.5": "gpt55"},
    "SPPARKS":      {"Opus 4.7": "opus47", "Sonnet 4.6": "sonnet46", "GPT-5.5": "gpt55"},
    "CLAMR":        {"Opus 4.7": "opus47", "Sonnet 4.6": "sonnet46", "GPT-5.5": "gpt55_retry"},
    "SPARTA":       {"Opus 4.7": "opus47", "Sonnet 4.6": "sonnet46", "GPT-5.5": "gpt55_retry"},
    "LAMMPS":       {"Opus 4.7": "opus47", "Sonnet 4.6": "sonnet46", "GPT-5.5": "gpt55"},
    "Athena++":     {"Opus 4.7": "opus47", "Sonnet 4.6": "sonnet46", "GPT-5.5": None},
    "Smilei":       {"Opus 4.7": "opus47", "Sonnet 4.6": "sonnet46", "GPT-5.5": "gpt55"},
    "OpenLB":       {"Opus 4.7": "opus47", "Sonnet 4.6": "sonnet46", "GPT-5.5": "gpt55"},
    "WarpX":        {"Opus 4.7": "opus47", "Sonnet 4.6": "sonnet46", "GPT-5.5": "gpt55"},
    "ROSS":         {"Opus 4.7": "opus47", "Sonnet 4.6": None,       "GPT-5.5": None},
    "Nyx":          {"Opus 4.7": None,     "Sonnet 4.6": "sonnet46", "GPT-5.5": None},
    "SAMRAI":       {"Opus 4.7": None,     "Sonnet 4.6": None,       "GPT-5.5": "gpt55_retry"},
}


def median_cell_for(model_label: str, app: str) -> str | None:
    """Return the actual cell_id whose iter count matches Table II's median
    for this (app, model) pair, or ``None`` if no TRUSTED trial exists.

    Plot scripts that want figures to reflect the same trial reported in
    Table II should resolve the cell through this helper rather than
    using the fixed ``CELLS`` list.  See ``MEDIAN_CELL_MAP`` for the
    full per-app catalogue and the tie-break rule used for even-numbered
    trial counts.
    """
    return MEDIAN_CELL_MAP.get(app, {}).get(model_label)


# ----------------------------------------------------------------------
# Multi-trial cell resolution for Fig 3 (per-group summary + scatter).
# PS/PD/Enc apps -> AVERAGE metrics across all TRUSTED+CONDITIONAL_TRUSTED
# trials (1-3 cells per (app, model)).  Mod apps -> SINGLE first-run cell
# (gpt55_retry fallback for GPT-5.5 when gpt55 itself FAILed).
# ----------------------------------------------------------------------
_PS_APPS  = frozenset({"PRK_Stencil", "HPCG", "SW4lite", "HyPar"})
_PD_APPS  = frozenset({"CoMD", "SPPARKS", "CLAMR", "SPARTA", "LAMMPS"})
_ENC_APPS = frozenset({"Athena++", "Smilei", "OpenLB", "WarpX"})
_MOD_APPS = frozenset({"ROSS", "Nyx", "SAMRAI"})
_AVERAGED_APPS = _PS_APPS | _PD_APPS | _ENC_APPS

_MODEL_TO_RUNS: dict[str, tuple[str, ...]] = {
    "Opus 4.7":   ("opus47",   "opus47_retry",   "opus47_retry2"),
    "Sonnet 4.6": ("sonnet46", "sonnet46_retry", "sonnet46_retry2"),
    "GPT-5.5":    ("gpt55",    "gpt55_retry",    "gpt55_retry2"),
}
_SUCCESS_STATUSES = frozenset({"TRUSTED", "CONDITIONAL_TRUSTED"})


def cells_for(model_label: str, app: str) -> list[str]:
    """Return the list of cell_ids whose data Fig 3 should load for this
    (app, model) pair.

    For PS/PD/Enc apps: all cells with a successful audit verdict
    (TRUSTED or CONDITIONAL_TRUSTED) across the three trials — callers
    should average the metrics across these cells.

    For Mod apps: a single-element list containing the first-run cell
    (opus47 / sonnet46), or the gpt55_retry fallback for GPT-5.5 when
    gpt55 itself failed.  Empty list if no qualifying cell exists.
    """
    if not TRUST.exists():
        return []
    trust = json.loads(TRUST.read_text())
    runs = _MODEL_TO_RUNS.get(model_label, ())

    def _is_success(cell: str) -> bool:
        entry = trust.get(f"{app}_baseline_{cell}", {})
        return entry.get("status") in _SUCCESS_STATUSES

    if app in _AVERAGED_APPS:
        return [c for c in runs if _is_success(c)]

    # Mod apps -> first-run cell, with gpt55_retry fallback for GPT-5.5.
    if model_label == "GPT-5.5":
        for c in ("gpt55", "gpt55_retry"):
            if _is_success(c):
                return [c]
        return []
    primary = runs[0] if runs else None
    return [primary] if primary and _is_success(primary) else []

# Per-model color palette.  Single source of truth referenced by every
# plot script.  Wong colorblind-friendly palette: blue / vermillion /
# bluish-green keep good separation in print + grayscale.
MODEL_COLORS: dict[str, str] = {
    "opus47":        "#0072B2",   # blue        — Claude Opus 4.7
    "sonnet46":      "#D55E00",   # vermillion  — Claude Sonnet 4.6
    "gpt55_unified": "#009E73",   # green       — GPT-5.5 (merge of original + retry)
}

# Display label per model cell.  Matches the CELLS labels but addressable
# by cell_id without an enumerate(CELLS) lookup.
MODEL_LABELS: dict[str, str] = {
    "opus47":        "Opus 4.7",
    "sonnet46":      "Sonnet 4.6",
    "gpt55_unified": "GPT-5.5",
}

# Universal iteration cap.  Plot scripts measure tokens / wall / code-gen
# / count over only the first ``DNC_CAP`` iterations of every (model, app)
# pair, regardless of whether the run was successful or not.  This keeps
# any future long-running successful run from being visually equivalent
# to several short successful runs, and it guarantees cross-model
# comparability (e.g. if a future Sonnet/GPT-5.5 app needs 15+ iters to
# succeed, its cost is reported on the same 10-iter baseline).  Variable
# name kept for compatibility with sibling plot scripts; the
# ``is_dnc`` parameter on ``load_result`` is now informational only.
DNC_CAP = 10

# Per-cell unsuccessful-run archive lookup.  Each entry maps app -> the
# directory whose ``result.json`` carries the iter-loop metrics for the
# unsuccessful run.  Sonnet's archive has an additional ``iter_logs/``
# nesting level that Opus does not, so we record the canonical leaf dir
# here and let callers join further (e.g. ``source/`` subdir for
# modpct/readpct scripts).
_DNC_DIRS: dict[str, dict[str, Path]] = {
    "opus47": {
        "Nyx":    RESULTS / "archives" / "opus47_nyx_samrai_dnc" / "Nyx_baseline",
        "SAMRAI": RESULTS / "archives" / "opus47_nyx_samrai_dnc" / "SAMRAI_baseline",
    },
    "sonnet46": {
        "ROSS":   RESULTS / "models" / "sonnet46" / "archive" / "ROSS"   / "iter_logs",
        "SAMRAI": RESULTS / "models" / "sonnet46" / "archive" / "SAMRAI" / "iter_logs",
    },
    "gpt55_unified": {
        # Apps that remained unsuccessful in BOTH the original gpt55 run and
        # the gpt55_retry run.  Per user choice, we keep the original-gpt55
        # archive copies for these.  The symlinked path under
        # gpt55_unified/archive resolves to the chosen source.
        "Athena++": RESULTS / "models" / "gpt55_unified" / "archive" / "Athena++" / "iter_logs",
        "Nyx":      RESULTS / "models" / "gpt55_unified" / "archive" / "Nyx"      / "iter_logs",
        "ROSS":     RESULTS / "models" / "gpt55_unified" / "archive" / "ROSS"     / "iter_logs",
        # CLAMR / SAMRAI / SPARTA are no longer DNC after the retry — they
        # promoted to TRUSTED via gpt55_retry and live under iter_logs/.
    },
}

# Trust-key suffix per cell.  All trust verdicts live in the single
# ``_trust.json`` file; the cell is encoded in the key's suffix.  Each
# cell maps to a tuple of suffixes that are checked in order — most cells
# have a single suffix, but ``gpt55_unified`` merges verdicts from both
# the original ``_baseline_gpt55`` run and the ``_baseline_gpt55_retry``
# follow-up, taking the TRUSTED verdict if either side has one.
_TRUST_SUFFIX: dict[str, tuple[str, ...]] = {
    # Aggregated "anchor" cells used by the CELLS list.
    "opus47":        ("_baseline_opus47", "_baseline"),  # new audit + legacy
    "sonnet46":      ("_baseline_sonnet46",),
    "gpt55_unified": ("_baseline_gpt55_retry", "_baseline_gpt55"),
    # Raw per-run cells referenced by MEDIAN_CELL_MAP for Fig 3 + Fig 4a
    # (each entry uses the same <APP>_baseline_<cell> trust key pattern).
    "opus47_retry":  ("_baseline_opus47_retry",),
    "opus47_retry2": ("_baseline_opus47_retry2",),
    "sonnet46_retry":  ("_baseline_sonnet46_retry",),
    "sonnet46_retry2": ("_baseline_sonnet46_retry2",),
    "gpt55":         ("_baseline_gpt55",),
    "gpt55_retry":   ("_baseline_gpt55_retry",),
    "gpt55_retry2":  ("_baseline_gpt55_retry2",),
}


def cell_iter_logs(cell: str) -> Path:
    """Return ``results/models/<cell>/iter_logs/``.

    The path may not exist on disk for placeholder cells; callers must
    guard with ``.exists()`` or ``.is_dir()`` before reading.
    """
    return RESULTS / "models" / cell / "iter_logs"


def cell_source_root(cell: str) -> Path:
    """Return ``results/models/<cell>/source/`` (per-app LLM-modified trees)."""
    return RESULTS / "models" / cell / "source"


def cell_bench(cell: str, app: str) -> Path:
    """Return ``results/models/<cell>/bench/<app>/`` (per-app bench root)."""
    return RESULTS / "models" / cell / "bench" / app


def cell_dnc_dirs(cell: str) -> dict[str, Path]:
    """Return ``{app: dir}`` for every unsuccessful-run archive of ``cell``.

    Each ``dir`` is the directory that contains ``result.json`` (and
    ``iter_*`` siblings for the source-read script).  For unsuccessful
    apps that also need the LLM-modified source tree, see
    ``cell_dnc_source``.  Function name kept for back-compat with
    sibling plot scripts.
    """
    return dict(_DNC_DIRS.get(cell, {}))


def cell_dnc_source(cell: str, app: str) -> Path | None:
    """Return the LLM-modified source dir for an unsuccessful app, or None.

    Opus archives have ``<archive>/source/<...>``.  Sonnet archives have
    ``<archive_parent>/source/`` where archive_parent is the sibling of
    ``iter_logs/``.
    """
    if cell == "opus47":
        base = _DNC_DIRS["opus47"].get(app)
        return (base / "source") if base else None
    if cell == "sonnet46":
        # iter_logs/.. = the archive root (sibling of source/).
        base = _DNC_DIRS["sonnet46"].get(app)
        return (base.parent / "source") if base else None
    return None


def trusted_apps(cell: str) -> set[str]:
    """Return apps whose ``<APP><suffix>`` unit is TRUSTED in _trust.json.

    Multi-suffix cells (e.g. ``gpt55_unified``) take the union of TRUSTED
    apps across all configured suffixes.
    """
    suffixes = _TRUST_SUFFIX.get(cell)
    if not suffixes or not TRUST.exists():
        return set()
    d = json.loads(TRUST.read_text())
    out: set[str] = set()
    for suffix in suffixes:
        for k, v in d.items():
            if not k.endswith(suffix) or not isinstance(v, dict):
                continue
            if v.get("status") != "TRUSTED":
                continue
            out.add(k[: -len(suffix)])
    return out


def trust_status(cell: str, app: str) -> str:
    """Return raw trust status string for ``<APP><suffix>`` (or 'MISSING').

    Multi-suffix cells return ``TRUSTED`` if any suffix verdict is TRUSTED;
    otherwise the first non-MISSING status is returned.
    """
    if not TRUST.exists():
        return "MISSING"
    suffixes = _TRUST_SUFFIX.get(cell, ("_baseline",))
    d = json.loads(TRUST.read_text())
    statuses = [d.get(f"{app}{s}", {}).get("status", "MISSING") for s in suffixes]
    if "TRUSTED" in statuses:
        return "TRUSTED"
    for s in statuses:
        if s != "MISSING":
            return s
    return "MISSING"


def load_result(
    result_dir: Path, *,
    is_dnc: bool,
    dnc_cap: int = DNC_CAP,
) -> dict | None:
    """Load ``<result_dir>/result.json`` with optional unsuccessful-run cap.

    For unsuccessful apps the cap clamps the metrics callers read out to
    the first ``dnc_cap`` ``per_iteration`` entries; this keeps
    unsuccessful runs visually comparable to bounded trusted runs.
    TRUSTED apps are returned verbatim because their iter count is
    already ≤ ``dnc_cap`` in the current data; verify with ``iters``
    before promoting any new trusted app whose iter count would change
    this assumption.

    Returns ``None`` if ``result.json`` is missing.  The returned dict
    carries the post-cap normalized keys callers should read:

    * ``iterations``                — int, clamped at ``dnc_cap`` when unsuccessful
    * ``total_tokens``              — int, capped sum
    * ``total_input_tokens``        — int, capped sum (0 if absent)
    * ``total_output_tokens``       — int, capped sum (0 if absent)
    * ``total_opencode_elapsed_s``  — float, capped sum
    * ``total_validation_elapsed_s``— float, capped sum
    * ``wall_elapsed_s``            — float, total_elapsed_s at the cap'th
                                      iter (or actual total if cap not reached)
    * ``per_iteration``             — list, sliced at the cap when unsuccessful
    * ``raw``                       — full unmodified parsed JSON, for
                                      callers that need original fields
    """
    p = result_dir / "result.json"
    if not p.exists():
        return None
    raw = json.loads(p.read_text())
    pi = list(raw.get("per_iteration") or [])
    n_full = len(pi)

    if n_full > dnc_cap:
        pi_capped = pi[:dnc_cap]
    else:
        pi_capped = pi

    iters = int(raw.get("iterations", n_full))
    iters = min(iters, dnc_cap)

    def _sum(key: str) -> float:
        return sum((it.get(key) or 0) for it in pi_capped)

    tot_tokens = int(_sum("total_tokens"))
    tot_in     = int(_sum("input_tokens"))
    tot_out    = int(_sum("output_tokens"))
    tot_oc     = float(_sum("opencode_elapsed_s"))
    tot_vd     = float(_sum("validation_elapsed_s"))

    # Wall time: total_elapsed_s carries the running-total wall clock per
    # iter; at the cap boundary this is the elapsed-at-cap reading the
    # iter loop saw.  If the run didn't reach the cap, fall back to the
    # full wall_elapsed_s.
    if n_full > dnc_cap and pi_capped:
        wall_s = float(pi_capped[-1].get("total_elapsed_s")
                       or raw.get("wall_elapsed_s") or 0.0)
    else:
        wall_s = float(raw.get("wall_elapsed_s") or 0.0)

    # If per_iteration is empty (rare; legacy runs), fall back to top-level
    # totals so existing trusted-app rendering doesn't regress.
    if not pi_capped:
        tot_tokens = int(raw.get("total_tokens") or 0)
        tot_in     = int(raw.get("total_input_tokens") or 0)
        tot_out    = int(raw.get("total_output_tokens") or 0)
        tot_oc     = float(raw.get("total_opencode_elapsed_s") or 0.0)
        tot_vd     = float(raw.get("total_validation_elapsed_s") or 0.0)

    return {
        "iterations": iters,
        "total_tokens": tot_tokens,
        "total_input_tokens": tot_in,
        "total_output_tokens": tot_out,
        "total_opencode_elapsed_s": tot_oc,
        "total_validation_elapsed_s": tot_vd,
        "wall_elapsed_s": wall_s,
        "per_iteration": pi_capped,
        "raw": raw,
    }
