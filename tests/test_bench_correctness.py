"""Tests for the bench-stage per-run output-correctness check.

The bench stage (`metrics_collector.run_benchmark_sweep`) now applies the
same output comparator the correctness stage uses on every per-run output
file, comparing it to the canonical baseline at
``build/baseline_cache/<APP>/<output_file_name>``.  These tests cover:

  * RunMetrics carries the new output_correct fields and round-trips
    them through to_dict / _load_bench_progress.
  * _build_summary aggregates per-(scenario,codebase) verdicts so the
    trust gate sees a single ``all_passed`` boolean per cell.
  * _build_bench_output_check returns ``(None, None)`` when the
    baseline file is missing (additive opt-in behaviour).
  * The file-based closure round-trips a real CompareResult and
    correctly flips passed → False on mismatch / missing candidate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from validation.veloc.metrics_collector import (
    RunMetrics,
    _build_summary,
    _load_bench_progress,
    _save_bench_progress,
)
from validation.veloc.validate import _build_bench_output_check


# ---------------------------------------------------------------------------
# RunMetrics field plumbing
# ---------------------------------------------------------------------------


def test_run_metrics_carries_output_correctness_fields() -> None:
    m = RunMetrics(
        scenario_name="small-nofail",
        codebase="resilient",
        run_index=1,
        elapsed_s=12.5,
        injected=False,
        num_attempts=1,
        output_correct=True,
        output_compare_method="numeric-tolerance",
        output_compare_message="max_abs_diff=0.0",
    )
    d = m.to_dict()
    assert d["output_correct"] is True
    assert d["output_compare_method"] == "numeric-tolerance"
    assert d["output_compare_message"] == "max_abs_diff=0.0"


def test_run_metrics_defaults_to_none_when_check_disabled() -> None:
    m = RunMetrics(
        scenario_name="small-nofail",
        codebase="original",
        run_index=1,
        elapsed_s=10.0,
        injected=False,
        num_attempts=1,
    )
    assert m.output_correct is None
    assert m.output_compare_method is None
    assert m.output_compare_message is None


def test_bench_progress_round_trips_output_correctness_fields(
    tmp_path: Path,
) -> None:
    runs = [
        RunMetrics(
            scenario_name="small-nofail",
            codebase="resilient",
            run_index=1,
            elapsed_s=12.5,
            injected=False,
            num_attempts=1,
            checkpoint_size_bytes=4096,
            output_correct=True,
            output_compare_method="hash",
            output_compare_message="byte-identical",
        ),
        RunMetrics(
            scenario_name="small-nofail",
            codebase="resilient",
            run_index=2,
            elapsed_s=13.0,
            injected=False,
            num_attempts=1,
            checkpoint_size_bytes=4096,
            output_correct=False,
            output_compare_method="hash",
            output_compare_message="SHA-256 mismatch",
        ),
    ]
    bench_dir = tmp_path / "benchmarks"
    bench_dir.mkdir()
    _save_bench_progress(bench_dir, runs)
    loaded, keys = _load_bench_progress(bench_dir)
    assert len(loaded) == 2
    assert {r.output_correct for r in loaded} == {True, False}
    assert all(r.output_compare_method == "hash" for r in loaded)
    assert "small-nofail:resilient:1" in keys


# ---------------------------------------------------------------------------
# _build_summary aggregation
# ---------------------------------------------------------------------------


def _mk_run(
    sc: str, cb: str, idx: int, oc: bool | None,
) -> RunMetrics:
    return RunMetrics(
        scenario_name=sc, codebase=cb, run_index=idx, elapsed_s=1.0,
        injected=False, num_attempts=1, output_correct=oc,
    )


def test_summary_aggregates_all_passed_true_when_every_run_matches() -> None:
    runs = [
        _mk_run("small-nofail", "resilient", 1, True),
        _mk_run("small-nofail", "resilient", 2, True),
        _mk_run("small-nofail", "resilient", 3, True),
    ]
    summary = _build_summary(runs)
    oc = summary["small-nofail"]["resilient"]["output_correct"]
    assert oc == {
        "n_total": 3, "n_checked": 3, "n_passed": 3,
        "all_passed": True, "any_checked": True,
    }


def test_summary_aggregates_all_passed_false_when_any_run_fails() -> None:
    runs = [
        _mk_run("small-once", "resilient", 1, True),
        _mk_run("small-once", "resilient", 2, False),
        _mk_run("small-once", "resilient", 3, True),
    ]
    summary = _build_summary(runs)
    oc = summary["small-once"]["resilient"]["output_correct"]
    assert oc["n_passed"] == 2
    assert oc["n_checked"] == 3
    assert oc["all_passed"] is False


def test_summary_marks_check_skipped_when_all_runs_have_none() -> None:
    runs = [
        _mk_run("small-nofail", "resilient", 1, None),
        _mk_run("small-nofail", "resilient", 2, None),
    ]
    summary = _build_summary(runs)
    oc = summary["small-nofail"]["resilient"]["output_correct"]
    assert oc["n_checked"] == 0
    assert oc["any_checked"] is False
    assert oc["all_passed"] is False  # any_checked=False ⇒ all_passed=False


def test_summary_partial_check_counts_only_checked_runs() -> None:
    runs = [
        _mk_run("small-nofail", "resilient", 1, True),
        _mk_run("small-nofail", "resilient", 2, None),
        _mk_run("small-nofail", "resilient", 3, True),
    ]
    summary = _build_summary(runs)
    oc = summary["small-nofail"]["resilient"]["output_correct"]
    assert oc == {
        "n_total": 3, "n_checked": 2, "n_passed": 2,
        "all_passed": True, "any_checked": True,
    }


# ---------------------------------------------------------------------------
# _build_bench_output_check closure behaviour
# ---------------------------------------------------------------------------


def _make_args(
    output_file_name: str = "validation_output.bin",
    comparison_method: str = "hash",
) -> argparse.Namespace:
    return argparse.Namespace(
        output_file_name=output_file_name,
        comparison_method=comparison_method,
        numeric_atol=1e-6,
        numeric_rtol=1e-6,
        hdf5_dataset="data",
        ssim_threshold=0.9999,
        custom_comparator=None,
        text_ignore_patterns=None,
        text_keep_patterns=None,
        text_strip_patterns=None,
    )


def _populate_baseline_cache(
    tmp_path: Path, app_name: str, output_file_name: str, content: bytes,
) -> tuple[Path, Path]:
    """Create build/baseline_cache/<APP>/<output_file_name> under tmp_path."""
    cache_dir = (
        tmp_path / "build" / "baseline_cache" / app_name
    )
    cache_dir.mkdir(parents=True)
    baseline_file = cache_dir / output_file_name
    baseline_file.write_bytes(content)
    return cache_dir, baseline_file


def test_build_check_returns_none_when_baseline_missing(
    tmp_path: Path,
) -> None:
    args = _make_args()
    fake_src = tmp_path / "tests" / "apps" / "vanillas" / "FakeApp"
    fake_src.mkdir(parents=True)
    # No baseline_cache populated → check is opt-in (returns None, None).
    # Use monkeypatching of the default cache resolver: easier path is to
    # point original_src under tmp_path so _default_baseline_cache_dir
    # lands somewhere we know doesn't exist.
    import validation.veloc.validate as v
    saved = v._default_baseline_cache_dir
    try:
        v._default_baseline_cache_dir = lambda src: tmp_path / "noexist" / src.name
        cmp_fn, baseline = _build_bench_output_check(
            args=args, original_src=fake_src,
        )
    finally:
        v._default_baseline_cache_dir = saved
    assert cmp_fn is None
    assert baseline is None


def test_build_check_returns_none_when_no_output_file_name(
    tmp_path: Path,
) -> None:
    args = _make_args(output_file_name="")
    fake_src = tmp_path / "FakeApp"
    fake_src.mkdir()
    cmp_fn, baseline = _build_bench_output_check(
        args=args, original_src=fake_src,
    )
    assert cmp_fn is None
    assert baseline is None


def test_build_check_returns_passing_closure_on_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    args = _make_args(comparison_method="hash")
    fake_src = tmp_path / "FakeApp"
    fake_src.mkdir()
    cache_dir, baseline = _populate_baseline_cache(
        tmp_path, "FakeApp", "validation_output.bin", b"identical-bytes",
    )
    monkeypatch.setattr(
        "validation.veloc.validate._default_baseline_cache_dir",
        lambda src: cache_dir,
    )
    cmp_fn, baseline_out = _build_bench_output_check(
        args=args, original_src=fake_src,
    )
    assert cmp_fn is not None
    assert baseline_out == baseline

    candidate = tmp_path / "candidate.bin"
    candidate.write_bytes(b"identical-bytes")
    passed, method, message = cmp_fn(baseline_out, candidate)
    assert passed is True
    assert "hash" in method.lower()


def test_build_check_returns_failing_closure_on_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    args = _make_args(comparison_method="hash")
    fake_src = tmp_path / "FakeApp"
    fake_src.mkdir()
    cache_dir, baseline = _populate_baseline_cache(
        tmp_path, "FakeApp", "validation_output.bin", b"golden-bytes",
    )
    monkeypatch.setattr(
        "validation.veloc.validate._default_baseline_cache_dir",
        lambda src: cache_dir,
    )
    cmp_fn, baseline_out = _build_bench_output_check(
        args=args, original_src=fake_src,
    )
    assert cmp_fn is not None
    candidate = tmp_path / "candidate.bin"
    candidate.write_bytes(b"different-bytes")
    passed, method, message = cmp_fn(baseline_out, candidate)
    assert passed is False
    assert "mismatch" in message.lower() or "sha-256" in message.lower()


def test_build_check_reports_missing_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    args = _make_args(comparison_method="hash")
    fake_src = tmp_path / "FakeApp"
    fake_src.mkdir()
    cache_dir, baseline = _populate_baseline_cache(
        tmp_path, "FakeApp", "validation_output.bin", b"x",
    )
    monkeypatch.setattr(
        "validation.veloc.validate._default_baseline_cache_dir",
        lambda src: cache_dir,
    )
    cmp_fn, baseline_out = _build_bench_output_check(
        args=args, original_src=fake_src,
    )
    missing_candidate = tmp_path / "does_not_exist.bin"
    passed, method, message = cmp_fn(baseline_out, missing_candidate)
    assert passed is False
    assert "missing" in message.lower()
