#!/usr/bin/env python3
"""CLI entry point for validating app pairs (vanilla + checkpointed).

Resume is automatic — every completed step (build, golden run, etc.) is
cached in the output directory.  Re-running the same command picks up
where it left off.

Usage:
    # Validate all apps (resumes automatically)
    python validation/veloc/validate_apps.py

    # Validate a single app
    python validation/veloc/validate_apps.py --app CoMD

    # Validate a category
    python validation/veloc/validate_apps.py --category iterative_fixed

    # Show progress so far
    python validation/veloc/validate_apps.py --status

    # List all discovered apps
    python validation/veloc/validate_apps.py --list

    # Dry run (show what would be validated without running)
    python validation/veloc/validate_apps.py --dry-run

    # Discard all cached results and start over
    python validation/veloc/validate_apps.py --fresh

    # Re-validate a single app from scratch
    python validation/veloc/validate_apps.py --app CoMD --fresh

    # Clear cached state for an app without re-running
    python validation/veloc/validate_apps.py --clear CoMD
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from validation.veloc.app_registry import AppRegistry
from validation.veloc.pipeline import AppValidationPipeline


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate app pairs (vanilla has no recovery, checkpointed recovers correctly) (resumes automatically)",
    )
    parser.add_argument(
        "--app",
        help="Validate a single app by name (e.g. CoMD, LULESH)",
    )
    parser.add_argument(
        "--category",
        help="Validate all apps in a category (e.g. iterative_fixed)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(_project_root / "build" / "validation_output"),
        help="Directory for validation results (default: build/validation_output/)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all discovered apps and exit",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show validation progress and exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be validated without running",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Discard cached results and re-validate from scratch",
    )
    parser.add_argument(
        "--clear",
        metavar="APP",
        help="Clear cached state for APP (or 'all') and exit",
    )
    args = parser.parse_args()

    registry = AppRegistry(_project_root)

    if len(registry) == 0:
        print("No apps found. Check tests/apps/vanillas/*/app.yaml")
        return 1

    # --list mode
    if args.list:
        _print_app_list(registry)
        return 0

    output_dir = Path(args.output_dir)
    pipeline = AppValidationPipeline(registry, _project_root, output_dir)

    # --status mode
    if args.status:
        _print_status(pipeline, registry)
        return 0

    # --clear mode
    if args.clear:
        if args.clear == "all":
            pipeline.clear()
            print("Cleared all cached state.")
        else:
            pipeline.clear(args.clear)
            print(f"Cleared cached state for {args.clear}.")
        return 0

    # Resolve target apps
    targets = _resolve_targets(registry, args)
    if targets is None:
        return 1

    # --dry-run mode
    if args.dry_run:
        _print_dry_run(registry, pipeline, targets)
        return 0

    # Run the pipeline
    print(f"Validating {len(targets)} app(s): {', '.join(targets)}")
    print(f"Output: {output_dir}")
    if not args.fresh:
        print("Resume: ON (use --fresh to start over)\n")
    else:
        print("Resume: OFF (--fresh: re-validating from scratch)\n")

    results = pipeline.run_reference_phase(
        apps=targets,
        skip_completed=not args.fresh,
        fresh=args.fresh,
    )

    # Generate report (includes previously completed apps)
    report_path = pipeline.generate_report()

    # Summary
    newly_validated = len(results)
    passed = sum(1 for r in results.values() if r.output_match and r.output_match.passed)
    failed = newly_validated - passed
    total_done = pipeline._count_completed("reference")
    total_apps = len(registry)

    print(f"\nThis run: {passed} passed, {failed} failed ({newly_validated} validated)")
    print(f"Overall:  {total_done}/{total_apps} apps completed")

    if total_done < total_apps:
        remaining = total_apps - total_done
        print(f"\nTo continue: python validation/veloc/validate_apps.py")
        print(f"  ({remaining} app(s) remaining)")

    return 0 if failed == 0 else 1


def _resolve_targets(registry: AppRegistry, args) -> list[str] | None:
    if args.app:
        cfg = registry.get(args.app)
        if cfg is None:
            print(f"App '{args.app}' not found. Available: {', '.join(a.name for a in registry)}")
            return None
        return [cfg.name]
    if args.category:
        apps = registry.by_category(args.category)
        if not apps:
            print(f"No apps in category '{args.category}'. Available: {', '.join(registry.categories())}")
            return None
        return [a.name for a in apps]
    return [a.name for a in registry]


def _print_app_list(registry: AppRegistry) -> None:
    print(f"{'Name':<15} {'Category':<22} {'Lang':<5} {'MPI Ranks':<10} {'Checkpoint':<10} {'Has Ckpt Dir'}")
    print("-" * 85)
    for app in sorted(registry, key=lambda a: (a.category, a.name)):
        has_ckpt = "yes" if registry.has_checkpointed(app.name) else "NO"
        print(
            f"{app.name:<15} {app.category:<22} {app.language:<5} "
            f"{app.mpi_ranks:<10} {app.checkpoint.library:<10} {has_ckpt}"
        )
    print(f"\nTotal: {len(registry)} apps across {len(registry.categories())} categories")


def _print_status(pipeline: AppValidationPipeline, registry: AppRegistry) -> None:
    summary = pipeline.status()
    if not summary:
        print("No validation results yet. Run without --status to start.")
        return

    print(f"{'Name':<15} {'Category':<22} {'Reference':<12} {'Tools'}")
    print("-" * 65)
    done = 0
    for name in sorted(summary):
        info = summary[name]
        ref = info["reference"]
        tools = ", ".join(info.get("tools", [])) or "-"
        print(f"{name:<15} {info['category']:<22} {ref:<12} {tools}")
        if ref == "PASS":
            done += 1

    total = len(registry)
    pending = total - len(summary)
    partial = sum(1 for v in summary.values() if v["reference"] == "PARTIAL")
    print(f"\n{done} passed, {partial} partial, {pending} pending out of {total} total")

    if done < total:
        print(f"\nTo continue: python validation/veloc/validate_apps.py")


def _print_dry_run(registry: AppRegistry, pipeline: AppValidationPipeline, targets: list[str]) -> None:
    summary = pipeline.status()
    print("DRY RUN - would validate:\n")
    for name in targets:
        cfg = registry.get(name)
        if cfg is None:
            continue
        has_ckpt = "yes" if registry.has_checkpointed(name) else "MISSING"
        status = summary.get(name, {}).get("reference", "PENDING")
        skip = " (will skip - already done)" if status == "PASS" else ""
        print(f"  {name}{skip}")
        print(f"    Category:    {cfg.category}")
        print(f"    Build:       {cfg.build.cmd}")
        print(f"    Run:         {cfg.run.cmd}")
        print(f"    Compare:     {cfg.comparison.method} (tol={cfg.comparison.tolerance})")
        print(f"    Checkpoint:  {cfg.checkpoint.library}")
        print(f"    Has ckpt dir: {has_ckpt}")
        print(f"    Status:      {status}")
        print()


if __name__ == "__main__":
    sys.exit(main())
