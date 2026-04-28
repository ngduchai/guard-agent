"""
tune_injection_delays.py — set per-app `small-low.injection_delay` to mid-run.

Reads each app's measured baseline from build/baseline_cache/<APP>/ground_truth_meta.json
and updates the app's benchmark_config/<APP>.json so that any failure-injection
scenario fires at ~baseline/2 — guaranteed to be after the first checkpoint
fires (assuming reasonable checkpoint cadence) and before the run completes.

This kills two birds:
  1. The current configs have many small-low delays at 4-15s, which inject
     before the app even reaches its first checkpoint.  Restart then has
     nothing to recover from → measures full re-run, not actual recovery.
  2. The old delays were hand-picked per app, often without a rationale
     comment, and have drifted from the actual workload sizes.

Idempotent:
  - Apps with no cached baseline are SKIPPED (no change).
  - Apps where the current delay already equals the suggested value: no write.
  - Only the `injection_delay` field of `small-low` (and any other scenario
    with `inject_failures: true`) is updated.  Workload args, num_runs,
    failures_per_run, max_attempts are untouched.

Usage:
  python -m validation.veloc.scripts.tune_injection_delays
  python -m validation.veloc.scripts.tune_injection_delays --dry-run
  python -m validation.veloc.scripts.tune_injection_delays --app CoMD
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BASELINE_CACHE = REPO_ROOT / "build" / "baseline_cache"
BENCHMARK_CONFIGS = REPO_ROOT / "validation" / "veloc" / "benchmark_configs"


def _cached_baseline(app: str) -> float | None:
    meta = BASELINE_CACHE / app / "ground_truth_meta.json"
    if not meta.exists():
        return None
    try:
        return float(json.loads(meta.read_text())["elapsed_s"])
    except (KeyError, ValueError, json.JSONDecodeError):
        return None


def tune_one(app: str, dry_run: bool = False) -> dict:
    """Tune `app`'s benchmark_config in place. Returns a status dict."""
    cfg = BENCHMARK_CONFIGS / f"{app}.json"
    if not cfg.exists():
        return {"app": app, "status": "skipped", "reason": "no benchmark_config"}

    baseline = _cached_baseline(app)
    if baseline is None:
        return {"app": app, "status": "skipped", "reason": "no baseline cache"}

    suggested_delay = round(baseline / 2.0, 1)

    raw = cfg.read_text()
    d = json.loads(raw)
    changes = []
    for s in d.get("scenarios", []):
        if not s.get("inject_failures"):
            continue
        old = s.get("injection_delay")
        if old is None:
            continue
        try:
            old_f = float(old)
        except (TypeError, ValueError):
            continue
        if abs(old_f - suggested_delay) < 0.5:
            continue  # already close enough
        s["injection_delay"] = suggested_delay
        changes.append({"scenario": s.get("name", "?"), "old": old_f, "new": suggested_delay})

    if not changes:
        return {
            "app": app, "status": "no-change",
            "baseline": baseline, "suggested": suggested_delay,
        }

    if not dry_run:
        # ensure_ascii=False so em-dashes / × / → in _comment fields stay as
        # readable UTF-8 instead of getting escaped to — / × / →
        # (which would balloon the diff with cosmetic noise)
        new_raw = json.dumps(d, indent=2, ensure_ascii=False)
        cfg.write_text(new_raw + "\n")

    return {
        "app": app, "status": ("dry-run" if dry_run else "updated"),
        "baseline": baseline, "suggested": suggested_delay, "changes": changes,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--app", help="Tune only this app (default: all apps with cached baseline)")
    p.add_argument("--dry-run", action="store_true", help="Print what would change, don't write")
    args = p.parse_args(argv)

    if args.app:
        apps = [args.app]
    else:
        apps = sorted({p.stem for p in BENCHMARK_CONFIGS.glob("*.json")})

    skipped, no_change, updated = [], [], []
    for app in apps:
        r = tune_one(app, dry_run=args.dry_run)
        if r["status"] in ("skipped",):
            skipped.append(r)
        elif r["status"] == "no-change":
            no_change.append(r)
        else:
            updated.append(r)

    if updated:
        print(f"\n=== {('Would update' if args.dry_run else 'Updated')}: {len(updated)} app(s) ===")
        for r in updated:
            print(f"  {r['app']:14}  baseline={r['baseline']:.1f}s  → injection_delay={r['suggested']:.1f}s")
            for ch in r["changes"]:
                print(f"     {ch['scenario']}: {ch['old']:.1f}s → {ch['new']:.1f}s")

    if no_change:
        print(f"\n=== Already correct: {len(no_change)} app(s) ===")
        for r in no_change:
            print(f"  {r['app']:14}  baseline={r['baseline']:.1f}s  injection_delay={r['suggested']:.1f}s")

    if skipped:
        print(f"\n=== Skipped (no cached baseline yet): {len(skipped)} app(s) ===")
        for r in skipped:
            print(f"  {r['app']:14}  ({r['reason']})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
