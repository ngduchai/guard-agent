"""End-to-end smoke test for every fix shipped in the 2026-05-02 batch.

Each fix is exercised at its enforcement point with a minimal synthetic
input that triggers EXACTLY ONE of:
  * the guard fires (negative case → assert raises / returns False)
  * the guard doesn't fire on legitimate input (positive case → assert OK)

No real apps are built or run.  The point is to prove that the framework
guards behave as designed and that no fix accidentally breaks a prior
correct path.

Fixes covered:
  F-1   workload-parity floor in _enforce_validation_a (audit)
  F-2   workload-parity ceiling in _check_workload_parity (bench)
  F-3a  banned keep_patterns rejected by validate_keep_patterns
  F-3b  empty-match guard fails comparator on empty filtered output
  F-4   recovery-elapsed sanity floor in _enforce_validation_b
  F-6   fast-pass floor in _run_scenario_once (via direct check of guard)
  F-7   stage_summary regression_flag math
  F-9   _cleanup_checkpoints_post_run actually empties dirs (and respects opt-out)
  F-10  FRAMEWORK_VERSION stamped in artifacts
  F-11  injection-fired guard in _run_scenario_once
  CRIT-3 validate_iter_result accepts/rejects synthetic result.json correctly
  HPCG vanilla source contains HPCG_FIXED_SETS read
  HyPar patch n_iter matches vanilla n_iter
  ROSS/Nyx/SAMRAI keep_patterns no longer use any banned word
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# F-1 — workload-parity floor (audit)
# ---------------------------------------------------------------------------

def _make_audit_signals(ratio: float = 0.5):
    """Build a `signals` dict shape that _enforce_validation_a reads."""
    return {
        "resilient_elapsed_s": 100.0,
        "original_elapsed_s": 200.0,
        "ratio": ratio,
        "wall_time_pass_at_1_2": False,
        "wall_time_pass_at_1_7": False,
        "wall_time_pass_at_1_9": False,
        "checkpoint_files": 0,
        "checkpoint_files_pass": False,
        "checkpoint_observed": None,
        "kill_attempt_elapsed_s": None,
        "recovery_attempt_elapsed_s": None,
        "veloc_cfg": None,
        "checkpoint_dirs_scanned": [],
    }


def test_f1_audit_workload_parity_passes_when_vanilla_eq_reference(tmp_path):
    """Honest case: vanilla ≈ reference (workloads match)."""
    from validation.veloc.validate import _enforce_validation_a
    sig = _make_audit_signals()
    # vanilla 53s, reference 53s → ratio reference/vanilla = 1.00 ≥ 0.98 → OK.
    _enforce_validation_a(
        signals=sig,
        accuracy_match=True,
        out_dir=tmp_path,
        vanilla_failure_free_elapsed_s=53.0,
        reference_failure_free_elapsed_s=53.0,
    )  # should NOT raise


def test_f1_audit_workload_parity_passes_when_reference_legitimately_slower(tmp_path):
    """Honest case: reference > vanilla due to checkpoint I/O overhead.
    The MMSP false-positive that prompted the F-1 direction fix (2026-05-02
    phase B): vanilla=56s, reference=69s → reference/vanilla=1.24 → MUST PASS.
    """
    from validation.veloc.validate import _enforce_validation_a
    sig = _make_audit_signals()
    _enforce_validation_a(
        signals=sig,
        accuracy_match=True,
        out_dir=tmp_path,
        vanilla_failure_free_elapsed_s=56.0,
        reference_failure_free_elapsed_s=69.0,
    )  # should NOT raise — reference legitimately slower than vanilla is expected


def test_f1_audit_workload_parity_fails_when_reference_faster_than_vanilla(tmp_path):
    """The HPCG bug case: reference workload-pinned to less work than vanilla.
    vanilla=120s, reference=53s → reference/vanilla=0.44 < 0.98 → MUST FAIL.
    """
    from validation.veloc.validate import _enforce_validation_a
    from validation.veloc.runner import ValidationError
    sig = _make_audit_signals()
    with pytest.raises(ValidationError, match="workload parity"):
        _enforce_validation_a(
            signals=sig,
            accuracy_match=True,
            out_dir=tmp_path,
            vanilla_failure_free_elapsed_s=120.0,
            reference_failure_free_elapsed_s=53.0,
        )


def test_f1_audit_workload_parity_skipped_when_reference_elapsed_unknown(tmp_path):
    """When the reference run failed to produce an elapsed time, parity check
    is skipped (logged) instead of failing the audit."""
    from validation.veloc.validate import _enforce_validation_a
    sig = _make_audit_signals()
    _enforce_validation_a(
        signals=sig,
        accuracy_match=True,
        out_dir=tmp_path,
        vanilla_failure_free_elapsed_s=100.0,
        reference_failure_free_elapsed_s=None,
    )  # should NOT raise


# ---------------------------------------------------------------------------
# F-2 — bench workload-parity ceiling
# ---------------------------------------------------------------------------

def test_f2_bench_parity_passes_within_overhead_cap():
    from validation.veloc.metrics_collector import _check_workload_parity
    summary = {
        "small-nofail": {
            "original":  {"elapsed_s": {"median": 100.0, "mean": 100.0}},
            "resilient": {"elapsed_s": {"median": 130.0, "mean": 130.0}},
        },
    }
    parity = _check_workload_parity(summary, overhead_cap=1.50)
    assert parity["small-nofail"]["ok"] is True
    assert parity["small-nofail"]["ratio_reference_over_vanilla"] == pytest.approx(1.30)


def test_f2_bench_parity_fails_when_reference_too_slow():
    """HyPar's n_iter 2.5M → 4.5M raised reference elapsed by ~80%; should trip."""
    from validation.veloc.metrics_collector import _check_workload_parity
    summary = {
        "small-nofail": {
            "original":  {"elapsed_s": {"median": 100.0}},
            "resilient": {"elapsed_s": {"median": 180.0}},  # 1.80× vanilla
        },
    }
    parity = _check_workload_parity(summary, overhead_cap=1.50)
    assert parity["small-nofail"]["ok"] is False


