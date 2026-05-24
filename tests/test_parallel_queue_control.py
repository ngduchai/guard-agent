"""Tests for the parallel-queue dynamic control plane.

The orchestrator polls ``build/_experiment_state/queue_control.jsonl`` from
its main wait loop and dispatches add/remove/list commands.  These tests
exercise the dispatch helpers directly (no real workers spawned) so we can
assert duplicate-detection, queue-filter, priority-queue, and reset-for-redo
behaviour without touching real MPI or LLM stacks.
"""

from __future__ import annotations

import json
import queue as queue_mod
from pathlib import Path

import pytest

from validation.veloc.scripts import run_parallel_queue as rpq
from validation.veloc.scripts.run_parallel_queue import (
    ACTIVE_APP_STATES,
    AppState,
    Orchestrator,
    TERMINAL_APP_STATES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def fake_vanillas(monkeypatch, tmp_path: Path) -> Path:
    """Stand up a fake vanilla root so Orchestrator.__init__ resolves apps.

    Returns the root.  Each test that needs an app must mkdir
    ``root / <APP_NAME>`` before instantiating Orchestrator.
    """
    root = tmp_path / "fake_vanillas"
    root.mkdir()
    monkeypatch.setattr(rpq, "VANILLA_ROOTS", [root])
    return root


@pytest.fixture
def control_files(monkeypatch, tmp_path: Path) -> tuple[Path, Path, Path]:
    """Redirect EXP_STATE_DIR and the two control files into tmp_path.

    Returns (exp_state_dir, control_file, ack_file).
    """
    exp_state = tmp_path / "exp_state"
    exp_state.mkdir()
    control = exp_state / "queue_control.jsonl"
    ack = exp_state / "queue_control.ack.jsonl"
    monkeypatch.setattr(rpq, "EXP_STATE_DIR", exp_state)
    monkeypatch.setattr(rpq, "CONTROL_FILE", control)
    monkeypatch.setattr(rpq, "CONTROL_ACK_FILE", ack)
    monkeypatch.setattr(rpq, "BUILD_DIR", tmp_path / "build")
    monkeypatch.setattr(rpq, "ITERATIVE_LOGS", tmp_path / "build" / "iterative_logs")
    return exp_state, control, ack


@pytest.fixture
def orch(fake_vanillas: Path, control_files: tuple[Path, Path, Path]) -> Orchestrator:
    """Build an Orchestrator with two fake apps ALPHA and BETA, no workers."""
    (fake_vanillas / "ALPHA").mkdir()
    (fake_vanillas / "BETA").mkdir()
    return Orchestrator(
        app_names=["ALPHA", "BETA"],
        max_gen_workers=2,
        max_iters=10,
        benchmark_num_runs=3,
        label="baseline",
        opencode_retries=2,
        skip_bench=False,
    )


def _last_ack(ack_file: Path) -> dict:
    """Read the most recent ack record."""
    assert ack_file.exists(), "no ack file produced"
    lines = [ln for ln in ack_file.read_text().splitlines() if ln.strip()]
    assert lines, "ack file is empty"
    return json.loads(lines[-1])


# ---------------------------------------------------------------------------
# Snapshot + filter helpers
# ---------------------------------------------------------------------------
def test_snapshot_queue_returns_items_in_order(orch: Orchestrator) -> None:
    orch.ready_for_gen.put("X")
    orch.ready_for_gen.put("Y")
    snap = orch._snapshot_queue(orch.ready_for_gen)
    assert snap == ["X", "Y"]
    # snapshot must not consume the queue
    assert orch.ready_for_gen.qsize() == 2


def test_filter_queue_removes_only_matching_app(orch: Orchestrator) -> None:
    orch.ready_for_gen.put("ALPHA")
    orch.ready_for_gen.put("BETA")
    orch.ready_for_gen.put("ALPHA")
    orch.ready_for_gen.put(None)  # shutdown sentinel must survive
    n = orch._filter_queue(orch.ready_for_gen, "ALPHA")
    assert n == 2
    remaining = orch._snapshot_queue(orch.ready_for_gen)
    assert remaining == ["BETA", None]


def test_filter_queue_handles_tuple_entries(orch: Orchestrator) -> None:
    orch.executor_queue.put(("ALPHA", "validate", 1))
    orch.executor_queue.put(("BETA", "bench", 0))
    orch.executor_queue.put(("ALPHA", "bench", 0))
    n = orch._filter_queue(orch.executor_queue, "ALPHA")
    assert n == 2
    assert orch._snapshot_queue(orch.executor_queue) == [("BETA", "bench", 0)]


def test_app_in_queue_string_and_tuple(orch: Orchestrator) -> None:
    orch.ready_for_gen.put("ALPHA")
    orch.executor_queue.put(("BETA", "validate", 3))
    assert orch._app_in_queue("ALPHA", orch.ready_for_gen)
    assert not orch._app_in_queue("BETA", orch.ready_for_gen)
    assert orch._app_in_queue("BETA", orch.executor_queue)
    assert not orch._app_in_queue("ALPHA", orch.executor_queue)


# ---------------------------------------------------------------------------
# add --queue gen
# ---------------------------------------------------------------------------
def test_add_gen_first_time_enqueues(orch: Orchestrator,
                                     control_files) -> None:
    # ALPHA starts NOT_STARTED — first add should succeed and enqueue.
    orch._ctl_add_gen("c1", "ALPHA", force=False)
    assert orch.apps["ALPHA"].state == AppState.READY_FOR_GEN
    assert orch._app_in_queue("ALPHA", orch.ready_for_gen)
    ack = _last_ack(control_files[2])
    assert ack["status"] == "ok"


def test_add_gen_duplicate_refused_without_force(orch: Orchestrator,
                                                  control_files) -> None:
    orch.apps["ALPHA"].state = AppState.GENERATING
    orch._ctl_add_gen("c2", "ALPHA", force=False)
    ack = _last_ack(control_files[2])
    assert ack["status"] == "duplicate"
    # state must be untouched and queue must not have a new entry
    assert orch.apps["ALPHA"].state == AppState.GENERATING
    assert not orch._app_in_queue("ALPHA", orch.ready_for_gen)


def test_add_gen_force_overrides_active(orch: Orchestrator,
                                         control_files) -> None:
    orch.apps["ALPHA"].state = AppState.GENERATING
    orch._ctl_add_gen("c3", "ALPHA", force=True)
    ack = _last_ack(control_files[2])
    assert ack["status"] == "ok"
    assert orch.apps["ALPHA"].state == AppState.READY_FOR_GEN
    assert orch._app_in_queue("ALPHA", orch.ready_for_gen)


def test_add_gen_unknown_app_errors(orch: Orchestrator,
                                     control_files) -> None:
    orch._ctl_add_gen("c4", "GAMMA", force=False)
    ack = _last_ack(control_files[2])
    assert ack["status"] == "err"
    assert "unknown app" in ack["msg"].lower()


def test_add_gen_terminal_app_resets_and_bumps_remaining(
    orch: Orchestrator, control_files
) -> None:
    # Simulate ALPHA having finished.
    orch.apps["ALPHA"].state = AppState.DONE_PASSED
    orch.remaining = 0
    orch.all_done_event.set()
    orch._ctl_add_gen("c5", "ALPHA", force=False)
    assert orch.apps["ALPHA"].state == AppState.READY_FOR_GEN
    assert orch.apps["ALPHA"].iter == 0
    assert orch.apps["ALPHA"].loop_attempt == 1
    assert orch.remaining == 1
    assert not orch.all_done_event.is_set()


# ---------------------------------------------------------------------------
# add --queue exec
# ---------------------------------------------------------------------------
def test_add_exec_validate_uses_main_queue_by_default(
    orch: Orchestrator, control_files
) -> None:
    orch._ctl_add_exec("c6", "ALPHA", kind="validate", iter_n=3,
                       immediate=False, force=False)
    assert orch.apps["ALPHA"].state == AppState.QUEUED_FOR_EXECUTOR
    assert orch._app_in_queue("ALPHA", orch.executor_queue)
    assert not orch._app_in_queue("ALPHA", orch.executor_priority_queue)
    snap = orch._snapshot_queue(orch.executor_queue)
    assert snap == [("ALPHA", "validate", 3)]


def test_add_exec_immediate_uses_priority_queue(
    orch: Orchestrator, control_files
) -> None:
    orch._ctl_add_exec("c7", "ALPHA", kind="bench", iter_n=None,
                       immediate=True, force=False)
    assert orch._app_in_queue("ALPHA", orch.executor_priority_queue)
    assert not orch._app_in_queue("ALPHA", orch.executor_queue)


def test_add_exec_duplicate_in_queue_refused(
    orch: Orchestrator, control_files
) -> None:
    orch._ctl_add_exec("c8a", "ALPHA", kind="validate", iter_n=1,
                       immediate=False, force=False)
    orch._ctl_add_exec("c8b", "ALPHA", kind="validate", iter_n=2,
                       immediate=False, force=False)
    ack = _last_ack(control_files[2])
    assert ack["status"] == "duplicate"
    # Only the first enqueue should be present
    snap = orch._snapshot_queue(orch.executor_queue)
    assert snap == [("ALPHA", "validate", 1)]


def test_add_exec_running_app_refused_without_force(
    orch: Orchestrator, control_files
) -> None:
    orch.apps["ALPHA"].state = AppState.EXECUTING
    orch._ctl_add_exec("c9", "ALPHA", kind="bench", iter_n=None,
                       immediate=False, force=False)
    ack = _last_ack(control_files[2])
    assert ack["status"] == "duplicate"
    assert not orch._app_in_queue("ALPHA", orch.executor_queue)


def test_add_exec_running_app_force_allows(
    orch: Orchestrator, control_files
) -> None:
    orch.apps["ALPHA"].state = AppState.EXECUTING
    orch._ctl_add_exec("c10", "ALPHA", kind="bench", iter_n=None,
                       immediate=True, force=True)
    ack = _last_ack(control_files[2])
    assert ack["status"] == "ok"
    assert orch._app_in_queue("ALPHA", orch.executor_priority_queue)


def test_add_exec_bad_kind_errors(orch: Orchestrator,
                                   control_files) -> None:
    orch._ctl_add_exec("c11", "ALPHA", kind="nonsense", iter_n=None,
                       immediate=False, force=False)
    ack = _last_ack(control_files[2])
    assert ack["status"] == "err"


def test_add_exec_validate_defaults_iter_when_omitted(
    orch: Orchestrator, control_files
) -> None:
    orch.apps["ALPHA"].iter = 7
    orch._ctl_add_exec("c12", "ALPHA", kind="validate", iter_n=None,
                       immediate=False, force=False)
    snap = orch._snapshot_queue(orch.executor_queue)
    assert snap == [("ALPHA", "validate", 7)]


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------
def test_remove_drains_all_queues_for_app(
    orch: Orchestrator, control_files
) -> None:
    orch.ready_for_gen.put("ALPHA")
    orch.executor_queue.put(("ALPHA", "validate", 1))
    orch.executor_priority_queue.put(("ALPHA", "bench", 0))
    orch.executor_queue.put(("BETA", "validate", 1))
    orch._ctl_remove("c13", "ALPHA", which="all")
    ack = _last_ack(control_files[2])
    assert ack["status"] == "ok"
    assert not orch._app_in_queue("ALPHA", orch.ready_for_gen)
    assert not orch._app_in_queue("ALPHA", orch.executor_queue)
    assert not orch._app_in_queue("ALPHA", orch.executor_priority_queue)
    # BETA must be untouched
    assert orch._app_in_queue("BETA", orch.executor_queue)


def test_remove_gen_only_leaves_executor_alone(
    orch: Orchestrator, control_files
) -> None:
    orch.ready_for_gen.put("ALPHA")
    orch.executor_queue.put(("ALPHA", "validate", 1))
    orch._ctl_remove("c14", "ALPHA", which="gen")
    assert not orch._app_in_queue("ALPHA", orch.ready_for_gen)
    assert orch._app_in_queue("ALPHA", orch.executor_queue)


def test_remove_noop_when_app_absent(
    orch: Orchestrator, control_files
) -> None:
    orch._ctl_remove("c15", "ALPHA", which="all")
    ack = _last_ack(control_files[2])
    assert ack["status"] == "noop"


def test_remove_bad_queue_errors(
    orch: Orchestrator, control_files
) -> None:
    orch._ctl_remove("c16", "ALPHA", which="garbage")
    ack = _last_ack(control_files[2])
    assert ack["status"] == "err"


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------
def test_list_returns_snapshot_json(orch: Orchestrator,
                                     control_files) -> None:
    orch.ready_for_gen.put("ALPHA")
    orch.executor_queue.put(("BETA", "validate", 4))
    orch._ctl_list("c17")
    ack = _last_ack(control_files[2])
    assert ack["status"] == "ok"
    blob = json.loads(ack["msg"])
    assert "ALPHA" in blob["gen_queue"]
    assert blob["executor_queue"] == [["BETA", "validate", 4]]
    assert set(blob["per_app"]) == {"ALPHA", "BETA"}
    assert blob["remaining"] == 2


# ---------------------------------------------------------------------------
# Control file polling (end-to-end through JSONL)
# ---------------------------------------------------------------------------
def test_apply_control_commands_reads_appended_lines(
    orch: Orchestrator, control_files
) -> None:
    _, control, ack = control_files
    # Snap the initial offset (file does not exist yet — offset stays 0).
    orch._control_file_offset = 0
    cmd = {"id": "poll1", "ts": "x", "cmd": "add",
           "app": "ALPHA", "queue": "gen", "force": False}
    control.write_text(json.dumps(cmd) + "\n")
    orch._apply_control_commands()
    assert orch._app_in_queue("ALPHA", orch.ready_for_gen)
    assert orch._control_file_offset == control.stat().st_size
    # A second poll should be a no-op.
    orch._apply_control_commands()
    assert orch.ready_for_gen.qsize() == 1


def test_apply_control_commands_skips_malformed_lines(
    orch: Orchestrator, control_files
) -> None:
    _, control, _ = control_files
    control.write_text("not-json\n" + json.dumps(
        {"id": "p2", "cmd": "add", "app": "ALPHA",
         "queue": "gen", "force": False}) + "\n")
    orch._control_file_offset = 0
    orch._apply_control_commands()
    # Good line still applied
    assert orch._app_in_queue("ALPHA", orch.ready_for_gen)


def test_apply_control_commands_unknown_cmd_writes_err_ack(
    orch: Orchestrator, control_files
) -> None:
    _, control, ack_file = control_files
    control.write_text(json.dumps(
        {"id": "p3", "cmd": "explode", "app": "ALPHA"}) + "\n")
    orch._control_file_offset = 0
    orch._apply_control_commands()
    ack = _last_ack(ack_file)
    assert ack["id"] == "p3"
    assert ack["status"] == "err"


def test_apply_control_commands_no_double_apply_across_polls(
    orch: Orchestrator, control_files
) -> None:
    _, control, _ = control_files
    cmd = {"id": "p4", "cmd": "add", "app": "ALPHA",
           "queue": "gen", "force": False}
    control.write_text(json.dumps(cmd) + "\n")
    orch._control_file_offset = 0
    orch._apply_control_commands()
    # Second poll with no new lines: queue must NOT grow.
    before = orch.ready_for_gen.qsize()
    orch._apply_control_commands()
    assert orch.ready_for_gen.qsize() == before


# ---------------------------------------------------------------------------
# Active/terminal state set sanity (frozensets are immutable contracts)
# ---------------------------------------------------------------------------
def test_active_and_terminal_states_partition_correctly() -> None:
    all_states = set(AppState)
    # ACTIVE_APP_STATES + TERMINAL_APP_STATES + {NOT_STARTED} should partition.
    assert ACTIVE_APP_STATES.isdisjoint(TERMINAL_APP_STATES)
    assert AppState.NOT_STARTED not in ACTIVE_APP_STATES
    assert AppState.NOT_STARTED not in TERMINAL_APP_STATES
    union = ACTIVE_APP_STATES | TERMINAL_APP_STATES | {AppState.NOT_STARTED}
    assert union == all_states
