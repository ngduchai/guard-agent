"""MCP server for guard-agent — exposes resilience workflow tools.

Provides tools for coding agents (Claude Code, OpenCode) to:
  1. Inspect code and identify critical state  (inspect_codebase)
  2. Generate checkpoint injection plans       (get_checkpoint_plan)
  3. Access VeloC API documentation            (get_veloc_reference)
  4. Validate checkpoint injection             (validate_injection)
  5. Read project resilience config            (get_resilience_config)

Validation enforcement: every tool output includes a mandatory next-step
reminder. The final step always requires calling validate_injection.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from guard_agent.analyzer import analyze_project
from guard_agent.guide import get_guide_json
from guard_agent.planner import generate_checkpoint_plan
from guard_agent.project_config import load_config
from guard_agent.validator import validate_injection as _validate_injection

mcp = FastMCP("guard-agent")


# ---------------------------------------------------------------------------
# Validation enforcement — appended to every tool response
# ---------------------------------------------------------------------------

_VALIDATE_REMINDER = (
    "\n\n---\n"
    "MANDATORY: After applying code changes, you MUST call `validate_injection` "
    "to verify correctness. Build the code, run with small input (timeout 60-120s), "
    "and pass veloc.cfg path. If it fails, fix and retry. "
    "The task is NOT complete until validate_injection returns passed=true.\n"
    "veloc.cfg paths: use scratch=/tmp/scratch and persistent=/tmp/persistent "
    "unless the user specifies otherwise."
)


# ---------------------------------------------------------------------------
# Tool 1: inspect_codebase — Step (1) of the workflow
# ---------------------------------------------------------------------------

@mcp.tool()
def inspect_codebase(
    file_paths: list[str],
    config_path: str | None = None,
    config_overrides: dict | None = None,
) -> str:
    """Inspect C/C++ source files to identify critical state and checkpoint needs.

    This is step (1) of the resilience workflow. Analyzes the code to detect:
    - Heap allocations and data structures (critical state candidates)
    - MPI/OpenMP patterns (process/thread structure)
    - Computation loops (checkpoint boundary candidates)
    - Existing VeloC instrumentation

    Returns a structured analysis with candidate critical state and a guided
    prompt for you to review and confirm what needs protection.

    After reviewing, call get_checkpoint_plan with your confirmed state.

    Args:
        file_paths: Source file or directory paths to analyze.
        config_path: Optional path to .guard-agent.yaml.
        config_overrides: Optional dict to override config values.
    """
    config = load_config(path=config_path, overrides=config_overrides)
    inspection = analyze_project(file_paths, config)
    result = inspection.model_dump_json(indent=2)
    return result + _VALIDATE_REMINDER


# ---------------------------------------------------------------------------
# Tool 2: get_checkpoint_plan — Step (3) of the workflow
# ---------------------------------------------------------------------------

@mcp.tool()
def get_checkpoint_plan(
    critical_state: list[dict[str, Any]],
    file_paths: list[str],
    config_path: str | None = None,
    config_overrides: dict | None = None,
) -> str:
    """Generate a VeloC checkpoint injection plan with code templates.

    This is step (3) of the resilience workflow. Call this AFTER reviewing
    the inspection results and confirming which variables need protection.

    Returns exact code templates for VeloC init, mem_protect, checkpoint,
    restart, finalize, plus veloc.cfg content and CMake modifications.

    Apply the returned templates to inject checkpointing into your code.

    Args:
        critical_state: Confirmed critical variables. Each dict should have:
            - name: variable name (e.g., "recon")
            - type: C/C++ type (e.g., "float*")
            - element_type: element type (e.g., "float")
            - count_expr: element count expression (e.g., "recon_size")
            Optional:
            - size_expr: size expression
            - rationale: why this is critical
        file_paths: Source files to base the plan on (re-analyzed for context).
        config_path: Optional path to .guard-agent.yaml.
        config_overrides: Optional dict to override config values.
    """
    config = load_config(path=config_path, overrides=config_overrides)
    inspection = analyze_project(file_paths, config)
    plan = generate_checkpoint_plan(critical_state, inspection, config)
    result = plan.model_dump_json(indent=2)
    return result + _VALIDATE_REMINDER


# ---------------------------------------------------------------------------
# Tool 3: get_veloc_reference — VeloC API documentation
# ---------------------------------------------------------------------------

@mcp.tool()
def get_veloc_reference(
    section: str | None = None,
    list_sections_flag: bool = False,
) -> str:
    """Return VeloC API documentation.

    Use this to look up correct API signatures, configuration keys,
    and code examples when implementing checkpoint injection.

    Args:
        section: Specific section heading to retrieve (e.g., "C API Reference",
                 "C++ API Reference", "Configuration File Reference",
                 "Complete Code Examples", "Best Practices").
        list_sections_flag: If true, return only the list of available sections.
    """
    result = get_guide_json(
        section=section or "",
        list_sections_flag=list_sections_flag,
    )
    return result + _VALIDATE_REMINDER


# ---------------------------------------------------------------------------
# Tool 4: validate_injection — Step (5) of the workflow
# ---------------------------------------------------------------------------

@mcp.tool()
def validate_injection(
    project_dir: str,
    build_cmd: str,
    run_cmd: str,
    num_procs: int = 2,
    comparison_method: str = "hash",
    output_file: str | None = None,
    timeout: int = 120,
    veloc_cfg_path: str | None = None,
) -> str:
    """Validate checkpoint injection by building, running with failure, and comparing.

    Builds the code, runs a baseline, then simulates a process failure
    (kill + restart), and compares outputs to verify correctness.

    IMPORTANT timeout guidance:
    - Start with a SHORT timeout (60-120s). If it times out, reduce
      the problem size in run_cmd args (fewer iterations, smaller input)
      so the test completes within the timeout.
    - A small, fast test that passes is better than a large test that
      times out. The goal is to verify checkpoint/restart correctness,
      not run a full-scale simulation.

    Args:
        project_dir: Path to the project directory.
        build_cmd: Build command (e.g., "mkdir -p build && cd build && cmake .. && make").
        run_cmd: Run command with SMALL input for fast testing
                 (e.g., "mpirun -np 2 ./build/app <small_args>").
        num_procs: Number of MPI processes.
        comparison_method: Output comparison: "hash", "text", or "numeric".
        output_file: Output file to compare (if None, compares stdout).
        timeout: Maximum seconds for EACH run step (build, baseline, restart).
                 Keep this short (60-120s). If a step times out, the result
                 will say so — reduce the problem size and retry.
        veloc_cfg_path: Path to veloc.cfg (for cleaning checkpoint dirs between runs).
                 veloc.cfg should use scratch=/tmp/scratch and persistent=/tmp/persistent
                 unless the user specifies otherwise.
    """
    result = _validate_injection(
        project_dir=project_dir,
        build_cmd=build_cmd,
        run_cmd=run_cmd,
        num_procs=num_procs,
        comparison_method=comparison_method,
        output_file=output_file,
        timeout=timeout,
        veloc_cfg_path=veloc_cfg_path,
    )
    output = result.model_dump_json(indent=2)
    if not result.passed:
        output += (
            "\n\n---\n"
            "VALIDATION FAILED. You MUST fix the code and call validate_injection again. "
            "Read the error_analysis and suggestions above. Common issues:\n"
            "- Build errors: check CMakeLists.txt links veloc-client, #include <veloc.h>\n"
            "- Runtime crash: check VELOC_Mem_protect args (pointer, count, sizeof)\n"
            "- Restart failure: ensure VELOC_Restart_test + VELOC_Restart before main loop\n"
            "- Output mismatch: ensure checkpoint captures ALL critical state\n"
            "- Timeout: reduce problem size in run_cmd args\n"
            "Fix the issues and call validate_injection again."
        )
    return output


# ---------------------------------------------------------------------------
# Tool 5: get_resilience_config — Project configuration
# ---------------------------------------------------------------------------

@mcp.tool()
def get_resilience_config(
    config_path: str | None = None,
) -> str:
    """Return the project's resilience configuration from .guard-agent.yaml.

    Returns parsed config with all defaults applied. If no config file is
    found, returns default configuration values.

    Args:
        config_path: Optional explicit path to .guard-agent.yaml.
    """
    config = load_config(path=config_path)
    return config.model_dump_json(indent=2)


# NOTE: run_veloc_agent is NOT exposed as an MCP tool because it runs a full
# LLM agent loop that exceeds MCP request timeouts. Use the CLI instead:
#   guard-agent run <project_dir>


# ---------------------------------------------------------------------------
# MCP Prompt: resilience_check workflow
# ---------------------------------------------------------------------------

@mcp.prompt()
def resilience_check() -> str:
    """Resilience check workflow for coding agents.

    Load this prompt to enable automatic VeloC checkpointing after C/C++ edits.
    """
    return """\
