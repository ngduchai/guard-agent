"""
LangGraph workflow for injecting VeloC-based resilient code.

Workflow (from diagram):
  0. Copy source to given workspace (ensure_directory + copy_tree); discover C/C++ sources; all edits happen in workspace.
  1. Identify data to save between failures and inject VeloC (using only discovered file paths from step 0).
  2. Add header and CMake files for compilation → Complete.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Literal, TypedDict
import os

from langgraph.graph import StateGraph, END

from agents.deploy.config import get_settings
from agents.deploy.llm import _tools_context, _veloc_guide_context
from agents.deploy.mcp_client import call_tool


# Step names as in the workflow
STEP_DISCOVER_SOURCES = "discover_sources"
STEP_IDENTIFY_AND_INJECT = "identify_and_inject"  # merged: identify_data + code_injection
STEP_ADD_BUILD = "add_build"
STEP_COMPLETE = "complete"
STEP_CHECK_INPUT = "check_input"

WORKFLOW_ORDER = [
    STEP_DISCOVER_SOURCES,
    STEP_IDENTIFY_AND_INJECT,
    STEP_ADD_BUILD,
]


class AgentState(TypedDict, total=False):
    """State for the VeloC injection workflow."""

    messages: List[Dict[str, str]]
    # Accumulated results per workflow step (for LLM context and final plan)
    workflow_plan: Dict[str, Any]
    # If set, last step reported an error; go to identify_and_fix
    workflow_error: str
    # After identify_and_fix, which step to re-enter (e.g. "identify_and_inject")
    step_to_return_to: str
    # API response fields
    status: str
    assistant_question: str
    plan: Dict[str, Any]
    raw_llm_response: str
    # Debug trace of all LLM interactions in this run
    llm_trace: List[Dict[str, str]]
    # Limit iterations to avoid infinite loops
    iteration_count: int


async def _call_llm(prompt: str) -> str:
    """Call configured LLM; return raw content."""
    settings = get_settings()
    debug_env = os.getenv("DEPLOY_AGENT_DEBUG_LLM", "").lower() in {"1", "true", "yes", "on"}
    if debug_env:
        # Stream prompt to stdout so users can watch interaction live (CLI or server logs)
        max_len = 4000
        p_snip = prompt if len(prompt) <= max_len else prompt[:max_len] + "\n...[prompt truncated]..."
        print("\n[LLM Debug] Prompt sent to model:\n")
        print(p_snip)

    if settings.llm_provider == "anthropic":
        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            return json.dumps({"error": "anthropic not installed"})
        if not settings.anthropic_api_key:
            return json.dumps({"error": "ANTHROPIC_API_KEY not set"})
        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        msg = await client.messages.create(
            model=settings.llm_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        content = (msg.content[0].text if msg.content else "") or ""
        if debug_env:
            r_snip = content if len(content) <= max_len else content[:max_len] + "\n...[response truncated]..."
            print("\n[LLM Debug] Model response:\n")
            print(r_snip)
        return content
    try:
        from openai import AsyncOpenAI
    except ImportError:
        return json.dumps({"error": "openai not installed"})
    if not settings.openai_api_key:
        return json.dumps({"error": "OPENAI_API_KEY not set"})
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": prompt}],
    )
    content = (resp.choices[0].message.content or "") if resp.choices else ""
    if debug_env:
        r_snip = content if len(content) <= max_len else content[:max_len] + "\n...[response truncated]..."
        print("\n[LLM Debug] Model response:\n")
        print(r_snip)
    return content


def _extract_json(raw: str) -> str:
    """Strip markdown code fences and return inner JSON string."""
    text = raw.strip()
    if "```" in text:
        start = text.find("```")
        if text[start:].startswith("```json"):
            start += 7
        else:
            start += 3
        end = text.find("```", start)
        if end != -1:
            text = text[start:end]
    return text


def _conversation_and_context(state: AgentState) -> str:
    """Build conversation + VeloC guide + MCP tools for prompts."""
    messages = state.get("messages") or []
    parts = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        parts.append(f"{role.capitalize()}: {content}")
    conv = "\n\n".join(parts) if parts else "User: <no prior messages>"
    tools = _tools_context()
    guide = _veloc_guide_context()
    return f"""Conversation:
{conv}