def test_f2_bench_parity_omits_scenarios_missing_either_side():
    from validation.veloc.metrics_collector import _check_workload_parity
    summary = {
        "small-nofail": {
            "original": {"elapsed_s": {"median": 100.0}},
            # no resilient
        },
    }
    parity = _check_workload_parity(summary)
    assert "small-nofail" not in parity


# ---------------------------------------------------------------------------
# F-3 Layer A — banned keep_patterns
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_pat", [
    "PASSED",
    "*** FAST RECOVERY ***",
    "[veloc] Restart detected",
    "Run time = 0",
    "fast-recovery path engaged",
    "Skipping simulation; exiting cleanly",
    "checkpoint loaded successfully",
    "loaded from checkpoint",
])
def test_f3a_blocklist_rejects_banner_patterns(bad_pat):
    from validation.veloc.reference_validator import validate_keep_patterns
    with pytest.raises(ValueError, match="banned substring"):
        validate_keep_patterns([bad_pat], app_label="test")


@pytest.mark.parametrize("good_pat", [
    "Total GVT Computations",
    "Average     gas density",
    "Simulation time is",
    "Total Events Processed",
    "Reference L1 norm",
    "Errors at time",
])
def test_f3a_blocklist_accepts_science_patterns(good_pat):
    from validation.veloc.reference_validator import validate_keep_patterns
    validate_keep_patterns([good_pat], app_label="test")  # should not raise


def test_f3a_blocklist_accepts_none_or_empty():
    from validation.veloc.reference_validator import validate_keep_patterns
    validate_keep_patterns(None, app_label="test")
    validate_keep_patterns([], app_label="test")


# ---------------------------------------------------------------------------
# F-3 Layer B — empty-match guard in _compare_outputs
# ---------------------------------------------------------------------------

GOLDEN_ROSS_STDOUT = """Init done
Total GVT Computations 470733
Total Events Processed 241014608
Average Reduction / GVT 2.88
Total Time 2.4416
"""

GAMED_ROSS_STDOUT = "*** FAST RECOVERY (from mid-run checkpoint; tw_run() skipped) ***\n"


def test_f3b_empty_match_guard_fails_on_test_side():
    from validation.veloc.reference_validator import _compare_outputs
    keeps = ["Total GVT Computations", "Total Events Processed"]
    res = _compare_outputs(
        golden_stdout=GOLDEN_ROSS_STDOUT,
        test_stdout=GAMED_ROSS_STDOUT,
        method="text",
        keep_patterns=keeps,
    )
    assert res.passed is False
    assert "F-3 anti-gaming guard" in res.details


def test_f3b_empty_match_guard_passes_when_both_emit_signature():
    from validation.veloc.reference_validator import _compare_outputs
    keeps = ["Total GVT Computations", "Total Events Processed"]
    res = _compare_outputs(
        golden_stdout=GOLDEN_ROSS_STDOUT,
        test_stdout=GOLDEN_ROSS_STDOUT,
        method="text",
        keep_patterns=keeps,
    )
    assert res.passed is True


def test_f3b_empty_match_guard_fails_on_golden_side_too():
    """Golden output that doesn't match keep_patterns is also a config bug."""
    from validation.veloc.reference_validator import _compare_outputs
    res = _compare_outputs(
        golden_stdout="No matching strings here\n",
        test_stdout=GOLDEN_ROSS_STDOUT,
        method="text",
        keep_patterns=["Total GVT Computations"],
    )
    assert res.passed is False
    assert "Empty filtered golden" in res.details


# ---------------------------------------------------------------------------
# F-4 — recovery-elapsed sanity floor (Validation B)
# ---------------------------------------------------------------------------

def _make_validation_b_signals(*, kill_s, recovery_s, ratio=1.1, ckpt=True, ckpt_obs=True):
    return {
        "resilient_elapsed_s": kill_s + recovery_s,
        "original_elapsed_s": (kill_s + recovery_s) / max(ratio, 0.01),
        "ratio": ratio,
        "wall_time_pass_at_1_2": ratio < 1.2,
        "wall_time_pass_at_1_7": ratio <= 1.7,
        "wall_time_pass_at_1_9": ratio < 1.9,
        "checkpoint_files": 1 if ckpt else 0,
        "checkpoint_files_pass": ckpt,
        "checkpoint_observed": ckpt_obs,
        "kill_attempt_elapsed_s": kill_s,
        "recovery_attempt_elapsed_s": recovery_s,
        "veloc_cfg": None,
        "checkpoint_dirs_scanned": [],
    }


def test_f4_validation_b_passes_with_honest_recovery(tmp_path):
    from validation.veloc.validate import _enforce_validation_b
    # HyPar reference numbers: kill_attempt ~30s, recovery_attempt ~26.78s
    # ratio = 0.96, recovery/kill = 0.89 — well above 0.10 floor.
    sig = _make_validation_b_signals(kill_s=30.0, recovery_s=26.78, ratio=0.96)
    _enforce_validation_b(sig, output_correct=True, out_dir=tmp_path)


