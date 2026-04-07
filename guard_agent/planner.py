"""Checkpoint plan generator — produces VeloC code templates and injection instructions.

Takes the coding agent's confirmed critical state + project config and returns
a CheckpointPlan with exact code snippets, veloc.cfg content, and CMake
modifications. The coding agent applies these templates to inject VeloC.
"""

from __future__ import annotations

import math
from typing import Any

from guard_agent.schemas import (
    CheckpointPlan,
    CodeInspection,
    CodeTemplate,
    CriticalStateCandidate,
    GuardAgentConfig,
    ProcessStructure,
)
from guard_agent.guide import get_api_reference, get_section


def generate_checkpoint_plan(
    critical_state: list[dict[str, Any]],
    inspection: CodeInspection,
    config: GuardAgentConfig | None = None,
) -> CheckpointPlan:
    """Generate a complete checkpoint injection plan.

    Args:
        critical_state: List of confirmed critical variables. Each dict should
            have at least {"name": str, "type": str, "count_expr": str,
            "element_type": str}. The coding agent's LLM provides this after
            reviewing the inspection results.
        inspection: The CodeInspection from analyze_project().
        config: Optional project config.

    Returns:
        CheckpointPlan with all code templates and injection instructions.
    """
    if config is None:
        from guard_agent.project_config import load_config
        config = load_config()

    language = inspection.language
    mode = config.resilience.mode
    process = inspection.process_structure

    # Build the confirmed CriticalStateCandidate list
    confirmed: list[CriticalStateCandidate] = []
    for i, cs in enumerate(critical_state):
        confirmed.append(CriticalStateCandidate(
            name=cs.get("name", f"var_{i}"),
            type_str=cs.get("type", "void*"),
            element_type=cs.get("element_type", "char"),
            element_count_expr=cs.get("count_expr"),
            size_expr=cs.get("size_expr"),
            rationale=cs.get("rationale", "Confirmed by user/LLM"),
            confidence=1.0,
            source="confirmed",
            veloc_protect_id=i,
        ))

    templates: list[CodeTemplate] = []
    cmake_mods: list[CodeTemplate] = []

    # --- Code templates ---
    if language == "cpp":
        templates.extend(_cpp_templates(confirmed, inspection, config))
    else:
        templates.extend(_c_templates(confirmed, inspection, config))

    # --- CMake modifications ---
    cmake_mods.extend(_cmake_templates(inspection))

    # --- veloc.cfg ---
    veloc_cfg = _generate_veloc_config(config)

    # --- Checkpoint interval ---
    interval = _calculate_interval(config)

    # --- Best practices ---
    practices = _best_practices(language, mode)

    # --- Checkpoint location ---
    main_loops = [
        l for l in inspection.computation_loops
        if l.contains_mpi_calls or l.contains_expensive_ops
    ]
    ckpt_location = ""
    if main_loops:
        loop = main_loops[0]
        ckpt_location = (
            f"Place checkpoint at the end of the loop body at line {loop.body_end_line - 1}, "
            f"after all computation and communication for iteration `{loop.iterator_var}` is complete."
        )

    return CheckpointPlan(
        critical_state=confirmed,
        checkpoint_mode=mode,
        api_language=language,
        code_templates=templates,
        veloc_config_content=veloc_cfg,
        cmake_modifications=cmake_mods,
        checkpoint_interval_seconds=interval,
        checkpoint_location_description=ckpt_location,
        best_practices=practices,
        summary=_build_summary(confirmed, language, mode, interval),
    )


# ---------------------------------------------------------------------------
# C API templates
# ---------------------------------------------------------------------------

