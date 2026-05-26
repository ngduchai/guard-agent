"""Tests for the checkpoint-size watchdog added to runner.run_once.

The watchdog terminates mpirun when the LLM's VeloC integration writes a
runaway checkpoint footprint (Nyx 2026-05-26 incident: 55 GB in /tmp across
~200 retained versions, cascading OSError 28 into unrelated iters).

These tests use small thresholds and short timeouts so the suite stays
fast.  The watchdog is exercised against a real ``sleep`` subprocess to
keep the integration honest (the process's termination is the real signal).
"""

from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path

import pytest

from validation.veloc.runner import (
    _DEFAULT_MAX_CHECKPOINT_BYTES,
    _DISK_GUARD_MARKER_NAME,
    _append_attempt_disk_guard_marker_to_stderr,
    _format_overage_message,
    _resolve_disk_guard_config,
    _start_checkpoint_size_watchdog,
)


def _terminated_by_guard(proc: subprocess.Popen) -> bool:
    # proc.terminate() sends SIGTERM (negative returncode on POSIX) or
    # produces a non-zero code on platforms that synthesise one.  Anything
    # other than a clean 0 exit means we successfully killed it.
    return proc.returncode != 0


def test_watchdog_terminates_on_overage(tmp_path: Path) -> None:
    ckpt_dir = tmp_path / "ckpt"
    ckpt_dir.mkdir()
    # 2 MB file vs 1 MB limit — must trigger within one poll cycle.
    (ckpt_dir / "big.bin").write_bytes(b"x" * (2 * 1024 * 1024))
    marker = tmp_path / "marker.txt"

    proc = subprocess.Popen(["sleep", "30"])
    stop = threading.Event()
    try:
        t = _start_checkpoint_size_watchdog(
            proc=proc,
            ckpt_dirs=[ckpt_dir],
            max_bytes=1024 * 1024,
            poll_interval_s=1.0,  # clamped to 1.0 minimum elsewhere; here 1s
            stop_event=stop,
            marker_path=marker,
        )
        proc.wait(timeout=10.0)
    finally:
        stop.set()
        try:
            proc.kill()
        except OSError:
            pass

    t.join(timeout=2.0)
    assert _terminated_by_guard(proc), (
        f"watchdog should have terminated proc; returncode={proc.returncode}"
    )
    assert marker.exists(), "watchdog must write the overage marker file"
    text = marker.read_text()
    assert "CHECKPOINT_SIZE_EXCEEDED" in text
    assert str(ckpt_dir) in text
    assert "VELOC_Mem_protect" in text  # fix-hint must be in the LLM-facing msg


def test_watchdog_clean_exit_when_proc_finishes_first(tmp_path: Path) -> None:
    ckpt_dir = tmp_path / "ckpt"
    ckpt_dir.mkdir()
    (ckpt_dir / "small.bin").write_bytes(b"x" * 1024)  # 1 KB — well under cap
    marker = tmp_path / "marker.txt"

    proc = subprocess.Popen(["true"])
    stop = threading.Event()
    t = _start_checkpoint_size_watchdog(
        proc=proc,
        ckpt_dirs=[ckpt_dir],
        max_bytes=10 * 1024 * 1024 * 1024,  # 10 GB — never triggers
        poll_interval_s=1.0,
        stop_event=stop,
        marker_path=marker,
    )
    proc.wait(timeout=5.0)
    stop.set()
    t.join(timeout=2.0)

    assert proc.returncode == 0, (
        f"`true` should exit cleanly; got {proc.returncode}"
    )
    assert not marker.exists(), "no overage => no marker file"


def test_watchdog_tolerates_missing_dirs(tmp_path: Path) -> None:
    # Mix of existing and missing dirs — measure_checkpoint_dirs returns
    # zero for missing ones; watchdog should not raise and should not fire.
    existing = tmp_path / "exists"
    existing.mkdir()
    (existing / "f.bin").write_bytes(b"x" * 100)
    missing = tmp_path / "ghost"  # never created
    marker = tmp_path / "marker.txt"

    proc = subprocess.Popen(["sleep", "1"])
    stop = threading.Event()
    t = _start_checkpoint_size_watchdog(
        proc=proc,
        ckpt_dirs=[existing, missing],
        max_bytes=10 * 1024 * 1024,
        poll_interval_s=1.0,
        stop_event=stop,
        marker_path=marker,
    )
    proc.wait(timeout=5.0)
    stop.set()
    t.join(timeout=2.0)

    assert proc.returncode == 0
    assert not marker.exists()