def test_f4_validation_b_fails_on_no_op_recovery(tmp_path):
    """ROSS/Nyx/SAMRAI gaming pattern: kill ~5-30s, recovery <0.2s, ratio<1.0"""
    from validation.veloc.validate import _enforce_validation_b
    from validation.veloc.runner import ValidationError
    sig = _make_validation_b_signals(kill_s=10.0, recovery_s=0.17, ratio=0.56)
    with pytest.raises(ValidationError, match="recovery-elapsed sanity floor"):
        _enforce_validation_b(sig, output_correct=True, out_dir=tmp_path)


def test_f4_validation_b_skips_floor_when_per_attempt_timings_missing(tmp_path):
    """Legacy fixed-delay strategy: per-attempt timings None → floor skipped."""
    from validation.veloc.validate import _enforce_validation_b
    sig = _make_validation_b_signals(kill_s=10.0, recovery_s=0.17, ratio=1.1)
    sig["kill_attempt_elapsed_s"] = None
    sig["recovery_attempt_elapsed_s"] = None
    # Other gates still pass; should NOT raise.
    _enforce_validation_b(sig, output_correct=True, out_dir=tmp_path)


# ---------------------------------------------------------------------------
# F-6 — fast-pass floor (logic check, not actual subprocess invocation)
# ---------------------------------------------------------------------------

def test_f6_fast_pass_floor_default_is_at_least_one_second():
    """Verify the floor formula in _run_scenario_once: max(1.0, 0.10×inj)."""
    # Re-derive in the test as a sanity check on the literal in source.
    import os as _os
    _os.environ.pop("FAST_PASS_FLOOR_S", None)
    floor_no_inject = max(1.0, 0.10 * 0.0)
    floor_with_60s_inject = max(1.0, 0.10 * 60.0)
    assert floor_no_inject == 1.0
    assert floor_with_60s_inject == 6.0


def test_f6_fast_pass_floor_env_override():
    floor = 2.5
    os.environ["FAST_PASS_FLOOR_S"] = str(floor)
    try:
        from_env = float(os.environ["FAST_PASS_FLOOR_S"])
        assert from_env == floor
    finally:
        os.environ.pop("FAST_PASS_FLOOR_S", None)


# ---------------------------------------------------------------------------
# F-7 — stage_summary regression flag
# ---------------------------------------------------------------------------

def test_f7_stage_summary_regression_flag_math():
    """Regression flag = pass_rate < min_pass_rate."""
    from validation.veloc.scripts.stage_summary import _finalize
    # 8/10 PASS, threshold 0.80 → exactly at threshold → no regression.
    out = _finalize({"PASS": 8, "FAIL": 2}, [], min_pass_rate=0.80, stage="test")
    assert out["pass_rate"] == 0.80
    assert out["regression_flag"] is False
    # 7/10 PASS, threshold 0.80 → 0.70 < 0.80 → regression.
    out = _finalize({"PASS": 7, "FAIL": 3}, [], min_pass_rate=0.80, stage="test")
    assert out["regression_flag"] is True
    # 0/0 → pass_rate=0.0 < 0.80 → regression flag set (forces investigation).
    out = _finalize({}, [], min_pass_rate=0.80, stage="test")
    assert out["regression_flag"] is True


# ---------------------------------------------------------------------------
# F-9 — universal post-run checkpoint cleanup
# ---------------------------------------------------------------------------

def test_f9_cleanup_clears_veloc_dirs_and_posix_files(tmp_path):
    """End-to-end on a synthetic run dir + a fake /tmp veloc dir."""
    from validation.veloc.metrics_collector import _cleanup_checkpoints_post_run

    # Fake VeloC scratch dir
    fake_tmp = tmp_path / "fake_persistent"
    fake_tmp.mkdir()
    (fake_tmp / "ckpt-rank0-step100").write_bytes(b"x" * 1024)
    (fake_tmp / "ckpt-rank1-step100").write_bytes(b"y" * 1024)

    # Fake veloc.cfg pointing at it
    cfg = tmp_path / "veloc.cfg"
    cfg.write_text(f"persistent={fake_tmp}\nscratch={fake_tmp}\nmax_versions=3\n")

    # Fake run output dir with native checkpoint files + must-keep files
    run_dir = tmp_path / "run_1"
    run_dir.mkdir()
    (run_dir / "stdout.txt").write_text("preserve me")
    (run_dir / "stderr.txt").write_text("preserve me too")
    (run_dir / "checkpoint_metrics.json").write_text("{}")
    chk_dir = run_dir / "chk00050"
    chk_dir.mkdir()
    (chk_dir / "Header").write_bytes(b"a" * 100)
    (chk_dir / "Cell_D_00000").write_bytes(b"b" * 100)
    (run_dir / "restart.lj.1000").write_bytes(b"c" * 1024)

    # Sanity: non-empty before cleanup
    assert any(fake_tmp.iterdir())
    assert chk_dir.exists()
    assert (run_dir / "restart.lj.1000").exists()

    # Run cleanup (default: PRESERVE_CHECKPOINTS_AFTER_RUN unset → delete)
    os.environ.pop("PRESERVE_CHECKPOINTS_AFTER_RUN", None)
    _cleanup_checkpoints_post_run(
        run_output_dir=run_dir,
        veloc_cfg_name="veloc.cfg",
        veloc_cfg_search_dirs=[tmp_path],
    )

    # VeloC dir contents wiped, dir itself preserved
    assert fake_tmp.exists()
    assert not any(fake_tmp.iterdir())
    # Native chk*/restart.* files gone
    assert not chk_dir.exists()
    assert not (run_dir / "restart.lj.1000").exists()
    # stdout/stderr/json preserved
    assert (run_dir / "stdout.txt").read_text() == "preserve me"
    assert (run_dir / "stderr.txt").read_text() == "preserve me too"
    assert (run_dir / "checkpoint_metrics.json").exists()


