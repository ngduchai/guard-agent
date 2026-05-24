"""Tests for the parallel-queue --resume capability.

The orchestrator continuously persists per-app state to:
    - build/iterative_logs/<APP>_<LABEL>/iter_N/metrics.json
        (written immediately after each validate completes)
    - build/iterative_logs/<APP>_<LABEL>/result.json
    - build/iterative_logs/<APP>_<LABEL>/parallel_timing.json
        (both written at every terminal transition AND at drain)

`--resume` reads these back via _load_app_resume_state and reconstructs
AppRun fields so the run continues from where it left off.  Apps that
already PASSed or that exhausted their retry budget are skipped.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from validation.veloc.scripts.run_parallel_queue import (
    AppRun,
    AppState,
    IterMetrics,
    LoopAttempt,
    Orchestrator,
    _archive_crashed_logs,
    _classify_iter_crash,
    _gen_metrics_complete,
    _load_app_resume_state,
    _load_partial_gen_iter,
    _metrics_complete,
)


def _make_app(tmp_path: Path, *, max_iters: int = 50,
              max_loop_attempts: int = 3) -> AppRun:
    return AppRun(
        name="STUB",
        label="baseline",
        app_dir=tmp_path / "tests_baseline" / "STUB",
        log_dir=tmp_path / "iterative_logs" / "STUB_baseline",
        vanilla_src=tmp_path / "vanillas" / "STUB",
        max_iters=max_iters,
        max_loop_attempts=max_loop_attempts,
        benchmark_num_runs=3,
    )


def _write_iter_metrics(log_dir: Path, iter_n: int, *,
                        validation_passed: bool,
                        opencode_elapsed_s: float = 10.0,
                        validation_elapsed_s: float = 20.0,
                        input_tokens: int = 100,
                        output_tokens: int = 200,
                        stall_aborted: bool = False) -> None:
    d = log_dir / f"iter_{iter_n}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "metrics.json").write_text(json.dumps({
        "iter": iter_n,
        "opencode_elapsed_s": opencode_elapsed_s,
        "validation_elapsed_s": validation_elapsed_s,
        "total_elapsed_s": opencode_elapsed_s + validation_elapsed_s,
        "validation_passed": validation_passed,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "stall_aborted": stall_aborted,
        "gen_queue_wait_s": 0.5,
        "val_queue_wait_s": 1.5,
    }))


def _write_result_json(log_dir: Path, *, passed: bool,
                       loop_attempt_final: int = 1,
                       prior_attempts: list | None = None,
                       loop_stall_count: int = 0,
                       loop_max_iters_count: int = 0) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "result.json").write_text(json.dumps({
        "app_name": "STUB",
        "schema_version": 2,
        "passed": passed,
        "loop_attempt_final": loop_attempt_final,
        "loop_stall_count": loop_stall_count,
        "loop_max_iters_count": loop_max_iters_count,
        "prior_loop_attempts": prior_attempts or [],
    }))


def _write_parallel_timing(log_dir: Path, *,
                           per_iter: list[dict] | None = None,
                           bench_wall_s: float = 0.0,
                           bench_exit_code: int = 0) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "parallel_timing.json").write_text(json.dumps({
        "schema": "parallel_timing_v1",
        "app_name": "STUB",
        "label": "baseline",
        "per_iter": per_iter or [],
        "bench_wall_s": bench_wall_s,
        "bench_queue_wait_s": 0.0,
        "bench_started_at": None,
        "bench_exit_code": bench_exit_code,
        "loop_attempts_total": 1,
        "loop_stall_count": 0,
        "loop_max_iters_count": 0,
        "verdict": "IN_PROGRESS",
    }))


# --- _load_app_resume_state ---------------------------------------------------


def test_load_resume_no_prior_data(tmp_path: Path) -> None:
    """Empty log_dir → empty dict (treat as fresh start)."""
    app = _make_app(tmp_path)
    assert _load_app_resume_state(app) == {}


def test_load_resume_log_dir_with_no_iter_metrics(tmp_path: Path) -> None:
    """log_dir exists but no iter_*/metrics.json → empty dict."""
    app = _make_app(tmp_path)
    app.log_dir.mkdir(parents=True)
    (app.log_dir / "result.json").write_text("{}")
    assert _load_app_resume_state(app) == {}


def test_load_resume_skips_iter_dirs_without_metrics(tmp_path: Path) -> None:
    """iter_5 exists but has no metrics.json → treated as not-yet-validated."""
    app = _make_app(tmp_path)
    _write_iter_metrics(app.log_dir, 1, validation_passed=False)
    _write_iter_metrics(app.log_dir, 2, validation_passed=False)
    (app.log_dir / "iter_3").mkdir()  # no metrics.json
    prior = _load_app_resume_state(app)
    assert len(prior["completed_iters"]) == 2
    assert prior["completed_iters"][-1].iter == 2


def test_load_resume_pass_verdict(tmp_path: Path) -> None:
    """A passing run produces verdict=PASS and verdict_passed=True."""
    app = _make_app(tmp_path)
    _write_iter_metrics(app.log_dir, 1, validation_passed=False)
    _write_iter_metrics(app.log_dir, 2, validation_passed=True)
    _write_result_json(app.log_dir, passed=True, loop_attempt_final=1)
    prior = _load_app_resume_state(app)
    assert prior["verdict"] == "PASS"
    assert prior["verdict_passed"] is True
    assert prior["exhausted_retries"] is False
    assert len(prior["completed_iters"]) == 2


def test_load_resume_exhausted_retries(tmp_path: Path) -> None:
    """All loop attempts used + no pass → verdict=FAIL, exhausted_retries=True."""
    app = _make_app(tmp_path, max_loop_attempts=2)
    _write_iter_metrics(app.log_dir, 1, validation_passed=False)
    _write_iter_metrics(app.log_dir, 2, validation_passed=False)
    _write_result_json(
        app.log_dir,
        passed=False,
        loop_attempt_final=2,
        prior_attempts=[
            {"attempt": 1, "outcome": "stall", "iters_run": 1, "stall_iteration": 1},
            {"attempt": 2, "outcome": "max_iters", "iters_run": 1, "stall_iteration": 0},
        ],
    )
    prior = _load_app_resume_state(app)
    assert prior["verdict"] == "FAIL"
    assert prior["exhausted_retries"] is True
    assert len(prior["prior_attempts"]) == 2


def test_load_resume_in_progress(tmp_path: Path) -> None:
    """Mid-attempt run with retries remaining → verdict=IN_PROGRESS."""
    app = _make_app(tmp_path, max_loop_attempts=3)
    _write_iter_metrics(app.log_dir, 1, validation_passed=False)
    _write_iter_metrics(app.log_dir, 2, validation_passed=False)
    _write_iter_metrics(app.log_dir, 3, validation_passed=False)
    _write_result_json(app.log_dir, passed=False, loop_attempt_final=1)
    prior = _load_app_resume_state(app)
    assert prior["verdict"] == "IN_PROGRESS"
    assert prior["exhausted_retries"] is False
    assert prior["loop_attempt"] == 1
    assert prior["completed_iters"][-1].iter == 3


def test_load_resume_in_progress_no_result_json(tmp_path: Path) -> None:
    """Iter dirs but no result.json → default loop_attempt=1, IN_PROGRESS."""
    app = _make_app(tmp_path)
    _write_iter_metrics(app.log_dir, 1, validation_passed=False)
    _write_iter_metrics(app.log_dir, 2, validation_passed=False)
    prior = _load_app_resume_state(app)
    assert prior["verdict"] == "IN_PROGRESS"
    assert prior["loop_attempt"] == 1
    assert prior["exhausted_retries"] is False


def test_load_resume_restores_per_iter_exit_codes(tmp_path: Path) -> None:
    """parallel_timing.json provides gen/val exit codes + started_at."""
    app = _make_app(tmp_path)
    _write_iter_metrics(app.log_dir, 1, validation_passed=False)
    _write_iter_metrics(app.log_dir, 2, validation_passed=False)
    _write_parallel_timing(app.log_dir, per_iter=[
        {"iter": 1, "gen_exit_code": 0, "val_exit_code": 1,
         "gen_started_at": "2026-05-24T10:00:00Z",
         "val_started_at": "2026-05-24T10:00:10Z"},
        {"iter": 2, "gen_exit_code": 0, "val_exit_code": 124,
         "gen_started_at": "2026-05-24T10:01:00Z",
         "val_started_at": "2026-05-24T10:01:10Z"},
    ])
    prior = _load_app_resume_state(app)
    m1, m2 = prior["completed_iters"]
    assert m1.val_exit_code == 1
    assert m2.val_exit_code == 124
    assert m1.gen_started_at == "2026-05-24T10:00:00Z"


def test_load_resume_restores_bench_fields(tmp_path: Path) -> None:
    """bench_wall_s / bench_exit_code carry over from parallel_timing.json."""
    app = _make_app(tmp_path)
    _write_iter_metrics(app.log_dir, 1, validation_passed=True)
    _write_parallel_timing(app.log_dir, bench_wall_s=42.5, bench_exit_code=0)
    prior = _load_app_resume_state(app)
    assert prior["bench_wall_s"] == 42.5
    assert prior["bench_exit_code"] == 0


def test_load_resume_corrupt_result_json_is_safe(tmp_path: Path) -> None:
    """Malformed result.json must NOT crash — fall back to defaults."""
    app = _make_app(tmp_path)
    _write_iter_metrics(app.log_dir, 1, validation_passed=False)
    (app.log_dir / "result.json").write_text("{ not valid json")
    prior = _load_app_resume_state(app)
    # Falls back to defaults but iter_metrics still loaded.
    assert prior["loop_attempt"] == 1
    assert prior["completed_iters"][0].iter == 1


# --- _apply_resume_state (Orchestrator-level) --------------------------------


def _make_orchestrator(tmp_path: Path, *, max_iters: int = 50,
                        max_loop_attempts: int = 3,
                        skip_bench: bool = True,
                        monkeypatch) -> Orchestrator:
    """Build an Orchestrator with build paths redirected under tmp_path so the
    test does not touch the real repo layout.  Resolves the app name to a
    fake vanilla source by monkeypatching _resolve_vanilla."""
    fake_vanilla = tmp_path / "vanillas" / "STUB"
    fake_vanilla.mkdir(parents=True)
    monkeypatch.setattr(
        "validation.veloc.scripts.run_parallel_queue._resolve_vanilla",
        lambda name: fake_vanilla,
    )
    monkeypatch.setattr(
        "validation.veloc.scripts.run_parallel_queue.BUILD_DIR",
        tmp_path / "build",
    )
    monkeypatch.setattr(
        "validation.veloc.scripts.run_parallel_queue.ITERATIVE_LOGS",
        tmp_path / "build" / "iterative_logs",
    )
    orch = Orchestrator(
        app_names=["STUB"],
        max_gen_workers=1,
        max_iters=max_iters,
        benchmark_num_runs=3,
        label="baseline",
        opencode_retries=max_loop_attempts - 1,
        skip_bench=skip_bench,
        resume=True,
    )
    return orch


def test_apply_resume_returns_false_when_no_prior(tmp_path: Path,
                                                    monkeypatch) -> None:
    orch = _make_orchestrator(tmp_path, monkeypatch=monkeypatch)
    app = orch.apps["STUB"]
    assert orch._apply_resume_state(app) is False
    assert app.iter == 0
    assert app.state == AppState.NOT_STARTED


def test_apply_resume_marks_pass_terminal(tmp_path: Path,
                                            monkeypatch) -> None:
    orch = _make_orchestrator(tmp_path, monkeypatch=monkeypatch)
    app = orch.apps["STUB"]
    app.log_dir.mkdir(parents=True)
    _write_iter_metrics(app.log_dir, 1, validation_passed=True)
    _write_result_json(app.log_dir, passed=True)
    _write_parallel_timing(app.log_dir)

    initial_remaining = orch.remaining
    skipped = orch._apply_resume_state(app)
    assert skipped is True
    assert app.state == AppState.DONE_PASSED
    assert orch.remaining == initial_remaining - 1
    assert app.verdict_passed is True
    # _mark_app_done writes the per-app JSONs idempotently.
    assert (app.log_dir / "result.json").exists()


def test_apply_resume_marks_exhausted_fail_terminal(tmp_path: Path,
                                                      monkeypatch) -> None:
    orch = _make_orchestrator(tmp_path, max_loop_attempts=2,
                              monkeypatch=monkeypatch)
    app = orch.apps["STUB"]
    app.log_dir.mkdir(parents=True)
    _write_iter_metrics(app.log_dir, 1, validation_passed=False)
    _write_result_json(
        app.log_dir,
        passed=False,
        loop_attempt_final=2,
        prior_attempts=[
            {"attempt": 1, "outcome": "max_iters", "iters_run": 50, "stall_iteration": 0},
            {"attempt": 2, "outcome": "max_iters", "iters_run": 50, "stall_iteration": 0},
        ],
    )
    _write_parallel_timing(app.log_dir)

    initial_remaining = orch.remaining
    skipped = orch._apply_resume_state(app)
    assert skipped is True
    assert app.state == AppState.DONE_FAILED
    assert orch.remaining == initial_remaining - 1


def test_apply_resume_restores_in_progress_and_returns_false(
    tmp_path: Path, monkeypatch
) -> None:
    """The interesting case: continue from iter N+1 with budget remaining."""
    orch = _make_orchestrator(tmp_path, max_loop_attempts=3,
                              monkeypatch=monkeypatch)
    app = orch.apps["STUB"]
    app.log_dir.mkdir(parents=True)
    _write_iter_metrics(app.log_dir, 1, validation_passed=False)
    _write_iter_metrics(app.log_dir, 2, validation_passed=False)
    _write_iter_metrics(app.log_dir, 3, validation_passed=False)
    _write_result_json(app.log_dir, passed=False, loop_attempt_final=1)
    _write_parallel_timing(app.log_dir)

    initial_remaining = orch.remaining
    skipped = orch._apply_resume_state(app)
    assert skipped is False
    assert app.iter == 3                        # next iter will be 4
    assert app.loop_attempt == 1
    assert len(app.per_iter) == 3
    assert orch.remaining == initial_remaining  # not decremented for in-progress
    # State is NOT yet READY_FOR_GEN — caller (run()) sets that AFTER us.
    # We only restore bookkeeping in _apply_resume_state.


def test_apply_resume_preserves_prior_attempts(tmp_path: Path,
                                                 monkeypatch) -> None:
    """prior_loop_attempts must round-trip so the D3 retry budget is honored."""
    orch = _make_orchestrator(tmp_path, max_loop_attempts=3,
                              monkeypatch=monkeypatch)
    app = orch.apps["STUB"]
    app.log_dir.mkdir(parents=True)
    _write_iter_metrics(app.log_dir, 1, validation_passed=False)
    _write_result_json(
        app.log_dir,
        passed=False,
        loop_attempt_final=2,
        prior_attempts=[
            {"attempt": 1, "outcome": "stall", "iters_run": 3, "stall_iteration": 3},
        ],
        loop_stall_count=1,
    )
    _write_parallel_timing(app.log_dir)

    orch._apply_resume_state(app)
    assert len(app.prior_attempts) == 1
    assert app.prior_attempts[0].outcome == "stall"
    assert app.prior_attempts[0].stall_iteration == 3
    assert app.loop_attempt == 2
    assert app.loop_stall_count == 1


def test_resume_flag_off_does_not_load_prior_state(tmp_path: Path,
                                                     monkeypatch) -> None:
    """Without --resume, prior state on disk is ignored."""
    # Build orch WITHOUT resume=True.
    fake_vanilla = tmp_path / "vanillas" / "STUB"
    fake_vanilla.mkdir(parents=True)
    monkeypatch.setattr(
        "validation.veloc.scripts.run_parallel_queue._resolve_vanilla",
        lambda name: fake_vanilla,
    )
    monkeypatch.setattr(
        "validation.veloc.scripts.run_parallel_queue.BUILD_DIR",
        tmp_path / "build",
    )
    monkeypatch.setattr(
        "validation.veloc.scripts.run_parallel_queue.ITERATIVE_LOGS",
        tmp_path / "build" / "iterative_logs",
    )
    orch = Orchestrator(
        app_names=["STUB"],
        max_gen_workers=1,
        max_iters=10,
        benchmark_num_runs=3,
        label="baseline",
        opencode_retries=2,
        skip_bench=True,
        resume=False,
    )
    app = orch.apps["STUB"]
    app.log_dir.mkdir(parents=True)
    _write_iter_metrics(app.log_dir, 1, validation_passed=True)
    _write_result_json(app.log_dir, passed=True)

    # _apply_resume_state would mark it terminal, but the run() guard
    # `if self.resume and self._apply_resume_state(app)` short-circuits
    # before calling the method.  We assert the guard semantics here.
    assert orch.resume is False
    # And the AppRun is still pristine.
    assert app.iter == 0
    assert app.per_iter == []


# --- Crash-immediate resume classification + dispatch ------------------------
#
# Per project policy (2026-05-24): when the orchestrator crashes mid-iter, the
# on-disk source tree under app_dir may be a partial LLM edit.  Recovery rule
# is differentiated by which stage of the iter was in flight:
#
#   mid_gen      → wipe app + restage vanilla + restart iter 1 (crash does
#                  NOT burn a retry attempt; prior logs archived for the paper)
#   mid_validate → preserve source (LLM iter completed = source is a clean
#                  checkpoint), re-queue ("validate", N) on the executor
#   mid_bench    → preserve everything, re-queue ("bench", final_iter)
#   clean        → existing logic (continue from highest_complete + 1)
#   terminal     → existing logic (skip)


def _write_iter_gen_metrics(log_dir: Path, iter_n: int, *,
                             gen_wall_s: float = 10.0,
                             tokens_input: int = 100,
                             tokens_output: int = 200) -> None:
    """Write iter_N/metrics_gen.json only (no metrics.json) — simulates a
    mid-validate crash where the helper completed gen but the orchestrator
    never wrote the post-validate metrics."""
    d = log_dir / f"iter_{iter_n}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "metrics_gen.json").write_text(json.dumps({
        "gen_wall_s": gen_wall_s,
        "tokens_input": tokens_input,
        "tokens_output": tokens_output,
        "tokens_total": tokens_input + tokens_output,
        "stall_aborted": False,
    }))


def _write_iter_empty(log_dir: Path, iter_n: int) -> None:
    """Create iter_N/ with no metrics files — simulates a mid-gen crash."""
    (log_dir / f"iter_{iter_n}").mkdir(parents=True, exist_ok=True)


# --- _metrics_complete / _gen_metrics_complete -------------------------------


def test_metrics_complete_missing_file(tmp_path: Path) -> None:
    assert _metrics_complete(tmp_path / "metrics.json") is False


def test_metrics_complete_malformed(tmp_path: Path) -> None:
    p = tmp_path / "metrics.json"
    p.write_text("{ not json")
    assert _metrics_complete(p) is False


def test_metrics_complete_missing_validation_passed(tmp_path: Path) -> None:
    p = tmp_path / "metrics.json"
    p.write_text(json.dumps({"iter": 1}))
    assert _metrics_complete(p) is False


def test_metrics_complete_full(tmp_path: Path) -> None:
    p = tmp_path / "metrics.json"
    p.write_text(json.dumps({"iter": 1, "validation_passed": True}))
    assert _metrics_complete(p) is True


def test_gen_metrics_complete_full(tmp_path: Path) -> None:
    p = tmp_path / "metrics_gen.json"
    p.write_text(json.dumps({"gen_wall_s": 5.0}))
    assert _gen_metrics_complete(p) is True


def test_gen_metrics_complete_missing_field(tmp_path: Path) -> None:
    p = tmp_path / "metrics_gen.json"
    p.write_text(json.dumps({"tokens_input": 10}))
    assert _gen_metrics_complete(p) is False


# --- _classify_iter_crash ----------------------------------------------------


def test_classify_iter_crash_no_log_dir(tmp_path: Path) -> None:
    assert _classify_iter_crash(tmp_path / "nope")["mode"] == "clean"


def test_classify_iter_crash_empty_log_dir(tmp_path: Path) -> None:
    (tmp_path / "logs").mkdir()
    assert _classify_iter_crash(tmp_path / "logs")["mode"] == "clean"


def test_classify_iter_crash_all_iters_complete(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    _write_iter_metrics(log_dir, 1, validation_passed=False)
    _write_iter_metrics(log_dir, 2, validation_passed=True)
    assert _classify_iter_crash(log_dir)["mode"] == "clean"


def test_classify_iter_crash_mid_gen_iter_1(tmp_path: Path) -> None:
    """iter 1 dir exists but no metrics_gen.json → mid_gen at iter 1."""
    log_dir = tmp_path / "logs"
    _write_iter_empty(log_dir, 1)
    result = _classify_iter_crash(log_dir)
    assert result == {"mode": "mid_gen", "iter": 1}


def test_classify_iter_crash_mid_gen_after_clean_iters(tmp_path: Path) -> None:
    """iters 1-3 complete, iter 4 dir exists with no metrics_gen.json."""
    log_dir = tmp_path / "logs"
    _write_iter_metrics(log_dir, 1, validation_passed=False)
    _write_iter_metrics(log_dir, 2, validation_passed=False)
    _write_iter_metrics(log_dir, 3, validation_passed=False)
    _write_iter_empty(log_dir, 4)
    result = _classify_iter_crash(log_dir)
    assert result == {"mode": "mid_gen", "iter": 4}


def test_classify_iter_crash_mid_validate_iter_1(tmp_path: Path) -> None:
    """iter 1 has metrics_gen.json but no metrics.json → mid_validate."""
    log_dir = tmp_path / "logs"
    _write_iter_gen_metrics(log_dir, 1)
    result = _classify_iter_crash(log_dir)
    assert result == {"mode": "mid_validate", "iter": 1}


def test_classify_iter_crash_mid_validate_after_clean_iters(tmp_path: Path) -> None:
    """iters 1-4 complete, iter 5 has gen but no validate."""
    log_dir = tmp_path / "logs"
    for n in range(1, 5):
        _write_iter_metrics(log_dir, n, validation_passed=False)
    _write_iter_gen_metrics(log_dir, 5, gen_wall_s=7.5)
    result = _classify_iter_crash(log_dir)
    assert result == {"mode": "mid_validate", "iter": 5}


def test_classify_iter_crash_ignores_lower_incomplete(tmp_path: Path) -> None:
    """Only the highest iter is classified — defensive shape check.  In
    practice the orchestrator never starts iter N+1 until iter N completes,
    so a lower iter without metrics is structurally impossible.  But the
    classifier must not crash on the shape regardless."""
    log_dir = tmp_path / "logs"
    _write_iter_empty(log_dir, 1)  # lower incomplete
    _write_iter_metrics(log_dir, 2, validation_passed=True)
    # Highest iter (2) is complete → classifier returns clean.
    assert _classify_iter_crash(log_dir)["mode"] == "clean"


# --- _archive_crashed_logs ---------------------------------------------------


def test_archive_crashed_logs_moves_dir(tmp_path: Path) -> None:
    log_dir = tmp_path / "STUB_baseline"
    log_dir.mkdir()
    (log_dir / "marker.txt").write_text("hello")
    archive = _archive_crashed_logs(log_dir)
    assert archive is not None
    assert archive.parent == tmp_path
    assert archive.name.startswith("STUB_baseline.CRASHED_")
    assert (archive / "marker.txt").read_text() == "hello"
    assert not log_dir.exists()


def test_archive_crashed_logs_collision_disambiguates(tmp_path: Path) -> None:
    """Two archives in the same UTC second must not collide."""
    log_dir = tmp_path / "X"
    log_dir.mkdir()
    a1 = _archive_crashed_logs(log_dir)
    log_dir.mkdir()
    a2 = _archive_crashed_logs(log_dir)
    assert a1 is not None and a2 is not None
    assert a1 != a2


def test_archive_crashed_logs_no_dir_is_noop(tmp_path: Path) -> None:
    assert _archive_crashed_logs(tmp_path / "missing") is None


# --- _load_partial_gen_iter --------------------------------------------------


def test_load_partial_gen_iter_full_fields(tmp_path: Path) -> None:
    d = tmp_path / "iter_3"
    d.mkdir()
    (d / "metrics_gen.json").write_text(json.dumps({
        "gen_wall_s": 8.25,
        "tokens_input": 50,
        "tokens_output": 75,
        "tokens_total": 125,
        "stall_aborted": False,
    }))
    m = _load_partial_gen_iter(d, 3)
    assert m.iter == 3
    assert m.gen_wall_s == 8.25
    assert m.tokens_input == 50
    assert m.tokens_output == 75
    assert m.val_wall_s == 0.0  # not yet populated
    assert m.validation_passed is False  # default


def test_load_partial_gen_iter_missing_file(tmp_path: Path) -> None:
    d = tmp_path / "iter_1"
    d.mkdir()
    m = _load_partial_gen_iter(d, 1)
    assert m.iter == 1
    assert m.gen_wall_s == 0.0


# --- Orchestrator _apply_resume_state — crash branches ----------------------


def test_apply_resume_mid_gen_archives_wipes_and_resets(
    tmp_path: Path, monkeypatch
) -> None:
    """LLM was mid-edit at iter 4: prior 3 iters complete; iter 4 dir exists
    with no metrics_gen.json; app_dir contains stale edits.

    Expect: logs moved to CRASHED archive, app_dir wiped and restaged from
    vanilla, AppRun reset to iter=0 / loop_attempt=1 (no retry burned),
    log_dir recreated empty.  Returns False so caller enqueues at READY_FOR_GEN.
    """
    orch = _make_orchestrator(tmp_path, max_loop_attempts=3,
                              monkeypatch=monkeypatch)
    app = orch.apps["STUB"]
    # 3 complete iters
    _write_iter_metrics(app.log_dir, 1, validation_passed=False)
    _write_iter_metrics(app.log_dir, 2, validation_passed=False)
    _write_iter_metrics(app.log_dir, 3, validation_passed=False)
    _write_result_json(app.log_dir, passed=False, loop_attempt_final=1)
    _write_parallel_timing(app.log_dir)
    # iter 4 mid-gen: dir exists, no metrics_gen.json
    _write_iter_empty(app.log_dir, 4)
    # Stale edits in app_dir (LLM was editing here when crash hit)
    app.app_dir.mkdir(parents=True, exist_ok=True)
    (app.app_dir / "STALE_EDIT.cpp").write_text("// half-edited junk")
    # Vanilla source has a clean marker file
    (app.vanilla_src / "VANILLA_MARKER.txt").write_text("clean")

    initial_remaining = orch.remaining
    result = orch._apply_resume_state(app)

    assert result is False  # caller enqueues at READY_FOR_GEN
    # Archive sibling exists under iterative_logs/ with the crashed contents.
    archives = list(app.log_dir.parent.glob("STUB_baseline.CRASHED_*"))
    assert len(archives) == 1
    assert (archives[0] / "iter_4").is_dir()
    assert (archives[0] / "iter_3" / "metrics.json").exists()
    # log_dir recreated empty
    assert app.log_dir.exists()
    assert list(app.log_dir.iterdir()) == []
    # app_dir restaged from vanilla, stale edit gone
    assert not (app.app_dir / "STALE_EDIT.cpp").exists()
    assert (app.app_dir / "VANILLA_MARKER.txt").exists()
    # AppRun reset
    assert app.state == AppState.NOT_STARTED
    assert app.iter == 0
    assert app.loop_attempt == 1
    assert app.per_iter == []
    assert app.prior_attempts == []
    # remaining is NOT decremented — app is alive, just restarted
    assert orch.remaining == initial_remaining


def test_apply_resume_mid_validate_requeues_executor(
    tmp_path: Path, monkeypatch
) -> None:
    """iter 5 gen completed, validate crashed before writing metrics.json.

    Expect: source preserved (no wipe), prior 4 iters restored, partial iter 5
    appended with only gen fields, state = QUEUED_FOR_EXECUTOR, executor_queue
    has ("STUB", "validate", 5).  Returns True (skip default enqueue).
    """
    orch = _make_orchestrator(tmp_path, max_loop_attempts=3, skip_bench=False,
                              monkeypatch=monkeypatch)
    app = orch.apps["STUB"]
    for n in range(1, 5):
        _write_iter_metrics(app.log_dir, n, validation_passed=False)
    _write_iter_gen_metrics(app.log_dir, 5, gen_wall_s=12.5)
    _write_result_json(app.log_dir, passed=False, loop_attempt_final=1)
    _write_parallel_timing(app.log_dir)
    # Source tree from the LLM's iter-5 edit — must be preserved
    app.app_dir.mkdir(parents=True, exist_ok=True)
    (app.app_dir / "LLM_EDIT.cpp").write_text("// iter 5 final code")

    initial_remaining = orch.remaining
    result = orch._apply_resume_state(app)

    assert result is True
    # No archive should have been created
    assert not list(app.log_dir.parent.glob("STUB_baseline.CRASHED_*"))
    # Source preserved
    assert (app.app_dir / "LLM_EDIT.cpp").read_text() == "// iter 5 final code"
    # State restored
    assert app.iter == 5
    assert app.state == AppState.QUEUED_FOR_EXECUTOR
    assert len(app.per_iter) == 5
    assert app.per_iter[-1].iter == 5
    assert app.per_iter[-1].gen_wall_s == 12.5
    assert app.per_iter[-1].validation_passed is False  # not yet
    # Executor queue has the validate task
    items = list(orch.executor_queue.queue)
    assert ("STUB", "validate", 5) in items
    # remaining not decremented — app still in flight
    assert orch.remaining == initial_remaining


def test_apply_resume_mid_validate_at_iter_1(
    tmp_path: Path, monkeypatch
) -> None:
    """Edge: mid_validate hits at iter 1 with no prior complete iters."""
    orch = _make_orchestrator(tmp_path, max_loop_attempts=3, skip_bench=False,
                              monkeypatch=monkeypatch)
    app = orch.apps["STUB"]
    app.log_dir.mkdir(parents=True)
    _write_iter_gen_metrics(app.log_dir, 1, gen_wall_s=4.0)

    result = orch._apply_resume_state(app)
    assert result is True
    assert app.iter == 1
    assert len(app.per_iter) == 1
    assert app.per_iter[0].iter == 1
    assert app.per_iter[0].gen_wall_s == 4.0
    assert app.state == AppState.QUEUED_FOR_EXECUTOR
    items = list(orch.executor_queue.queue)
    assert ("STUB", "validate", 1) in items


def test_apply_resume_mid_bench_requeues_executor(
    tmp_path: Path, monkeypatch
) -> None:
    """iter loop passed (latest iter validation_passed=true), no result.json,
    bench was queued or running.  Expect re-queue at executor as bench task.
    """
    orch = _make_orchestrator(tmp_path, max_loop_attempts=3, skip_bench=False,
                              monkeypatch=monkeypatch)
    app = orch.apps["STUB"]
    _write_iter_metrics(app.log_dir, 1, validation_passed=False)
    _write_iter_metrics(app.log_dir, 2, validation_passed=True)
    # NO result.json — bench never finalized
    _write_parallel_timing(app.log_dir)

    initial_remaining = orch.remaining
    result = orch._apply_resume_state(app)

    assert result is True
    assert app.state == AppState.QUEUED_FOR_BENCH
    assert app.verdict_passed is True
    assert app.iter == 2
    items = list(orch.executor_queue.queue)
    assert ("STUB", "bench", 2) in items
    # Bench fields reset so the new bench run captures fresh measurements
    assert app.bench_started_at is None
    assert app.bench_wall_s == 0.0
    # remaining not decremented — still in flight
    assert orch.remaining == initial_remaining


def test_apply_resume_skip_bench_pass_without_result_is_terminal(
    tmp_path: Path, monkeypatch
) -> None:
    """When skip_bench=True, a validation_passed iter without result.json
    must NOT be treated as mid_bench — the orchestrator would have written
    result.json synchronously on PASS in skip_bench mode.  Such on-disk
    shape is anomalous; we treat it as IN_PROGRESS (existing logic) rather
    than queueing a bench that the user explicitly disabled."""
    orch = _make_orchestrator(tmp_path, max_loop_attempts=3, skip_bench=True,
                              monkeypatch=monkeypatch)
    app = orch.apps["STUB"]
    _write_iter_metrics(app.log_dir, 1, validation_passed=True)
    _write_parallel_timing(app.log_dir)

    result = orch._apply_resume_state(app)
    # NOT enqueued at bench (skip_bench=True suppresses the branch).
    assert app.state != AppState.QUEUED_FOR_BENCH
    assert not any(t for t in list(orch.executor_queue.queue) if t and t[1] == "bench")
    # Falls through to normal in-progress disposition.
    assert result is False


def test_apply_resume_clean_path_still_works_after_crash_dispatch(
    tmp_path: Path, monkeypatch
) -> None:
    """Regression: existing clean-resume PASS path must still mark terminal."""
    orch = _make_orchestrator(tmp_path, max_loop_attempts=3,
                              monkeypatch=monkeypatch)
    app = orch.apps["STUB"]
    _write_iter_metrics(app.log_dir, 1, validation_passed=False)
    _write_iter_metrics(app.log_dir, 2, validation_passed=True)
    _write_result_json(app.log_dir, passed=True, loop_attempt_final=1)
    _write_parallel_timing(app.log_dir)

    initial_remaining = orch.remaining
    result = orch._apply_resume_state(app)
    assert result is True
    assert app.state == AppState.DONE_PASSED
    assert orch.remaining == initial_remaining - 1
