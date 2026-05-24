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
    _load_app_resume_state,
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
    assert app.state == AppState.NOT_STARTED
