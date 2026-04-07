"""Data models for the guard-agent resilience workflow.

These Pydantic models define the I/O contracts between:
  - analyzer.py  (code inspection)
  - planner.py   (checkpoint plan generation)
  - validator.py (injection validation)
  - mcp_server.py / cli.py (external interfaces)
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Source location
# ---------------------------------------------------------------------------

class SourceLocation(BaseModel):
    """A specific location in a source file."""
    file_path: str
    line_number: int
    context_lines: list[str] = Field(
        default_factory=list,
        description="Surrounding source lines for reference",
    )


# ---------------------------------------------------------------------------
# Code inspection results (output of analyzer.py)
# ---------------------------------------------------------------------------

class MPIPattern(BaseModel):
    """A detected MPI API call."""
    call_name: str = Field(description="e.g. MPI_Init, MPI_Allreduce")
    location: SourceLocation
    arguments: list[str] = Field(default_factory=list)
    communicator: str | None = None


class AllocationInfo(BaseModel):
    """A detected heap allocation."""
    variable_name: str
    type_str: str = Field(description="e.g. float*, double*")
    size_expr: str | None = Field(None, description="e.g. N*N, recon_size")
    element_type: str = Field(description="e.g. float, double, int")
    element_count_expr: str | None = None
    location: SourceLocation
    allocation_kind: str = Field(description="malloc, calloc, new, new[]")


class LoopInfo(BaseModel):
    """A detected computation loop."""
    location: SourceLocation
    iterator_var: str = Field(description="e.g. i, t, iter")
    start_expr: str = Field(description="e.g. 0, v")
    end_expr: str = Field(description="e.g. num_outer_iter, T")
    body_start_line: int
    body_end_line: int
    contains_mpi_calls: bool = False
    contains_expensive_ops: bool = False


class CriticalStateCandidate(BaseModel):
    """A variable identified as a candidate for checkpoint protection."""
    name: str
    type_str: str = Field(description="e.g. float*, int")
    size_expr: str | None = Field(None, description="Size expression if array")
    element_type: str | None = Field(None, description="e.g. float, double")
    element_count_expr: str | None = None
    rationale: str = Field(description="Why this variable is critical")
    confidence: float = Field(
        default=0.7,
        ge=0.0, le=1.0,
        description="Confidence that this needs protection",
    )
    source: str = Field(
        default="static_analysis",
        description="How this was identified: static_analysis, user_hint, mpi_buffer",
    )
    location: SourceLocation | None = None


class ExistingVelocState(BaseModel):
    """Summary of existing VeloC instrumentation in the code."""
    has_veloc_include: bool = False
    has_veloc_init: bool = False
    has_veloc_finalize: bool = False
    has_mem_protect: bool = False
    has_checkpoint: bool = False
    has_restart: bool = False
    protected_variables: list[str] = Field(default_factory=list)
    details: list[str] = Field(
        default_factory=list,
        description="Human-readable notes about existing VeloC usage",
    )

    @property
    def is_protected(self) -> bool:
        return self.has_veloc_include and self.has_veloc_init and self.has_checkpoint


class ProcessStructure(BaseModel):
    """Detected process/thread structure."""
    uses_mpi: bool = False
    rank_variable: str | None = None
    size_variable: str | None = None
    communicator: str | None = None
    uses_openmp: bool = False
    uses_threads: bool = False
    mpi_init_location: SourceLocation | None = None
    mpi_finalize_location: SourceLocation | None = None


class BuildSystemInfo(BaseModel):
    """Detected build system information."""
    build_system: str | None = Field(None, description="cmake, make, none")
    cmake_file: str | None = None
    has_mpi_dependency: bool = False
    has_veloc_dependency: bool = False
    link_targets: list[str] = Field(default_factory=list)


class CodeInspection(BaseModel):
    """Complete analysis of a codebase — output of inspect_codebase()."""
    files_analyzed: list[str]
    language: str = Field(description="c or cpp")
    allocations: list[AllocationInfo] = Field(default_factory=list)
    mpi_patterns: list[MPIPattern] = Field(default_factory=list)
    computation_loops: list[LoopInfo] = Field(default_factory=list)
    critical_state_candidates: list[CriticalStateCandidate] = Field(default_factory=list)
    existing_veloc: ExistingVelocState = Field(default_factory=ExistingVelocState)
    process_structure: ProcessStructure = Field(default_factory=ProcessStructure)
    build_system: BuildSystemInfo = Field(default_factory=BuildSystemInfo)
    warnings: list[str] = Field(default_factory=list)
    guided_prompt: str = Field(
        default="",
        description=(
            "A prompt for the coding agent's LLM to review the analysis, "
            "confirm critical state, and decide checkpoint strategy."
        ),
    )


# ---------------------------------------------------------------------------
# Checkpoint plan (output of planner.py)
# ---------------------------------------------------------------------------

class CodeTemplate(BaseModel):
    """A code snippet to be inserted at a specific location."""
    action: str = Field(description=(
        "What this does: add_include, add_init, add_mem_protect, "
        "add_restart, add_checkpoint, add_finalize, modify_cmake, "
        "create_file"
    ))
    file_path: str
    line_number: int | None = Field(None, description="Target line for insertion")
    placement: str = Field(
        default="after",
        description="Where to insert: before, after, replace",
    )
    code_snippet: str = Field(description="Exact code to insert")
    explanation: str = Field(description="Why this is needed")
    priority: int = Field(
        default=1,
        description="1=critical, 2=important, 3=nice-to-have",
    )


class CheckpointPlan(BaseModel):
    """Complete checkpoint injection plan — output of get_checkpoint_plan()."""
    critical_state: list[CriticalStateCandidate]
    checkpoint_mode: str = Field(description="memory or file-based")
    api_language: str = Field(description="c or cpp")
    code_templates: list[CodeTemplate] = Field(default_factory=list)
    veloc_config_content: str = Field(
        default="",
        description="Content for veloc.cfg file",
    )
    cmake_modifications: list[CodeTemplate] = Field(default_factory=list)
    checkpoint_interval_seconds: float | None = None
    checkpoint_location_description: str = Field(
        default="",
        description="Where in the code to place checkpoint calls",
    )
    best_practices: list[str] = Field(default_factory=list)
    summary: str = Field(default="")


# ---------------------------------------------------------------------------
# Validation result (output of validator.py)
# ---------------------------------------------------------------------------

class ComparisonResult(BaseModel):
    """Output comparison between baseline and resilient runs."""
    method: str = Field(description="hash, ssim, numeric, text")
    passed: bool
    details: str = Field(default="")
    score: float | None = Field(None, description="Similarity score if applicable")


class ValidationResult(BaseModel):
    """Complete validation result — output of validate_injection()."""
    passed: bool
    build_success: bool = False
    baseline_run_success: bool = False
    resilient_run_success: bool = False
    failure_injection_success: bool = False
    restart_success: bool = False
    comparison: ComparisonResult | None = None
    error_message: str | None = None
    error_analysis: str | None = Field(
        None,
        description="Detailed analysis of what went wrong (for LLM to fix)",
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Suggested fixes for the LLM",
    )
    build_output: str = Field(default="")
    run_output: str = Field(default="")
    elapsed_seconds: float | None = None


# ---------------------------------------------------------------------------
# Project configuration (.guard-agent.yaml)
# ---------------------------------------------------------------------------

class ResilienceConfig(BaseModel):
    """Resilience settings from .guard-agent.yaml."""
    library: str = Field(default="veloc", description="Checkpoint library")
    mode: str = Field(
        default="memory",
        description="memory (VeloC memory-based) or file-based",
    )
    checkpoint_interval: str | float = Field(
        default="auto",
        description="auto (Young-Daly) or interval in seconds",
    )
    mtbf: float = Field(
        default=36000,
        description="Mean Time Between Failures in seconds",
    )
    max_versions: int = Field(default=3)


class EnvironmentConfig(BaseModel):
    """Environment settings."""
    type: str = Field(default="hpc", description="hpc or cloud")
    scratch_dir: str = Field(default="/tmp/veloc_scratch")
    persistent_dir: str = Field(default="/tmp/veloc_persistent")


class SourceConfig(BaseModel):
    """Source code settings."""
    paths: list[str] = Field(default_factory=lambda: ["src/"])
    language: str = Field(default="auto", description="auto, c, or cpp")
    build_system: str = Field(default="cmake", description="cmake or none")


class HintsConfig(BaseModel):
    """User hints for the analyzer."""
    critical_variables: list[str] = Field(default_factory=list)
    checkpoint_location: str = Field(
        default="main_loop",
        description="main_loop or custom",
    )


class GuardAgentConfig(BaseModel):
    """Parsed .guard-agent.yaml configuration."""
    resilience: ResilienceConfig = Field(default_factory=ResilienceConfig)
    environment: EnvironmentConfig = Field(default_factory=EnvironmentConfig)
    source: SourceConfig = Field(default_factory=SourceConfig)
    hints: HintsConfig = Field(default_factory=HintsConfig)
