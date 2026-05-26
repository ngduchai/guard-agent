"""Tests for the per-iter stall-retry mechanism (2026-05-26).

Background: prior behavior on a mid-iter OpenCode stall was to abort the
current loop attempt and restart from vanilla on a new loop attempt.  This
discarded all prior successful iters of the current loop, costing many
LLM tokens.  The new behavior (per user directive 2026-05-26):

  1. snapshot the codebase tree at iter start via `git init` + `git add -A`
     + `git commit --allow-empty`;
  2. on stall, hard-reset the tree to that snapshot (discarding partial
     mid-stall edits) and re-queue the SAME iter;
  3. cap retries at --opencode-retries; on exhaustion, transition straight
     to DONE_FAILED (no fallback loop-restart, per user directive).

Forensics on each stall attempt are preserved by renaming the stalled
iter dir to ``iter_<N>_stall<retry>`` BEFORE the retry begins.

These tests pin all four behaviors:
    - git snapshot is idempotent and works on fresh and existing repos
    - git reset rolls back uncommitted partial edits
    - _handle_stall retry path increments counter, archives, re-queues
    - _handle_stall exhaustion path goes terminal without loop-restart
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from validation.veloc.scripts.run_parallel_queue import (
    AppRun,
    AppState,
    IterMetrics,
    LoopAttempt,
    Orchestrator,
    _git,
    _git_init_snapshot,
    _git_reset_hard,
)


# Skip everything in this module if git is not installed.
pytestmark = pytest.mark.skipif(
    shutil.which("git") is None,
    reason="git binary required for stall-retry snapshot tests",
)


# --- _git helper -------------------------------------------------------------


def test_git_helper_returns_127_when_dir_missing(tmp_path: Path) -> None:
    """The wrapper does not raise on missing cwd — it returns a non-zero rc."""
    rc, out = _git(tmp_path / "does_not_exist", "status")
    # subprocess.run raises FileNotFoundError on missing cwd; helper catches it.
    assert rc != 0
    assert isinstance(out, str)


# --- _git_init_snapshot ------------------------------------------------------


def test_git_init_snapshot_creates_repo_and_commits(tmp_path: Path) -> None:
    """First call: initializes repo, commits everything."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "src.cpp").write_text("int main(){}\n")

    ok = _git_init_snapshot(app_dir, "first snapshot")
    assert ok is True
    assert (app_dir / ".git").is_dir()

    # Verify the commit landed.
    rc, out = _git(app_dir, "log", "--oneline")
    assert rc == 0
    assert "first snapshot" in out


def test_git_init_snapshot_is_idempotent(tmp_path: Path) -> None:
    """Calling twice on the same dir does not fail; produces 2 commits."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "f.txt").write_text("a")
    assert _git_init_snapshot(app_dir, "snap1") is True

    (app_dir / "f.txt").write_text("b")
    assert _git_init_snapshot(app_dir, "snap2") is True

    rc, out = _git(app_dir, "log", "--oneline")
    assert rc == 0
    lines = [l for l in out.splitlines() if l.strip()]
    assert len(lines) == 2


def test_git_init_snapshot_allows_empty(tmp_path: Path) -> None:
    """Snapshotting twice with no changes between still succeeds (--allow-empty)."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "f.txt").write_text("a")
    _git_init_snapshot(app_dir, "snap1")
    # No changes — should still commit thanks to --allow-empty.
    assert _git_init_snapshot(app_dir, "snap2_empty") is True


def test_git_init_snapshot_missing_dir_returns_false(tmp_path: Path) -> None:
    """Non-existent app_dir → returns False, no crash."""
    assert _git_init_snapshot(tmp_path / "missing", "x") is False


# --- _git_reset_hard ---------------------------------------------------------


def test_git_reset_hard_rolls_back_modifications(tmp_path: Path) -> None:
    """Uncommitted edits to tracked files are discarded by reset."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "src.cpp").write_text("original\n")
    _git_init_snapshot(app_dir, "baseline")

    # LLM-style partial edit
    (app_dir / "src.cpp").write_text("PARTIAL EDIT (stalled)\n")

    assert _git_reset_hard(app_dir) is True
    assert (app_dir / "src.cpp").read_text() == "original\n"


def test_git_reset_hard_removes_untracked_files(tmp_path: Path) -> None:
    """Files created by the stalled iter (not yet committed) are removed."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "src.cpp").write_text("orig\n")
    _git_init_snapshot(app_dir, "baseline")

    # LLM created a new file mid-stall
    (app_dir / "NEW_HALF_BAKED.cpp").write_text("// junk\n")
    (app_dir / "subdir").mkdir()
    (app_dir / "subdir" / "also.h").write_text("// junk\n")

    assert _git_reset_hard(app_dir) is True
    assert not (app_dir / "NEW_HALF_BAKED.cpp").exists()
    assert not (app_dir / "subdir").exists()
    # Original tracked file untouched
    assert (app_dir / "src.cpp").read_text() == "orig\n"


