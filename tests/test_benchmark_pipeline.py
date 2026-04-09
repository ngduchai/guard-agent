"""Tests for the app validation pipeline.

Covers:
  - AppRegistry: discovery and loading of app configurations
  - ReferenceValidator: verify_no_recovery, verify_recovery, validate_reference
  - ToolEvaluator: ToolAdapter protocol, evaluate_tool
  - Pipeline: end-to-end orchestration
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from guard_agent.schemas import (
    AppConfig,
    BuildConfig,
    CheckpointLibConfig,
    ComparisonConfig,
    ComparisonResult,
    PipelineResult,
    ReferenceResult,
    RunConfig,
    ToolEvaluationResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Create a minimal project with one test app."""
    vanillas = tmp_path / "tests" / "apps" / "vanillas" / "TestApp"
    checkpointed = tmp_path / "tests" / "apps" / "checkpointed" / "TestApp"
    docs = tmp_path / "tests" / "apps" / "docs" / "TestApp"
    vanillas.mkdir(parents=True)
    checkpointed.mkdir(parents=True)
    docs.mkdir(parents=True)

    # Create app.yaml
    (vanillas / "app.yaml").write_text(textwrap.dedent("""\
        name: TestApp
        category: iterative_fixed
        language: cpp
        description: "Test application"
        mpi_ranks: 2
        build:
          system: make
          cmd: "make"
        run:
          cmd: "mpirun -np {mpi_ranks} ./test_app"
          timeout: 30
        comparison:
          method: text
          output_file: null
          tolerance: 1.0e-6
        checkpoint:
          library: veloc
          config_file: null
    """))

    (vanillas / "prompt.txt").write_text(
        "I want you to make this application resilient against MPI process failures with VeloC checkpoints."
    )

    return tmp_path


@pytest.fixture
def sample_app_config() -> AppConfig:
    """Create a minimal AppConfig for unit tests."""
    return AppConfig(
        name="TestApp",
        category="iterative_fixed",
        language="cpp",
        description="Test application",
        mpi_ranks=2,
        build=BuildConfig(system="make", cmd="make"),
        run=RunConfig(cmd="echo 'result: 42'", timeout=10),
        comparison=ComparisonConfig(method="text", tolerance=1e-6),
        checkpoint=CheckpointLibConfig(library="veloc"),
    )


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

class TestSchemas:
    """Test new Pydantic models for the benchmark pipeline."""

    def test_app_config_creation(self, sample_app_config: AppConfig) -> None:
        assert sample_app_config.name == "TestApp"
        assert sample_app_config.category == "iterative_fixed"
        assert sample_app_config.mpi_ranks == 2
        assert sample_app_config.build.system == "make"
        assert sample_app_config.run.timeout == 10
        assert sample_app_config.comparison.method == "text"
        assert sample_app_config.checkpoint.library == "veloc"

    def test_app_config_serialization(self, sample_app_config: AppConfig) -> None:
        data = sample_app_config.model_dump()
        restored = AppConfig(**data)
        assert restored.name == sample_app_config.name
        assert restored.build.cmd == sample_app_config.build.cmd

    def test_reference_result_defaults(self) -> None:
        r = ReferenceResult(app_name="test")
        assert r.vanilla_build_success is False
        assert r.golden_run_success is False
        assert r.vanilla_no_recovery_verified is False
        assert r.checkpointed_build_success is False
        assert r.checkpointed_recovery_verified is False
        assert r.output_match is None
        assert r.error_message is None

    def test_reference_result_full(self) -> None:
        r = ReferenceResult(
            app_name="test",
            vanilla_build_success=True,
            golden_run_success=True,
            vanilla_no_recovery_verified=True,
            checkpointed_build_success=True,
            checkpointed_recovery_verified=True,
            output_match=ComparisonResult(method="text", passed=True),
        )
        assert r.output_match.passed is True

    def test_tool_evaluation_result(self) -> None:
        r = ToolEvaluationResult(
            app_name="test",
            tool_name="guard-agent",
            build_success=True,
            recovery_verified=True,
            output_match=ComparisonResult(method="numeric", passed=True, score=1.0),
            metrics={"transform_time_s": 5.2},
        )
        assert r.tool_name == "guard-agent"
        assert r.metrics["transform_time_s"] == 5.2

    def test_pipeline_result(self, sample_app_config: AppConfig) -> None:
        ref = ReferenceResult(app_name="TestApp", vanilla_build_success=True)
        pr = PipelineResult(app=sample_app_config, reference=ref)
        assert pr.app.name == "TestApp"
        assert len(pr.tool_evaluations) == 0

    def test_pipeline_result_with_tools(self, sample_app_config: AppConfig) -> None:
        ref = ReferenceResult(app_name="TestApp")
        te = ToolEvaluationResult(app_name="TestApp", tool_name="guard-agent")
        pr = PipelineResult(
            app=sample_app_config,
            reference=ref,
            tool_evaluations=[te],
        )
        assert len(pr.tool_evaluations) == 1
        assert pr.tool_evaluations[0].tool_name == "guard-agent"


