"""Read-coverage (unique LoC read by the LLM) vs total-tokens scatter.

Companion to ``_plot_loc_vs_tokens.py`` and ``_plot_modpct_vs_tokens.py``:
same visual encoding (color = complexity group, shape = model; no
success/failure differentiation), but the x-axis is the fraction of
the source tree the agent actually *read* across the entire iter loop,
deduplicated by ``(file, line)``.  Reads outside the app tree
(``..``-rooted paths, sibling apps, repo internals) are excluded so the
metric measures exploration of the app's own codebase, not cross-app
reference reads.

See module docstring in the previous revision history for the full
caveats list (reads of LLM-created files, files mutating across iters,
Grep/Glob excluded, etc.).

Saves PDF (vector) + PNG (300 DPI) to docs/figs/ and mirrors the PDF
into each active paper's Figures dir.
"""
from __future__ import annotations

import re
from collections import defaultdict
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
OUT_DIR = REPO_ROOT / "docs" / "figs"
PAPER_FIGURES_DIRS = [
    REPO_ROOT / "docs" / "paper" / "eScience" / "Figures",
]
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Per-app LoC and complexity groups — single source of truth duplicated
# across the fast_tier_*.py family; update in lock-step.
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


# --- Read-event parser ----------------------------------------------------
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
# "→ Read <path>"  or  "→ Read <path> [offset=N, limit=M]"  or
# "→ Read <path> [limit=M]".  Path has no spaces in the logs we have.
READ_RE = re.compile(r"→\s*Read\s+(\S+?)(?:\s+\[([^\]]+?)\])?\s*$")
DEFAULT_READ_LIMIT = 2000  # opencode default when no [limit=] is given


def _parse_read_events(text: str):
    for raw in text.splitlines():
        line = ANSI_RE.sub("", raw).rstrip()
        m = READ_RE.search(line)
        if not m:
            continue
        path = m.group(1)
        params = m.group(2)
        off, lim = 0, None
        if params:
            for kv in params.split(","):
                k, _, v = kv.strip().partition("=")
                v = v.strip()
                if k == "offset":
                    try:
                        off = int(v)
                    except ValueError:
                        pass
                elif k == "limit":
                    try:
                        lim = int(v)
                    except ValueError:
                        pass
        yield path, off, lim


def _count_lines(p: Path) -> int:
    try:
        with p.open("rb") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def _iter_dirs(log_base: Path) -> list[Path]:
    return sorted(log_base.glob("iter_*"))


def _is_in_scope(path: str) -> bool:
    if path.startswith("../"):
        return False
    if path in (".", "app.yaml", "prompt.txt"):
        return False
    return True


def _load_read_coverage(src_dir: Path, log_base: Path) -> tuple[int, dict]:
    seen: defaultdict[Path, set[int]] = defaultdict(set)
    stats = {"events": 0, "outside": 0, "missing": 0, "dirs": 0,
             "truncated": 0, "in_scope": 0, "files_touched": 0}
    for iter_dir in _iter_dirs(log_base):
        log = iter_dir / "opencode_stderr.txt"
        if not log.exists():
            continue
        text = log.read_text(errors="replace")
        for path, off, lim in _parse_read_events(text):
            stats["events"] += 1
            if not _is_in_scope(path):
                stats["outside"] += 1
                continue
            resolved = (src_dir / path).resolve()
            if not resolved.exists():
                stats["missing"] += 1
                continue
            if resolved.is_dir():
                stats["dirs"] += 1
                continue
            total = _count_lines(resolved)
            if total == 0:
                continue
            start = off + 1
            if lim is None:
                end = min(start + DEFAULT_READ_LIMIT - 1, total)
                if total > DEFAULT_READ_LIMIT:
                    stats["truncated"] += 1
            else:
                end = min(start + lim - 1, total)
            if end < start:
                continue
            stats["in_scope"] += 1
            seen[resolved].update(range(start, end + 1))
    stats["files_touched"] = len(seen)
    unique = sum(len(s) for s in seen.values())
    return unique, stats