Available MCP tools (use these in your plan for tool_used / tool_args when proposing concrete steps):
{tools}

VeloC integration guide:
{guide}
"""


def _workflow_diagram_instruction() -> str:
    return """
Workflow you are following (from diagram):
  0. **Prepare workspace (copy + discover)** (MUST run first): Using MCP tools only (no LLM), copy the user's source tree into the given workspace path with ensure_directory + copy_tree, then list all C/C++ sources under the copied directory. The next step receives only these discovered file paths.
  1. **Identify data and inject VeloC**: **Read** code files discovered from step 0, (a) identify all data that must be saved between failures, (b) inject VeloC (VELOC_Init, VELOC_Mem_protect, VELOC_Restart, VELOC_Checkpoint, VELOC_Finalize) by generating **complete new file contents** with the injected code and overwriting the existing files.
  2. Add header and CMake files for compilation → Complete.

**VeloC API vs MCP tools (critical):**
- VELOC_Init, VELOC_Mem_protect, VELOC_Checkpoint, VELOC_Restart, VELOC_Finalize are **C library functions** provided by the VeloC library. They are **NOT** MCP tools. You must **inject them as source code** into the user's .c/.cpp files by generating full updated file contents that include these calls and then writing those files with the MCP tool `write_code_file(path, content, overwrite=True)`. Example: read the original file with `read_code_file`, generate a complete new version that adds `VELOC_Init(MPI_COMM_WORLD, "myapp", "veloc.conf");` after `MPI_Init(&argc, &argv);`, then overwrite the original file path with the full new content.
- The **only** VeloC-related MCP tool is **veloc_configure_checkpoint** (generates a config snippet for veloc.conf). All other VeloC integration is done by emitting **mcp_steps** that use `read_code_file` and `write_code_file` to create or replace the actual C code (including every VELOC_* call).

**Path and filename rules (mandatory):**
- Let `source_root` be the original project path and `workspace_root` be the copied project path (created in step 0 by the prepare workspace step). `workspace_root` must be **exactly** the directory path string the user provided as the workspace/output location (e.g. `examples/resilient_matrix_mul_mpi`); do not invent a different directory name.
- For any **existing file**, you must keep the same relative path and filename: if the original file is `source_root/foo/bar/code.c` then the workspace file is `workspace_root/foo/bar/code.c`. You are **forbidden** to rename existing files (e.g. never change `code.c` to `main.c`) or move them to new directories in this workflow.
- All `path` arguments to `read_code_file` and `write_code_file` must be **relative to PROJECT_ROOT** and must start with `workspace_root` when referring to workspace files. `workspace_root` is a conceptual name; in tool_args you must use the concrete directory string (e.g. `examples/resilient_matrix_mul_mpi/...`), never the literal word `"workspace_root"`.
- Renaming or moving existing source files is not allowed. Do not invent new filenames for existing sources when injecting VeloC; use the exact filenames already present in the copied workspace tree.

**Editing rules (mandatory):**
- **Existing files** (e.g. .c, .cpp, .h already in the workspace): Use `read_code_file(path)` to understand the current content, then generate a **complete new version** of the file that includes all original logic plus injected VeloC logic, and write it with `write_code_file(path, content, overwrite=True)`.
- **New files** (e.g. veloc.conf, a new CMakeLists.txt): Use `write_code_file(path, content)` with the full content (and `overwrite=False` or omitted).
- Do not emit partial text edits or refer to an `apply_text_patch` tool; that tool is not available in this workflow.
"""


# --- Node: check_input -------------------------------------------------------

async def check_input(state: AgentState) -> AgentState:
    """Decide if we have enough info to start the workflow; else ask user."""
    out: AgentState = dict(state)
    out.setdefault("workflow_plan", {})
    out.setdefault("iteration_count", 0)
    out.setdefault("llm_trace", [])

    messages = state.get("messages") or []
    if not messages:
        out["status"] = "ask"
        out["assistant_question"] = (
            "Please describe your application: which code or code path should be made resilient, "
            "target environment (e.g. HPC cluster), and where to put the transformed code (workspace path)."
        )
        return out

    last_user = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
    prompt = f"""You are the first step of a VeloC resilience workflow. Based on the user's message, decide if we have enough information to start, and if so, extract the source_root and workspace_root paths to use later.