# ---------------------------------------------------------------------------
# AppRegistry tests
# ---------------------------------------------------------------------------

class TestAppRegistry:
    """Test app discovery and configuration loading."""

    def test_discover_apps(self, project_root: Path) -> None:
        from validation.veloc.app_registry import discover_apps
        apps = discover_apps(project_root)
        assert len(apps) == 1
        assert apps[0].name == "TestApp"

    def test_load_app_config(self, project_root: Path) -> None:
        from validation.veloc.app_registry import load_app_config
        app_dir = project_root / "tests" / "apps" / "vanillas" / "TestApp"
        cfg = load_app_config(app_dir)
        assert cfg.name == "TestApp"
        assert cfg.category == "iterative_fixed"
        assert cfg.language == "cpp"
        assert cfg.mpi_ranks == 2

    def test_load_app_config_missing_yaml(self, tmp_path: Path) -> None:
        from validation.veloc.app_registry import load_app_config
        with pytest.raises(FileNotFoundError):
            load_app_config(tmp_path)

    def test_registry_discovery(self, project_root: Path) -> None:
        from validation.veloc.app_registry import AppRegistry
        reg = AppRegistry(project_root)
        assert len(reg) == 1
        assert reg.get("TestApp") is not None
        assert reg.get("NonExistent") is None

    def test_registry_by_category(self, project_root: Path) -> None:
        from validation.veloc.app_registry import AppRegistry
        reg = AppRegistry(project_root)
        fixed = reg.by_category("iterative_fixed")
        assert len(fixed) == 1
        assert fixed[0].name == "TestApp"
        assert reg.by_category("unknown_category") == []

    def test_registry_categories(self, project_root: Path) -> None:
        from validation.veloc.app_registry import AppRegistry
        reg = AppRegistry(project_root)
        cats = reg.categories()
        assert "iterative_fixed" in cats

    def test_registry_paths(self, project_root: Path) -> None:
        from validation.veloc.app_registry import AppRegistry
        reg = AppRegistry(project_root)
        van = reg.vanilla_path("TestApp")
        ckpt = reg.checkpointed_path("TestApp")
        assert van.name == "TestApp"
        assert "vanillas" in str(van)
        assert "checkpointed" in str(ckpt)

    def test_registry_has_checkpointed(self, project_root: Path) -> None:
        from validation.veloc.app_registry import AppRegistry
        reg = AppRegistry(project_root)
        assert reg.has_checkpointed("TestApp") is True
        assert reg.has_checkpointed("NonExistent") is False

    def test_empty_project(self, tmp_path: Path) -> None:
        from validation.veloc.app_registry import AppRegistry
        reg = AppRegistry(tmp_path)
        assert len(reg) == 0


# ---------------------------------------------------------------------------
# ReferenceValidator tests
# ---------------------------------------------------------------------------