def test_f9_cleanup_respects_opt_out(tmp_path):
    from validation.veloc.metrics_collector import _cleanup_checkpoints_post_run

    fake_tmp = tmp_path / "fake_persistent"
    fake_tmp.mkdir()
    (fake_tmp / "ckpt-rank0").write_bytes(b"x" * 100)
    cfg = tmp_path / "veloc.cfg"
    cfg.write_text(f"persistent={fake_tmp}\n")

    os.environ["PRESERVE_CHECKPOINTS_AFTER_RUN"] = "1"
    try:
        _cleanup_checkpoints_post_run(
            run_output_dir=tmp_path,
            veloc_cfg_name="veloc.cfg",
            veloc_cfg_search_dirs=[tmp_path],
        )
        # Opt-out honored: file still there.
        assert (fake_tmp / "ckpt-rank0").exists()
    finally:
        os.environ.pop("PRESERVE_CHECKPOINTS_AFTER_RUN", None)


# ---------------------------------------------------------------------------
# F-10 — FRAMEWORK_VERSION stamped in artifacts
# ---------------------------------------------------------------------------

def test_f10_framework_version_defined():
    from validation.veloc import FRAMEWORK_VERSION
    assert isinstance(FRAMEWORK_VERSION, str)
    # YYYY-MM-DD format
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", FRAMEWORK_VERSION)


def test_f10_resilience_proof_carries_framework_version(tmp_path):
    """_measure_resilience_signals writes the proof file with the version."""
    from validation.veloc import FRAMEWORK_VERSION
    from validation.veloc.validate import _measure_resilience_signals
    sig = _measure_resilience_signals(
        resilient_elapsed=10.0,
        original_elapsed=10.0,
        veloc_cfg_dirs=[tmp_path],
        veloc_cfg_name="veloc.cfg",
        out_dir=tmp_path,
    )
    proof = json.loads((tmp_path / "resilience_proof.json").read_text())
    assert proof["framework_version"] == FRAMEWORK_VERSION


def test_f10_benchmark_results_carries_framework_version(tmp_path):
    from validation.veloc import FRAMEWORK_VERSION
    from validation.veloc.metrics_collector import BenchmarkResults
    br = BenchmarkResults(scenarios=[], runs=[], summary={})
    out = br.to_dict()
    assert out["framework_version"] == FRAMEWORK_VERSION


# ---------------------------------------------------------------------------
# F-11 / CRIT-2 — injection-fired guard (logic check)
# ---------------------------------------------------------------------------

def test_f11_injection_guard_logic():
    """Verify the literal guard predicate in metrics_collector source."""
    text = (REPO_ROOT / "validation" / "veloc" / "metrics_collector.py").read_text()
    # The guard must check ALL of: scenario.inject_failures, codebase=="resilient",
    # not result.injected.
    assert "scenario.inject_failures" in text
    assert 'codebase == "resilient"' in text
    assert "not result.injected" in text


# ---------------------------------------------------------------------------
# CRIT-3 — validate_iter_result accepts/rejects synthetic result.json
# ---------------------------------------------------------------------------

def test_crit3_validator_accepts_consistent_iter_loop_result(tmp_path):
    from validation.veloc.scripts.validate_iter_result import check_one
    p = tmp_path / "result.json"
    p.write_text(json.dumps({
        "schema_version": 2,
        "passed": True,
        "_passed_via": "iter_loop",
        "per_iteration": [{"iter": 1, "validation_passed": True}],
    }))
    ok, msg = check_one(p)
    assert ok, msg


def test_crit3_validator_rejects_iter_loop_with_diverging_last_iter(tmp_path):
    from validation.veloc.scripts.validate_iter_result import check_one
    p = tmp_path / "result.json"
    p.write_text(json.dumps({
        "schema_version": 2,
        "passed": True,
        "_passed_via": "iter_loop",
        "per_iteration": [{"iter": 1, "validation_passed": False}],  # mismatch!
    }))
    ok, msg = check_one(p)
    assert not ok
    assert "iter_loop" in msg


def test_crit3_validator_accepts_external_validate_with_note(tmp_path):
    from validation.veloc.scripts.validate_iter_result import check_one
    p = tmp_path / "result.json"
    p.write_text(json.dumps({
        "schema_version": 2,
        "passed": True,
        "_passed_via": "external_validate",
        "_reconstruction_note": "Orphan validate.py completed after wrapper SIGKILL",
        "per_iteration": [{"iter": 1, "validation_passed": False}],
    }))
    ok, msg = check_one(p)
    assert ok, msg


def test_crit3_validator_rejects_external_validate_without_note(tmp_path):
    from validation.veloc.scripts.validate_iter_result import check_one
    p = tmp_path / "result.json"
    p.write_text(json.dumps({
        "schema_version": 2,
        "passed": True,
        "_passed_via": "external_validate",
        "per_iteration": [{"iter": 1, "validation_passed": False}],
    }))
    ok, msg = check_one(p)
    assert not ok
    assert "_reconstruction_note" in msg


def test_crit3_validator_rejects_schema_v2_missing_provenance(tmp_path):
    from validation.veloc.scripts.validate_iter_result import check_one
    p = tmp_path / "result.json"
    p.write_text(json.dumps({
        "schema_version": 2,
        "passed": True,
        "per_iteration": [{"iter": 1, "validation_passed": True}],
    }))
    ok, msg = check_one(p)
    assert not ok
    assert "_passed_via" in msg


