"""Tests for the F-collective-restart asymmetric-restart gate.

The gate restores the failure-prone leg's VELOC snapshot, deletes
rank-(N-1)'s per-rank checkpoint files, restarts the binary, and compares
the output against the baseline.  This file exercises:

  * the structural skip paths (no veloc.cfg, single rank, empty snapshot,
    aggregated layout with no per-rank files, etc.) — these MUST return
    None so the caller treats the gate as not-applicable rather than as
    a verdict.
  * the happy path (rank-(N-1) files deleted, run_once + do_compare invoked
    with the correct arguments, output-file presence enforced).
  * the deadlock / crash path (no output file → failing CompareResult,
    NOT a skipped None).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from validation.veloc.comparator import CompareResult
from validation.veloc.validate import _run_asymmetric_restart_check


def _write_veloc_cfg(d: Path, scratch: Path, persistent: Path) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    cfg = d / "veloc.cfg"
    cfg.write_text(
        f"scratch = {scratch}\npersistent = {persistent}\n", encoding="utf-8"
    )
    return cfg


def _build_snapshot(snapshot_root: Path, dir_name: str, files: dict[str, bytes]) -> None:
    sub = snapshot_root / dir_name
    sub.mkdir(parents=True, exist_ok=True)
    for name, payload in files.items():
        (sub / name).write_bytes(payload)


def _common_call_args(
    *, snapshot_src: Path, cfg_dir: Path, output_dir: Path, num_procs: int,
    golden: Path, do_compare: Any = None,
) -> dict:
    return dict(
        snapshot_src=snapshot_src,
        veloc_cfg_dirs=[cfg_dir],
        veloc_cfg_name="veloc.cfg",
        build_dir=cfg_dir,
        executable_name="dummy_exe",
        num_procs=num_procs,
        app_args=[],
        output_dir=output_dir,
        env=None,
        timeout_s=30.0,
        output_file_name="validation_output.bin",
        comparison_golden_file=golden,
        do_compare=do_compare or (lambda *_: CompareResult(
            passed=True, method="dummy", score=None, message="",
        )),
    )


# ---------------------------------------------------------------------------
# Skip paths
# ---------------------------------------------------------------------------


def test_skip_when_no_veloc_cfg(tmp_path: Path) -> None:
    """Non-VELOC app: veloc.cfg absent → gate skipped (returns None)."""
    snapshot = tmp_path / "snap"
    snapshot.mkdir()
    out = tmp_path / "out"
    res = _run_asymmetric_restart_check(
        **_common_call_args(
            snapshot_src=snapshot, cfg_dir=tmp_path / "no-cfg",
            output_dir=out, num_procs=4, golden=tmp_path / "g.bin",
        )
    )
    assert res is None


def test_skip_when_single_rank(tmp_path: Path) -> None:
    """num_procs=1 → no per-rank divergence possible → skip."""
    scratch = tmp_path / "scratch"
    persistent = tmp_path / "persistent"
    scratch.mkdir(); persistent.mkdir()
    cfg_dir = tmp_path / "cfg"
    _write_veloc_cfg(cfg_dir, scratch, persistent)
    snapshot = tmp_path / "snap"
    _build_snapshot(snapshot, "persistent", {"app-0-1.dat": b"x"})
    out = tmp_path / "out"
    res = _run_asymmetric_restart_check(
        **_common_call_args(
            snapshot_src=snapshot, cfg_dir=cfg_dir, output_dir=out,
            num_procs=1, golden=tmp_path / "g.bin",
        )
    )
    assert res is None


def test_skip_when_snapshot_missing(tmp_path: Path) -> None:
    scratch = tmp_path / "scratch"
    persistent = tmp_path / "persistent"
    scratch.mkdir(); persistent.mkdir()
    cfg_dir = tmp_path / "cfg"
    _write_veloc_cfg(cfg_dir, scratch, persistent)
    res = _run_asymmetric_restart_check(
        **_common_call_args(
            snapshot_src=tmp_path / "no-snap", cfg_dir=cfg_dir,
            output_dir=tmp_path / "out", num_procs=4,
            golden=tmp_path / "g.bin",
        )
    )
    assert res is None


def test_skip_when_snapshot_empty(tmp_path: Path) -> None:
    scratch = tmp_path / "scratch"
    persistent = tmp_path / "persistent"
    scratch.mkdir(); persistent.mkdir()
    cfg_dir = tmp_path / "cfg"
    _write_veloc_cfg(cfg_dir, scratch, persistent)
    snapshot = tmp_path / "snap"
    snapshot.mkdir()  # exists but no subdirs
    res = _run_asymmetric_restart_check(
        **_common_call_args(
            snapshot_src=snapshot, cfg_dir=cfg_dir,
            output_dir=tmp_path / "out", num_procs=4,
            golden=tmp_path / "g.bin",
        )
    )
    assert res is None


def test_skip_when_aggregated_layout(tmp_path: Path) -> None:
    """Snapshot has files but none match <prefix>-<rank>-<ver>.dat
    (posix_agg_module aggregated layout) → gate inapplicable."""
    scratch = tmp_path / "scratch"
    persistent = tmp_path / "persistent"
    scratch.mkdir(); persistent.mkdir()
    cfg_dir = tmp_path / "cfg"
    _write_veloc_cfg(cfg_dir, scratch, persistent)
    snapshot = tmp_path / "snap"
    _build_snapshot(snapshot, "persistent", {
        "aggregated.dat": b"x",
        "checkpoint_v3.bin": b"y",
    })
    res = _run_asymmetric_restart_check(
        **_common_call_args(
            snapshot_src=snapshot, cfg_dir=cfg_dir,
            output_dir=tmp_path / "out", num_procs=4,
            golden=tmp_path / "g.bin",
        )
    )
    assert res is None


def test_skip_when_victim_rank_has_no_files(tmp_path: Path) -> None:
    """num_procs=4 → victim is rank 3.  Snapshot contains rank-0/1/2 only
    (e.g. rank 3 never wrote a checkpoint due to short run); gate cannot
    exercise the divergence path → skip."""
    scratch = tmp_path / "scratch"
    persistent = tmp_path / "persistent"
    scratch.mkdir(); persistent.mkdir()
    cfg_dir = tmp_path / "cfg"
    _write_veloc_cfg(cfg_dir, scratch, persistent)
    snapshot = tmp_path / "snap"
    _build_snapshot(snapshot, "persistent", {
        "app-0-1.dat": b"x",
        "app-1-1.dat": b"x",
        "app-2-1.dat": b"x",
    })
    res = _run_asymmetric_restart_check(
        **_common_call_args(
            snapshot_src=snapshot, cfg_dir=cfg_dir,
            output_dir=tmp_path / "out", num_procs=4,
            golden=tmp_path / "g.bin",
        )
    )
    assert res is None


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_happy_path_restores_corrupts_runs_and_compares(
    tmp_path: Path, monkeypatch
) -> None:
    """Full gate execution.  Verifies:
      * snapshot restored into live persistent dir,
      * rank-3 (num_procs=4) files deleted, other ranks intact,
      * run_once invoked with skip_pre_run_clear=True,
      * output file present → do_compare called with the right label,
      * forensic JSON written.
    """
    scratch = tmp_path / "scratch"
    persistent = tmp_path / "persistent"
    scratch.mkdir(); persistent.mkdir()
    cfg_dir = tmp_path / "cfg"
    _write_veloc_cfg(cfg_dir, scratch, persistent)

    snapshot = tmp_path / "snap"
    _build_snapshot(snapshot, "persistent", {
        "app-0-1.dat": b"r0",
        "app-1-1.dat": b"r1",
        "app-2-1.dat": b"r2",
        "app-3-1.dat": b"r3",
    })

    out = tmp_path / "out"

    captured_run: dict[str, Any] = {}

    def fake_run_once(**kwargs: Any) -> Any:
        captured_run.update(kwargs)
        # Simulate that the resilient binary cold-restarted unanimously
        # and produced an output file under output_dir.
        out_dir: Path = kwargs["output_dir"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "validation_output.bin").write_bytes(b"GOLDEN")
        return SimpleNamespace(exit_code=0, elapsed_s=1.23, injected=False)

    monkeypatch.setattr(
        "validation.veloc.validate.run_once", fake_run_once
    )

    captured_compare: dict[str, Any] = {}

    def fake_compare(label: str, golden: Path, test: Path) -> CompareResult:
        captured_compare["label"] = label
        captured_compare["golden"] = golden
        captured_compare["test"] = test
        return CompareResult(
            passed=True, method=f"numeric [{label}]", score=0.0, message="ok",
        )

    golden_file = tmp_path / "golden.bin"
    golden_file.write_bytes(b"GOLDEN")

    res = _run_asymmetric_restart_check(
        **_common_call_args(
            snapshot_src=snapshot, cfg_dir=cfg_dir, output_dir=out,
            num_procs=4, golden=golden_file, do_compare=fake_compare,
        )
    )

    # Verdict came from do_compare.
    assert res is not None
    assert res.passed is True

    # run_once was invoked with the bypass flag.
    assert captured_run["skip_pre_run_clear"] is True
    assert captured_run["num_procs"] == 4

    # do_compare was invoked with the asymmetric label and the asym
    # output path under our output_dir.
    assert captured_compare["label"] == "VeloC, collective-restart"
    assert captured_compare["golden"] == golden_file
    assert captured_compare["test"] == out / "validation_output.bin"

    # Live persistent dir holds rank-0/1/2 files; rank-3 was deleted.
    live_names = sorted(p.name for p in persistent.iterdir())
    assert live_names == ["app-0-1.dat", "app-1-1.dat", "app-2-1.dat"]

    # Forensic JSON exists and references victim rank.
    forensic = out / "asymmetric_corruption.json"
    assert forensic.exists()
    text = forensic.read_text()
    assert '"victim_rank": 3' in text
    assert "app-3-1.dat" in text


def test_missing_output_returns_failing_result(
    tmp_path: Path, monkeypatch
) -> None:
    """Buggy implementation hangs or crashes → no output file → gate
    returns a FAILING CompareResult (not None), so the caller records
    it as a real verdict."""
    scratch = tmp_path / "scratch"
    persistent = tmp_path / "persistent"
    scratch.mkdir(); persistent.mkdir()
    cfg_dir = tmp_path / "cfg"
    _write_veloc_cfg(cfg_dir, scratch, persistent)

    snapshot = tmp_path / "snap"
    _build_snapshot(snapshot, "persistent", {
        "app-0-1.dat": b"r0",
        "app-1-1.dat": b"r1",
        "app-2-1.dat": b"r2",
        "app-3-1.dat": b"r3",
    })

    def fake_run_once(**kwargs: Any) -> Any:
        # Don't write any output → simulates deadlock/crash on partial state.
        return SimpleNamespace(exit_code=-9, elapsed_s=30.0, injected=False)

    monkeypatch.setattr(
        "validation.veloc.validate.run_once", fake_run_once
    )

    def fail_if_called(*_a: Any, **_k: Any) -> CompareResult:
        raise AssertionError("do_compare must not be called when output is missing")

    res = _run_asymmetric_restart_check(
        **_common_call_args(
            snapshot_src=snapshot, cfg_dir=cfg_dir,
            output_dir=tmp_path / "out", num_procs=4,
            golden=tmp_path / "g.bin", do_compare=fail_if_called,
        )
    )
    assert res is not None
    assert res.passed is False
    assert "no output" in res.message
    assert "exit_code=-9" in res.message