class TestReferenceValidator:
    """Test the output comparison logic in reference_validator."""

    def test_compare_outputs_text_match(self) -> None:
        from validation.veloc.reference_validator import _compare_outputs
        result = _compare_outputs("hello world\n", "hello world\n", method="text")
        assert result.passed is True

    def test_compare_outputs_text_mismatch(self) -> None:
        from validation.veloc.reference_validator import _compare_outputs
        result = _compare_outputs("hello\n", "world\n", method="text")
        assert result.passed is False

    def test_compare_outputs_numeric_match(self) -> None:
        from validation.veloc.reference_validator import _compare_outputs
        result = _compare_outputs("result: 42.000001", "result: 42.000002", method="numeric", tolerance=1e-4)
        assert result.passed is True

    def test_compare_outputs_numeric_mismatch(self) -> None:
        from validation.veloc.reference_validator import _compare_outputs
        result = _compare_outputs("result: 42.0", "result: 99.0", method="numeric", tolerance=1e-6)
        assert result.passed is False

    def test_compare_outputs_hash_match(self) -> None:
        from validation.veloc.reference_validator import _compare_outputs
        result = _compare_outputs("exact", "exact", method="hash")
        assert result.passed is True

    def test_compare_outputs_hash_mismatch(self) -> None:
        from validation.veloc.reference_validator import _compare_outputs
        result = _compare_outputs("a", "b", method="hash")
        assert result.passed is False

    def test_compare_outputs_numeric_different_count(self) -> None:
        from validation.veloc.reference_validator import _compare_outputs
        result = _compare_outputs("1 2 3", "1 2", method="numeric")
        assert result.passed is False
        assert "Different number" in result.details


# ---------------------------------------------------------------------------
# ToolEvaluator tests
# ---------------------------------------------------------------------------

class TestToolEvaluator:
    """Test the tool adapter protocol and evaluation logic."""

    def test_noop_adapter_protocol(self) -> None:
        from validation.veloc.tool_evaluator import NoopAdapter, ToolAdapter
        adapter = NoopAdapter()
        assert isinstance(adapter, ToolAdapter)
        assert adapter.name == "noop"

    def test_prebuilt_adapter(self, tmp_path: Path, sample_app_config: AppConfig) -> None:
        from validation.veloc.tool_evaluator import PrebuiltAdapter
        source = tmp_path / "source"
        source.mkdir()
        (source / "main.cpp").write_text("int main() {}")
        adapter = PrebuiltAdapter(source, label="reference")
        assert adapter.name == "reference"
        output = tmp_path / "output"
        assert adapter.transform(tmp_path, output, sample_app_config) is True
        assert (output / "main.cpp").is_file()

    def test_prebuilt_adapter_missing_dir(self, tmp_path: Path, sample_app_config: AppConfig) -> None:
        from validation.veloc.tool_evaluator import PrebuiltAdapter
        adapter = PrebuiltAdapter(tmp_path / "nonexistent")
        assert adapter.transform(tmp_path, tmp_path / "out", sample_app_config) is False

    def test_noop_adapter_copies_files(self, tmp_path: Path, sample_app_config: AppConfig) -> None:
        from validation.veloc.tool_evaluator import NoopAdapter
        source = tmp_path / "source"
        source.mkdir()
        (source / "main.cpp").write_text("int main() {}")
        adapter = NoopAdapter()
        output = tmp_path / "output"
        assert adapter.transform(source, output, sample_app_config) is True
        assert (output / "main.cpp").is_file()


# ---------------------------------------------------------------------------
# Integration test: real app registry on the actual benchmark directory
# ---------------------------------------------------------------------------

class TestRealRegistry:
    """Integration test against the actual tests/apps/ directory."""

    @pytest.fixture
    def real_root(self) -> Path:
        return Path(__file__).parent.parent

    def test_discover_real_apps(self, real_root: Path) -> None:
        from validation.veloc.app_registry import AppRegistry
        reg = AppRegistry(real_root)
        # Should find at least a few apps from Batch 1
        assert len(reg) >= 1, f"Expected at least 1 app, found {len(reg)}"
        # Check a known app
        lulesh = reg.get("LULESH")
        if lulesh:
            assert lulesh.category == "iterative_fixed"
            assert lulesh.language == "cpp"