def test_format_overage_message_includes_all_dirs() -> None:
    summary = {
        "total_size_bytes": 12 * 10**9,
        "total_file_count": 200,
        "per_dir": [
            {
                "path": "/tmp/nyx_scratch",
                "size_bytes": 7 * 10**9,
                "file_count": 100,
                "exists": True,
            },
            {
                "path": "/tmp/nyx_persistent",
                "size_bytes": 5 * 10**9,
                "file_count": 100,
                "exists": True,
            },
        ],
    }
    msg = _format_overage_message(summary, 10 * 10**9)
    assert "CHECKPOINT_SIZE_EXCEEDED" in msg
    assert "12.00 GB" in msg
    assert "10.00 GB" in msg
    assert "/tmp/nyx_scratch" in msg
    assert "/tmp/nyx_persistent" in msg
    # All three remediation hints must be present so the LLM has a chance
    # of picking one applicable to its design.
    assert "VELOC_Mem_protect" in msg
    assert "max_ckpts" in msg
    assert "Checkpoint cadence" in msg


def test_format_overage_skips_missing_dirs() -> None:
    summary = {
        "total_size_bytes": 7 * 10**9,
        "total_file_count": 100,
        "per_dir": [
            {
                "path": "/tmp/real",
                "size_bytes": 7 * 10**9,
                "file_count": 100,
                "exists": True,
            },
            {
                "path": "/tmp/ghost",
                "size_bytes": 0,
                "file_count": 0,
                "exists": False,
            },
        ],
    }
    msg = _format_overage_message(summary, 10**9)
    assert "/tmp/real" in msg
    assert "/tmp/ghost" not in msg


def test_resolve_disk_guard_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GUARD_AGENT_MAX_CHECKPOINT_BYTES", raising=False)
    monkeypatch.delenv("GUARD_AGENT_DISK_GUARD_POLL_S", raising=False)
    max_bytes, poll_s = _resolve_disk_guard_config()
    assert max_bytes == _DEFAULT_MAX_CHECKPOINT_BYTES
    assert poll_s == 5.0


def test_resolve_disk_guard_config_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUARD_AGENT_MAX_CHECKPOINT_BYTES", "0")
    max_bytes, _ = _resolve_disk_guard_config()
    assert max_bytes is None


def test_resolve_disk_guard_config_invalid_disables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUARD_AGENT_MAX_CHECKPOINT_BYTES", "not-a-number")
    max_bytes, _ = _resolve_disk_guard_config()
    assert max_bytes is None


def test_resolve_disk_guard_config_clamps_short_poll(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUARD_AGENT_DISK_GUARD_POLL_S", "0.1")
    _, poll_s = _resolve_disk_guard_config()
    assert poll_s >= 1.0


def test_resolve_disk_guard_config_custom_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUARD_AGENT_MAX_CHECKPOINT_BYTES", str(2 * 1024**3))
    monkeypatch.setenv("GUARD_AGENT_DISK_GUARD_POLL_S", "15")
    max_bytes, poll_s = _resolve_disk_guard_config()
    assert max_bytes == 2 * 1024**3
    assert poll_s == 15.0


# ---------------------------------------------------------------------------
# Per-attempt marker forwarding for the checkpoint-observed (resilient) path
# ---------------------------------------------------------------------------
# Added after the Nyx 2026-05-26 incident: _launch_attempt now arms the
# watchdog per attempt; the helper below folds the marker into stderr so the
# LLM sees a CHECKPOINT_SIZE_EXCEEDED message on the next iter instead of an
# opaque SIGTERM.


def test_append_marker_noop_when_marker_missing(tmp_path: Path) -> None:
    attempt = tmp_path / "attempt_1"
    attempt.mkdir()
    stderr_path = attempt / "stderr.txt"
    stderr_path.write_text("original stderr\n")
    result = _append_attempt_disk_guard_marker_to_stderr(
        attempt, stderr_path, "original stderr\n"
    )
    assert result == "original stderr\n"
    # On-disk stderr unchanged.
    assert stderr_path.read_text() == "original stderr\n"


def test_append_marker_folds_into_stderr_when_present(tmp_path: Path) -> None:
    attempt = tmp_path / "attempt_1"
    attempt.mkdir()
    stderr_path = attempt / "stderr.txt"
    stderr_path.write_text("mpirun output\n")
    marker = attempt / _DISK_GUARD_MARKER_NAME
    marker.write_text("[validator-guard] CHECKPOINT_SIZE_EXCEEDED\n  total: 12 GB\n")
    result = _append_attempt_disk_guard_marker_to_stderr(
        attempt, stderr_path, "mpirun output\n"
    )
    assert "CHECKPOINT_SIZE_EXCEEDED" in result
    assert "mpirun output" in result
    # And the file on disk was also updated for forensic readers.
    assert "CHECKPOINT_SIZE_EXCEEDED" in stderr_path.read_text()


def test_append_marker_handles_empty_starting_stderr(tmp_path: Path) -> None:
    attempt = tmp_path / "attempt_2"
    attempt.mkdir()
    stderr_path = attempt / "stderr.txt"
    stderr_path.write_text("")
    marker = attempt / _DISK_GUARD_MARKER_NAME
    marker.write_text("[validator-guard] CHECKPOINT_SIZE_EXCEEDED\n")
    result = _append_attempt_disk_guard_marker_to_stderr(
        attempt, stderr_path, ""
    )
    assert "CHECKPOINT_SIZE_EXCEEDED" in result