{_workflow_diagram_instruction()}

{_conversation_and_context(state)}

If we do NOT have enough information (e.g. missing: code location, workspace path for transformed code, or resilience requirements), respond with JSON:
{{ "status": "ask", "assistant_question": "One clear question asking for ALL missing information." }}

If we DO have enough to start (code path or reference, workspace path, and resilience intent), respond with JSON:
{{ "status": "proceed", "source_root": "relative/path/to/original/code/dir", "workspace_root": "relative/path/to/workspace/dir" }}

Where:
- source_root is the directory containing the original code (e.g. "examples/matrix_mul_mpi").
- workspace_root is the directory where the agent should place the transformed/copy of the code (e.g. "examples/resilient_matrix_mul_mpi" or "build/resilient_matrix_mul_mpi").
Use only paths the user explicitly mentioned or that are simple derivatives (e.g. appending "_resilient"), and keep them relative to the project root.

Output only valid JSON, no markdown fences."""

    raw = await _call_llm(prompt)
    out["raw_llm_response"] = raw
    trace = list(out.get("llm_trace") or [])
    trace.append(
        {
            "step": STEP_CHECK_INPUT,
            "prompt": prompt,
            "response": raw,
        }
    )
    out["llm_trace"] = trace
    text = _extract_json(raw)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        out["status"] = "error"
        out["assistant_question"] = "Could not parse response. Please try again with a clearer description."
        return out

    status = str(data.get("status", "")).lower()
    if status == "ask":
        out["status"] = "ask"
        out["assistant_question"] = str(data.get("assistant_question", "Please provide more details."))
        return out
    if status == "proceed":
        source_root = data.get("source_root")
        workspace_root = data.get("workspace_root")
        plan = out.get("workflow_plan") or {}
        plan["paths"] = {
            "source_root": source_root,
            "workspace_root": workspace_root,
        }
        out["workflow_plan"] = plan
    return out


# --- Step nodes: each runs one workflow step ---------------------------------

def _build_step_prompt(step_name: str, step_instruction: str, state: AgentState) -> str:
    """Build prompt for a single workflow step."""
    plan = state.get("workflow_plan") or {}
    plan_summary = json.dumps(plan, indent=2) if plan else "No prior steps yet."
    wrong_steps = "|".join(WORKFLOW_ORDER)
    return f"""You are inside a VeloC resilience workflow. Current step: **{step_name}**.

{_workflow_diagram_instruction()}

Results from previous steps (use these to be consistent):
{plan_summary}

{_conversation_and_context(state)}

Task for this step:
{step_instruction}

Respond with a single JSON object (no markdown fences). Either:
- Success: {{ "ok": true, "result": {{ ... your detailed result for this step ... }}, "mcp_steps": [ {{ "id": "...", "name": "...", "description": "...", "tool_used": "tool_name", "tool_args": {{}} }} ] }}
  Allowed tool_used values are **only**: ensure_directory, copy_tree, read_code_file, write_code_file, veloc_configure_checkpoint, delete_path, list_project_files. There is NO tool named VELOC_Mem_protect or VELOC_Mem_protect—VELOC_Mem_protect is a C function; inject it by generating updated C source code and writing it with write_code_file (full-file overwrite). For existing source files, you must always emit write_code_file(path, content, overwrite=True) with the **complete new file content** (do not emit partial patches). All 'path' or 'root' arguments must either equal the concrete workspace_root string (e.g. 'examples/resilient_matrix_mul_mpi') or be inside it (e.g. 'examples/resilient_matrix_mul_mpi/...'); never use the literal word 'workspace_root' in tool_args. For existing files you must keep the same relative filename as in the original project (e.g. if it was 'code.c' it must remain 'code.c'). Renaming existing files (such as 'code.c' → 'main.c') is forbidden in this workflow. Do not invent new filenames for existing code. Include tool_args.