def _c_templates(
    state: list[CriticalStateCandidate],
    inspection: CodeInspection,
    config: GuardAgentConfig,
) -> list[CodeTemplate]:
    """Generate C API VeloC code templates."""
    templates: list[CodeTemplate] = []
    proc = inspection.process_structure

    # 1. Include
    templates.append(CodeTemplate(
        action="add_include",
        file_path=inspection.files_analyzed[0] if inspection.files_analyzed else "",
        code_snippet='#include <veloc.h>',
        explanation="Include the VeloC C header.",
        priority=1,
    ))

    # 2. Config path variable + init
    init_line = None
    if proc.mpi_init_location:
        init_line = proc.mpi_init_location.line_number

    cfg_snippet = (
        '    /* VeloC configuration path — accept optional --veloc-cfg argument */\n'
        '    const char *veloc_cfg = "veloc.cfg";\n'
        '    for (int _i = 1; _i < argc - 1; _i++) {\n'
        '        if (strcmp(argv[_i], "--veloc-cfg") == 0) {\n'
        '            veloc_cfg = argv[_i + 1];\n'
        '            break;\n'
        '        }\n'
        '    }\n'
    )
    templates.append(CodeTemplate(
        action="add_config_variable",
        file_path=inspection.files_analyzed[0] if inspection.files_analyzed else "",
        line_number=init_line,
        placement="after",
        code_snippet=cfg_snippet,
        explanation="Parse optional --veloc-cfg argument for VeloC config path.",
        priority=1,
    ))

    init_snippet = "    VELOC_Init(MPI_COMM_WORLD, veloc_cfg);\n"
    templates.append(CodeTemplate(
        action="add_init",
        file_path=inspection.files_analyzed[0] if inspection.files_analyzed else "",
        line_number=init_line,
        placement="after",
        code_snippet=init_snippet,
        explanation="Initialize VeloC immediately after MPI_Init.",
        priority=1,
    ))

    # 3. Memory protection
    for cs in state:
        count = cs.element_count_expr or "1"
        elem_size = f"sizeof({cs.element_type})" if cs.element_type else "1"
        is_pointer = "*" in cs.type_str
        addr = cs.name if is_pointer else f"&{cs.name}"

        snippet = f"    VELOC_Mem_protect({cs.veloc_protect_id}, {addr}, {count}, {elem_size});\n"
        templates.append(CodeTemplate(
            action="add_mem_protect",
            file_path=inspection.files_analyzed[0] if inspection.files_analyzed else "",
            code_snippet=snippet,
            explanation=f"Register `{cs.name}` for checkpoint protection.",
            priority=1,
        ))

    # 4. Restart logic
    restart_snippet = (
        '    /* Check for existing checkpoint and restart if available */\n'
        '    int _veloc_version = VELOC_Restart_test("ckpt", 0);\n'
        '    if (_veloc_version > 0) {\n'
        '        VELOC_Restart("ckpt", _veloc_version);\n'
        '    } else {\n'
        '        _veloc_version = 0;\n'
        '    }\n'
    )
    templates.append(CodeTemplate(
        action="add_restart",
        file_path=inspection.files_analyzed[0] if inspection.files_analyzed else "",
        code_snippet=restart_snippet,
        explanation=(
            "Check for a previous checkpoint and restore state if found. "
            "Place this BEFORE the main computation loop. "
            "Update the loop start to resume from the restored iteration."
        ),
        priority=1,
    ))

    # 5. Checkpoint call
    checkpoint_snippet = (
        '        /* Checkpoint at end of iteration */\n'
        '        VELOC_Checkpoint("ckpt", <iteration_variable> + 1);\n'
    )
    templates.append(CodeTemplate(
        action="add_checkpoint",
        file_path=inspection.files_analyzed[0] if inspection.files_analyzed else "",
        code_snippet=checkpoint_snippet,
        explanation=(
            "Checkpoint at the end of each iteration. Replace <iteration_variable> "
            "with the actual loop iterator. The version must increase with each call."
        ),
        priority=1,
    ))

    # 6. Finalize
    finalize_line = None
    if proc.mpi_finalize_location:
        finalize_line = proc.mpi_finalize_location.line_number

    templates.append(CodeTemplate(
        action="add_finalize",
        file_path=inspection.files_analyzed[0] if inspection.files_analyzed else "",
        line_number=finalize_line,
        placement="before",
        code_snippet="    VELOC_Finalize(1);  /* drain=1: wait for async flushes */\n",
        explanation="Finalize VeloC before MPI_Finalize. drain=1 ensures all checkpoints are flushed.",
        priority=1,
    ))

    # 7. veloc.cfg file
    templates.append(CodeTemplate(
        action="create_file",
        file_path="veloc.cfg",
        code_snippet=_generate_veloc_config(config),
        explanation="VeloC configuration file.",
        priority=1,
    ))

    return templates


