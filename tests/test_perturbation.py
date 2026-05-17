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

import argparse
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
    _build_parser,
    _compute_perturbed_baseline,
    _enforce_validation_b,
    _load_perturbation_spec_for_app,
    _parse_perturbation_fractions,
    _strip_output_dir_suffix,
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

    @pytest.mark.parametrize("app", [
        "SAMRAI", "Nyx", "Athena++", "HyPar", "LAMMPS", "QMCPACK",
        "SW4lite", "SPARTA", "SPPARKS", "Smilei", "WarpX",
    ])
    def test_real_yamls_never_touch_vanilla_source(self, app, tmp_path):
        """Regression: apply each committed YAML's regex_replace perturbation
        against the actual vanilla source file and confirm the source is
        byte-identical before and after.

        Catches three classes of future bug:
          1. A YAML accidentally specifies an absolute file path (which
             would make ``cwd / spec.file`` escape cwd and overwrite
             source).
          2. apply_perturbation is modified to write to source_dir
             instead of cwd.
          3. A new method is added that writes to a file outside cwd.

        Limited to method=regex_replace (the only method that touches
        files); app_arg_override + env_var_set + disabled are
        file-agnostic by construction.
        """
        import hashlib
        from validation.veloc.app_config import load_cell

        cell = load_cell(app, size="validation", frequency="nofail")
        spec = cell.perturbation
        if spec is None or spec.method != "regex_replace":
            pytest.skip(f"{app} has no regex_replace perturbation")
        # File path must be relative (absolute would escape cwd)
        assert not spec.file.startswith("/"), (
            f"{app}: perturbation file path must be relative, got {spec.file!r}"
        )
        src_dir = Path("tests/apps/vanillas") / app
        src_file = (src_dir / spec.file).resolve()
        if not src_file.exists():
            pytest.skip(f"{app}: source file missing at {src_file}")
        pre_hash = hashlib.sha256(src_file.read_bytes()).hexdigest()
        pre_mtime = src_file.stat().st_mtime

        # Mirror what the runner does: create the cwd symlink, then perturb
        target = tmp_path / spec.file
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(src_file)
        value = resolve_perturbation_value(spec, seed=12345)
        apply_perturbation(
            spec, value, cwd=tmp_path, source_dir=src_dir, app_args=[], env={},
        )

        post_hash = hashlib.sha256(src_file.read_bytes()).hexdigest()
        post_mtime = src_file.stat().st_mtime
        assert pre_hash == post_hash, (
            f"{app}: source file hash CHANGED — apply_perturbation wrote to source: "
            f"{src_file}"
        )
        assert pre_mtime == post_mtime, (
            f"{app}: source file mtime CHANGED — even if content matches, source "
            f"was opened in write mode: {src_file}"
        )
        # Sanity: the cwd file should now be a real file (not a symlink) with
        # different content than the source
        assert not target.is_symlink(), (
            f"{app}: cwd target {target} is still a symlink — apply_perturbation "
            f"did not replace it as expected"
        )
        assert target.read_text() != src_file.read_text(), (
            f"{app}: cwd file content matches source — perturbation had no effect"
        )

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


# ---------------------------------------------------------------------------
# Multi-fraction orchestrator helpers (Piece B)
# ---------------------------------------------------------------------------


