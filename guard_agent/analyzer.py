"""Static code analyzer for identifying critical state and checkpoint needs.

Performs regex-based analysis of C/C++ source files to detect:
  - Critical state that needs checkpoint protection
  - Process/thread structure (MPI, OpenMP)
  - Computation loops suitable for checkpoint boundaries
  - Existing VeloC instrumentation
  - Build system configuration

This module does NOT use an LLM — it provides structured analysis results
that the coding agent's LLM uses to make decisions.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from guard_agent.schemas import (
    AllocationInfo,
    BuildSystemInfo,
    CodeInspection,
    CriticalStateCandidate,
    ExistingVelocState,
    GuardAgentConfig,
    LoopInfo,
    MPIPattern,
    ProcessStructure,
    SourceLocation,
)


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# MPI patterns
_MPI_INIT_RE = re.compile(r"\bMPI_Init\s*\(")
_MPI_INIT_THREAD_RE = re.compile(r"\bMPI_Init_thread\s*\(")
_MPI_FINALIZE_RE = re.compile(r"\bMPI_Finalize\s*\(")
_MPI_COMM_RANK_RE = re.compile(r"\bMPI_Comm_rank\s*\(\s*(\w+)\s*,\s*&(\w+)\s*\)")
_MPI_COMM_SIZE_RE = re.compile(r"\bMPI_Comm_size\s*\(\s*(\w+)\s*,\s*&(\w+)\s*\)")
_MPI_COLLECTIVE_RE = re.compile(
    r"\b(MPI_(?:Allgather|Allreduce|Alltoall|Bcast|Scatter|Gather|Reduce|"
    r"Sendrecv|Barrier|Scan|Exscan))\s*\("
)
_MPI_P2P_RE = re.compile(r"\b(MPI_(?:Send|Recv|Isend|Irecv|Ssend|Bsend))\s*\(")
_MPI_INCLUDE_RE = re.compile(r'#include\s*[<"]mpi\.h[>"]')

# Memory allocation patterns (critical state candidates)
_MALLOC_RE = re.compile(
    r"(\w+)\s*=\s*\((\w[\w\s\*]*\*)\)\s*malloc\s*\((.+?)\)\s*;"
)
_CALLOC_RE = re.compile(
    r"(\w+)\s*=\s*\((\w[\w\s\*]*\*)\)\s*calloc\s*\((.+?)\)\s*;"
)
_NEW_ARRAY_RE = re.compile(
    r"(\w+)\s*=\s*new\s+(\w+)\s*\[(.+?)\]\s*;"
)

# VeloC detection patterns
_VELOC_INCLUDE_C_RE = re.compile(r'#include\s*[<"]veloc\.h[>"]')
_VELOC_INCLUDE_CPP_RE = re.compile(r'#include\s*[<"]veloc\.hpp[>"]')
_VELOC_INIT_RE = re.compile(r"\bVELOC_Init\s*\(")
_VELOC_INIT_SINGLE_RE = re.compile(r"\bVELOC_Init_single\s*\(")
_VELOC_GET_CLIENT_RE = re.compile(r"\bveloc::get_client\s*\(")
_VELOC_FINALIZE_RE = re.compile(r"\bVELOC_Finalize\s*\(")
_VELOC_MEM_PROTECT_RE = re.compile(r"\bVELOC_Mem_protect\s*\(|->mem_protect\s*\(")
_VELOC_CHECKPOINT_RE = re.compile(r"\bVELOC_Checkpoint\s*\(|->checkpoint\s*\(")
_VELOC_RESTART_RE = re.compile(
    r"\bVELOC_Restart\s*\(|->restart\s*\(|"
    r"\bVELOC_Restart_test\s*\(|->restart_test\s*\("
)

# Loop patterns
_FOR_LOOP_RE = re.compile(
    r"\bfor\s*\(\s*(?:(?:int|unsigned|long|size_t)\s+)?(\w+)\s*=\s*([^;]+);\s*"
    r"\1\s*[<!=]+\s*([^;]+);\s*(?:\1\s*\+\+|\+\+\s*\1|\1\s*\+=\s*\d+)"
)

# OpenMP patterns
_OMP_PRAGMA_RE = re.compile(r"#pragma\s+omp\s+(parallel|for|sections|task)")

# CMake patterns
_CMAKE_FIND_MPI_RE = re.compile(r"find_package\s*\(\s*MPI\s+", re.IGNORECASE)
_CMAKE_FIND_VELOC_RE = re.compile(r"find_package\s*\(\s*veloc\s+", re.IGNORECASE)
_CMAKE_LINK_RE = re.compile(r"target_link_libraries\s*\(([^)]+)\)", re.IGNORECASE)

# C/C++ file extensions
_C_EXTENSIONS = {".c"}
_CPP_EXTENSIONS = {".cc", ".cpp", ".cxx", ".C"}
_HEADER_EXTENSIONS = {".h", ".hpp", ".hxx"}
_ALL_EXTENSIONS = _C_EXTENSIONS | _CPP_EXTENSIONS | _HEADER_EXTENSIONS


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_file(
    file_path: str | Path,
    config: GuardAgentConfig | None = None,
) -> CodeInspection:
    """Analyze a single C/C++ source file."""
    return analyze_project([str(file_path)], config)


def analyze_project(
    source_paths: list[str],
    config: GuardAgentConfig | None = None,
) -> CodeInspection:
    """Analyze one or more source files or directories.

    Args:
        source_paths: List of file paths or directories. Directories are
            scanned recursively for C/C++ source files.
        config: Optional project config for hints and settings.

    Returns:
        CodeInspection with all detected patterns and critical state candidates.
    """
    files = _collect_source_files(source_paths)
    if not files:
        return CodeInspection(
            files_analyzed=[],
            language="c",
            warnings=["No C/C++ source files found in the provided paths."],
        )

    language = _detect_language(files, config)
    all_lines: dict[str, list[str]] = {}
    for f in files:
        try:
            with open(f, "r", encoding="utf-8", errors="replace") as fh:
                all_lines[f] = fh.readlines()
        except OSError:
            pass

    # Run detection passes
    allocations: list[AllocationInfo] = []
    mpi_patterns: list[MPIPattern] = []
    loops: list[LoopInfo] = []
    veloc_state = ExistingVelocState()
    process_struct = ProcessStructure()

    for fpath, lines in all_lines.items():
        allocations.extend(_detect_allocations(lines, fpath))
        mpi_patterns.extend(_detect_mpi_patterns(lines, fpath))
        _update_veloc_state(lines, fpath, veloc_state)
        _update_process_structure(lines, fpath, mpi_patterns, process_struct)
        loops.extend(_detect_loops(lines, fpath, mpi_patterns))

    # Cross-reference: identify critical state
    candidates = _identify_critical_state(
        allocations, mpi_patterns, loops, config,
    )

    # Analyze build system
    build_info = _analyze_build_system(source_paths, files)

    # Generate guided prompt
    guided_prompt = _build_guided_prompt(
        candidates, process_struct, loops, veloc_state, language,
    )

    warnings: list[str] = []
    if not mpi_patterns and not allocations and not loops:
        warnings.append(
            "No MPI calls, heap allocations, or computation loops detected. "
            "This file may not need checkpointing."
        )

    return CodeInspection(
        files_analyzed=list(all_lines.keys()),
        language=language,
        allocations=allocations,
        mpi_patterns=mpi_patterns,
        computation_loops=loops,
        critical_state_candidates=candidates,
        existing_veloc=veloc_state,
        process_structure=process_struct,
        build_system=build_info,
        warnings=warnings,
        guided_prompt=guided_prompt,
    )


def quick_check(file_path: str | Path) -> bool:
    """Fast check: does this C/C++ file have state worth checkpointing but no VeloC?

    Used by the PostToolUse hook to decide whether to prompt the agent.
    Returns True if the file likely needs checkpointing protection.
    """
    path = Path(file_path)
    if path.suffix not in _ALL_EXTENSIONS:
        return False

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False

    lines = content.splitlines()

    # Already has VeloC?
    for line in lines:
        if (_VELOC_INCLUDE_C_RE.search(line) or _VELOC_INCLUDE_CPP_RE.search(line)
                or _VELOC_GET_CLIENT_RE.search(line)):
            return False

    # Has critical state indicators?
    has_allocation = any(
        _MALLOC_RE.search(line) or _CALLOC_RE.search(line) or _NEW_ARRAY_RE.search(line)
        for line in lines
    )
    has_mpi = any(_MPI_INCLUDE_RE.search(line) for line in lines)
    has_loop = any(_FOR_LOOP_RE.search(line) for line in lines)

    # Needs protection if it has allocations + loops (state + computation),
    # or MPI (distributed state at risk of node failure)
    return (has_allocation and has_loop) or has_mpi


# ---------------------------------------------------------------------------
# Internal detection functions
# ---------------------------------------------------------------------------

def _collect_source_files(paths: list[str]) -> list[str]:
    """Collect all C/C++ source files from the given paths."""
    files: list[str] = []
    for p in paths:
        path = Path(p)
        if path.is_file() and path.suffix in (_C_EXTENSIONS | _CPP_EXTENSIONS):
            files.append(str(path.resolve()))
        elif path.is_dir():
            for ext in _C_EXTENSIONS | _CPP_EXTENSIONS:
                files.extend(str(f.resolve()) for f in path.rglob(f"*{ext}"))
    return sorted(set(files))


def _detect_language(files: list[str], config: GuardAgentConfig | None) -> str:
    """Detect whether the project uses C or C++."""
    if config and config.source.language != "auto":
        return config.source.language

    for f in files:
        if Path(f).suffix in _CPP_EXTENSIONS:
            return "cpp"
    return "c"


def _make_location(file_path: str, line_idx: int, lines: list[str]) -> SourceLocation:
    """Create a SourceLocation with surrounding context."""
    start = max(0, line_idx - 1)
    end = min(len(lines), line_idx + 2)
    context = [lines[i].rstrip() for i in range(start, end)]
    return SourceLocation(
        file_path=file_path,
        line_number=line_idx + 1,
        context_lines=context,
    )


def _detect_allocations(lines: list[str], file_path: str) -> list[AllocationInfo]:
    """Detect heap allocations (malloc, calloc, new[])."""
    allocations: list[AllocationInfo] = []

    for i, line in enumerate(lines):
        # malloc
        m = _MALLOC_RE.search(line)
        if m:
            var_name, type_str, size_expr = m.group(1), m.group(2), m.group(3)
            elem_type = type_str.replace("*", "").strip()
            allocations.append(AllocationInfo(
                variable_name=var_name,
                type_str=type_str.strip(),
                size_expr=size_expr.strip(),
                element_type=elem_type,
                element_count_expr=_infer_count_from_malloc(size_expr, elem_type),
                location=_make_location(file_path, i, lines),
                allocation_kind="malloc",
            ))
            continue

        # calloc
        m = _CALLOC_RE.search(line)
        if m:
            var_name, type_str, args = m.group(1), m.group(2), m.group(3)
            elem_type = type_str.replace("*", "").strip()
            parts = [p.strip() for p in args.split(",", 1)]
            count_expr = parts[0] if parts else args
            allocations.append(AllocationInfo(
                variable_name=var_name,
                type_str=type_str.strip(),
                size_expr=args.strip(),
                element_type=elem_type,
                element_count_expr=count_expr,
                location=_make_location(file_path, i, lines),
                allocation_kind="calloc",
            ))
            continue

        # new[]
        m = _NEW_ARRAY_RE.search(line)
        if m:
            var_name, elem_type, count_expr = m.group(1), m.group(2), m.group(3)
            allocations.append(AllocationInfo(
                variable_name=var_name,
                type_str=f"{elem_type}*",
                size_expr=f"{count_expr} * sizeof({elem_type})",
                element_type=elem_type,
                element_count_expr=count_expr.strip(),
                location=_make_location(file_path, i, lines),
                allocation_kind="new[]",
            ))

    return allocations


def _infer_count_from_malloc(size_expr: str, elem_type: str) -> str | None:
    """Try to infer element count from a malloc size expression.

    E.g. "N * N * sizeof(double)" → "N * N"
    """
    # Remove sizeof(...) and extract the count part
    sizeof_re = re.compile(r"\*?\s*sizeof\s*\(\s*\w+\s*\)\s*\*?")
    cleaned = sizeof_re.sub("", size_expr).strip()
    # Remove casting like (size_t)
    cleaned = re.sub(r"\(\s*(?:size_t|int|unsigned)\s*\)\s*", "", cleaned)
    cleaned = cleaned.strip(" *")
    return cleaned if cleaned else None


def _detect_mpi_patterns(lines: list[str], file_path: str) -> list[MPIPattern]:
    """Detect MPI API calls."""
    patterns: list[MPIPattern] = []

    for i, line in enumerate(lines):
        for regex in [_MPI_INIT_RE, _MPI_INIT_THREAD_RE, _MPI_FINALIZE_RE]:
            if regex.search(line):
                call_name = "MPI_Init"
                if "Finalize" in line:
                    call_name = "MPI_Finalize"
                elif "thread" in line.lower():
                    call_name = "MPI_Init_thread"
                patterns.append(MPIPattern(
                    call_name=call_name,
                    location=_make_location(file_path, i, lines),
                ))
                break

        m = _MPI_COMM_RANK_RE.search(line)
        if m:
            patterns.append(MPIPattern(
                call_name="MPI_Comm_rank",
                location=_make_location(file_path, i, lines),
                arguments=[m.group(1), m.group(2)],
                communicator=m.group(1),
            ))

        m = _MPI_COMM_SIZE_RE.search(line)
        if m:
            patterns.append(MPIPattern(
                call_name="MPI_Comm_size",
                location=_make_location(file_path, i, lines),
                arguments=[m.group(1), m.group(2)],
                communicator=m.group(1),
            ))

        m = _MPI_COLLECTIVE_RE.search(line)
        if m:
            patterns.append(MPIPattern(
                call_name=m.group(1),
                location=_make_location(file_path, i, lines),
            ))

        m = _MPI_P2P_RE.search(line)
        if m:
            patterns.append(MPIPattern(
                call_name=m.group(1),
                location=_make_location(file_path, i, lines),
            ))

    return patterns


def _update_veloc_state(
    lines: list[str],
    file_path: str,
    state: ExistingVelocState,
) -> None:
    """Update existing VeloC state from file content."""
    for i, line in enumerate(lines):
        if _VELOC_INCLUDE_C_RE.search(line) or _VELOC_INCLUDE_CPP_RE.search(line):
            state.has_veloc_include = True
            state.details.append(f"{file_path}:{i+1}: VeloC include found")

        if _VELOC_INIT_RE.search(line) or _VELOC_INIT_SINGLE_RE.search(line) or _VELOC_GET_CLIENT_RE.search(line):
            state.has_veloc_init = True

        if _VELOC_FINALIZE_RE.search(line):
            state.has_veloc_finalize = True

        if _VELOC_MEM_PROTECT_RE.search(line):
            state.has_mem_protect = True
            # Try to extract variable name from the call
            m = re.search(r"(?:mem_protect|VELOC_Mem_protect)\s*\([^,]+,\s*&?(\w+)", line)
            if m and m.group(1) not in state.protected_variables:
                state.protected_variables.append(m.group(1))

        if _VELOC_CHECKPOINT_RE.search(line):
            state.has_checkpoint = True

        if _VELOC_RESTART_RE.search(line):
            state.has_restart = True


def _update_process_structure(
    lines: list[str],
    file_path: str,
    mpi_patterns: list[MPIPattern],
    struct: ProcessStructure,
) -> None:
    """Update process structure from detected patterns."""
    for p in mpi_patterns:
        if p.location.file_path != file_path:
            continue

        if p.call_name == "MPI_Init" or p.call_name == "MPI_Init_thread":
            struct.uses_mpi = True
            struct.mpi_init_location = p.location

        if p.call_name == "MPI_Finalize":
            struct.mpi_finalize_location = p.location

        if p.call_name == "MPI_Comm_rank" and p.arguments:
            struct.communicator = p.arguments[0] if len(p.arguments) > 0 else None
            struct.rank_variable = p.arguments[1] if len(p.arguments) > 1 else None

        if p.call_name == "MPI_Comm_size" and p.arguments:
            struct.size_variable = p.arguments[1] if len(p.arguments) > 1 else None

    for line in lines:
        if _OMP_PRAGMA_RE.search(line):
            struct.uses_openmp = True
            break


def _detect_loops(
    lines: list[str],
    file_path: str,
    mpi_patterns: list[MPIPattern],
) -> list[LoopInfo]:
    """Detect computation loops suitable for checkpoint boundaries."""
    loops: list[LoopInfo] = []

    # Collect line numbers of MPI calls in this file
    mpi_lines = {
        p.location.line_number
        for p in mpi_patterns
        if p.location.file_path == file_path
    }

    for i, line in enumerate(lines):
        m = _FOR_LOOP_RE.search(line)
        if not m:
            continue

        iterator_var = m.group(1)
        start_expr = m.group(2).strip()
        end_expr = m.group(3).strip()

        # Find the loop body boundaries (brace matching)
        body_start, body_end = _find_brace_range(lines, i)
        if body_start is None:
            continue

        # Check if loop body contains MPI calls
        contains_mpi = any(
            body_start <= ln <= body_end for ln in mpi_lines
        )

        # Check for expensive operations in the body
        contains_expensive = False
        for j in range(body_start - 1, min(body_end, len(lines))):
            body_line = lines[j]
            if (re.search(r"\b(?:art|compute|solve|calculate|simulate|iterate)\b", body_line, re.IGNORECASE)
                    or _MPI_COLLECTIVE_RE.search(body_line)):
                contains_expensive = True
                break

        loops.append(LoopInfo(
            location=_make_location(file_path, i, lines),
            iterator_var=iterator_var,
            start_expr=start_expr,
            end_expr=end_expr,
            body_start_line=body_start,
            body_end_line=body_end,
            contains_mpi_calls=contains_mpi,
            contains_expensive_ops=contains_expensive,
        ))

    return loops


def _find_brace_range(lines: list[str], start_line: int) -> tuple[int | None, int | None]:
    """Find the opening and closing brace of a block starting at start_line.

    Returns (body_start_line, body_end_line) as 1-indexed line numbers,
    or (None, None) if braces not found.
    """
    depth = 0
    body_start = None

    for i in range(start_line, min(start_line + 500, len(lines))):
        for ch in lines[i]:
            if ch == "{":
                depth += 1
                if depth == 1:
                    body_start = i + 1  # 1-indexed
            elif ch == "}":
                depth -= 1
                if depth == 0 and body_start is not None:
                    return body_start, i + 1  # 1-indexed

    return None, None


def _identify_critical_state(
    allocations: list[AllocationInfo],
    mpi_patterns: list[MPIPattern],
    loops: list[LoopInfo],
    config: GuardAgentConfig | None,
) -> list[CriticalStateCandidate]:
    """Cross-reference allocations, MPI buffers, and loops to identify critical state."""
    candidates: list[CriticalStateCandidate] = []
    seen_names: set[str] = set()

    # Collect variable names used in MPI calls (from collective call context lines)
    mpi_buffer_vars: set[str] = set()
    for p in mpi_patterns:
        if p.call_name.startswith("MPI_") and p.call_name not in (
            "MPI_Init", "MPI_Init_thread", "MPI_Finalize",
            "MPI_Comm_rank", "MPI_Comm_size", "MPI_Barrier",
        ):
            # Extract variable names from context lines
            for ctx_line in p.location.context_lines:
                # Look for variable names in function arguments
                for var_match in re.finditer(r"\b(\w+)\s*[,)]", ctx_line):
                    name = var_match.group(1)
                    if not name.startswith("MPI_") and not name.isupper():
                        mpi_buffer_vars.add(name)

    # Each allocation is a critical state candidate
    protect_id = 0
    for alloc in allocations:
        name = alloc.variable_name
        if name in seen_names:
            continue
        seen_names.add(name)

        # Determine confidence based on evidence
        confidence = 0.5  # base: it's a heap allocation
        rationale_parts: list[str] = [f"Heap-allocated {alloc.type_str}"]

        if name in mpi_buffer_vars:
            confidence = 0.9
            rationale_parts.append("used as MPI communication buffer")

        # Check if this variable appears in any computation loop
        for loop in loops:
            if loop.contains_mpi_calls or loop.contains_expensive_ops:
                # This is a significant loop — allocations used here are critical
                confidence = max(confidence, 0.75)
                rationale_parts.append("used in computation loop")
                break

        candidates.append(CriticalStateCandidate(
            name=name,
            type_str=alloc.type_str,
            size_expr=alloc.size_expr,
            element_type=alloc.element_type,
            element_count_expr=alloc.element_count_expr,
            rationale="; ".join(rationale_parts),
            confidence=confidence,
            source="static_analysis" if name not in mpi_buffer_vars else "mpi_buffer",
            location=alloc.location,
            veloc_protect_id=protect_id,
        ))
        protect_id += 1

    # Add user-hinted variables
    if config and config.hints.critical_variables:
        for hint_name in config.hints.critical_variables:
            if hint_name not in seen_names:
                seen_names.add(hint_name)
                candidates.append(CriticalStateCandidate(
                    name=hint_name,
                    type_str="unknown",
                    rationale="User-specified critical variable",
                    confidence=1.0,
                    source="user_hint",
                    veloc_protect_id=protect_id,
                ))
                protect_id += 1

    # Sort by confidence (highest first)
    candidates.sort(key=lambda c: c.confidence, reverse=True)
    return candidates


def _analyze_build_system(
    source_paths: list[str],
    source_files: list[str],
) -> BuildSystemInfo:
    """Analyze CMakeLists.txt in the source directories."""
    info = BuildSystemInfo()

    # Look for CMakeLists.txt in source directories and their parents
    cmake_candidates: list[Path] = []
    for p in source_paths:
        path = Path(p)
        if path.is_file():
            path = path.parent
        for candidate_dir in [path, *path.parents]:
            cmake = candidate_dir / "CMakeLists.txt"
            if cmake.is_file():
                cmake_candidates.append(cmake)
                break

    if not cmake_candidates:
        return info

    cmake_path = cmake_candidates[0]
    info.build_system = "cmake"
    info.cmake_file = str(cmake_path)

    try:
        content = cmake_path.read_text(encoding="utf-8")
    except OSError:
        return info

    if _CMAKE_FIND_MPI_RE.search(content):
        info.has_mpi_dependency = True

    if _CMAKE_FIND_VELOC_RE.search(content):
        info.has_veloc_dependency = True

    for m in _CMAKE_LINK_RE.finditer(content):
        targets = m.group(1).strip()
        info.link_targets = [t.strip() for t in re.split(r"\s+", targets)]

    return info


def _build_guided_prompt(
    candidates: list[CriticalStateCandidate],
    process_struct: ProcessStructure,
    loops: list[LoopInfo],
    veloc_state: ExistingVelocState,
    language: str,
) -> str:
    """Generate a prompt guiding the coding agent's LLM through the analysis."""
    parts: list[str] = []

    if veloc_state.is_protected:
        parts.append(
            "This code already has VeloC checkpointing. Review the existing "
            "instrumentation and verify it covers all critical state after your changes."
        )
        return "\n\n".join(parts)

    parts.append("## Resilience Analysis — Review Required\n")

    # Process structure
    if process_struct.uses_mpi:
        parts.append(
            f"**Process structure:** MPI application "
            f"(rank variable: `{process_struct.rank_variable}`, "
            f"size variable: `{process_struct.size_variable}`, "
            f"communicator: `{process_struct.communicator}`)."
        )
    elif process_struct.uses_openmp:
        parts.append("**Process structure:** OpenMP multi-threaded application.")
    else:
        parts.append("**Process structure:** Serial application.")

    # Critical state candidates
    if candidates:
        parts.append("\n**Candidate critical state (review and confirm):**\n")
        for c in candidates:
            parts.append(
                f"- `{c.name}` ({c.type_str}): {c.rationale} "
                f"[confidence: {c.confidence:.0%}]"
            )
        parts.append(
            "\nPlease review these candidates. Confirm which variables truly need "
            "checkpoint protection. Consider: would losing this data on a process "
            "failure require restarting the entire computation from scratch?"
        )
    else:
        parts.append(
            "\nNo critical state candidates detected by static analysis. "
            "Review the code manually to identify state that would be lost on failure."
        )

    # Checkpoint boundaries
    main_loops = [l for l in loops if l.contains_mpi_calls or l.contains_expensive_ops]
    if main_loops:
        parts.append("\n**Checkpoint boundary candidates:**\n")
        for l in main_loops:
            parts.append(
                f"- `for ({l.iterator_var} = {l.start_expr}; ... < {l.end_expr}; ...)` "
                f"at line {l.location.line_number} "
                f"({'contains MPI calls' if l.contains_mpi_calls else 'contains expensive ops'})"
            )
        parts.append(
            "\nPlace checkpoint calls at the end of the loop body, after all "
            "computation and communication for that iteration is complete."
        )

    # Next step
    parts.append(
        "\n**Next step:** After confirming the critical state and checkpoint location, "
        "call `get_checkpoint_plan` with your confirmed state to get VeloC code templates."
    )

    return "\n".join(parts)
