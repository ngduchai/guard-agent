"""Tests for the parallel-queue validate-stage watchdog.

The watchdog was added 2026-05-24 after a WarpX iter hung for ~4h on an
LLM-introduced rank-0-early-return-before-collective-Barrier deadlock.
``subprocess.run(..., timeout=...)`` only SIGKILLs the direct child; when
the direct child is mpirun, the rank grandchildren survive as orphans and
the host-wide mpirun lane stays wedged.

The fix in ``_run_subprocess`` is to:
    1. spawn the child with ``start_new_session=True`` so it heads its own
       process group, and
    2. on TimeoutExpired, SIGKILL the entire group via
       ``os.killpg(os.getpgid(proc.pid), SIGKILL)``.

These tests pin both behaviours.
"""

from __future__ import annotations

import os
import signal
import time
from pathlib import Path

import pytest

from validation.veloc.scripts.run_parallel_queue import _build_prompt, _run_subprocess


def _pid_alive(pid: int) -> bool:
    """Return True iff *pid* is still alive (signal 0 = existence probe)."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def test_run_subprocess_timeout_returns_124(tmp_path: Path) -> None:
    """A child that outlives the cap returns rc=124 (conventional timeout code)."""
    stdout_log = tmp_path / "out.txt"
    stderr_log = tmp_path / "err.txt"
    rc, wall = _run_subprocess(
        ["sleep", "30"],
        stdout_log=stdout_log,
        stderr_log=stderr_log,
        timeout=1.0,
    )
    assert rc == 124, f"expected 124 on timeout, got {rc}"
    # Watchdog should fire promptly — generous upper bound for slow CI hosts.
    assert wall < 10.0, f"watchdog took too long: {wall:.1f}s"


def test_run_subprocess_normal_exit_returns_zero(tmp_path: Path) -> None:
    """No-timeout sanity: a fast child returns its real exit code."""
    rc, wall = _run_subprocess(
        ["true"],
        stdout_log=tmp_path / "out.txt",
        stderr_log=tmp_path / "err.txt",
        timeout=10.0,
    )
    assert rc == 0
    assert wall < 5.0


def test_run_subprocess_propagates_nonzero_exit(tmp_path: Path) -> None:
    """Watchdog must not mask a real non-zero exit as a timeout."""
    rc, _ = _run_subprocess(
        ["false"],
        stdout_log=tmp_path / "out.txt",
        stderr_log=tmp_path / "err.txt",
        timeout=10.0,
    )
    assert rc != 0 and rc != 124


def test_run_subprocess_timeout_kills_process_group(tmp_path: Path) -> None:
    """The whole process group dies on timeout — not just the direct child.

    This is the WarpX regression: mpirun would exit but the rank
    grandchildren survived and held the host-wide lane.  We simulate
    that by spawning a shell that backgrounds a long-lived grandchild
    and writes the grandchild PID to a file.  When the watchdog fires,
    the grandchild must also be dead.
    """
    pid_file = tmp_path / "grandchild.pid"
    # The shell parent sleeps forever so the watchdog has to kill it.
    # `setsid` would create a NEW session inside the shell, which would
    # ESCAPE our killpg — so we explicitly do NOT use it.  The grandchild
    # inherits the session-leader pgid (because we spawned with
    # start_new_session=True), and killpg() reaches it.
    script = (
        "sleep 30 &\n"
        f"echo $! > {pid_file}\n"
        "wait\n"
    )
    rc, wall = _run_subprocess(
        ["bash", "-c", script],
        stdout_log=tmp_path / "out.txt",
        stderr_log=tmp_path / "err.txt",
        timeout=2.0,
    )
    assert rc == 124

    # Give the OS a moment to reap the killed grandchild.
    deadline = time.monotonic() + 5.0
    grandchild_pid = int(pid_file.read_text().strip())
    while _pid_alive(grandchild_pid) and time.monotonic() < deadline:
        time.sleep(0.1)
    assert not _pid_alive(grandchild_pid), (
        f"grandchild PID {grandchild_pid} survived the watchdog — "
        f"killpg() did not reach it.  Did start_new_session=True get dropped?"
    )

    # Cleanup safety: if the assertion above ever loosens, do not leak.
    if _pid_alive(grandchild_pid):
        with pytest.raises(ProcessLookupError):
            os.kill(grandchild_pid, signal.SIGKILL)


# --- _build_prompt timeout-marker surfacing ----------------------------------


class _StubApp:
    """Minimal AppRun stand-in for _build_prompt — only the attrs it touches."""

    def __init__(self, app_dir: Path, log_dir: Path, name: str = "STUB",
                 label: str = "baseline") -> None:
        self.app_dir = app_dir
        self.log_dir = log_dir
        self.name = name
        self.label = label


def test_build_prompt_iter1_does_not_read_timeout_marker(tmp_path: Path) -> None:
    """iter 1 uses the canonical prompt.txt path; no prev-iter marker exists."""
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "prompt.txt").write_text("INITIAL PROMPT")
    app = _StubApp(app_dir=tmp_path / "app", log_dir=tmp_path / "logs")
    out = _build_prompt(app, iter_n=1)  # type: ignore[arg-type]
    assert "INITIAL PROMPT" in out


def test_build_prompt_iter2plus_surfaces_timeout_marker(tmp_path: Path) -> None:
    """When _TIMEOUT_KILLED.txt exists in prev iter dir, its body is appended."""
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "prompt.txt").write_text("INITIAL")
    log_dir = tmp_path / "logs"
    prev_iter = log_dir / "iter_1"
    prev_iter.mkdir(parents=True)
    marker_body = "VALIDATE STAGE TIMED OUT AND WAS KILLED\nApp: STUB\n"
    (prev_iter / "_TIMEOUT_KILLED.txt").write_text(marker_body)

    app = _StubApp(app_dir=tmp_path / "app", log_dir=log_dir)
    out = _build_prompt(app, iter_n=2)  # type: ignore[arg-type]
    assert "VALIDATE STAGE TIMED OUT AND WAS KILLED" in out
    assert "App: STUB" in out


def test_build_prompt_iter2plus_without_marker_omits_timeout_block(
    tmp_path: Path,
) -> None:
    """No marker → no timeout text leaks into the prompt (false signal hazard)."""
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "prompt.txt").write_text("INITIAL")
    log_dir = tmp_path / "logs"
    (log_dir / "iter_1").mkdir(parents=True)

    app = _StubApp(app_dir=tmp_path / "app", log_dir=log_dir)
    out = _build_prompt(app, iter_n=2)  # type: ignore[arg-type]
    assert "TIMED OUT" not in out
    assert "_TIMEOUT_KILLED" not in out