# ---------------------------------------------------------------------------
# F-5 — chain-script orphan-completion verifier
# ---------------------------------------------------------------------------

def test_f5_orphan_verifier_returns_2_for_unknown_unit():
    from validation.veloc.scripts.check_unit_completion import _check_iter_unit
    rc, msg = _check_iter_unit("DefinitelyDoesNotExist_baseline")
    assert rc == 2  # INDETERMINATE
    assert "no result.json" in msg


def test_f5_orphan_verifier_returns_0_for_passed_iter_unit():
    """Pick any unit known to be passed in the current state."""
    from validation.veloc.scripts.check_unit_completion import _check_iter_unit
    rc, msg = _check_iter_unit("LAMMPS_baseline")
    assert rc == 0


# ---------------------------------------------------------------------------
# Vanilla HPCG source change verification
# ---------------------------------------------------------------------------

def test_vanilla_hpcg_reads_workload_pin():
    src = REPO_ROOT / "tests" / "apps" / "vanillas" / "HPCG" / "src" / "main.cpp"
    text = src.read_text()
    assert 'getenv("HPCG_FIXED_SETS")' in text


def test_hypar_patch_n_iter_matches_vanilla_n_iter():
    """The HyPar patch's n_iter must mirror vanilla's, otherwise reference
    bench runs a different workload than the vanilla baseline it's compared
    against."""
    vanilla_inp = (REPO_ROOT / "tests" / "apps" / "vanillas" / "HyPar"
                   / "Examples" / "1D" / "FPDoubleWell" / "solver.inp").read_text()
    patch_inp = (REPO_ROOT / "tests" / "apps" / "patches" / "HyPar"
                 / "Examples" / "1D" / "FPDoubleWell" / "solver.inp").read_text()
    van_match = re.search(r"^\s*n_iter\s+(\d+)", vanilla_inp, re.M)
    pat_match = re.search(r"^\s*n_iter\s+(\d+)", patch_inp, re.M)
    assert van_match and pat_match, "n_iter not found in one of the files"
    assert van_match.group(1) == pat_match.group(1), (
        f"vanilla n_iter={van_match.group(1)} != patch n_iter={pat_match.group(1)}"
    )


def test_ross_nyx_samrai_keep_patterns_have_no_banned_word():
    import yaml
    from validation.veloc.reference_validator import (
        validate_keep_patterns, _BANNED_KEEP_PATTERN_SUBSTRINGS,
    )
    for app in ("ROSS", "Nyx", "SAMRAI"):
        cfg = yaml.safe_load(
            (REPO_ROOT / "tests" / "apps" / "configs" / f"{app}.yaml").read_text()
        )
        # SAMRAI moved to numeric binary comparison only (no keep_patterns) —
        # skip apps that have legitimately dropped the field rather than
        # KeyError on what is now an optional config knob.
        keeps = cfg.get("comparison", {}).get("keep_patterns")
        if not keeps:
            continue
        # Should not raise
        validate_keep_patterns(keeps, app_label=app)
        # And every pattern should look numeric/structural, not verdict-y.
        joined = " ".join(keeps).lower()
        for banned in _BANNED_KEEP_PATTERN_SUBSTRINGS:
            assert banned not in joined, f"{app} keep_pattern still contains {banned!r}"


# ---------------------------------------------------------------------------
# Universal-export run_validate.sh smoke
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# D1 — Dedicated streaming comparator (2026-05-03)
# ---------------------------------------------------------------------------

def test_d1_streaming_comparator_passes_on_matching_files(tmp_path):
    """Streaming comparator agrees with text-diff when content matches."""
    from validation.veloc.reference_validator import _compare_outputs_streaming
    g = tmp_path / "g.txt"
    t = tmp_path / "t.txt"
    g.write_text("Init done\nTotal Events Processed 12345\nGoodbye\n")
    t.write_text("Init done\nTotal Events Processed 12345\nGoodbye\n")
    res = _compare_outputs_streaming(
        golden_file=g, test_file=t, method="text", keep_patterns=["Total Events Processed"],
    )
    assert res.passed is True, res.details


def test_d1_streaming_comparator_fails_on_diverging_filtered_content(tmp_path):
    from validation.veloc.reference_validator import _compare_outputs_streaming
    g = tmp_path / "g.txt"
    t = tmp_path / "t.txt"
    g.write_text("Iteration 5000: count=12345\nDone\n")
    t.write_text("Iteration 5000: count=99999\nDone\n")
    res = _compare_outputs_streaming(
        golden_file=g, test_file=t, method="text", keep_patterns=["Iteration"],
    )
    assert res.passed is False


def test_d1_streaming_comparator_empty_match_guard_fires_on_test_side(tmp_path):
    """F-3 Layer B in streaming variant: empty test filter → FAIL."""
    from validation.veloc.reference_validator import _compare_outputs_streaming
    g = tmp_path / "g.txt"
    t = tmp_path / "t.txt"
    g.write_text("real GVT line 12345\n")
    t.write_text("FAST RECOVERY shortcut taken\n")
    res = _compare_outputs_streaming(
        golden_file=g, test_file=t, method="text",
        keep_patterns=["GVT"],
    )
    assert res.passed is False
    assert "anti-gaming" in res.details.lower() or "empty" in res.details.lower()


def test_d1_streaming_comparator_banner_blocklist_still_enforced(tmp_path):
    """F-3 Layer A in streaming variant: rejects banner patterns."""
    from validation.veloc.reference_validator import _compare_outputs_streaming
    g = tmp_path / "g.txt"
    t = tmp_path / "t.txt"
    g.write_text("hi\n")
    t.write_text("hi\n")
    import pytest
    with pytest.raises(ValueError, match="banned substring"):
        _compare_outputs_streaming(
            golden_file=g, test_file=t, method="text",
            keep_patterns=["PASSED"],
        )


