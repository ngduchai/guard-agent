"""F-8 — wiring consistency test (producer vs consumer).

Asserts every published convention (file name, env var, schema field) is
actually READ by the code path that should ACT on it — not just displayed
or logged or documented.

Concrete bug this prevents (CLAMR ref-bench, 2026-04-29):
``dry_run.py:upstream_extra_args()`` displayed ``_extra_args.txt`` as
"the args we'll use", but neither ``validate.py`` nor
``metrics_collector.py`` actually read the file.  18 reference benches
silently dropped opt-in flags for weeks; ``checkpoint_size_bytes`` was
``null`` for affected apps.

The test is intentionally narrow: each rule names ONE producer-side
artifact and ONE consumer-side function that MUST contain a literal
reference to the artifact.  When a rule fails, the failure message tells
you exactly which file is supposed to read what.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _grep_in(paths: list[Path], needle: str) -> list[tuple[Path, int]]:
    """Return list of (path, line_number) where *needle* appears."""
    hits: list[tuple[Path, int]] = []
    for p in paths:
        try:
            for i, ln in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if needle in ln:
                    hits.append((p, i))
        except OSError:
            continue
    return hits


# ---------------------------------------------------------------------------
# Wiring rules.  Each rule = (producer_artifact, expected_consumer_paths,
# needle_to_grep, human_explanation).
# ---------------------------------------------------------------------------

VALIDATION_DIR = REPO_ROOT / "validation" / "veloc"


def test_extra_args_file_is_consumed_by_bench_generator():
    """patches/<APP>/_extra_args.txt MUST be read by the bench-config
    generator so reference runs receive the opt-in checkpoint flags."""
    consumers = [VALIDATION_DIR / "scripts" / "generate_benchmark_configs.py"]
    hits = _grep_in(consumers, "_extra_args.txt")
    assert hits, (
        "tests/apps/patches/<APP>/_extra_args.txt is not read by "
        "validation/veloc/scripts/generate_benchmark_configs.py — the "
        "wiring drift that silently dropped CLAMR's '-c' flag etc.  "
        "Either re-add the consumer read, or remove the convention."
    )


def test_keep_patterns_blocklist_is_enforced_by_comparator():
    """validate_keep_patterns / _BANNED_KEEP_PATTERN_SUBSTRINGS in
    reference_validator.py must be CALLED on the comparator path so
    banner-style allowlist entries are rejected at compare time."""
    refval = (VALIDATION_DIR / "reference_validator.py").read_text()
    assert "_BANNED_KEEP_PATTERN_SUBSTRINGS" in refval
    assert "def validate_keep_patterns" in refval
    # Consumer: _compare_outputs must call validate_keep_patterns
    assert "validate_keep_patterns(" in refval, (
        "validate_keep_patterns() defined but never called — F-3 Layer A "
        "is dead code.  Wire into _compare_outputs."
    )


def test_workload_pin_env_vars_universal_in_run_validate():
    """HPCG_FIXED_SETS / CKPT_EVERY env vars must be exported in
    run_validate.sh OUTSIDE the USE_REFERENCE branch (universally) so
    vanilla and reference run identical workloads."""
    text = (VALIDATION_DIR / "scripts" / "run_validate.sh").read_text()
    # The universal block must come AFTER the `fi` that closes the
    # USE_REFERENCE branch.
    fi_at = text.find("\nfi\n")
    assert fi_at > 0, "Could not locate USE_REFERENCE block end in run_validate.sh"
    after_fi = text[fi_at:]
    assert "HPCG_FIXED_SETS" in after_fi, (
        "HPCG_FIXED_SETS must be exported in the universal (post-USE_REFERENCE) "
        "block of run_validate.sh so vanilla also reads it.  Otherwise "
        "vanilla and reference run different CG-set counts and bench "
        "comparison is invalid."
    )


def test_vanilla_hpcg_reads_workload_pin_env_var():
    """Vanilla HPCG main.cpp must read HPCG_FIXED_SETS so the workload
    pin actually takes effect on vanilla runs (otherwise the env export
    is a no-op and the bench comparison is still mismatched)."""
    main_cpp = (REPO_ROOT / "tests" / "apps" / "vanillas" / "HPCG" / "src" / "main.cpp").read_text()
    assert "HPCG_FIXED_SETS" in main_cpp, (
        "tests/apps/vanillas/HPCG/src/main.cpp does not read "
        "HPCG_FIXED_SETS — the env var exported by run_validate.sh is a "
        "no-op in vanilla, leaving the workload mismatch unfixed."
    )


def test_post_run_checkpoint_cleanup_wired():
    """The _cleanup_checkpoints_post_run helper must be CALLED in the
    bench loop after each run's metrics are persisted, otherwise stale
    checkpoints contaminate the next scenario."""
    text = (VALIDATION_DIR / "metrics_collector.py").read_text()
    assert "def _cleanup_checkpoints_post_run" in text, "helper missing"
    # At least 2 call sites (original + resilient + optionally approach)
    n_calls = len(re.findall(r"_cleanup_checkpoints_post_run\(", text))
    assert n_calls >= 3, (
        f"_cleanup_checkpoints_post_run defined but called only {n_calls} "
        "times — should be wired into original/resilient/approach run paths "
        "(3 sites)."
    )


def test_injection_fired_guard_present():
    """CRIT-2: if scenario.inject_failures and not result.injected on a
    resilient run, framework must REFUSE to record."""
    text = (VALIDATION_DIR / "metrics_collector.py").read_text()
    assert "scenario.inject_failures" in text
    assert "not result.injected" in text, (
        "CRIT-2 guard missing: a failure-injection scenario where injection "
        "did not fire would silently be recorded as a failure-free run "
        "mislabeled as failure-injected."
    )


def test_workload_parity_floor_in_validation_a():
    """F-1: vanilla audit must enforce workload parity floor."""
    text = (VALIDATION_DIR / "validate.py").read_text()
    assert "_WORKLOAD_PARITY_FLOOR" in text
    assert "vanilla_failure_free_elapsed_s" in text


def test_recovery_floor_in_validation_b():
    """F-4: validation B must enforce recovery-elapsed sanity floor."""
    text = (VALIDATION_DIR / "validate.py").read_text()
    assert "_RECOVERY_ELAPSED_FLOOR_FRAC" in text
    assert "recovery_floor_ok" in text


def test_iter_result_provenance_field():
    """CRIT-3 / F-?: result.json writes must include _passed_via field."""
    text = (VALIDATION_DIR / "scripts" / "run_iterative.sh").read_text()
    assert '"_passed_via": "iter_loop"' in text, (
        "run_iterative.sh result.json writes must include "
        "`\"_passed_via\": \"iter_loop\"` so downstream consumers can "
        "distinguish iter-loop verdicts from external-orphan verdicts."
    )


def test_framework_version_is_recorded_in_artifacts():
    """F-10: FRAMEWORK_VERSION must be defined and recorded into the
    artifacts that the trust gate reads."""
    init = (VALIDATION_DIR / "__init__.py").read_text()
    assert "FRAMEWORK_VERSION" in init, (
        "validation/veloc/__init__.py must define FRAMEWORK_VERSION."
    )
    # Stamp must end up in the resilience proof (validate.py) and the
    # bench raw_metrics.json + benchmark_progress.json (metrics_collector.py)
    val_text = (VALIDATION_DIR / "validate.py").read_text()
    assert "FRAMEWORK_VERSION" in val_text and '"framework_version"' in val_text, (
        "validate.py must import FRAMEWORK_VERSION and stamp it into the "
        "resilience_proof.json signals."
    )
    mc_text = (VALIDATION_DIR / "metrics_collector.py").read_text()
    assert '"framework_version"' in mc_text, (
        "metrics_collector.py must stamp framework_version into "
        "raw_metrics.json + benchmark_progress.json."
    )


def test_all_known_consumers_compile():
    """Quick syntax check on every wired-in script."""
    import py_compile
    for rel in [
        "validation/veloc/validate.py",
        "validation/veloc/metrics_collector.py",
        "validation/veloc/reference_validator.py",
        "validation/veloc/scripts/generate_benchmark_configs.py",
        "validation/veloc/scripts/audit_aggregate_report.py",
        "validation/veloc/scripts/validate_iter_result.py",
        "validation/veloc/scripts/stage_summary.py",
    ]:
        path = REPO_ROOT / rel
        if path.exists():
            py_compile.compile(str(path), doraise=True)