def test_git_reset_hard_no_git_dir_returns_false(tmp_path: Path) -> None:
    """Reset against a non-repo returns False (does not crash)."""
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    assert _git_reset_hard(app_dir) is False


# --- _handle_stall orchestrator method --------------------------------------


def _make_orchestrator(tmp_path: Path, *, opencode_retries: int = 2,
                       monkeypatch) -> Orchestrator:
    """Build an Orchestrator with paths redirected under tmp_path."""
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
    return Orchestrator(
        app_names=["STUB"],
        max_gen_workers=1,
        max_iters=50,
        benchmark_num_runs=3,
        label="baseline",
        opencode_retries=opencode_retries,
        skip_bench=True,
        resume=False,
    )


def _seed_stalled_iter(app: AppRun, iter_n: int) -> Path:
    """Append a stalled IterMetrics + create the iter_<N>/ log dir on disk.

    Mirrors what _do_one_gen_iter does BEFORE calling _handle_stall.
    """
    app.per_iter.append(IterMetrics(
        iter=iter_n,
        gen_wall_s=3600.0,
        tokens_input=1_500_000,
        tokens_output=10_000,
        tokens_total=1_510_000,
        stall_aborted=True,
        stall_retries=app.iter_stall_retry_count,
        gen_exit_code=0,
    ))
    iter_log = app.log_dir / f"iter_{iter_n}"
    iter_log.mkdir(parents=True, exist_ok=True)
    (iter_log / "metrics_gen.json").write_text(json.dumps({
        "stall_aborted": True, "gen_wall_s": 3600.0,
    }))
    (iter_log / "stall_watch.log").write_text("stall detected at 1234s\n")
    return iter_log


def test_handle_stall_retry_within_budget(tmp_path: Path, monkeypatch) -> None:
    """First stall on iter 3: archives, resets git, re-queues SAME iter."""
    orch = _make_orchestrator(tmp_path, opencode_retries=2,
                              monkeypatch=monkeypatch)
    app = orch.apps["STUB"]
    # Seed the app_dir as a git repo with a pre-iter-3 snapshot
    app.app_dir.mkdir(parents=True, exist_ok=True)
    (app.app_dir / "src.cpp").write_text("clean iter-3 start\n")
    _git_init_snapshot(app.app_dir, "pre-iter 3")
    # Simulate LLM partial edit that needs to be rolled back
    (app.app_dir / "src.cpp").write_text("HALF-EDITED MID-STALL\n")
    (app.app_dir / "JUNK.h").write_text("// junk\n")
    # Set iter cursor BEFORE the stall (mimic _do_one_gen_iter)
    app.iter = 3
    iter_log = _seed_stalled_iter(app, 3)

    orch._handle_stall(app, 3, iter_log)

    # Counter incremented, but not exhausted
    assert app.iter_stall_retry_count == 1
    # Archive exists; original iter dir gone
    assert not iter_log.exists()
    assert (app.log_dir / "iter_3_stall1").is_dir()
    assert (app.log_dir / "iter_3_stall1" / "stall_watch.log").exists()
    # Per-iter list popped the stalled entry (retry will re-append)
    assert app.per_iter == []
    # Git reset rolled back the partial edit + removed junk
    assert (app.app_dir / "src.cpp").read_text() == "clean iter-3 start\n"
    assert not (app.app_dir / "JUNK.h").exists()
    # State + queue: ready for gen, iter cursor decremented to N-1
    assert app.state == AppState.READY_FOR_GEN
    assert app.iter == 2  # _do_one_gen_iter will increment back to 3
    assert "STUB" in list(orch.ready_for_gen.queue)
    # No loop-restart bookkeeping touched
    assert app.loop_attempt == 1
    assert app.prior_attempts == []
    assert app.loop_stall_count == 0