class TestStripOutputDirSuffix:
    """``_strip_output_dir_suffix`` maps validation output dir names back to
    the canonical app name used as the key in tests/apps/configs/<APP>.yaml.
    """

    def test_baseline_suffix(self):
        assert _strip_output_dir_suffix("SAMRAI_baseline") == "SAMRAI"

    def test_reference_suffix(self):
        assert _strip_output_dir_suffix("Nyx_reference") == "Nyx"

    def test_audit_suffix(self):
        assert _strip_output_dir_suffix("CoMD_audit") == "CoMD"

    def test_no_suffix_unchanged(self):
        assert _strip_output_dir_suffix("HPCG") == "HPCG"

    def test_internal_underscore_preserved(self):
        # PRK_Stencil_baseline → PRK_Stencil (only the trailing _baseline
        # is stripped; intra-name underscores survive).
        assert _strip_output_dir_suffix("PRK_Stencil_baseline") == "PRK_Stencil"

    def test_empty_string(self):
        assert _strip_output_dir_suffix("") == ""

    def test_baseline_tagged_suffix(self):
        # 3-D model exploration: sharded cells encode the LLM tag after the
        # canonical mode suffix.  SAMRAI_baseline_sonnet46 must still
        # resolve to "SAMRAI" so the per-app perturbation spec and per-app
        # cap lookups continue to work for the sharded cell.
        assert _strip_output_dir_suffix("SAMRAI_baseline_sonnet46") == "SAMRAI"

    def test_reference_tagged_suffix(self):
        assert _strip_output_dir_suffix("Nyx_reference_haiku45") == "Nyx"

    def test_audit_tagged_suffix(self):
        assert _strip_output_dir_suffix("CoMD_audit_gpt55") == "CoMD"

    def test_baseline_tagged_with_internal_underscore_app(self):
        # PRK_Stencil_baseline_opus47_128k → PRK_Stencil.  Both the intra-
        # name underscores and the tag (which itself contains underscores)
        # must be handled correctly.
        assert (
            _strip_output_dir_suffix("PRK_Stencil_baseline_opus47_128k")
            == "PRK_Stencil"
        )


class TestLoadPerturbationSpecForApp:
    """``_load_perturbation_spec_for_app`` reads the per-app YAML and
    returns a ``PerturbationSpec`` when the YAML defines one.
    """

    def test_unknown_app_returns_none(self):
        # No YAML file exists for this name → returns None (not raise).
        assert _load_perturbation_spec_for_app("__nonexistent_app__") is None

    def test_samrai_returns_spec(self):
        # SAMRAI.yaml has a perturbation: block (committed in a6d96fcc5).
        spec = _load_perturbation_spec_for_app("SAMRAI")
        # If the spec was ever removed/changed this gracefully degrades to
        # None — the test only asserts the loader does not crash and
        # returns the right type when the spec is present.
        if spec is not None:
            assert spec.method != "disabled"
            assert spec.file or spec.arg_index is not None or spec.env_var

    def test_disabled_spec_returns_none(self, tmp_path, monkeypatch):
        # Inject a fake unified-config loader that returns a perturbation
        # block marked 'disabled' — loader must filter it out.
        from validation.veloc import app_config as _ac
        fake_cfg = {
            "mpi_ranks": 1,
            "executable": "app",
            "sizes": {"validation": {"app_args": ["a"]}},
            "perturbation": {"method": "disabled", "reason": "test"},
        }
        monkeypatch.setattr(_ac, "load_unified", lambda app: fake_cfg)
        monkeypatch.setattr(_ac, "load_frequencies",
                            lambda: {"once": {"inject_failures": False}})
        assert _load_perturbation_spec_for_app("X") is None


# ---------------------------------------------------------------------------
# --perturbation-fractions + --no-perturbation CLI plumbing (Piece C)
# ---------------------------------------------------------------------------