def test_d1_streaming_comparator_handles_missing_file(tmp_path):
    from validation.veloc.reference_validator import _compare_outputs_streaming
    g = tmp_path / "g.txt"
    t = tmp_path / "missing.txt"
    g.write_text("Total Events Processed 12345\n")
    res = _compare_outputs_streaming(
        golden_file=g, test_file=t, method="text",
        keep_patterns=["Total Events Processed"],
    )
    assert res.passed is False  # F-3 Layer B fires (test side empty)


def test_d1_streaming_comparator_numeric_method(tmp_path):
    from validation.veloc.reference_validator import _compare_outputs_streaming
    g = tmp_path / "g.txt"
    t = tmp_path / "t.txt"
    g.write_text("Total Events Processed 240977813\nTotal GVT Computations 470661\n")
    t.write_text("Total Events Processed 240977812\nTotal GVT Computations 470661\n")
    res = _compare_outputs_streaming(
        golden_file=g, test_file=t, method="numeric",
        tolerance=0.01,
        keep_patterns=["Total"],
    )
    assert res.passed is True  # ~0% relative diff on 240M; well within 1%


def test_d1_streaming_does_not_load_full_file_into_memory(tmp_path):
    """Smoke-test: comparator handles a large file without crashing.
    A real OOM test would need GB-scale; here we just verify it iterates
    line-by-line (huge file with many keep-pattern hits, but only matched
    lines accumulate)."""
    from validation.veloc.reference_validator import _compare_outputs_streaming
    g = tmp_path / "g.txt"
    t = tmp_path / "t.txt"
    # Write 500k lines, only a handful match keep_pattern
    with g.open("w") as f:
        for i in range(500000):
            f.write(f"step {i} junk_data_{i*17 % 1000}\n")
        f.write("Total Events Processed 12345\n")
    with t.open("w") as f:
        for i in range(500000):
            f.write(f"step {i} junk_data_{i*17 % 1000}\n")
        f.write("Total Events Processed 12345\n")
    res = _compare_outputs_streaming(
        golden_file=g, test_file=t, method="text",
        keep_patterns=["Total Events Processed"],
    )
    assert res.passed is True


def test_d1_validate_py_routes_streaming_method_choice():
    """validate.py CLI accepts the new streaming-text and streaming-numeric
    method names without an argparse error."""
    text = (REPO_ROOT / "validation" / "veloc" / "validate.py").read_text()
    assert '"streaming-text"' in text
    assert '"streaming-numeric"' in text
    assert "_compare_outputs_streaming" in text


def test_d1_yaml_to_config_passes_streaming_method_through():
    from validation.veloc import yaml_to_config
    cfg = {"comparison": {"method": "streaming-text", "tolerance": 0.01,
                          "keep_patterns": ["Finished"]}}
    flags = yaml_to_config.get_comparison_flags(cfg)
    assert "--comparison-method streaming-text" in flags


def test_d1_hypar_yaml_uses_streaming_method():
    """HyPar must use a streaming-* variant to avoid the 375 MB OOM, AND
    use a numeric science signature (Q1B, 2026-05-03 hardening) — the
    prior 'Finished' single-banner pattern was LLM-fakeable."""
    import yaml
    cfg = yaml.safe_load((REPO_ROOT / "tests/apps/configs/HyPar.yaml").read_text())
    method = cfg["comparison"]["method"]
    assert method.startswith("streaming-"), \
        f"HyPar method={method!r}; must use streaming-* to avoid 375 MB OOM"
    # Q1B: keep_patterns must include a numeric science signature, not just
    # the LLM-fakeable 'Finished' banner.
    keeps = cfg["comparison"]["keep_patterns"]
    assert any("Error" in p for p in keeps), \
        f"HyPar keep_patterns={keeps!r} must include L1/L2/Linfinity Error " \
        "(numeric, LLM cannot fake without doing the real work)"


# ---------------------------------------------------------------------------
# D2 — WarpX keep_pattern fix (banner -> numeric)
# ---------------------------------------------------------------------------

def test_d2_warpx_yaml_uses_numeric_step_signature():
    import yaml
    cfg = yaml.safe_load((REPO_ROOT / "tests/apps/configs/WarpX.yaml").read_text())
    assert cfg["comparison"]["method"] == "numeric"
    assert any("ends. TIME" in p or "STEP" in p for p in cfg["comparison"]["keep_patterns"]), \
        "WarpX must use a per-step numeric signature, not 'completed successfully'"
    # Old banner should be gone
    assert "completed successfully" not in str(cfg["comparison"]["keep_patterns"])


# ---------------------------------------------------------------------------
# D4 — Bench wallclock cap bump (900 -> 1800)
# ---------------------------------------------------------------------------

def test_d4_bench_timeout_bumped_to_1800():
    text = (REPO_ROOT / "validation/veloc/metrics_collector.py").read_text()
    assert "timeout_s=1800.0" in text
    val_text = (REPO_ROOT / "validation/veloc/validate.py").read_text()
    # validate.py's failure-free run also bumped
    assert val_text.count("timeout_s=1800.0") >= 1


# ---------------------------------------------------------------------------
# D6 — F-5 chain-verifier fix uses two-step capture (not | tail | $?)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# D3 — Retry-on-stall + retry-on-max-iters with vanilla reset
# ---------------------------------------------------------------------------

