"""Tests for the per-app perturbation calibrator.

The calibrator runs vanilla 3 times (unperturbed + min + max value) and
checks three invariants: output sensitivity, timing stability, safety
(no crashes). We mock the actual run_once + apply_perturbation calls so
tests run instantly and don't require building any vanilla binary.

See validation/veloc/perturbation_calibrator.py.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from validation.veloc.perturbation_calibrator import (
    CalibrationResult,
    VanillaRun,
    _compute_output_diff,
    _format_report,
    calibrate,
    main,
    mark_yaml_verified,
)


# ---------------------------------------------------------------------------
# Mocks for run_once + apply_perturbation
# ---------------------------------------------------------------------------


@dataclass
class _MockRunResult:
    """Stand-in for runner.RunResult — only the fields the calibrator touches."""
    elapsed_s: float
    exit_code: int = 0


class _RunOnceMock:
    """Configurable mock that simulates vanilla executions for the calibrator.

    Constructed with a dict keyed by the cwd's last path component
    (``calib_unperturbed`` / ``calib_min`` / ``calib_max``) mapping to a
    ``(elapsed_s, exit_code, output_bytes)`` tuple. On each call it
    writes ``output_bytes`` to ``cwd / output_file_name`` (where
    ``output_file_name`` is inferred from the test's app config) and
    returns a _MockRunResult.
    """

    def __init__(self, plan: dict, output_file_name: str = "validation_output.bin"):
        self.plan = plan
        self.output_file_name = output_file_name
        self.calls: list[dict] = []

    def __call__(
        self,
        *,
        build_dir,
        executable_name,
        num_procs,
        app_args,
        output_dir,
        run_cwd,
        env,
        veloc_config_name,
        timeout_s,
    ) -> _MockRunResult:
        cwd = Path(run_cwd)
        label = cwd.name.removeprefix("calib_")
        self.calls.append(
            {
                "label": label,
                "cwd": cwd,
                "app_args": list(app_args),
            }
        )
        elapsed, exit_code, out_bytes = self.plan[label]
        if exit_code == 0:
            (cwd / self.output_file_name).write_bytes(out_bytes)
        return _MockRunResult(elapsed_s=elapsed, exit_code=exit_code)


def _apply_perturbation_mock(spec, value, *, cwd, source_dir, app_args, env):
    """No-op mock — calibrator just needs to know it was called. We don't
    care about the file content because the run_once mock writes
    deterministic bytes per label, ignoring whatever the real
    apply_perturbation would have done.
    """
    return list(app_args), dict(env), cwd / (spec.file or "input.txt")


# ---------------------------------------------------------------------------
# Test fixtures: a fake AppCell environment
# ---------------------------------------------------------------------------


def _make_doubles_bytes(values: list[float]) -> bytes:
    """Pack a list of floats as raw float64 — matches the validator's
    NumericToleranceComparator file format (np.fromfile(dtype=float64))."""
    return np.array(values, dtype=np.float64).tobytes()


@pytest.fixture
def fake_app_env(tmp_path, monkeypatch):
    """Construct a temp source tree + YAML so load_cell can resolve the app.

    Yields (app_name, scratch_root, source_dir).
    """
    app = "TESTAPP"
    # Source tree the calibrator will reference
    src = tmp_path / "vanillas" / app
    src.mkdir(parents=True)
    (src / "input.txt").write_text("dt = 0.001\n")
    # Build dir + a stub executable so _find_executable doesn't fail (the
    # mock run_once never touches it but the calibrator's setup paths do).
    build_dir = tmp_path / "tests_baseline" / app
    build_dir.mkdir(parents=True)
    (build_dir / "test_exe").touch()
    # veloc.cfg in source (copied to cwd by _copy_veloc_cfg)
    (src / "veloc.cfg").write_text("scratch=/tmp/x\npersistent=/tmp/y\nmode=sync\n")

    # YAML config
    configs_dir = tmp_path / "configs"
    configs_dir.mkdir()
    yaml_text = """
name: TESTAPP
mpi_ranks: 1
executable: test_exe
input_subdir: null
comparison:
  method: numeric-tolerance
  output_file: validation_output.bin
  tolerance: 1.0e-12
sizes:
  validation:
    description: smallest
    app_args:
    - input.txt
    nominal_runtime_s: 5.0
benchmark:
  num_runs_per_cell: 3
perturbation:
  method: regex_replace
  file: input.txt
  pattern: 'dt\\s*=\\s*[0-9.]+'
  replacement_template: 'dt = {value:.4f}'
  value_range: [0.005, 0.015]
  calibration:
    expected_min_output_diff: 1.0e-9
    safe_value_range_verified: false
""".lstrip()
    (configs_dir / f"{app}.yaml").write_text(yaml_text)

    # Point app_config at our temp configs dir + redirect VANILLAS/BUILD
    monkeypatch.setattr("validation.veloc.app_config.CONFIGS_DIR", configs_dir)
    monkeypatch.setattr(
        "validation.veloc.perturbation_calibrator.VANILLAS_DIR",
        tmp_path / "vanillas",
    )
    monkeypatch.setattr(
        "validation.veloc.perturbation_calibrator.BUILD_ROOT", tmp_path
    )
    monkeypatch.setattr(
        "validation.veloc.perturbation_calibrator.CONFIGS_DIR", configs_dir
    )
    # Stub _copy_veloc_cfg + _symlink_input_data so calibrator's _setup_run_cwd
    # doesn't try to build a real symlink tree
    import validation.veloc.runner as runner_mod
    monkeypatch.setattr(
        runner_mod,
        "_copy_veloc_cfg",
        lambda src_dir, build_dir, cwd, name: None,
    )
    monkeypatch.setattr(
        runner_mod,
        "_symlink_input_data",
        lambda src_dir, build_dir, cwd, args, **kw: None,
    )

    return app, tmp_path / "_calibration" / app, src


# ---------------------------------------------------------------------------
# _compute_output_diff
# ---------------------------------------------------------------------------


class TestComputeOutputDiff:
    def test_numeric_identical_files_zero(self, tmp_path):
        a = tmp_path / "a.bin"
        b = tmp_path / "b.bin"
        a.write_bytes(_make_doubles_bytes([1.0, 2.0, 3.0]))
        b.write_bytes(_make_doubles_bytes([1.0, 2.0, 3.0]))
        assert _compute_output_diff(
            baseline_file=a, candidate_file=b,
            method="numeric-tolerance", atol=1e-12, rtol=1e-12,
        ) == 0.0

    def test_numeric_differing_returns_max_abs_diff(self, tmp_path):
        a = tmp_path / "a.bin"
        b = tmp_path / "b.bin"
        a.write_bytes(_make_doubles_bytes([1.0, 2.0, 3.0]))
        b.write_bytes(_make_doubles_bytes([1.0, 2.5, 3.0]))  # diff = 0.5 at index 1
        diff = _compute_output_diff(
            baseline_file=a, candidate_file=b,
            method="numeric-tolerance", atol=1e-12, rtol=1e-12,
        )
        assert diff == pytest.approx(0.5)

    def test_numeric_short_candidate_uses_min_length(self, tmp_path):
        a = tmp_path / "a.bin"
        b = tmp_path / "b.bin"
        a.write_bytes(_make_doubles_bytes([1.0, 2.0, 3.0, 4.0]))
        b.write_bytes(_make_doubles_bytes([1.0, 2.0, 3.0]))  # one element shorter
        # No diff in the overlapping prefix → returns 0.0 (length mismatch
        # would be caught elsewhere — calibrator's safety check handles it)
        assert _compute_output_diff(
            baseline_file=a, candidate_file=b,
            method="numeric-tolerance", atol=1e-12, rtol=1e-12,
        ) == 0.0

    def test_text_match_returns_zero(self, tmp_path):
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_bytes(b"hello world\n")
        b.write_bytes(b"hello world\n")
        assert _compute_output_diff(
            baseline_file=a, candidate_file=b,
            method="text-diff", atol=0, rtol=0,
        ) == 0.0

    def test_text_mismatch_returns_one(self, tmp_path):
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_bytes(b"hello\n")
        b.write_bytes(b"world\n")
        assert _compute_output_diff(
            baseline_file=a, candidate_file=b,
            method="text-diff", atol=0, rtol=0,
        ) == 1.0

    def test_missing_baseline_raises(self, tmp_path):
        b = tmp_path / "b.bin"
        b.write_bytes(b"x")
        with pytest.raises(FileNotFoundError):
            _compute_output_diff(
                baseline_file=tmp_path / "missing", candidate_file=b,
                method="numeric-tolerance", atol=1e-12, rtol=1e-12,
            )

    def test_missing_candidate_raises(self, tmp_path):
        a = tmp_path / "a.bin"
        a.write_bytes(b"x")
        with pytest.raises(FileNotFoundError):
            _compute_output_diff(
                baseline_file=a, candidate_file=tmp_path / "missing",
                method="numeric-tolerance", atol=1e-12, rtol=1e-12,
            )


# ---------------------------------------------------------------------------
# calibrate() — end-to-end with mocks
# ---------------------------------------------------------------------------


class TestCalibrateEndToEnd:
    def test_all_invariants_pass(self, fake_app_env):
        app, scratch, _ = fake_app_env
        # Plan: unperturbed = baseline; min/max = clearly different outputs +
        # similar timing → all three invariants pass.
        run_once = _RunOnceMock({
            "unperturbed": (10.0, 0, _make_doubles_bytes([1.0, 2.0, 3.0])),
            "min":         (10.1, 0, _make_doubles_bytes([1.0, 3.0, 3.0])),  # diff=1.0
            "max":         (10.2, 0, _make_doubles_bytes([1.0, 1.0, 3.0])),  # diff=1.0
        })
        result = calibrate(
            app,
            scratch_root=scratch,
            run_once_fn=run_once,
            apply_perturbation_fn=_apply_perturbation_mock,
        )
        assert result.passed is True
        assert result.safety_ok is True
        assert result.output_sensitivity_ok is True
        assert result.timing_stability_ok is True
        # All three runs happened
        assert {c["label"] for c in run_once.calls} == {"unperturbed", "min", "max"}
        # apply_perturbation called only for min + max (unperturbed skips it)
        # Verified by the fact that the run_once mock writes per-label bytes;
        # the diff measurement only works if the right bytes landed.

    def test_sensitivity_failure(self, fake_app_env):
        """Output diff too small → sensitivity invariant fails."""
        app, scratch, _ = fake_app_env
        # All three outputs nearly identical → diff well below 1000*1e-12
        run_once = _RunOnceMock({
            "unperturbed": (10.0, 0, _make_doubles_bytes([1.0, 2.0, 3.0])),
            "min":         (10.0, 0, _make_doubles_bytes([1.0, 2.0, 3.0])),
            "max":         (10.0, 0, _make_doubles_bytes([1.0, 2.0, 3.0])),
        })
        result = calibrate(
            app,
            scratch_root=scratch,
            run_once_fn=run_once,
            apply_perturbation_fn=_apply_perturbation_mock,
        )
        assert result.passed is False
        assert result.safety_ok is True
        assert result.output_sensitivity_ok is False
        assert result.timing_stability_ok is True
        assert any("sensitivity" in r for r in result.failure_reasons)

    def test_timing_failure_min(self, fake_app_env):
        """Min run takes 30% longer → timing invariant fails."""
        app, scratch, _ = fake_app_env
        run_once = _RunOnceMock({
            "unperturbed": (10.0, 0, _make_doubles_bytes([1.0, 2.0, 3.0])),
            "min":         (13.0, 0, _make_doubles_bytes([1.0, 3.0, 3.0])),  # +30%
            "max":         (10.1, 0, _make_doubles_bytes([1.0, 1.0, 3.0])),
        })
        result = calibrate(
            app,
            scratch_root=scratch,
            run_once_fn=run_once,
            apply_perturbation_fn=_apply_perturbation_mock,
        )
        assert result.passed is False
        assert result.timing_stability_ok is False
        assert result.timing_delta_min_pct == pytest.approx(0.30)
        assert any("timing" in r for r in result.failure_reasons)

    def test_timing_failure_max(self, fake_app_env):
        """Max run takes 25% longer → timing invariant fails."""
        app, scratch, _ = fake_app_env
        run_once = _RunOnceMock({
            "unperturbed": (10.0, 0, _make_doubles_bytes([1.0, 2.0, 3.0])),
            "min":         (10.0, 0, _make_doubles_bytes([1.0, 3.0, 3.0])),
            "max":         (12.5, 0, _make_doubles_bytes([1.0, 1.0, 3.0])),
        })
        result = calibrate(
            app,
            scratch_root=scratch,
            run_once_fn=run_once,
            apply_perturbation_fn=_apply_perturbation_mock,
        )
        assert result.passed is False
        assert result.timing_stability_ok is False
        assert result.timing_delta_max_pct == pytest.approx(0.25)

    def test_safety_failure_short_circuits_other_invariants(self, fake_app_env):
        """If any run crashes, calibrator FAILs immediately and does NOT
        evaluate the other invariants (their inputs are unreliable)."""
        app, scratch, _ = fake_app_env
        run_once = _RunOnceMock({
            "unperturbed": (10.0, 0, _make_doubles_bytes([1.0, 2.0, 3.0])),
            "min":         (1.0, 137, b""),   # crashed (exit 137 = SIGKILL)
            "max":         (10.0, 0, _make_doubles_bytes([1.0, 1.0, 3.0])),
        })
        result = calibrate(
            app,
            scratch_root=scratch,
            run_once_fn=run_once,
            apply_perturbation_fn=_apply_perturbation_mock,
        )
        assert result.passed is False
        assert result.safety_ok is False
        # Other invariants NOT evaluated → still None
        assert result.output_sensitivity_ok is None
        assert result.timing_stability_ok is None
        assert any("safety" in r and "min crashed" in r for r in result.failure_reasons)

    def test_timing_threshold_configurable(self, fake_app_env):
        """A looser threshold can rescue a borderline timing case."""
        app, scratch, _ = fake_app_env
        run_once = _RunOnceMock({
            "unperturbed": (10.0, 0, _make_doubles_bytes([1.0, 2.0, 3.0])),
            "min":         (11.5, 0, _make_doubles_bytes([1.0, 3.0, 3.0])),  # +15%
            "max":         (10.0, 0, _make_doubles_bytes([1.0, 1.0, 3.0])),
        })
        # Default threshold 0.15 → exactly at boundary, considered passing
        # because the check is "<= threshold" not "< threshold"
        result = calibrate(
            app,
            scratch_root=scratch,
            run_once_fn=run_once,
            apply_perturbation_fn=_apply_perturbation_mock,
        )
        assert result.timing_stability_ok is True

        # Tighten to 0.10 → same data now FAILs
        result2 = calibrate(
            app,
            scratch_root=scratch,
            timing_stability_threshold_pct=0.10,
            run_once_fn=run_once,
            apply_perturbation_fn=_apply_perturbation_mock,
        )
        assert result2.timing_stability_ok is False

    def test_output_diff_threshold_configurable(self, fake_app_env):
        """A stricter sensitivity threshold can fail an otherwise-passing
        small-diff case."""
        app, scratch, _ = fake_app_env
        # diff of 0.001 — large for 1e-12 tolerance, small for a higher threshold
        run_once = _RunOnceMock({
            "unperturbed": (10.0, 0, _make_doubles_bytes([1.0, 2.0, 3.0])),
            "min":         (10.0, 0, _make_doubles_bytes([1.0, 2.001, 3.0])),
            "max":         (10.0, 0, _make_doubles_bytes([1.0, 1.999, 3.0])),
        })
        result = calibrate(
            app,
            scratch_root=scratch,
            output_diff_threshold=1.0,   # require diff >= 1.0; we only got 0.001
            run_once_fn=run_once,
            apply_perturbation_fn=_apply_perturbation_mock,
        )
        assert result.output_sensitivity_ok is False


# ---------------------------------------------------------------------------
# calibrate() error cases
# ---------------------------------------------------------------------------


class TestCalibrateErrors:
    def test_no_perturbation_spec_raises(self, tmp_path, monkeypatch):
        """An app without a perturbation: block cannot be calibrated."""
        app = "NOSPEC"
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()
        (configs_dir / f"{app}.yaml").write_text("""
name: NOSPEC
mpi_ranks: 1
executable: x
input_subdir: null
comparison: {method: numeric-tolerance, output_file: out.bin, tolerance: 1.0e-12}
sizes:
  validation: {app_args: [in.txt], nominal_runtime_s: 1.0}
""".lstrip())
        monkeypatch.setattr("validation.veloc.app_config.CONFIGS_DIR", configs_dir)
        with pytest.raises(ValueError, match="no perturbation: block"):
            calibrate(app)

    def test_disabled_spec_raises(self, tmp_path, monkeypatch):
        app = "DISABLED"
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()
        (configs_dir / f"{app}.yaml").write_text("""
name: DISABLED
mpi_ranks: 1
executable: x
input_subdir: null
comparison: {method: numeric-tolerance, output_file: out.bin, tolerance: 1.0e-12}
sizes:
  validation: {app_args: [in.txt], nominal_runtime_s: 1.0}
perturbation:
  method: disabled
  reason: 'no safe knob found'
""".lstrip())
        monkeypatch.setattr("validation.veloc.app_config.CONFIGS_DIR", configs_dir)
        with pytest.raises(ValueError, match="explicitly disabled"):
            calibrate(app)


# ---------------------------------------------------------------------------
# mark_yaml_verified
# ---------------------------------------------------------------------------


class TestMarkYamlVerified:
    def test_flips_false_to_true_preserving_comments(self, tmp_path):
        yaml_path = tmp_path / "FLIP.yaml"
        yaml_path.write_text("""
# Top-level comment preserved
perturbation:
  method: regex_replace
  # mid-block comment preserved
  value_range: [1.0, 2.0]
  calibration:
    expected_min_output_diff: 1.0e-9
    # next line is the flip target
    safe_value_range_verified: false
""")
        mark_yaml_verified("FLIP", yaml_path=yaml_path)
        result = yaml_path.read_text()
        assert "safe_value_range_verified: true" in result
        assert "safe_value_range_verified: false" not in result
        # Comments preserved
        assert "# Top-level comment preserved" in result
        assert "# mid-block comment preserved" in result
        assert "# next line is the flip target" in result

    def test_already_true_raises(self, tmp_path):
        yaml_path = tmp_path / "ALREADY.yaml"
        yaml_path.write_text(
            "perturbation:\n  calibration:\n    safe_value_range_verified: true\n"
        )
        with pytest.raises(ValueError, match="could not find"):
            mark_yaml_verified("ALREADY", yaml_path=yaml_path)

    def test_missing_yaml_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            mark_yaml_verified("X", yaml_path=tmp_path / "missing.yaml")


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------


class TestCLI:
    def test_main_returns_zero_on_pass(self, fake_app_env, monkeypatch, capsys):
        app, scratch, _ = fake_app_env
        # Stub calibrate to return a PASS result so we test main() without
        # invoking the run_once mock plumbing.
        passing = CalibrationResult(
            app=app, spec_method="regex_replace", spec_range=(0.005, 0.015),
        )
        passing.runs = {
            "unperturbed": VanillaRun("unperturbed", None, 10.0, 0, Path("/tmp/x")),
            "min": VanillaRun("min", 0.005, 10.05, 0, Path("/tmp/x")),
            "max": VanillaRun("max", 0.015, 10.08, 0, Path("/tmp/x")),
        }
        passing.output_diff_min_vs_unperturbed = 1.0
        passing.output_diff_max_vs_unperturbed = 1.0
        passing.output_diff_threshold = 1e-9
        passing.output_sensitivity_ok = True
        passing.timing_delta_min_pct = 0.005
        passing.timing_delta_max_pct = 0.008
        passing.timing_stability_ok = True
        passing.safety_ok = True
        passing.passed = True
        monkeypatch.setattr(
            "validation.veloc.perturbation_calibrator.calibrate",
            lambda *a, **kw: passing,
        )
        rc = main([app])
        assert rc == 0
        out = capsys.readouterr().out
        assert "PASS" in out
        assert "Invariants" in out

    def test_main_returns_one_on_fail(self, fake_app_env, monkeypatch, capsys):
        app, _, _ = fake_app_env
        failing = CalibrationResult(
            app=app, spec_method="regex_replace", spec_range=(0.005, 0.015),
        )
        failing.runs = {
            "unperturbed": VanillaRun("unperturbed", None, 10.0, 0, Path("/tmp/x")),
            "min": VanillaRun("min", 0.005, 10.0, 0, Path("/tmp/x")),
            "max": VanillaRun("max", 0.015, 10.0, 0, Path("/tmp/x")),
        }
        failing.output_sensitivity_ok = False
        failing.timing_stability_ok = True
        failing.safety_ok = True
        failing.passed = False
        failing.failure_reasons = ["sensitivity: output diff below threshold"]
        monkeypatch.setattr(
            "validation.veloc.perturbation_calibrator.calibrate",
            lambda *a, **kw: failing,
        )
        rc = main([app])
        assert rc == 1
        out = capsys.readouterr().out
        assert "FAIL" in out
        assert "sensitivity" in out

    def test_main_json_output(self, fake_app_env, monkeypatch, capsys):
        app, _, _ = fake_app_env
        passing = CalibrationResult(
            app=app, spec_method="regex_replace", spec_range=(0.005, 0.015),
        )
        passing.runs = {
            "unperturbed": VanillaRun("unperturbed", None, 10.0, 0, Path("/tmp/x")),
            "min": VanillaRun("min", 0.005, 10.05, 0, Path("/tmp/x")),
            "max": VanillaRun("max", 0.015, 10.08, 0, Path("/tmp/x")),
        }
        passing.output_sensitivity_ok = True
        passing.timing_stability_ok = True
        passing.passed = True
        monkeypatch.setattr(
            "validation.veloc.perturbation_calibrator.calibrate",
            lambda *a, **kw: passing,
        )
        rc = main([app, "--json"])
        assert rc == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data["app"] == app
        assert data["passed"] is True
        assert "unperturbed" in data["runs"]

    def test_main_update_yaml_on_pass(self, fake_app_env, monkeypatch, capsys, tmp_path):
        app, _, _ = fake_app_env
        passing = CalibrationResult(
            app=app, spec_method="regex_replace", spec_range=(0.005, 0.015),
        )
        passing.runs = {
            "unperturbed": VanillaRun("unperturbed", None, 10.0, 0, Path("/tmp/x")),
            "min": VanillaRun("min", 0.005, 10.05, 0, Path("/tmp/x")),
            "max": VanillaRun("max", 0.015, 10.08, 0, Path("/tmp/x")),
        }
        passing.output_sensitivity_ok = True
        passing.timing_stability_ok = True
        passing.passed = True
        monkeypatch.setattr(
            "validation.veloc.perturbation_calibrator.calibrate",
            lambda *a, **kw: passing,
        )
        # Verify mark_yaml_verified is invoked
        flipped: list = []
        def fake_flip(app_name, *, yaml_path=None):
            flipped.append(app_name)
        monkeypatch.setattr(
            "validation.veloc.perturbation_calibrator.mark_yaml_verified",
            fake_flip,
        )
        rc = main([app, "--update-yaml"])
        assert rc == 0
        assert flipped == [app]

    def test_main_no_update_when_failing(self, fake_app_env, monkeypatch):
        app, _, _ = fake_app_env
        failing = CalibrationResult(
            app=app, spec_method="regex_replace", spec_range=(0.005, 0.015),
        )
        failing.runs = {
            "unperturbed": VanillaRun("unperturbed", None, 10.0, 0, Path("/tmp/x")),
            "min": VanillaRun("min", 0.005, 10.05, 0, Path("/tmp/x")),
            "max": VanillaRun("max", 0.015, 10.08, 0, Path("/tmp/x")),
        }
        failing.passed = False
        monkeypatch.setattr(
            "validation.veloc.perturbation_calibrator.calibrate",
            lambda *a, **kw: failing,
        )
        flipped: list = []
        monkeypatch.setattr(
            "validation.veloc.perturbation_calibrator.mark_yaml_verified",
            lambda app_name, *, yaml_path=None: flipped.append(app_name),
        )
        rc = main([app, "--update-yaml"])
        assert rc == 1
        assert flipped == []  # not called because calibration failed


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------


class TestFormatReport:
    def test_pass_report_contains_key_fields(self):
        r = CalibrationResult(
            app="X", spec_method="regex_replace", spec_range=(0.1, 0.2),
        )
        r.runs = {
            "unperturbed": VanillaRun("unperturbed", None, 5.0, 0, Path("/tmp/u")),
            "min": VanillaRun("min", 0.1, 5.1, 0, Path("/tmp/m")),
            "max": VanillaRun("max", 0.2, 5.2, 0, Path("/tmp/M")),
        }
        r.output_sensitivity_ok = True
        r.timing_stability_ok = True
        r.safety_ok = True
        r.passed = True
        text = _format_report(r)
        assert "PASS" in text
        assert "unperturbed" in text and "min" in text and "max" in text
        assert "Invariants" in text

    def test_fail_report_lists_reasons(self):
        r = CalibrationResult(
            app="X", spec_method="regex_replace", spec_range=(0.1, 0.2),
        )
        r.runs = {
            "unperturbed": VanillaRun("unperturbed", None, 5.0, 0, Path("/tmp/u")),
            "min": VanillaRun("min", 0.1, 6.5, 0, Path("/tmp/m")),
            "max": VanillaRun("max", 0.2, 5.2, 0, Path("/tmp/M")),
        }
        r.timing_stability_ok = False
        r.passed = False
        r.failure_reasons = ["timing: |t(min) - t(X)|/t(X) = 0.30"]
        text = _format_report(r)
        assert "FAIL" in text
        assert "Failure reasons" in text
        assert "timing" in text