# ---------------------------------------------------------------------------
# C++ API templates
# ---------------------------------------------------------------------------

def _cpp_templates(
    state: list[CriticalStateCandidate],
    inspection: CodeInspection,
    config: GuardAgentConfig,
) -> list[CodeTemplate]:
    """Generate C++ API VeloC code templates."""
    templates: list[CodeTemplate] = []
    proc = inspection.process_structure

    # 1. Include
    templates.append(CodeTemplate(
        action="add_include",
        file_path=inspection.files_analyzed[0] if inspection.files_analyzed else "",
        code_snippet='#include "veloc.hpp"',
        explanation="Include the VeloC C++ header.",
        priority=1,
    ))

    # 2. Config path variable
    rank_var = proc.rank_variable or "rank"

    cfg_snippet = (
        '    /* VeloC configuration path — accept optional --veloc-cfg argument */\n'
        '    const char *check_point_config = "veloc.cfg";\n'
        '    for (int _i = 1; _i < argc - 1; _i++) {\n'
        '        if (strcmp(argv[_i], "--veloc-cfg") == 0) {\n'
        '            check_point_config = argv[_i + 1];\n'
        '            break;\n'
        '        }\n'
        '    }\n'
    )
    templates.append(CodeTemplate(
        action="add_config_variable",
        file_path=inspection.files_analyzed[0] if inspection.files_analyzed else "",
        code_snippet=cfg_snippet,
        explanation="Parse optional --veloc-cfg argument for VeloC config path.",
        priority=1,
    ))

    # 3. Init (C++ API)
    init_snippet = (
        f'    veloc::client_t *ckpt = veloc::get_client((unsigned int){rank_var}, check_point_config);\n'
    )
    templates.append(CodeTemplate(
        action="add_init",
        file_path=inspection.files_analyzed[0] if inspection.files_analyzed else "",
        code_snippet=init_snippet,
        explanation=(
            "Initialize VeloC client after MPI_Init and MPI_Comm_rank. "
            f"Uses rank variable `{rank_var}`."
        ),
        priority=1,
    ))

    # 4. Memory protection (C++ API)
    for cs in state:
        count = cs.element_count_expr or "1"
        elem_size = f"sizeof({cs.element_type})" if cs.element_type else "1"

        snippet = f"    ckpt->mem_protect({cs.veloc_protect_id}, {cs.name}, {elem_size}, {count});\n"
        templates.append(CodeTemplate(
            action="add_mem_protect",
            file_path=inspection.files_analyzed[0] if inspection.files_analyzed else "",
            code_snippet=snippet,
            explanation=f"Register `{cs.name}` for checkpoint protection.",
            priority=1,
        ))

    # 5. Checkpoint name
    templates.append(CodeTemplate(
        action="add_checkpoint_name",
        file_path=inspection.files_analyzed[0] if inspection.files_analyzed else "",
        code_snippet='    const char* ckpt_name = "ckpt";\n',
        explanation="Define checkpoint name label.",
        priority=2,
    ))

    # 6. Restart logic (C++ API)
    restart_snippet = (
        '    int v = ckpt->restart_test(ckpt_name, 0);\n'
        '    if (v > 0) {\n'
        '        ckpt->restart(ckpt_name, v);\n'
        '    } else {\n'
        '        v = 0;\n'
        '    }\n'
    )
    templates.append(CodeTemplate(
        action="add_restart",
        file_path=inspection.files_analyzed[0] if inspection.files_analyzed else "",
        code_snippet=restart_snippet,
        explanation=(
            "Check for a previous checkpoint and restore state if found. "
            "Place BEFORE the main computation loop. "
            "Update the loop start to resume from restored iteration `v`."
        ),
        priority=1,
    ))

    # 7. Checkpoint call (C++ API)
    checkpoint_snippet = (
        '        /* Checkpoint at end of iteration */\n'
        '        ckpt->checkpoint(ckpt_name, <iteration_variable> + 1);\n'
    )
    templates.append(CodeTemplate(
        action="add_checkpoint",
        file_path=inspection.files_analyzed[0] if inspection.files_analyzed else "",
        code_snippet=checkpoint_snippet,
        explanation=(
            "Checkpoint at the end of each iteration. Replace <iteration_variable> "
            "with the actual loop iterator. The version must increase with each call."
        ),
        priority=1,
    ))

    # 8. veloc.cfg file
    templates.append(CodeTemplate(
        action="create_file",
        file_path="veloc.cfg",
        code_snippet=_generate_veloc_config(config),
        explanation="VeloC configuration file.",
        priority=1,
    ))

    return templates


