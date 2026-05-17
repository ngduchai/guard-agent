"""Per-group aggregate of LLM iter-loop wall time and token cost.

Two side-by-side panels: (left) mean wall time in minutes per complexity
group; (right) mean tokens consumed in millions per complexity group.
Individual app values are overlaid as scatter dots so the within-group
variance stays visible alongside the group mean.

Saves PDF + PNG to docs/figs/ and mirrors the PDF into each active paper's
Figures dir, matching the convention used by the other fast_tier plots.
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

# --- Inputs ---------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
ITER_LOGS = REPO_ROOT / "build" / "iterative_logs"
TRUST = REPO_ROOT / "build" / "_experiment_state" / "_trust.json"
OUT_DIR = REPO_ROOT / "docs" / "figs"
PAPER_FIGURES_DIRS = [
    REPO_ROOT / "docs" / "paper" / "eScience" / "Figures",
]
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _mirror_to_papers(stem: str) -> None:
    import shutil
    src = OUT_DIR / f"{stem}.pdf"
    if not src.exists():
        return
    for paper_dir in PAPER_FIGURES_DIRS:
        if paper_dir.exists():
            shutil.copy2(src, paper_dir / f"{stem}.pdf")


# Same grouping used by the per-app charts.
GROUPS = {
    "Plain,\nfixed shape":       ["HPCG", "PRK_Stencil", "SW4lite", "HyPar"],
    "Plain,\nvariable per-rank": ["CoMD", "SPARTA", "SPPARKS", "CLAMR", "LAMMPS"],
    "Encapsulated,\naccessible": ["Nyx", "Athena++", "WarpX"],
    "Encapsulated,\nopaque":     ["OpenLB", "Smilei", "QMCPACK", "ROSS", "SAMRAI"],
}

GROUP_COLORS = ["#0072B2", "#E69F00", "#009E73", "#CC79A7"]


def _trusted_apps() -> set[str]:
    """Return the set of apps whose <APP>_baseline is TRUSTED in _trust.json."""
    if not TRUST.exists():
        return set()
    d = json.loads(TRUST.read_text())
    out = set()
    for k, v in d.items():
        if not k.endswith("_baseline") or not isinstance(v, dict):
            continue
        if v.get("status") == "TRUSTED":
            out.add(k[: -len("_baseline")])
    return out


def _load_app(app: str) -> tuple[float, float] | None:
    """Return (wall_min, tokens_M) for app, or None if missing."""
    p = ITER_LOGS / f"{app}_baseline" / "result.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    wall_min = d.get("wall_elapsed_s", 0) / 60.0
    tokens_M = d.get("total_tokens", 0) / 1e6
    return (wall_min, tokens_M)


def main() -> None:
    # Restrict the aggregate to apps whose _baseline unit is TRUSTED so the
    # group means match the per-app charts (which blank UNTRUSTED bars).
    trusted = _trusted_apps()
    per_group: dict[str, list[tuple[float, float]]] = {}
    for label, apps in GROUPS.items():
        rows = []
        for a in apps:
            if a not in trusted:
                continue
            r = _load_app(a)
            if r is not None:
                rows.append(r)
        per_group[label] = rows

    labels = list(GROUPS.keys())
    # Annotate each label with the n actually included (TRUSTED + has result.json)
    n_per_group = [len(per_group[l]) for l in labels]
    labels_with_n = [f"{l}\n(n={n})" for l, n in zip(labels, n_per_group)]
    wall_means = [statistics.mean(w for w, _ in per_group[l]) if per_group[l] else 0
                  for l in labels]
    tok_means  = [statistics.mean(t for _, t in per_group[l]) if per_group[l] else 0
                  for l in labels]

    print("Per-group means:")
    for l, w, t in zip(labels, wall_means, tok_means):
        flat = l.replace("\n", " ")
        n = len(per_group[l])
        print(f"  {flat:30s} n={n}  wall={w:5.1f} min  tok={t:.2f} M")

    fig, (ax_w, ax_t) = plt.subplots(1, 2, figsize=(7.2, 3.0),
                                     gridspec_kw={"wspace": 0.38})

    x = list(range(len(labels)))

    # ---- Left panel: wall time ----
    ax_w.bar(x, wall_means, color=GROUP_COLORS, width=0.62,
             edgecolor="black", linewidth=0.5, zorder=2)
    # Scatter individual apps to show within-group variance
    for i, l in enumerate(labels):
        ys = [w for w, _ in per_group[l]]
        ax_w.scatter([i] * len(ys), ys, color="black", s=14,
                     zorder=3, alpha=0.65, edgecolor="white", linewidth=0.5)
    ax_w.set_ylabel("Wall time per app (min)")
    ax_w.set_xticks(x)
    ax_w.set_xticklabels(labels_with_n, fontsize=8)
    ax_w.tick_params(axis="x", which="both", length=0)
    ax_w.set_ylim(0, max(max(w for w, _ in per_group[l]) for l in labels) * 1.15)
    # Numeric mean labels above each bar
    for i, m in enumerate(wall_means):
        ax_w.text(i, m + 4, f"{m:.0f}", ha="center", va="bottom",
                  fontsize=8, fontweight="bold")
    ax_w.set_title("(a) Wall time", fontsize=10)

    # ---- Right panel: tokens ----
    ax_t.bar(x, tok_means, color=GROUP_COLORS, width=0.62,
             edgecolor="black", linewidth=0.5, zorder=2)
    for i, l in enumerate(labels):
        ys = [t for _, t in per_group[l]]
        ax_t.scatter([i] * len(ys), ys, color="black", s=14,
                     zorder=3, alpha=0.65, edgecolor="white", linewidth=0.5)
    ax_t.set_ylabel("Tokens per app (M)")
    ax_t.set_xticks(x)
    ax_t.set_xticklabels(labels_with_n, fontsize=8)
    ax_t.tick_params(axis="x", which="both", length=0)
    ax_t.set_ylim(0, max(max(t for _, t in per_group[l]) for l in labels) * 1.15)
    for i, m in enumerate(tok_means):
        ax_t.text(i, m + 0.3, f"{m:.1f}", ha="center", va="bottom",
                  fontsize=8, fontweight="bold")
    ax_t.set_title("(b) Token cost", fontsize=10)

    fig.tight_layout()

    stem = "fast_tier_per_group_summary"
    fig.savefig(OUT_DIR / f"{stem}.pdf")
    fig.savefig(OUT_DIR / f"{stem}.png", dpi=300)
    plt.close(fig)
    _mirror_to_papers(stem)
    print(f"\nSaved: {OUT_DIR}/{stem}.{{pdf,png}} (and mirrored)")


if __name__ == "__main__":
    main()