# --- Plot styling ---------------------------------------------------------
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

    Each point tuple = (app, pct, tokens_M, unique, stats).
    """
    trusted = trusted_apps(cell)
    dnc = cell_dnc_dirs(cell)
    iter_logs = cell_iter_logs(cell)
    src_root = cell_source_root(cell)
    points, dnc_points = [], []
    dropped_not_trusted, dropped_no_result, dropped_no_source = [], [], []
    for app, loc in APP_LOC.items():
        if app in dnc:
            log_base = dnc[app]
            tk = _load_tokens(log_base, is_dnc=True)
            if tk is None:
                dropped_no_result.append(f"{app}(unsuccessful-missing)")
                continue
            llm_dir = cell_dnc_source(cell, app)
            if llm_dir is None or not llm_dir.is_dir():
                dropped_no_source.append(f"{app}(unsuccessful-source-missing)")
                continue
            unique, stats = _load_read_coverage(llm_dir, log_base)
            pct = 100.0 * unique / loc
            dnc_points.append((app, pct, tk / 1e6, unique, stats))
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
        src_dir = src_root / app
        if not src_dir.is_dir():
            dropped_no_source.append(app)
            continue
        unique, stats = _load_read_coverage(src_dir, iter_logs / app)
        pct = 100.0 * unique / loc
        points.append((app, pct, tk / 1e6, unique, stats))
    return points, dnc_points, dropped_not_trusted, dropped_no_result, dropped_no_source


def main() -> None:
    per_cell: dict[str, dict] = {}
    for cell_id, label, marker in CELLS:
        pts, dnc_pts, dnt, dnr, dns = _collect(cell_id)
        print(f"[{cell_id} = {label}]")
        print(f"  [dropped non-TRUSTED]    {sorted(dnt)}")
        print(f"  [dropped no result.json] {sorted(dnr)}")
        print(f"  [dropped no source dir]  {sorted(dns)}")
        rows = sorted(pts + dnc_pts, key=lambda p: p[1])
        for app, pct, tk_m, unique, stats in rows:
            tag = "UNSUCC " if (app, pct, tk_m, unique, stats) in dnc_pts else "TRUSTED"
            print(f"  [{tag}] {app:<12}  read={unique:>6}  app={APP_LOC[app]:>7,}  "
                  f"pct={pct:6.2f}%  tokens={tk_m:5.1f}M  files={stats['files_touched']:>3}  "
                  f"trunc={stats['truncated']:>2}  outside={stats['outside']:>3}  "
                  f"missing={stats['missing']:>3}")
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
        for app, pct, tk_m, _u, _s in (cell_data["points"] + cell_data["dnc"]):
            grp = _group_of(app)
            color = GROUP_COLORS.get(grp, "#777777")
            ax.scatter([pct], [tk_m], s=DOT_SIZE, marker=marker,
                       color=color, edgecolor="black", linewidth=0.5,
                       zorder=3)

    by_app: dict[str, list[tuple[float, float]]] = {}
    for cell_id in (c[0] for c in CELLS):
        for app, pct, tk_m, _u, _s in (per_cell[cell_id]["points"]
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
    ax.set_xlabel("Source read by LLM (% of LoC, log scale)")
    ax.set_ylabel("Total tokens (M)")
    lo = min(all_pcts) if all_pcts else 0.05
    hi = max(all_pcts) if all_pcts else 100.0
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

    stem = "readpct_vs_tokens"
    fig.savefig(OUT_DIR / f"{stem}.pdf", bbox_inches="tight",
                bbox_extra_artists=[leg1])
    fig.savefig(OUT_DIR / f"{stem}.png", dpi=300, bbox_inches="tight",
                bbox_extra_artists=[leg1])
    plt.close(fig)
    _mirror_to_papers(stem)
    print(f"\nSaved: {OUT_DIR}/{stem}.{{pdf,png}} (and mirrored)")


if __name__ == "__main__":
    main()