# ---------------------------------------------------------------------------
# CMake templates
# ---------------------------------------------------------------------------

def _cmake_templates(inspection: CodeInspection) -> list[CodeTemplate]:
    """Generate CMake modification templates."""
    mods: list[CodeTemplate] = []
    build = inspection.build_system

    if build.build_system != "cmake" or not build.cmake_file:
        return mods

    if not build.has_veloc_dependency:
        mods.append(CodeTemplate(
            action="modify_cmake",
            file_path=build.cmake_file,
            code_snippet="find_package(veloc REQUIRED)",
            explanation=(
                "Add VeloC dependency to CMakeLists.txt. "
                "Place after find_package(MPI REQUIRED) if present."
            ),
            priority=1,
        ))

    if "veloc-client" not in build.link_targets:
        mods.append(CodeTemplate(
            action="modify_cmake",
            file_path=build.cmake_file,
            code_snippet="veloc-client",
            explanation=(
                "Add veloc-client to target_link_libraries. "
                "Append to existing link targets."
            ),
            priority=1,
        ))

    # Install rule for veloc.cfg
    mods.append(CodeTemplate(
        action="modify_cmake",
        file_path=build.cmake_file,
        code_snippet='install(FILES veloc.cfg DESTINATION .)',
        explanation="Install veloc.cfg to the build directory.",
        priority=2,
    ))

    return mods


# ---------------------------------------------------------------------------
# Config and interval calculation
# ---------------------------------------------------------------------------

def _generate_veloc_config(config: GuardAgentConfig) -> str:
    """Generate veloc.cfg content."""
    mode = "sync" if config.resilience.mode == "memory" else "async"
    return (
        f"scratch = {config.environment.scratch_dir}\n"
        f"persistent = {config.environment.persistent_dir}\n"
        f"mode = {mode}\n"
        f"max_versions = {config.resilience.max_versions}\n"
    )


def _calculate_interval(config: GuardAgentConfig) -> float | None:
    """Calculate optimal checkpoint interval using Young-Daly formula."""
    interval = config.resilience.checkpoint_interval
    if isinstance(interval, (int, float)):
        return float(interval)
    if interval == "auto":
        mtbf = config.resilience.mtbf
        checkpoint_cost = 10.0  # default estimate in seconds
        return math.sqrt(2.0 * checkpoint_cost * mtbf)
    return None


def _best_practices(language: str, mode: str) -> list[str]:
    """Return relevant best practices."""
    practices = [
        "Call VeloC init immediately after MPI_Init (or after MPI_Comm_rank for C++ API).",
        "Call VeloC finalize with drain=1 before MPI_Finalize to flush pending checkpoints.",
        "The checkpoint version number must increase with each call — use the loop iteration.",
        "Place checkpoint calls AFTER all computation and communication for that iteration.",
        "Place restart logic BEFORE the main computation loop.",
        "Update the loop start variable to resume from the restored checkpoint version.",
        "Do NOT change any existing command-line arguments — only add the optional --veloc-cfg.",
    ]
    if mode == "memory":
        practices.append(
            "Memory-based mode: register all critical state with mem_protect BEFORE "
            "the restart check. VeloC handles serialization automatically."
        )
    else:
        practices.append(
            "File-based mode: use checkpoint_begin/route_file/checkpoint_end for "
            "custom serialization. You must manually write and read data."
        )
    return practices


def _build_summary(
    state: list[CriticalStateCandidate],
    language: str,
    mode: str,
    interval: float | None,
) -> str:
    """Build a human-readable summary of the plan."""
    var_names = ", ".join(f"`{s.name}`" for s in state)
    api = "C++" if language == "cpp" else "C"
    interval_str = f"{interval:.0f} seconds" if interval else "per iteration"
    return (
        f"Checkpoint plan: protect {len(state)} variables ({var_names}) "
        f"using VeloC {api} API in {mode}-based mode. "
        f"Recommended checkpoint interval: {interval_str}."
    )