def test_handle_stall_second_retry_within_budget(tmp_path: Path, monkeypatch) -> None:
    """Second stall on the SAME iter: counter goes to 2, archive uses stall2 suffix."""
    orch = _make_orchestrator(tmp_path, opencode_retries=2,
                              monkeypatch=monkeypatch)
    app = orch.apps["STUB"]
    app.app_dir.mkdir(parents=True, exist_ok=True)
    (app.app_dir / "src.cpp").write_text("clean\n")
    _git_init_snapshot(app.app_dir, "pre-iter 3")
    # Already had one stall on iter 3
    app.iter_stall_retry_count = 1
    app.iter = 3
    iter_log = _seed_stalled_iter(app, 3)

    orch._handle_stall(app, 3, iter_log)

    assert app.iter_stall_retry_count == 2
    assert (app.log_dir / "iter_3_stall2").is_dir()
    assert app.state == AppState.READY_FOR_GEN
    # Still under budget (budget=2): no terminal transition
    assert app.app_finished_at == 0.0
    assert orch.remaining == 1  # not decremented


def test_handle_stall_exhausts_budget_goes_terminal(tmp_path: Path,
                                                    monkeypatch) -> None:
    """Third stall on iter 3 with budget=2: terminal DONE_FAILED, NO loop restart."""
    orch = _make_orchestrator(tmp_path, opencode_retries=2,
                              monkeypatch=monkeypatch)
    app = orch.apps["STUB"]
    app.app_dir.mkdir(parents=True, exist_ok=True)
    _git_init_snapshot(app.app_dir, "pre-iter 3")
    # Already exhausted both retries on iter 3 (counter at 2)
    app.iter_stall_retry_count = 2
    app.iter = 3
    iter_log = _seed_stalled_iter(app, 3)

    orch._handle_stall(app, 3, iter_log)

    # Counter goes to 3 → exceeds budget=2 → terminal
    assert app.iter_stall_retry_count == 3
    # Archive still happens even on terminal (forensics for the final attempt)
    assert (app.log_dir / "iter_3_stall3").is_dir()
    # Terminal state
    assert app.state == AppState.DONE_FAILED
    assert app.final_stall_aborted is True
    assert app.final_stall_iteration == 3
    assert app.loop_stall_count == 1
    # On terminal, the stalled IterMetrics is KEPT for visibility
    assert len(app.per_iter) == 1
    assert app.per_iter[0].iter == 3
    assert app.per_iter[0].stall_aborted is True
    # prior_attempts records the stall_exhausted outcome
    assert len(app.prior_attempts) == 1
    assert app.prior_attempts[0].outcome == "stall_exhausted"
    assert app.prior_attempts[0].iters_run == 3
    assert app.prior_attempts[0].stall_iteration == 3
    # loop_attempt NOT incremented (no fallback restart per user directive)
    assert app.loop_attempt == 1
    # _mark_app_done was called: remaining decremented + per-app JSON written
    assert orch.remaining == 0
    assert (app.log_dir / "result.json").exists()
    # And the app did NOT re-queue itself for another gen attempt
    assert "STUB" not in list(orch.ready_for_gen.queue)


def test_handle_stall_counter_does_not_persist_across_iters(
    tmp_path: Path, monkeypatch
) -> None:
    """A stall on iter 3 + successful iter 4: iter 5 stall must get a fresh budget.

    This is tested indirectly: _do_one_gen_iter resets iter_stall_retry_count
    to 0 after a successful (non-stall) gen completion.  We assert that
    invariant by simulating the reset and then a fresh stall.
    """
    orch = _make_orchestrator(tmp_path, opencode_retries=2,
                              monkeypatch=monkeypatch)
    app = orch.apps["STUB"]
    app.app_dir.mkdir(parents=True, exist_ok=True)
    _git_init_snapshot(app.app_dir, "pre-iter")

    # Pretend iter 3 stalled once and was successfully retried.
    # _do_one_gen_iter sets counter back to 0 after non-stall gen.
    app.iter_stall_retry_count = 0
    app.iter = 5
    iter_log = _seed_stalled_iter(app, 5)

    orch._handle_stall(app, 5, iter_log)
    # Fresh stall on iter 5 → counter=1 (not piggybacked on prior iter)
    assert app.iter_stall_retry_count == 1
    assert app.state == AppState.READY_FOR_GEN


def test_max_iter_stall_retries_initialized_from_opencode_retries(
    tmp_path: Path, monkeypatch
) -> None:
    """Per-iter retry budget is wired from --opencode-retries at AppRun init."""
    orch = _make_orchestrator(tmp_path, opencode_retries=5,
                              monkeypatch=monkeypatch)
    app = orch.apps["STUB"]
    assert app.max_iter_stall_retries == 5
    # And the legacy loop-attempts count is still 1 + opencode_retries
    assert app.max_loop_attempts == 6
