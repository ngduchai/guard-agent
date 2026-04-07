"""MCP server for guard-agent — exposes resilience workflow tools.

Provides tools for coding agents (Claude Code, OpenCode) to:
  1. Inspect code and identify critical state  (inspect_codebase)
  2. Generate checkpoint injection plans       (get_checkpoint_plan)
  3. Access VeloC API documentation            (get_veloc_reference)
  4. Validate checkpoint injection             (validate_injection)
  5. Read project resilience config            (get_resilience_config)
  6. Run full autonomous VeloC agent           (run_veloc_agent)

Also provides a prompt template that instructs the coding agent
to perform resilience checks after modifying C/C++ code.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from guard_agent.analyzer import analyze_project, quick_check
from guard_agent.guide import get_guide_json, list_sections, get_section, load_full_guide
from guard_agent.planner import generate_checkpoint_plan
from guard_agent.project_config import find_config, load_config
from guard_agent.validator import validate_injection as _validate_injection

mcp = FastMCP("guard-agent")


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
    return inspection.model_dump_json(indent=2)


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
    return plan.model_dump_json(indent=2)


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
    return get_guide_json(
        section=section or "",
        list_sections_flag=list_sections_flag,
    )


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
    timeout: int = 300,
    veloc_cfg_path: str | None = None,
) -> str:
    """Validate checkpoint injection by building, running with failure, and comparing.

    This is step (5) of the resilience workflow. Builds the code, runs a
    baseline, then runs with a simulated process failure (kill + restart),
    and compares outputs.

    If validation fails, the result includes error analysis and suggestions.
    Review them, fix the code, and retry from step (1).

    Args:
        project_dir: Path to the project directory.
        build_cmd: Build command (e.g., "cmake --build build").
        run_cmd: Run command (e.g., "mpirun -np 4 ./build/app").
        num_procs: Number of MPI processes.
        comparison_method: Output comparison: "hash", "text", or "numeric".
        output_file: Output file to compare (if None, compares stdout).
        timeout: Maximum seconds for each run.
        veloc_cfg_path: Path to veloc.cfg (for cleaning checkpoint dirs).
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
    return result.model_dump_json(indent=2)


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


# ---------------------------------------------------------------------------
# Tool 6: run_veloc_agent — Full autonomous agent mode
# ---------------------------------------------------------------------------

@mcp.tool()
def run_veloc_agent(
    project_dir: str,
    prompt: str,
    llm_provider: str | None = None,
    llm_model: str | None = None,
) -> str:
    """Run the full VeloC agent autonomously (requires LLM API key).

    This runs the complete 8-step VeloC agent workflow with its own LLM:
    explore → identify state → consult guide → inject → validate → report.

    Use this when you want the guard-agent to handle everything autonomously
    instead of following the step-by-step workflow.

    Requires LLM_PROVIDER and corresponding API key in environment.

    Args:
        project_dir: Path to the project containing the code to protect.
        prompt: Description of what needs resilience (e.g., "Make this MPI
                simulation resilient with VeloC checkpointing every 5 minutes").
        llm_provider: Optional LLM provider override (openai, argo, generic).
        llm_model: Optional model name override.
    """
    import asyncio
    import os

    # Set environment overrides if provided
    if llm_provider:
        os.environ["LLM_PROVIDER"] = llm_provider
    if llm_model:
        os.environ["LLM_MODEL"] = llm_model
    os.environ["GUARD_AGENT_PROJECT_ROOT"] = project_dir

    try:
        from agents.veloc.agent import run_veloc_agent as _run_agent
        messages = [{"role": "user", "content": prompt}]
        result = asyncio.run(_run_agent(messages))
        return json.dumps(result, default=str, indent=2)
    except ImportError:
        return json.dumps({
            "status": "error",
            "error_message": (
                "Full agent mode requires the agents.veloc package. "
                "Ensure the guard-agent project is properly installed."
            ),
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error_message": str(e),
        })


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

When you modify any C/C++ source file, perform a resilience check before \
completing your task:

1. **Inspect**: Call `inspect_codebase` with the modified file paths.
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
   builds the code, runs with a simulated failure, and compares outputs.

6. **Fix if needed**: If validation fails, review the error analysis and \
   suggestions. Fix the code and retry from step 1.

Important:
- Do NOT change existing command-line arguments — only add optional --veloc-cfg
- Place checkpoint calls AFTER all computation for that iteration
- The checkpoint version number must increase with each call (use loop iterator)
- Use `get_veloc_reference` to look up correct API signatures when needed
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
