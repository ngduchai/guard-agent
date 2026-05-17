"""Tests for the input-perturbation + slope-test infrastructure.

Covers:
- :class:`PerturbationSpec` parsing and validation (app_config.py)
- :func:`resolve_perturbation_value` determinism
- :func:`apply_perturbation` for all three methods + symlink edge case
- :func:`compute_recovery_slope` and :func:`kill_fractions_for_bench` (validate.py)
- End-to-end gate behavior in :func:`_enforce_validation_b`:
  honest recovery (slope -1) PASSes, cold-replay (slope 0) FAILs

See plan: /home/ndhai/.claude/plans/tranquil-napping-meerkat.md
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from validation.veloc.app_config import (
    PERTURBATION_METHODS,
    PerturbationSpec,
    _parse_perturbation,
    apply_perturbation,
    resolve_perturbation_value,
)
from validation.veloc.validate import (
    _DEFAULT_KILL_FRACTIONS,
    _RECOVERY_RESUMED_SLOPE_THRESHOLD,
    ValidationError,
    _compute_perturbed_baseline,
    _enforce_validation_b,
    compute_recovery_slope,
    kill_fractions_for_bench,
)


# ---------------------------------------------------------------------------
# PerturbationSpec parsing
# ---------------------------------------------------------------------------


class TestParsePerturbation:
    def test_none_returns_none(self):
        assert _parse_perturbation(None) is None

    def test_disabled_returns_disabled_spec(self):
        spec = _parse_perturbation({"method": "disabled", "reason": "no safe knob"})
        assert spec.method == "disabled"
        assert spec.reason == "no safe knob"

    def test_regex_replace_complete(self):
        spec = _parse_perturbation({
            "method": "regex_replace",
            "file": "input.txt",
            "pattern": r"dt\s*=\s*[0-9.]+",
            "replacement_template": "dt = {value}",
            "value_range": [0.01, 0.02],
        })
        assert spec.method == "regex_replace"
        assert spec.file == "input.txt"
        assert spec.value_range == (0.01, 0.02)

    def test_regex_replace_accepts_format_spec(self):
        spec = _parse_perturbation({
            "method": "regex_replace",
            "file": "x.txt",
            "pattern": "y",
            "replacement_template": "k = {value:.4f}",
            "value_range": [0, 1],
        })
        assert spec is not None

    def test_app_arg_override_complete(self):
        spec = _parse_perturbation({
            "method": "app_arg_override",
            "arg_index": 2,
            "value_range": [10, 100],
        })
        assert spec.method == "app_arg_override"
        assert spec.arg_index == 2

    def test_env_var_set_complete(self):
        spec = _parse_perturbation({
            "method": "env_var_set",
            "env_var": "OMP_NUM_THREADS",
            "value_range": [1, 4],
        })
        assert spec.method == "env_var_set"
        assert spec.env_var == "OMP_NUM_THREADS"

    @pytest.mark.parametrize("bad_input", [
        {"method": "unknown_method", "value_range": [0, 1]},
        {"method": "regex_replace", "value_range": [0, 1]},  # missing file/pattern/template
        {"method": "regex_replace", "file": "x", "pattern": "y",
         "replacement_template": "no placeholder", "value_range": [0, 1]},
        {"method": "app_arg_override", "value_range": [0, 1]},  # missing arg_index
        {"method": "env_var_set", "value_range": [0, 1]},  # missing env_var
        {"method": "regex_replace", "file": "x", "pattern": "y",
         "replacement_template": "{value}", "value_range": [1, 0]},  # inverted range
        {"method": "regex_replace", "file": "x", "pattern": "y",
         "replacement_template": "{value}", "value_range": [0]},  # 1-element range
        "not_a_dict",
    ])
    def test_malformed_raises(self, bad_input):
        with pytest.raises((ValueError, TypeError)):
            _parse_perturbation(bad_input)


# ---------------------------------------------------------------------------
# resolve_perturbation_value
# ---------------------------------------------------------------------------


class TestResolvePerturbationValue:
    def test_float_range_deterministic(self):
        spec = _parse_perturbation({
            "method": "regex_replace", "file": "x", "pattern": "y",
            "replacement_template": "{value}",
            "value_range": [0.01, 0.02],
        })
        v1 = resolve_perturbation_value(spec, seed=42)
        v2 = resolve_perturbation_value(spec, seed=42)
        v3 = resolve_perturbation_value(spec, seed=43)
        assert v1 == v2
        assert v1 != v3
        assert 0.01 <= v1 <= 0.02

    def test_int_range_returns_int(self):
        spec = _parse_perturbation({
            "method": "app_arg_override", "arg_index": 0,
            "value_range": [10, 100],
        })
        v = resolve_perturbation_value(spec, seed=42)
        assert isinstance(v, int)
        assert 10 <= v <= 100

    def test_disabled_raises(self):
        spec = _parse_perturbation({"method": "disabled", "reason": "x"})
        with pytest.raises(ValueError):
            resolve_perturbation_value(spec, seed=42)


# ---------------------------------------------------------------------------
# apply_perturbation
# ---------------------------------------------------------------------------


class TestApplyPerturbation:
    def test_regex_replace_modifies_cwd_not_source(self, tmp_path):
        src = tmp_path / "src"
        cwd = tmp_path / "cwd"
        src.mkdir()
        cwd.mkdir()
        original = "header\ndt = 0.001\nfooter\n"
        (src / "input.txt").write_text(original)
        spec = _parse_perturbation({
            "method": "regex_replace", "file": "input.txt",
            "pattern": r"dt\s*=\s*[0-9.]+",
            "replacement_template": "dt = {value:.4f}",
            "value_range": [0.005, 0.015],
        })
        new_args, new_env, modf = apply_perturbation(
            spec, 0.012, cwd=cwd, source_dir=src, app_args=[], env={},
        )
        assert "dt = 0.0120" in (cwd / "input.txt").read_text()
        assert (src / "input.txt").read_text() == original, "source must not be modified"
        assert modf == cwd / "input.txt"

    def test_regex_replace_via_symlink_replaces_symlink(self, tmp_path):
        # Simulates the runner scenario: input file is a symlink in cwd
        # pointing back to source.  apply_perturbation must replace the
        # symlink with a modified copy, NOT modify the symlink target.
        src = tmp_path / "src"
        cwd = tmp_path / "cwd"
        src.mkdir()
        cwd.mkdir()
        (src / "input.txt").write_text("dt = 0.001\n")
        (cwd / "input.txt").symlink_to(src / "input.txt")

        spec = _parse_perturbation({
            "method": "regex_replace", "file": "input.txt",
            "pattern": r"dt\s*=\s*[0-9.]+",
            "replacement_template": "dt = {value}",
            "value_range": [0.005, 0.015],
        })
        apply_perturbation(spec, 0.009, cwd=cwd, source_dir=src, app_args=[], env={})
        assert (cwd / "input.txt").read_text() == "dt = 0.009\n"
        assert (src / "input.txt").read_text() == "dt = 0.001\n", "source preserved"
        assert not (cwd / "input.txt").is_symlink(), "symlink replaced with real file"

    def test_regex_replace_no_match_raises(self, tmp_path):
        src = tmp_path / "src"
        cwd = tmp_path / "cwd"
        src.mkdir()
        cwd.mkdir()
        (src / "input.txt").write_text("no dt here\n")
        spec = _parse_perturbation({
            "method": "regex_replace", "file": "input.txt",
            "pattern": r"dt\s*=\s*[0-9.]+",
            "replacement_template": "dt = {value}",
            "value_range": [0, 1],
        })
        with pytest.raises(ValueError, match="did not match"):
            apply_perturbation(spec, 0.5, cwd=cwd, source_dir=src, app_args=[], env={})

    def test_app_arg_override_replaces_index(self, tmp_path):
        spec = _parse_perturbation({
            "method": "app_arg_override", "arg_index": 1,
            "value_range": [10, 100],
        })
        new_args, new_env, modf = apply_perturbation(
            spec, 55, cwd=tmp_path, source_dir=tmp_path,
            app_args=["-x", "10", "-y", "20"], env={"A": "b"},
        )
        assert new_args == ["-x", "55", "-y", "20"]
        assert new_env == {"A": "b"}, "env unchanged for app_arg_override"
        assert modf is None

    def test_app_arg_override_out_of_range_raises(self, tmp_path):
        spec = _parse_perturbation({
            "method": "app_arg_override", "arg_index": 5,
            "value_range": [10, 100],
        })
        with pytest.raises(IndexError):
            apply_perturbation(
                spec, 55, cwd=tmp_path, source_dir=tmp_path,
                app_args=["-x", "10"], env={},
            )

    def test_env_var_set_adds_var(self, tmp_path):
        spec = _parse_perturbation({
            "method": "env_var_set", "env_var": "MY_SEED",
            "value_range": [1, 1000],
        })
        _, new_env, _ = apply_perturbation(
            spec, 42, cwd=tmp_path, source_dir=tmp_path,
            app_args=[], env={"EXISTING": "x"},
        )
        assert new_env == {"EXISTING": "x", "MY_SEED": "42"}

    def test_disabled_is_noop(self, tmp_path):
        spec = _parse_perturbation({"method": "disabled", "reason": "x"})
        new_args, new_env, modf = apply_perturbation(
            spec, 0, cwd=tmp_path, source_dir=tmp_path,
            app_args=["-x"], env={"A": "b"},
        )
        assert new_args == ["-x"]
        assert new_env == {"A": "b"}
        assert modf is None


# ---------------------------------------------------------------------------
# compute_recovery_slope + kill_fractions_for_bench
# ---------------------------------------------------------------------------


class TestRecoverySlope:
    def test_honest_recovery_slope_minus_one(self):
        # ratios = [0.75, 0.50, 0.25] for fractions [0.25, 0.50, 0.75]
        slope, intercept = compute_recovery_slope(
            [0.25, 0.50, 0.75], [0.75, 0.50, 0.25]
        )
        assert slope == pytest.approx(-1.0, abs=1e-9)
        assert intercept == pytest.approx(1.0, abs=1e-9)
        assert slope < _RECOVERY_RESUMED_SLOPE_THRESHOLD

    def test_cold_replay_slope_zero(self):
        # ratios are constant 1.0 regardless of fraction
        slope, intercept = compute_recovery_slope(
            [0.25, 0.50, 0.75], [1.0, 1.0, 1.0]
        )
        assert slope == pytest.approx(0.0, abs=1e-9)
        assert not (slope < _RECOVERY_RESUMED_SLOPE_THRESHOLD)

    def test_samrai_iter21_style_flat_0_857(self):
        # SAMRAI iter-21 actually showed ratio 0.857 in single-point check
        # and passed.  Multi-fraction would show the same value at every
        # fraction (flat curve) → slope 0 → fails new gate.
        slope, intercept = compute_recovery_slope(
            [0.25, 0.50, 0.75], [0.857, 0.857, 0.857]
        )
        assert slope == pytest.approx(0.0, abs=1e-9)
        assert not (slope < _RECOVERY_RESUMED_SLOPE_THRESHOLD)

    def test_noisy_honest_passes(self):
        # Honest recovery with +0.10 fixed setup overhead at every fraction
        slope, intercept = compute_recovery_slope(
            [0.25, 0.50, 0.75], [0.85, 0.60, 0.35]
        )
        assert slope == pytest.approx(-1.0, abs=1e-9)
        assert slope < _RECOVERY_RESUMED_SLOPE_THRESHOLD

    def test_mismatched_lengths_raises(self):
        with pytest.raises(ValueError):
            compute_recovery_slope([0.25, 0.50], [0.5])

    def test_too_few_points_raises(self):
        with pytest.raises(ValueError):
            compute_recovery_slope([0.25], [0.5])

    def test_identical_fractions_raises(self):
        # Slope undefined when all x values are equal
        with pytest.raises(ValueError, match="identical"):
            compute_recovery_slope([0.5, 0.5, 0.5], [0.5, 0.3, 0.7])


class TestKillFractions:
    def test_default_fractions(self):
        delays = kill_fractions_for_bench(100.0)
        assert delays == [25.0, 50.0, 75.0]

    def test_custom_fractions(self):
        delays = kill_fractions_for_bench(80.0, (0.20, 0.50, 0.80))
        assert delays == pytest.approx([16.0, 40.0, 64.0])

    def test_default_constant(self):
        assert _DEFAULT_KILL_FRACTIONS == (0.25, 0.50, 0.75)

    def test_nonpositive_raises(self):
        with pytest.raises(ValueError):
            kill_fractions_for_bench(0.0)
        with pytest.raises(ValueError):
            kill_fractions_for_bench(-5.0)


# ---------------------------------------------------------------------------
# _enforce_validation_b end-to-end gate behavior
# ---------------------------------------------------------------------------


def _base_signals():
    return {
        "checkpoint_observed": True,
        "checkpoint_files_pass": True,
        "wall_time_pass_at_1_2": True,
        "checkpoint_files": 4,
        "ratio": 1.15,
        "production_cap_ratio": 1.2,
        "kill_attempt_elapsed_s": 50.0,
        "recovery_attempt_elapsed_s": 25.0,
        "original_elapsed_s": 100.0,
        "checkpoint_size_bytes": 1024,
    }


def _seed_proof(out_dir: Path):
    (out_dir / "resilience_proof.json").write_text("{}")


class TestEnforceValidationB:
    def test_honest_multi_fraction_passes(self, tmp_path):
        _seed_proof(tmp_path)
        pfr = [
            {"fraction": 0.25, "recovery_elapsed_s": 75.0, "failure_free_elapsed_s": 100.0},
            {"fraction": 0.50, "recovery_elapsed_s": 50.0, "failure_free_elapsed_s": 100.0},
            {"fraction": 0.75, "recovery_elapsed_s": 25.0, "failure_free_elapsed_s": 100.0},
        ]
        # Returns None on PASS; raises ValidationError on FAIL
        _enforce_validation_b(
            _base_signals(), output_correct=True, out_dir=tmp_path,
            per_fraction_results=pfr, perturbation_active=True,
        )

    def test_cold_replay_multi_fraction_fails(self, tmp_path):
        _seed_proof(tmp_path)
        pfr = [
            {"fraction": 0.25, "recovery_elapsed_s": 100.0, "failure_free_elapsed_s": 100.0},
            {"fraction": 0.50, "recovery_elapsed_s": 100.0, "failure_free_elapsed_s": 100.0},
            {"fraction": 0.75, "recovery_elapsed_s": 100.0, "failure_free_elapsed_s": 100.0},
        ]
        with pytest.raises(ValidationError) as exc_info:
            _enforce_validation_b(
                _base_signals(), output_correct=True, out_dir=tmp_path,
                per_fraction_results=pfr, perturbation_active=True,
            )
        assert "slope" in str(exc_info.value).lower()

    def test_samrai_iter21_pattern_fails_under_slope(self, tmp_path):
        # SAMRAI iter-21 PASSED under old single-point F-19 at 0.857.
        # New multi-fraction slope gate must FAIL it.
        _seed_proof(tmp_path)
        pfr = [
            {"fraction": 0.25, "recovery_elapsed_s": 85.7, "failure_free_elapsed_s": 100.0},
            {"fraction": 0.50, "recovery_elapsed_s": 85.7, "failure_free_elapsed_s": 100.0},
            {"fraction": 0.75, "recovery_elapsed_s": 85.7, "failure_free_elapsed_s": 100.0},
        ]
        with pytest.raises(ValidationError):
            _enforce_validation_b(
                _base_signals(), output_correct=True, out_dir=tmp_path,
                per_fraction_results=pfr, perturbation_active=True,
            )

    def test_legacy_single_point_still_works(self, tmp_path):
        # When per_fraction_results=None and perturbation_active=False,
        # the gate falls back to the single-point F-19 check.
        _seed_proof(tmp_path)
        _enforce_validation_b(
            _base_signals(), output_correct=True, out_dir=tmp_path,
            per_fraction_results=None, perturbation_active=False,
        )

    def test_proof_json_records_slope_fields(self, tmp_path):
        _seed_proof(tmp_path)
        pfr = [
            {"fraction": 0.25, "recovery_elapsed_s": 75.0, "failure_free_elapsed_s": 100.0},
            {"fraction": 0.50, "recovery_elapsed_s": 50.0, "failure_free_elapsed_s": 100.0},
            {"fraction": 0.75, "recovery_elapsed_s": 25.0, "failure_free_elapsed_s": 100.0},
        ]
        _enforce_validation_b(
            _base_signals(), output_correct=True, out_dir=tmp_path,
            per_fraction_results=pfr, perturbation_active=True,
        )
        proof = json.loads((tmp_path / "resilience_proof.json").read_text())
        assert proof["recovery_resumed_mode"] == "multi_fraction_slope"
        assert proof["recovery_resume_slope"] == pytest.approx(-1.0)
        assert proof["recovery_resume_intercept"] == pytest.approx(1.0)
        assert proof["perturbation_active"] is True
        assert len(proof["per_fraction_results"]) == 3

    def test_proof_json_records_legacy_fields(self, tmp_path):
        _seed_proof(tmp_path)
        _enforce_validation_b(
            _base_signals(), output_correct=True, out_dir=tmp_path,
            per_fraction_results=None, perturbation_active=False,
        )
        proof = json.loads((tmp_path / "resilience_proof.json").read_text())
        assert proof["recovery_resumed_mode"] == "single_point_legacy"
        assert proof["recovery_resume_slope"] is None
        assert proof["perturbation_active"] is False


# ---------------------------------------------------------------------------
# _compute_perturbed_baseline (Piece A)
# ---------------------------------------------------------------------------


class _FakeRunResult:
    """Minimal stand-in for runner.RunResult used by the mock below."""
    def __init__(self, *, exit_code: int, elapsed_s: float,
                 stdout: str = "", stderr: str = ""):
        self.exit_code = exit_code
        self.elapsed_s = elapsed_s
        self.stdout = stdout
        self.stderr = stderr

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0


class TestComputePerturbedBaseline:
    """Unit tests for the perturbed-baseline helper.

    Mocks runner.run_once so we do not need MPI or a built binary.  The
    mock writes a synthetic output file into the cwd so the helper's
    "did the run produce the expected file?" check succeeds, and the
    perturbation_seed is recorded so we can also assert that the input
    file in cwd was actually modified by apply_perturbation.
    """

    def _common(self, tmp_path):
        src = tmp_path / "src"
        build = tmp_path / "build"
        scratch = tmp_path / "scratch"
        src.mkdir()
        build.mkdir()
        # Source input file the perturbation will modify in cwd (NOT here).
        (src / "input.txt").write_text("dt = 0.001\n")
        spec = _parse_perturbation({
            "method": "regex_replace", "file": "input.txt",
            "pattern": r"dt\s*=\s*[0-9.]+",
            "replacement_template": "dt = {value:.4f}",
            "value_range": [0.005, 0.015],
        })
        return src, build, scratch, spec

    def _install_mock_run_once(self, monkeypatch, *,
                               elapsed: float = 12.34,
                               output_name: str = "out.bin",
                               output_content: bytes = b"FAKE",
                               exit_code: int = 0,
                               call_log: "list | None" = None):
        """Patch runner.run_once + the validate-side import.

        Writes ``output_content`` into ``output_dir/output_name`` so the
        helper's post-run output-file check passes.  Records each call
        in ``call_log`` for assertion (kwargs only — args is unused).
        """
        def fake_run_once(*, build_dir, executable_name, num_procs, app_args,
                          output_dir, run_cwd=None, env=None,
                          veloc_config_sources=None, veloc_config_name="veloc.cfg",
                          memory_monitor_fn=None, memory_stop_event=None,
                          memory_samples_holder=None, timeout_s=None):
            if call_log is not None:
                call_log.append({
                    "build_dir": str(build_dir),
                    "executable_name": executable_name,
                    "num_procs": num_procs,
                    "app_args": list(app_args),
                    "output_dir": str(output_dir),
                    "run_cwd": str(run_cwd) if run_cwd else None,
                })
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / output_name).write_bytes(output_content)
            return _FakeRunResult(exit_code=exit_code, elapsed_s=elapsed)

        # validate.py imports run_once at call time via
        # `from .runner import run_once, ...` inside the helper, so we patch
        # the runner module itself (the canonical source).
        import validation.veloc.runner as _runner
        monkeypatch.setattr(_runner, "run_once", fake_run_once)
        # _copy_veloc_cfg + _symlink_input_data are also imported inside the
        # helper; patch with no-ops so we don't need real veloc.cfg files
        # or input directories laid out under src/build.
        monkeypatch.setattr(_runner, "_copy_veloc_cfg",
                            lambda *a, **k: None)
        monkeypatch.setattr(_runner, "_symlink_input_data",
                            lambda *a, **k: None)
        return fake_run_once

    def test_writes_output_and_returns_value(self, tmp_path, monkeypatch):
        src, build, scratch, spec = self._common(tmp_path)
        calls: list = []
        self._install_mock_run_once(monkeypatch, call_log=calls, elapsed=9.5)
        elapsed, out_path, value = _compute_perturbed_baseline(
            original_src=src, build_dir=build, executable_name="app",
            num_procs=4, app_args=[],
            perturbation_spec=spec, perturbation_seed=42,
            scratch_root=scratch, veloc_config_name="veloc.cfg",
            app_input_subdir=None, extra_source_dirs=None,
            output_file_name="out.bin",
        )
        assert elapsed == 9.5
        assert out_path == scratch / "seed_42" / "out.bin"
        assert out_path.exists()
        assert 0.005 <= float(value) <= 0.015
        # Input file in cwd was overwritten with the perturbed value.
        cwd_input = (scratch / "seed_42" / "input.txt").read_text()
        assert "dt = " in cwd_input
        assert "dt = 0.001" not in cwd_input  # source value replaced
        # Source file untouched.
        assert (src / "input.txt").read_text() == "dt = 0.001\n"
        assert len(calls) == 1

    def test_same_seed_returns_cached_without_rerun(self, tmp_path, monkeypatch):
        src, build, scratch, spec = self._common(tmp_path)
        calls: list = []
        self._install_mock_run_once(monkeypatch, call_log=calls, elapsed=7.7)
        # First call populates cache.
        e1, p1, v1 = _compute_perturbed_baseline(
            original_src=src, build_dir=build, executable_name="app",
            num_procs=4, app_args=[],
            perturbation_spec=spec, perturbation_seed=99,
            scratch_root=scratch, veloc_config_name="veloc.cfg",
            app_input_subdir=None, extra_source_dirs=None,
            output_file_name="out.bin",
        )
        # Second call same seed → cached path: run_once NOT invoked again.
        e2, p2, v2 = _compute_perturbed_baseline(
            original_src=src, build_dir=build, executable_name="app",
            num_procs=4, app_args=[],
            perturbation_spec=spec, perturbation_seed=99,
            scratch_root=scratch, veloc_config_name="veloc.cfg",
            app_input_subdir=None, extra_source_dirs=None,
            output_file_name="out.bin",
        )
        assert len(calls) == 1, "cached seed must not re-invoke run_once"
        assert e1 == e2 == 7.7
        assert p1 == p2
        assert v1 == v2

    def test_different_seed_reruns(self, tmp_path, monkeypatch):
        src, build, scratch, spec = self._common(tmp_path)
        calls: list = []
        self._install_mock_run_once(monkeypatch, call_log=calls)
        _, _, v_a = _compute_perturbed_baseline(
            original_src=src, build_dir=build, executable_name="app",
            num_procs=4, app_args=[],
            perturbation_spec=spec, perturbation_seed=1,
            scratch_root=scratch, veloc_config_name="veloc.cfg",
            app_input_subdir=None, extra_source_dirs=None,
            output_file_name="out.bin",
        )
        _, _, v_b = _compute_perturbed_baseline(
            original_src=src, build_dir=build, executable_name="app",
            num_procs=4, app_args=[],
            perturbation_spec=spec, perturbation_seed=2,
            scratch_root=scratch, veloc_config_name="veloc.cfg",
            app_input_subdir=None, extra_source_dirs=None,
            output_file_name="out.bin",
        )
        assert len(calls) == 2
        assert v_a != v_b  # different seeds → different values

    def test_disabled_spec_raises(self, tmp_path, monkeypatch):
        src, build, scratch, _ = self._common(tmp_path)
        disabled = _parse_perturbation({"method": "disabled", "reason": "x"})
        with pytest.raises(ValueError, match="active PerturbationSpec"):
            _compute_perturbed_baseline(
                original_src=src, build_dir=build, executable_name="app",
                num_procs=4, app_args=[],
                perturbation_spec=disabled, perturbation_seed=1,
                scratch_root=scratch, veloc_config_name="veloc.cfg",
                app_input_subdir=None, extra_source_dirs=None,
                output_file_name="out.bin",
            )

    def test_none_spec_raises(self, tmp_path, monkeypatch):
        src, build, scratch, _ = self._common(tmp_path)
        with pytest.raises(ValueError, match="active PerturbationSpec"):
            _compute_perturbed_baseline(
                original_src=src, build_dir=build, executable_name="app",
                num_procs=4, app_args=[],
                perturbation_spec=None, perturbation_seed=1,
                scratch_root=scratch, veloc_config_name="veloc.cfg",
                app_input_subdir=None, extra_source_dirs=None,
                output_file_name="out.bin",
            )

    def test_nonzero_exit_raises_validation_error(self, tmp_path, monkeypatch):
        src, build, scratch, spec = self._common(tmp_path)
        self._install_mock_run_once(monkeypatch, exit_code=42)
        with pytest.raises(ValidationError, match="exit code 42"):
            _compute_perturbed_baseline(
                original_src=src, build_dir=build, executable_name="app",
                num_procs=4, app_args=[],
                perturbation_spec=spec, perturbation_seed=1,
                scratch_root=scratch, veloc_config_name="veloc.cfg",
                app_input_subdir=None, extra_source_dirs=None,
                output_file_name="out.bin",
            )

    def test_missing_output_file_raises(self, tmp_path, monkeypatch):
        src, build, scratch, spec = self._common(tmp_path)
        # output_name='out.bin' is what the helper expects, but mock writes
        # 'wrong_name.bin' so the post-run check fails.
        self._install_mock_run_once(monkeypatch, output_name="wrong_name.bin")
        with pytest.raises(ValidationError, match="produced no output"):
            _compute_perturbed_baseline(
                original_src=src, build_dir=build, executable_name="app",
                num_procs=4, app_args=[],
                perturbation_spec=spec, perturbation_seed=1,
                scratch_root=scratch, veloc_config_name="veloc.cfg",
                app_input_subdir=None, extra_source_dirs=None,
                output_file_name="out.bin",
            )

    def test_corrupt_cache_meta_reruns(self, tmp_path, monkeypatch):
        src, build, scratch, spec = self._common(tmp_path)
        calls: list = []
        self._install_mock_run_once(monkeypatch, call_log=calls, elapsed=5.0)
        # Populate cache.
        _compute_perturbed_baseline(
            original_src=src, build_dir=build, executable_name="app",
            num_procs=4, app_args=[],
            perturbation_spec=spec, perturbation_seed=7,
            scratch_root=scratch, veloc_config_name="veloc.cfg",
            app_input_subdir=None, extra_source_dirs=None,
            output_file_name="out.bin",
        )
        # Corrupt the meta.
        (scratch / "seed_7" / "_perturbed_baseline_meta.json").write_text("{not json")
        # Second call must rerun (NOT trust the corrupt meta).
        _compute_perturbed_baseline(
            original_src=src, build_dir=build, executable_name="app",
            num_procs=4, app_args=[],
            perturbation_spec=spec, perturbation_seed=7,
            scratch_root=scratch, veloc_config_name="veloc.cfg",
            app_input_subdir=None, extra_source_dirs=None,
            output_file_name="out.bin",
        )
        assert len(calls) == 2