class TestParsePerturbationFractionsType:
    """The argparse type converter for --perturbation-fractions."""

    def test_percent_form(self):
        assert _parse_perturbation_fractions("25,50,75") == (0.25, 0.50, 0.75)

    def test_decimal_form(self):
        assert _parse_perturbation_fractions("0.25,0.5,0.75") == (0.25, 0.50, 0.75)

    def test_two_fractions_minimum(self):
        # 2 points is the lower bound for fitting a slope.
        assert _parse_perturbation_fractions("30,70") == (0.30, 0.70)

    def test_one_fraction_rejected(self):
        # 1 point → slope undefined.
        with pytest.raises(argparse.ArgumentTypeError, match="at least 2"):
            _parse_perturbation_fractions("50")

    def test_empty_rejected(self):
        with pytest.raises(argparse.ArgumentTypeError, match="at least 2"):
            _parse_perturbation_fractions("")

    def test_mixed_scales_rejected(self):
        with pytest.raises(argparse.ArgumentTypeError, match="mixed"):
            _parse_perturbation_fractions("0.25,50,0.75")

    def test_zero_rejected(self):
        # 0 is the open-interval lower bound.
        with pytest.raises(argparse.ArgumentTypeError, match=r"\(0, 1\)"):
            _parse_perturbation_fractions("0,50,75")

    def test_one_hundred_rejected(self):
        # 100% (= 1.0 in decimal scale) is the open-interval upper bound.
        with pytest.raises(argparse.ArgumentTypeError, match=r"\(0, 1\)"):
            _parse_perturbation_fractions("25,50,100")

    def test_nonnumeric_rejected(self):
        with pytest.raises(argparse.ArgumentTypeError, match="parse"):
            _parse_perturbation_fractions("not,a,number")

    def test_whitespace_tolerated(self):
        assert _parse_perturbation_fractions(" 25 , 50 , 75 ") == (0.25, 0.50, 0.75)


class TestPerturbationFractionsFlag:
    """End-to-end: ``--perturbation-fractions`` plumbs through _build_parser
    into args.perturbation_fractions as a tuple of floats in (0, 1).
    """

    def _required_positionals(self):
        return ["orig", "res", "--executable-name", "app"]

    def test_default_is_none(self):
        # Default = None so the orchestrator falls back to
        # _DEFAULT_KILL_FRACTIONS without the CLI having to specify them.
        p = _build_parser()
        ns = p.parse_args(self._required_positionals())
        assert ns.perturbation_fractions is None

    def test_three_fraction_string_parses(self):
        p = _build_parser()
        ns = p.parse_args(
            self._required_positionals() + ["--perturbation-fractions", "25,50,75"]
        )
        assert ns.perturbation_fractions == (0.25, 0.50, 0.75)

    def test_equals_form_parses(self):
        # `--perturbation-fractions=25,50,75` (the form documented in the
        # brief's pilot command) must work alongside the space-separated
        # form above.
        p = _build_parser()
        ns = p.parse_args(
            self._required_positionals() + ["--perturbation-fractions=25,50,75"]
        )
        assert ns.perturbation_fractions == (0.25, 0.50, 0.75)

    def test_decimal_form_parses(self):
        p = _build_parser()
        ns = p.parse_args(
            self._required_positionals() + ["--perturbation-fractions", "0.2,0.5,0.8"]
        )
        assert ns.perturbation_fractions == (0.20, 0.50, 0.80)

    def test_invalid_value_exits(self):
        # argparse raises SystemExit on ArgumentTypeError.
        p = _build_parser()
        with pytest.raises(SystemExit):
            p.parse_args(
                self._required_positionals() + ["--perturbation-fractions", "0,50,100"]
            )


class TestNoPerturbationFlag:
    """``--no-perturbation`` is the escape hatch that forces
    perturbation_spec=None even when the YAML has a perturbation: block.
    """

    def _required_positionals(self):
        return ["orig", "res", "--executable-name", "app"]

    def test_default_false(self):
        p = _build_parser()
        ns = p.parse_args(self._required_positionals())
        assert ns.no_perturbation is False

    def test_flag_sets_true(self):
        p = _build_parser()
        ns = p.parse_args(self._required_positionals() + ["--no-perturbation"])
        assert ns.no_perturbation is True

    def test_flag_does_not_take_value(self):
        # --no-perturbation is a flag, not an option.  Passing a value
        # after it should make argparse treat the value as a positional
        # (and fail since positionals are exhausted).
        p = _build_parser()
        with pytest.raises(SystemExit):
            p.parse_args(self._required_positionals() + ["--no-perturbation", "extra-positional"])


