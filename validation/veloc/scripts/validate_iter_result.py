"""validate_iter_result.py — schema-check an iter loop result.json.

Asserts internal consistency between:
  - top-level `passed`
  - the LAST entry in `per_iteration[*].validation_passed`
  - the `_passed_via` provenance field

CRIT-3 root cause: a manually-reconstructed result.json had `passed: true`
at the top level while every per_iteration entry had `validation_passed: false`,
because the verdict actually came from a separate orphan validate.py run, not
from the iter loop.  This validator catches that divergence.

Exit codes:
  0 — result.json is internally consistent
  1 — divergence detected (printed to stderr)
  2 — schema/file error

Usage:
  python -m validation.veloc.scripts.validate_iter_result <path/to/result.json>
  python -m validation.veloc.scripts.validate_iter_result --all
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


_VALID_PASSED_VIA = ("iter_loop", "external_validate", "manual_reconstruction")


def check_one(path: Path) -> tuple[bool, str]:
    """Return (ok, message).  ok=False means inconsistency found."""
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return (False, f"cannot parse {path}: {exc}")

    top_passed = d.get("passed")
    per_iter = d.get("per_iteration") or []
    passed_via = d.get("_passed_via")

    if top_passed is None:
        return (False, f"{path}: missing top-level 'passed'")

    if per_iter:
        last_iter_passed = per_iter[-1].get("validation_passed")
    else:
        last_iter_passed = None

    # Tolerate the legacy schema (no _passed_via) but only if internally
    # consistent.  New writes (schema_version >= 2) MUST carry the field.
    schema_v = d.get("schema_version", 1)
    if schema_v >= 2 and passed_via not in _VALID_PASSED_VIA:
        return (False, (
            f"{path}: schema_version={schema_v} requires "
            f"_passed_via to be one of {_VALID_PASSED_VIA}; got {passed_via!r}"
        ))

    # Iter-loop verdicts must align with last iteration.
    if passed_via == "iter_loop":
        if top_passed and last_iter_passed is not True:
            return (False, (
                f"{path}: passed=true with _passed_via=iter_loop but the last "
                f"per_iteration entry has validation_passed={last_iter_passed!r} "
                "(should be true).  Either fix the file or change _passed_via "
                "to 'external_validate' or 'manual_reconstruction'."
            ))
        if (not top_passed) and last_iter_passed is True:
            return (False, (
                f"{path}: passed=false but the last per_iteration entry is "
                "validation_passed=true — internal contradiction."
            ))

    # External / manual provenance: explicit override is allowed, but we
    # still want SOME per-iteration evidence to exist.
    if passed_via in ("external_validate", "manual_reconstruction"):
        if not per_iter:
            return (False, (
                f"{path}: _passed_via={passed_via} requires per_iteration "
                "evidence; the array is empty."
            ))
        if top_passed and not d.get("_reconstruction_note"):
            return (False, (
                f"{path}: _passed_via={passed_via} with passed=true requires "
                "a non-empty _reconstruction_note field documenting how the "
                "external/manual verdict was derived."
            ))

    return (True, f"{path}: OK (passed={top_passed}, via={passed_via}, "
                  f"last_iter={last_iter_passed})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="validate_iter_result.py")
    parser.add_argument("paths", nargs="*", type=Path,
                        help="result.json paths to check")
    parser.add_argument("--all", action="store_true",
                        help="check every result.json under build/iterative_logs/")
    args = parser.parse_args(argv)

    paths: list[Path] = list(args.paths)
    if args.all:
        repo = Path(__file__).resolve().parents[3]
        paths.extend(sorted((repo / "build" / "iterative_logs").rglob("result.json")))

    if not paths:
        parser.error("provide at least one path or --all")

    failures = 0
    for p in paths:
        ok, msg = check_one(p)
        print(("PASS " if ok else "FAIL ") + msg, file=sys.stderr if not ok else sys.stdout)
        if not ok:
            failures += 1
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