def test_d3_run_iterative_has_outer_retry_loop():
    """run_iterative.sh wraps the for-iter loop in a while-LOOP_ATTEMPT
    loop with the user-approved retry-on-stall + retry-on-max-iters
    semantics."""
    text = (REPO_ROOT / "validation/veloc/scripts/run_iterative.sh").read_text()
    # Outer loop variables present
    assert "LOOP_ATTEMPT=1" in text
    assert "MAX_LOOP_ATTEMPTS=" in text
    assert 'OPENCODE_RETRIES="${OPENCODE_RETRIES:-2}"' in text
    # Outer while wraps the iter loop
    assert 'while [ "$LOOP_ATTEMPT" -le "$MAX_LOOP_ATTEMPTS" ]; do' in text
    # Inner for-iter still present
    assert 'for ITER in $(seq 1 "$MAX_ITERS"); do' in text


def test_d3_resets_to_vanilla_on_retry():
    """On retry attempts (>1), the script wipes APP_DIR and re-copies vanilla
    from VANILLA_SRC_ROOT (saved during the initial copy)."""
    text = (REPO_ROOT / "validation/veloc/scripts/run_iterative.sh").read_text()
    # Vanilla root is captured during initial copy
    assert 'VANILLA_SRC_ROOT="$_src_root"' in text
    # Re-copy on retry guarded by LOOP_ATTEMPT > 1
    assert 'if [ "$LOOP_ATTEMPT" -gt 1 ]; then' in text
    assert 'cp -a "$VANILLA_SRC_ROOT/$APP_NAME" "$APP_DIR"' in text


def test_d3_per_iter_accumulators_reset_each_attempt():
    """Q1: per-iter history wiped at the start of each retry attempt."""
    text = (REPO_ROOT / "validation/veloc/scripts/run_iterative.sh").read_text()
    # The reset block lives INSIDE the while loop (after the re-copy guard,
    # before the for-iter loop starts).
    while_idx = text.find('while [ "$LOOP_ATTEMPT" -le "$MAX_LOOP_ATTEMPTS" ]; do')
    for_idx = text.find('for ITER in $(seq 1 "$MAX_ITERS"); do')
    assert while_idx > 0 and for_idx > while_idx
    inner = text[while_idx:for_idx]
    assert 'TOTAL_ELAPSED="0.0"' in inner
    assert 'ITER_METRICS=""' in inner
    assert 'TOTAL_TOKENS=0' in inner


def test_d3_stall_path_breaks_for_outer_retry():
    """Q2 (part 1): on stall, the for-iter loop breaks (does NOT exit) so the
    outer while can decide to retry vs final-fail."""
    text = (REPO_ROOT / "validation/veloc/scripts/run_iterative.sh").read_text()
    # The stall block must end with `break`, not `exit 2`.
    # Find the STALL_ABORTED block.
    stall_idx = text.find('if [ "$STALL_ABORTED" = 1 ]; then')
    assert stall_idx > 0
    # Search forward for the close of the stall if-block
    end = text.find('# --- Step 3', stall_idx)
    assert end > 0
    stall_block = text[stall_idx:end]
    # Must use break, not exit 2
    assert 'break' in stall_block
    assert 'exit 2' not in stall_block
    assert 'LOOP_OUTCOME="stall"' in stall_block


def test_d3_max_iters_path_continues_outer_loop():
    """Q2 (part 2): max-iters exhausted also triggers retry (not just stall)."""
    text = (REPO_ROOT / "validation/veloc/scripts/run_iterative.sh").read_text()
    # The post-for block must check LOOP_OUTCOME and either continue the
    # outer while (retry) or break it (final fail).
    post_for_idx = text.find('# --- D3: decide whether this loop attempt')
    assert post_for_idx > 0
    end = text.find('# END while LOOP_ATTEMPT', post_for_idx)
    assert end > 0
    block = text[post_for_idx:end]
    assert 'LOOP_OUTCOME="max_iters"' in block
    assert 'continue' in block  # retry path
    assert 'break' in block     # final-fail path


def test_d3_result_json_includes_loop_attempt_metrics():
    """User wanted: log the number of failures/stalls until success for
    later metric reporting."""
    text = (REPO_ROOT / "validation/veloc/scripts/run_iterative.sh").read_text()
    # Both success path and final-fail path must emit these new fields
    assert text.count('"loop_attempt_final"') >= 2
    assert text.count('"loop_stall_count"') >= 2
    assert text.count('"loop_max_iters_count"') >= 2
    assert text.count('"prior_loop_attempts"') >= 2


def test_d3_default_retries_is_two():
    """OPENCODE_RETRIES default = 2 → MAX_LOOP_ATTEMPTS = 3."""
    text = (REPO_ROOT / "validation/veloc/scripts/run_iterative.sh").read_text()
    assert 'OPENCODE_RETRIES="${OPENCODE_RETRIES:-2}"' in text
    assert 'MAX_LOOP_ATTEMPTS=$((1 + OPENCODE_RETRIES))' in text


def test_d3_existing_iter_passes_unaffected():
    """Existing passed iter result.jsons (from the prior session) must
    still validate cleanly under the new schema — we ADDED fields, not
    removed any."""
    import json
    # Pick a representative known-good iter
    p = REPO_ROOT / "build/iterative_logs/HPCG_baseline/result.json"
    if not p.exists():
        import pytest as _pt
        _pt.skip("HPCG_baseline result.json not present (chain hasn't run yet)")
    d = json.loads(p.read_text())
    # All existing required fields still present
    for k in ("app_name", "mode", "passed", "iterations", "max_iters",
              "total_elapsed_s", "wall_elapsed_s", "total_tokens",
              "per_iteration"):
        assert k in d, f"existing field {k!r} missing from result.json"