- Problem: {{ "ok": false, "error": "What is wrong", "wrong_step": "{wrong_steps}" }} to trigger a fix and re-run from that step."""


def _extract_tool_result_text(result: dict) -> str:
    """Get the main text from an MCP tool result (content[].text or structuredContent.result)."""
    if not isinstance(result, dict):
        return ""
    for part in result.get("content", []):
        if isinstance(part, dict) and part.get("type") == "text":
            t = part.get("text")
            if isinstance(t, str):
                return t.strip()
    sc = result.get("structuredContent")
    if isinstance(sc, dict):
        r = sc.get("result")
        if isinstance(r, str):
            return r.strip()
    return ""


async def run_discover_sources(state: AgentState) -> AgentState:
    """
    Discover real source files in the copied workspace using MCP, without any LLM calls.

    This step:
      - Executes the copy_source MCP steps (ensure_directory, copy_tree) so the workspace exists.
      - Calls list_project_files on workspace_root to enumerate actual .c/.cpp files.
      - If the directory is missing or listing fails, sets workflow_error and returns.
      - Chooses candidate_sources heuristically from the discovered files.
    """
    out: AgentState = dict(state)
    out.setdefault("workflow_plan", {})
    plan = dict(out["workflow_plan"])

    paths = plan.get("paths") or {}
    workspace_root = paths.get("workspace_root")
    source_root = paths.get("source_root")

    if not workspace_root or not source_root:
        out["workflow_error"] = (
            "discover_sources: workspace_root/source_root missing from input. "
            "Ensure your prompt clearly specifies both the original code directory and the workspace/output directory."
        )
        out["workflow_plan"] = plan
        out["step_to_return_to"] = STEP_DISCOVER_SOURCES
        return out

    # Prepare workspace: ensure destination exists and copy sources into it.
    try:
        r1 = call_tool("ensure_directory", {"path": workspace_root})
        msg1 = _extract_tool_result_text(r1)
        if "error" in (msg1 or "").lower():
            out["workflow_error"] = f"discover_sources: ensure_directory failed: {msg1}"
            out["workflow_plan"] = plan
            out["step_to_return_to"] = STEP_DISCOVER_SOURCES
            return out
        r2 = call_tool(
            "copy_tree",
            {
                "source_root": source_root,
                "target_root": workspace_root,
                "pattern": "**/*",
                "overwrite": True,
                "max_files": 1000,
            },
        )
        msg2 = _extract_tool_result_text(r2)
        if "no such" in (msg2 or "").lower() or "not found" in (msg2 or "").lower():
            out["workflow_error"] = f"discover_sources: copy_tree failed: {msg2}"
            out["workflow_plan"] = plan
            out["step_to_return_to"] = STEP_DISCOVER_SOURCES
            return out
    except Exception as e:  # noqa: BLE001
        out["workflow_error"] = f"discover_sources: MCP prepare workspace failed: {e}"
        out["workflow_plan"] = plan
        out["step_to_return_to"] = STEP_DISCOVER_SOURCES
        return out

    discovered: List[str] = []
    list_error: str = ""

    def _list(pattern: str, max_files: int = 200) -> bool:
        """Return False if response indicates missing dir or error so caller can abort."""
        nonlocal list_error
        result = call_tool(
            "list_project_files",
            {"root": workspace_root, "pattern": pattern, "max_files": max_files},
        )
        if not isinstance(result, dict):
            return True
        text = _extract_tool_result_text(result)
        if not text:
            return True
        if "no such directory" in text.lower() or "not found" in text.lower():
            list_error = text
            return False
        for line in text.splitlines():
            line = line.strip()
            if not line or line.lower().startswith("no files"):
                continue
            if line not in discovered:
                discovered.append(line)
        return True


    def _is_code_file(filename: str) -> bool:
        return filename.endswith(".c") or filename.endswith(".cpp") or filename.endswith(".h") \
            or filename.endswith(".hpp") or filename.endswith(".cu") or filename.endswith(".cuh") \
            or filename.endswith(".cov") or filename.endswith(".cxx") or filename.endswith(".cc")
    
    
    if not _list("**/*.c"):
        out["workflow_error"] = (
            f"discover_sources: workspace directory not found or not created yet: {list_error}. "
            "Check that the workspace_root path is correct and that the project contains C sources."
        )
        out["workflow_plan"] = plan
        out["step_to_return_to"] = STEP_DISCOVER_SOURCES
        return out
    if not _list("**/*.cpp"):
        out["workflow_error"] = f"discover_sources: workspace directory not found: {list_error}."
        out["workflow_plan"] = plan
        out["step_to_return_to"] = STEP_DISCOVER_SOURCES
        return out

    if not discovered:
        out["workflow_error"] = (
            f"discover_sources: no C/C++ files found under {workspace_root}. "
            "Check that the original source_root contains .c/.cpp files and that it was copied correctly."
        )
        out["workflow_plan"] = plan
        out["step_to_return_to"] = STEP_DISCOVER_SOURCES
        return out

    # Heuristic selection of candidate sources: prefer obvious drivers.
    candidates: List[str] = []
    for f in discovered:
        name = f.split("/")[-1]
        lower = name.lower()
        if _is_code_file(name):
            candidates.append(f)
    if not candidates:
        candidates = list(discovered)

    step_result = {
        "workspace_root": workspace_root,
        "source_root": source_root,
        "discovered_files": discovered,
        "candidate_sources": candidates,
    }
    plan[STEP_DISCOVER_SOURCES] = step_result
    out["workflow_plan"] = plan
    out["workflow_error"] = ""
    return out


async def run_identify_and_inject(state: AgentState) -> AgentState:
    """
    Merged step: use paths from discover_sources only. Identify data to checkpoint, then inject
    VeloC (include, init, register, restart, checkpoint, finalize) into those files.
    """
    plan = state.get("workflow_plan") or {}
    discover = plan.get(STEP_DISCOVER_SOURCES) or {}
    paths = plan.get("paths") or {}
    workspace_root = discover.get("workspace_root") or paths.get("workspace_root") or ""
    candidate_sources = discover.get("candidate_sources") or []
    discovered_files = discover.get("discovered_files") or []

    if not candidate_sources and not discovered_files:
        out: AgentState = dict(state)
        out.setdefault("workflow_plan", {})
        out["workflow_error"] = (
            "identify_and_inject: no discovered or candidate source files from discover_sources step. "
            "Re-run the workflow so discover_sources populates candidate_sources."
        )
        out["step_to_return_to"] = STEP_DISCOVER_SOURCES
        return out

    files_list = candidate_sources if candidate_sources else discovered_files
    files_block = "\n".join(f"  - {f}" for f in files_list)
    workspace_block = f"**workspace_root (use this exact path in all tool_args for paths under the workspace):** `{workspace_root}`"

    # Pre-load the actual contents of each discovered source file via MCP so the LLM
    # never has to guess the code structure. These contents are stored in the plan
    # and included in the step prompt via _build_step_prompt.
    inputs_snapshot: Dict[str, Any] = {
        "workspace_root": workspace_root,
        "files": [],
    }
    for path in files_list:
        try:
            result = call_tool("read_code_file", {"path": path, "max_bytes": 20000})
            content = _extract_tool_result_text(result) or str(result)
        except Exception as exc:  # noqa: BLE001
            content = f"<error reading {path}: {exc}>"
        inputs_snapshot["files"].append(
            {
                "path": path,
                "content": content,
            }
        )

    # Persist inputs into workflow_plan so they appear in the context JSON for this step.
    out_plan = dict(plan)
    out_plan["identify_and_inject_inputs"] = inputs_snapshot

    # Instruction for STEP_IDENTIFY_AND_INJECT, with explicit MCP usage and VeloC algorithm guidance.
    instruction = (
        "You are in STEP_IDENTIFY_AND_INJECT of the VeloC workflow.\n"
        "\n"
        "Inputs for this step are **only** the code file paths and workspace_root provided by discover_sources (listed below). "
        "Do **not** invent or assume any other filenames or paths.\n"
        "\n"
        "**MANDATORY – list of files discovered in the workspace (use ONLY these paths in MCP tool calls):**\n"
        f"{files_block}\n"
        f"\n{workspace_block}\n"
        "\n"
        "You also have the current contents of each discovered file under "
        "workflow_plan['identify_and_inject_inputs']['files']; base all injected code strictly on those contents "
        "(do not guess or invent missing functions or loops).\n"
        "\n"
        "=== VeloC C/C++ injection algorithm (from the guide) ===\n"
        "For each selected C/C++ source file, inject VeloC function calls according to the following guide:\n"
        "**VeloC integration guide (for this task)**\n"
        f"{_veloc_guide_context()}\n"
        "NOTE: End of the injection guide.\n"
        "** POST INJECTION REQUIREMENTS **\n"
        "After understanding the original file via `read_code_file`, generate a **complete new version** of the file that:\n"
        "  - Preserves all original logic and structure (except for the added VeloC calls and minimal control-flow needed for restart).\n"
        "  - Adds all required VeloC includes and calls in the correct places as described above.\n"
        "\n"
        "Then, for each modified file, emit an MCP step `write_code_file` with arguments:\n"
        "  { \"path\": \"<same path as in the discovered list>\", \"content\": \"<full new file body>\", \"overwrite\": true }\n"
        "so the updated file replaces the original.\n"
        "\n"
        "If a given file does not contain a suitable `main`/entry point, MPI_Init/Finalize, or time-stepping loop, explain this "
        "in the result and skip injecting VeloC into that file instead of inventing new functions or loops.\n"
        "\n"
        "In your response:\n"
        "  - Set 'result' to a short summary of which files were modified, which variables/buffers were treated as persistent state, "
        "    and where VELOC_Init / VELOC_Mem_protect / VELOC_Restart / VELOC_Checkpoint / VELOC_Finalize were inserted.\n"
        "  - Set 'mcp_steps' to an ordered list of concrete MCP tool calls that you want executed. For each modified file this "
        "    should include at least one `read_code_file` and one `write_code_file(path, content, overwrite=True)`, using ONLY "
        "    the file paths listed above."
    )
    # For this step, we want the MCP-backed tool calls (read_code_file, write_code_file, etc.)
    # to be executed immediately as part of the workflow, not deferred until the final plan.
    # We also pass the enriched plan (with pre-read file contents) into the downstream prompt.
    next_state = dict(state)
    next_state.setdefault("workflow_plan", {})
    next_state["workflow_plan"] = out_plan
    return await _run_workflow_step(next_state, STEP_IDENTIFY_AND_INJECT, instruction, execute_mcp=True)


async def run_add_build(state: AgentState) -> AgentState:
    instruction = (
        "Add or update header includes and CMake/Makefile so the resilient code compiles. For **existing** source and "
        "build files, first use read_code_file(path) to understand the current content, then generate a complete new "
        "version of each file with the necessary VeloC includes and link flags, and write it using "
        "write_code_file(path, content, overwrite=True). Do not emit partial text patches or use apply_text_patch; "
        "always overwrite with the full updated file content. Use write_code_file without overwrite (or with a new path) "
        "for creating entirely new files (e.g. a new CMakeLists.txt in the workspace)."
    )
    # Build-related edits should also be applied immediately via MCP tools.
    return await _run_workflow_step(state, STEP_ADD_BUILD, instruction, execute_mcp=True)


async def run_recheck(state: AgentState) -> AgentState:
    instruction = (
        "Recheck the planned changes: verify that the code will compile, VeloC calls are correctly ordered, "
        "and there is no semantic difference between failure-free and failure-prone runs. If anything is wrong, set ok: false and wrong_step."
    )
    return await _run_workflow_step(state, STEP_RECHECK, instruction)


async def _run_workflow_step(
    state: AgentState,
    step_name: str,
    step_instruction: str,
    execute_mcp: bool = False,
) -> AgentState:
    """Generic runner for one workflow step: call LLM, optionally execute MCP tools, update state."""
    out: AgentState = dict(state)
    out.setdefault("workflow_plan", {})
    out.setdefault("llm_trace", [])
    plan = dict(out["workflow_plan"])

    prompt = _build_step_prompt(step_name, step_instruction, state)
    raw = await _call_llm(prompt)
    out["raw_llm_response"] = raw
    trace = list(out.get("llm_trace") or [])
    trace.append(
        {
            "step": step_name,
            "prompt": prompt,
            "response": raw,
        }
    )
    out["llm_trace"] = trace
    text = _extract_json(raw)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        out["workflow_error"] = f"Step {step_name}: could not parse LLM output as JSON."
        out["workflow_plan"] = plan
        return out

    if data.get("ok") is True:
        step_result = data.get("result") or {}
        mcp_steps = data.get("mcp_steps") or []
        step_mcp: List[Dict[str, Any]] = []
        mcp_results: List[Dict[str, Any]] = []
        for i, s in enumerate(mcp_steps):
            if not isinstance(s, dict):
                continue
            entry = {
                "id": s.get("id") or f"{step_name}_{i}",
                "name": s.get("name") or step_name,
                "description": s.get("description", ""),
                "tool_used": s.get("tool_used"),
                "tool_args": s.get("tool_args") or {},
                "order": i,
            }
            step_mcp.append(entry)
            if execute_mcp:
                tool_name = entry.get("tool_used")
                args = entry.get("tool_args") or {}
                if not tool_name:
                    continue
                try:
                    result_obj = call_tool(tool_name, args)
                except Exception as exc:  # noqa: BLE001
                    out["workflow_error"] = f"Step {step_name}: MCP tool '{tool_name}' failed: {exc}"
                    plan[step_name] = step_result
                    out["workflow_plan"] = plan
                    return out
                mcp_results.append(
                    {
                        "id": entry["id"],
                        "tool_used": tool_name,
                        "tool_args": args,
                        "result": result_obj,
                    }
                )
        step_result["_mcp_steps"] = step_mcp
        if execute_mcp:
            step_result["_mcp_results"] = mcp_results
        plan[step_name] = step_result
        out["workflow_plan"] = plan
        out["workflow_error"] = ""
        return out

    # LLM reported a problem
    out["workflow_error"] = str(data.get("error", "Unknown error"))
    out["workflow_plan"] = plan
    wrong = (data.get("wrong_step") or "").strip().lower()
    if wrong in WORKFLOW_ORDER:
        out["step_to_return_to"] = wrong
    else:
        out["step_to_return_to"] = STEP_DISCOVER_SOURCES
    return out


# --- complete -----------------------------------------------------------------

async def run_complete(state: AgentState) -> AgentState:
    """Build final deployment plan (summary + steps) for the API."""
    out: AgentState = dict(state)
    plan = state.get("workflow_plan") or {}

    # Build summary from workflow step results
    parts = []
    for step in WORKFLOW_ORDER:
        if step in plan and isinstance(plan[step], dict):
            val = plan[step]
            snippet = json.dumps(val)[:200] if isinstance(val, dict) else str(val)[:200]
            parts.append(f"**{step}**: {snippet}...")
        elif step in plan:
            parts.append(f"**{step}**: {str(plan[step])[:200]}")
    summary = "VeloC resilience workflow completed.\n\n" + "\n\n".join(parts) if parts else "Resilience plan ready."

    # Collect MCP steps from each workflow step in order
    steps = []
    order = 0
    for step in WORKFLOW_ORDER:
        step_result = plan.get(step)
        if not isinstance(step_result, dict):
            continue
        for s in step_result.get("_mcp_steps") or []:
            if isinstance(s, dict):
                steps.append({
                    "id": s.get("id") or f"step{order}",
                    "name": s.get("name", ""),
                    "description": s.get("description", ""),
                    "tool_used": s.get("tool_used"),
                    "tool_args": s.get("tool_args") or {},
                    "order": order,
                })
                order += 1
    steps.sort(key=lambda x: x.get("order", 0))

    out["status"] = "plan"
    out["plan"] = {
        "summary": summary,
        "steps": steps,
        "transformed_code": plan.get(STEP_IDENTIFY_AND_INJECT, {}).get("snippet") if isinstance(plan.get(STEP_IDENTIFY_AND_INJECT), dict) else None,
    }
    return out


# --- Routing ------------------------------------------------------------------

def route_after_check_input(state: AgentState) -> Literal["ask", "discover_sources"]:
    if state.get("status") == "ask":
        return "ask"
    return "discover_sources"


def route_after_step(
    state: AgentState,
) -> Literal[
    "discover_sources",
    "identify_and_inject",
    "add_build",
    "complete",
]:
    """From a step node: either advance to the next step or finish."""
    if state.get("workflow_error"):
        return "complete"
    plan = state.get("workflow_plan") or {}
    if STEP_ADD_BUILD in plan:
        return "complete"
    if STEP_IDENTIFY_AND_INJECT in plan:
        return "add_build"
    if STEP_DISCOVER_SOURCES in plan:
        return "identify_and_inject"
    return "identify_and_inject"


def route_ask_end(_state: AgentState) -> Literal["__end__"]:
    return "__end__"


# --- Graph build --------------------------------------------------------------

def build_agent_graph():
    """Build the VeloC injection workflow graph with error-correction loop."""
    workflow = StateGraph(AgentState)

    workflow.add_node(STEP_CHECK_INPUT, check_input)
    workflow.add_node(STEP_DISCOVER_SOURCES, run_discover_sources)
    workflow.add_node(STEP_IDENTIFY_AND_INJECT, run_identify_and_inject)
    workflow.add_node(STEP_ADD_BUILD, run_add_build)
    workflow.add_node(STEP_COMPLETE, run_complete)

    workflow.set_entry_point(STEP_CHECK_INPUT)

    # check_input → ask (END) or discover_sources
    workflow.add_conditional_edges(STEP_CHECK_INPUT, route_after_check_input, {
        "ask": END,
        "discover_sources": STEP_DISCOVER_SOURCES,
    })

    # discover_sources → identify_and_inject
    workflow.add_conditional_edges(STEP_DISCOVER_SOURCES, route_after_step, {
        "discover_sources": STEP_DISCOVER_SOURCES,
        "identify_and_inject": STEP_IDENTIFY_AND_INJECT,
        "add_build": STEP_ADD_BUILD,
        "complete": STEP_COMPLETE,
    })

    workflow.add_conditional_edges(STEP_IDENTIFY_AND_INJECT, route_after_step, {
        "discover_sources": STEP_DISCOVER_SOURCES,
        "identify_and_inject": STEP_IDENTIFY_AND_INJECT,
        "add_build": STEP_ADD_BUILD,
        "complete": STEP_COMPLETE,
    })
    workflow.add_conditional_edges(STEP_ADD_BUILD, route_after_step, {
        "discover_sources": STEP_DISCOVER_SOURCES,
        "identify_and_inject": STEP_IDENTIFY_AND_INJECT,
        "add_build": STEP_ADD_BUILD,
        "complete": STEP_COMPLETE,
    })

    workflow.add_edge(STEP_COMPLETE, END)

    return workflow.compile()