## Guard-Agent Resilience Check Workflow

When you need to make C/C++ code resilient with VeloC checkpointing:

1. **Inspect**: Call `inspect_codebase` with the source file paths.
   Review the returned analysis — it identifies candidate critical state \
   (variables that would be lost on process failure) and computation loops \
   (checkpoint boundary candidates).

2. **Confirm**: Review the critical state candidates. Determine which \
   variables truly need checkpoint protection. Ask yourself: "If this \
   process crashes, would losing this data require restarting the entire \
   computation?"

3. **Plan**: Call `get_checkpoint_plan` with your confirmed critical state. \
   This returns exact VeloC code templates — init, memory protection, \
   checkpoint calls, restart logic, finalize, veloc.cfg, and CMake changes.

4. **Inject**: Apply the returned code templates to inject VeloC \
   checkpointing. Follow the placement instructions carefully.

5. **Validate**: Call `validate_injection` to verify correctness. This \
   builds the code, runs a baseline, simulates a process failure \
   (kill + restart), and compares outputs.
   - Use a SHORT timeout (60-120s) and SMALL input so the test finishes fast.
   - If it times out, reduce the problem size in run_cmd and retry.
   - If validation fails, read the error analysis and fix the code.

Important:
- Do NOT change existing command-line arguments or behavior
- Place checkpoint calls AFTER all computation for that iteration
- The checkpoint version number must increase with each call (use loop iterator)
- Use `get_veloc_reference` to look up correct API signatures when needed
- Use find_package(veloc REQUIRED) and link veloc-client in CMakeLists.txt
- In veloc.cfg, use scratch=/tmp/scratch and persistent=/tmp/persistent unless the user specifies otherwise.
"""


# ---------------------------------------------------------------------------
# MCP Resource: project config
# ---------------------------------------------------------------------------

@mcp.resource("guard-agent://config")
def config_resource() -> str:
    """The project's .guard-agent.yaml configuration."""
    config = load_config()
    return config.model_dump_json(indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_server():
    """Start the MCP server with stdio transport."""
    mcp.run()