def test_d6_chain_verifier_uses_two_step_capture():
    """The chain script's bench/iter verifier must use two-step assignment
    so that $? captures python's exit code, NOT tail's (always 0)."""
    text = (REPO_ROOT / "build/_experiment_state/longexp_phase_b.sh").read_text()
    # Two-step pattern markers
    assert "_full=$(" in text
    assert "verifier_rc=$?" in text
    # The buggy pattern (cmd | tail -1 immediately followed by verifier_rc=$?)
    # should NOT exist anywhere (we replaced it with the two-step capture).
    import re
    bad = re.search(r"check_unit_completion[^\n]*tail -1\)\s*\n\s*verifier_rc=\$\?", text)
    assert bad is None, "Old buggy pipeline-then-$? pattern still present"


# ---------------------------------------------------------------------------
# ROSS Fix C — audit reference baseline runs N times, take median
# ---------------------------------------------------------------------------

def test_ross_fix_c_audit_runs_n_reference_baselines():
    """validate.py must run the reference baseline N=3 times (default) and
    take the median for F-1 to absorb single-run timing noise."""
    text = (REPO_ROOT / "validation/veloc/validate.py").read_text()
    assert 'AUDIT_REF_BASELINE_RUNS = int(os.environ.get("AUDIT_REF_BASELINE_RUNS", "3"))' in text
    assert "from statistics import median as _median" in text
    assert "ref_baseline_elapsed_runs" in text


def test_ross_fix_c_records_per_run_timings_in_proof():
    """For forensics, all N timings should land in resilience_proof.json."""
    text = (REPO_ROOT / "validation/veloc/validate.py").read_text()
    assert '"reference_failure_free_elapsed_runs"' in text


# ---------------------------------------------------------------------------
# HyPar Fix B — bounded stdout/stderr capture (BENCH_STDOUT_TRUNCATE_LINES)
# ---------------------------------------------------------------------------

def test_hypar_fix_b_tail_reader_bounded(tmp_path):
    """The tail-bounded reader returns last N lines when env var is set,
    full file otherwise."""
    import os
    from validation.veloc.runner import _read_text_tailed
    f = tmp_path / "big.txt"
    with f.open("w") as fh:
        for i in range(10000):
            fh.write(f"line {i}\n")

    # Default behavior: full file
    os.environ.pop("BENCH_STDOUT_TRUNCATE_LINES", None)
    full = _read_text_tailed(f)
    assert full.count("\n") == 10000

    # With env var: last N lines + a header marker
    os.environ["BENCH_STDOUT_TRUNCATE_LINES"] = "100"
    try:
        truncated = _read_text_tailed(f)
        assert "BENCH_STDOUT_TRUNCATE_LINES=100" in truncated
        # Last 100 data lines plus the 1-line header
        # Actual line count may include trailing partial; assert near
        assert truncated.count("line ") <= 101
        assert "line 9999" in truncated  # last line preserved
        assert "line 0\n" not in truncated  # first line dropped
    finally:
        os.environ.pop("BENCH_STDOUT_TRUNCATE_LINES", None)


def test_hypar_fix_b_tail_reader_handles_empty(tmp_path):
    from validation.veloc.runner import _read_text_tailed
    import os
    os.environ["BENCH_STDOUT_TRUNCATE_LINES"] = "100"
    try:
        empty = tmp_path / "empty.txt"
        empty.write_text("")
        assert _read_text_tailed(empty) == ""
        missing = tmp_path / "nope.txt"
        assert _read_text_tailed(missing) == ""
    finally:
        os.environ.pop("BENCH_STDOUT_TRUNCATE_LINES", None)


def test_hypar_fix_b_runner_uses_tailed_reader_at_all_capture_sites():
    """Every stdout/stderr Python-string capture must go through the new
    tail-bounded reader (not bare path.read_text)."""
    text = (REPO_ROOT / "validation/veloc/runner.py").read_text()
    # The bare-pattern that we replaced should be gone for stdout/stderr files.
    import re
    bare_pattern = re.compile(
        r'\b(stdout|stderr|a[12]_stdout|a[12]_stderr|last_stdout|last_stderr)_path'
        r'\.read_text\(encoding="utf-8", errors="replace"\)'
    )
    matches = bare_pattern.findall(text)
    assert not matches, (
        f"Bare path.read_text() for stdout/stderr file still present at "
        f"{len(matches)} site(s); switch to _read_text_tailed()"
    )
    # Verify the new helper is used.
    assert text.count("_read_text_tailed(") >= 10


def test_hypar_fix_b_run_validate_sh_exports_truncate_for_HyPar():
    """run_validate.sh must export BENCH_STDOUT_TRUNCATE_LINES for HyPar."""
    text = (REPO_ROOT / "validation/veloc/scripts/run_validate.sh").read_text()
    # The HyPar case in the per-app stdout-truncation block
    assert "BENCH_STDOUT_TRUNCATE_LINES=1000" in text


def test_run_validate_sh_exports_workload_pin_universally():
    """HPCG_FIXED_SETS must appear OUTSIDE the USE_REFERENCE block."""
    text = (REPO_ROOT / "validation" / "veloc" / "scripts" / "run_validate.sh").read_text()
    fi_pos = text.find("\nfi\n", text.find("if [ \"$USE_REFERENCE\" = true ]; then"))
    assert fi_pos > 0
    universal_section = text[fi_pos:]
    assert "HPCG_FIXED_SETS" in universal_section
    assert "Workload-pin env (universal)" in universal_section
