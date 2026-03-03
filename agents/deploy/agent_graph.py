"""
LangGraph workflow for injecting VeloC-based resilient code.

Workflow (from diagram):
  0. Copy source to given workspace (ensure_directory + copy_tree); all edits happen in workspace.
  1. Identify data to save between failures
  2. Register these data with VeloC
  3. Identify places in code for checkpoint/recovery (no difference failure-free vs failure-prone)
  4. Apply VeloC to save and load checkpoint (use apply_text_patch on existing files; write_code_file only for new files or full overwrite)
  5. Add header and CMake files for compilation
  6. Recheck the code to ensure everything works
  7. Complete

From any step 0–6, on error → "Identify which step is wrong, fix it" → re-enter at that step.
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
STEP_IDENTIFY_DATA = "identify_data"
STEP_CODE_INJECTION = "code_injection"
STEP_ADD_BUILD = "add_build"
STEP_RECHECK = "recheck"
STEP_IDENTIFY_AND_FIX = "identify_and_fix"
STEP_COMPLETE = "complete"
STEP_CHECK_INPUT = "check_input"

WORKFLOW_ORDER = [
    STEP_DISCOVER_SOURCES,
    STEP_IDENTIFY_DATA,
    STEP_CODE_INJECTION,
    STEP_ADD_BUILD,
    STEP_RECHECK,
]


class AgentState(TypedDict, total=False):
    """State for the VeloC injection workflow."""

    messages: List[Dict[str, str]]
    # Accumulated results per workflow step (for LLM context and final plan)
    workflow_plan: Dict[str, Any]
    # If set, last step reported an error; go to identify_and_fix
    workflow_error: str
    # After identify_and_fix, which step to re-enter (e.g. "identify_data")
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
  0. **Prepare workspace (copy + discover)** (MUST run first): Using MCP tools only (no LLM), copy the user's source tree into the given workspace path with ensure_directory + copy_tree, then list all C/C++ sources under the copied directory to select appropriate files (e.g. main drivers, MPI codes) so you work with real filenames and contents.
  1. Identify data that needs to be saved between failures.
  2. Plan how to register that data with VeloC (see below: VELOC_Register is C code, not an MCP tool).
  3. Identify places in the code where we can save the registered data to checkpoint and use the saved checkpoint for recovery (ensure there is no difference between failure-free and failure-prone execution).
  4. Apply VeloC to save and load checkpoint (inject C code via apply_text_patch).
  5. Add header and CMake files for compilation.
  6. Recheck the code to ensure everything works → Complete.

If at any step something is wrong, the flow goes to "Identify which step is wrong, fix it" and then re-enters at the appropriate earlier step.

**VeloC API vs MCP tools (critical):**
- VELOC_Init, VELOC_Register, VELOC_Checkpoint, VELOC_Restart, VELOC_Finalize are **C library functions** provided by the VeloC library. They are **NOT** MCP tools. You must **inject them as source code** into the user's .c/.cpp files using **apply_text_patch** (search/replace that inserts the exact C line(s)). Example: search "MPI_Init(&argc, &argv);" replace "MPI_Init(&argc, &argv);\\n  VELOC_Init(MPI_COMM_WORLD, \\"myapp\\", \\"veloc.conf\\");".
- The **only** VeloC-related MCP tool is **veloc_configure_checkpoint** (generates a config snippet for veloc.conf). All other VeloC integration is done by emitting **mcp_steps** that use read_code_file, apply_text_patch, or write_code_file to insert or create the actual C code (including every VELOC_* call).

**Path and filename rules (mandatory):**
- Let `source_root` be the original project path and `workspace_root` be the copied project path (created in step 0 by the prepare workspace step). `workspace_root` must be **exactly** the directory path string the user provided as the workspace/output location (e.g. `examples/resilient_matrix_mul_mpi`); do not invent a different directory name.
- For any **existing file**, you must keep the same relative path and filename: if the original file is `source_root/foo/bar/code.c` then the workspace file is `workspace_root/foo/bar/code.c`. You are **forbidden** to rename existing files (e.g. never change `code.c` to `main.c`) or move them to new directories in this workflow.
- All `path` arguments to read_code_file, apply_text_patch, and write_code_file must be **relative to PROJECT_ROOT** and must start with `workspace_root` when referring to workspace files. `workspace_root` is a conceptual name; in tool_args you must use the concrete directory string (e.g. `examples/resilient_matrix_mul_mpi/...`), never the literal word `"workspace_root"`.
- Renaming or moving existing source files is not allowed. Do not invent new filenames for existing sources when injecting VeloC; use the exact filenames already present in the copied workspace tree.

**Editing rules (mandatory):**
- **Existing files** (e.g. .c, .cpp, .h already in the workspace): Never overwrite with write_code_file. Always use **read_code_file(path)** then **apply_text_patch(path, search, replace)** for each insertion (e.g. add #include <veloc.h>, add VELOC_Init(...), add VELOC_Register(...), add VELOC_Checkpoint(...)). Use one apply_text_patch per logical edit so the original code is preserved.
- **New files** (e.g. veloc.conf, a new CMakeLists.txt): Use **write_code_file(path, content)** with the full content.
- **Full overwrite** of an existing file: Use write_code_file(path, content, overwrite=True) only when you are explicitly replacing the entire file with its complete new content (e.g. you generated the full new file body). Do not use write_code_file to put a single line or partial content into an existing file.
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
  Allowed tool_used values are **only**: ensure_directory, copy_tree, read_code_file, apply_text_patch, write_code_file, veloc_configure_checkpoint, delete_path, list_project_files. There is NO tool named VELOC_Register or veloc_register—VELOC_Register is a C function; inject it by using apply_text_patch with replace string containing the C code. For existing source files use apply_text_patch only; use write_code_file only for new files or full-file overwrite. All 'path' or 'root' arguments must either equal the concrete workspace_root string (e.g. 'examples/resilient_matrix_mul_mpi') or be inside it (e.g. 'examples/resilient_matrix_mul_mpi/...'); never use the literal word 'workspace_root' in tool_args. For existing files you must keep the same relative filename as in the original project (e.g. if it was 'code.c' it must remain 'code.c'). Renaming existing files (such as 'code.c' → 'main.c') is forbidden in this workflow. Do not invent new filenames for existing code. Include tool_args.
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


async def run_identify_data(state: AgentState) -> AgentState:
    instruction = (
        "Identify all application data that must be saved between failures (e.g. main loop index, "
        "arrays, state structs). List variables, their types, and where they are defined or used."
    )
    return await _run_workflow_step(state, STEP_IDENTIFY_DATA, instruction)


async def run_code_injection(state: AgentState) -> AgentState:
    instruction = (
        "Using the data identified in the previous step and the discovered source files, inject complete VeloC "
        "checkpoint/restart logic into the workspace code. Follow this algorithm, using only MCP tools to edit files:\n"
        "\n"
        "1) Inputs and context:\n"
        "   - workflow_plan['paths'] contains 'source_root' and 'workspace_root'.\n"
        "   - workflow_plan['discover_sources'] contains 'candidate_sources' under workspace_root.\n"
        "   - workflow_plan['identify_data'] lists variables that must be saved across failures.\n"
        "\n"
        "2) For each candidate source file under workspace_root:\n"
        "   a) Ensure it is a C/C++ source file; then use read_code_file to inspect it.\n"
        "   b) Locate program entry (main) and MPI_Init / MPI_Finalize, and the main time-stepping loop as described in the guide.\n"
        "\n"
        "3) For each selected file, plan and emit apply_text_patch steps that:\n"
        "   - Add '#include <veloc.h>' at the top (respecting existing includes).\n"
        "   - Insert VELOC_Init(...) after MPI_Init and before heavy work, using veloc.conf.\n"
        "   - Insert VELOC_Register(...) calls after allocation of each persistent buffer identified earlier.\n"
        "   - Insert VELOC_Restart(...) logic near the start of the main loop to restore state and set the loop index appropriately.\n"
        "   - Insert periodic VELOC_Checkpoint(...) inside the main loop conditioned on step modulo the checkpoint interval.\n"
        "   - Insert VELOC_Finalize() before MPI_Finalize.\n"
        "   Each insertion must be implemented as apply_text_patch(path, search, replace) on real workspace_root-relative paths.\n"
        "\n"
        "4) Semantics and safety:\n"
        "   - Preserve the original failure-free behavior; after restart, the program must resume as if it never failed.\n"
        "   - Do not introduce extra MPI calls or control-flow changes beyond what is needed for VeloC.\n"
        "   - Never overwrite whole source files; always use apply_text_patch for existing .c/.cpp/.h files.\n"
        "\n"
        "5) In your 'result', summarize which files were modified, which variables were registered, and how restart and checkpoint "
        "logic were wired. In 'mcp_steps', include the concrete read_code_file and apply_text_patch calls needed to realize these edits."
    )
    return await _run_workflow_step(state, STEP_CODE_INJECTION, instruction)


async def run_add_build(state: AgentState) -> AgentState:
    instruction = (
        "Add or update header includes and CMake/Makefile so the resilient code compiles. For **existing** source "
        "files use apply_text_patch to insert #include <veloc.h> (exact search/replace). For existing CMakeLists.txt "
        "use apply_text_patch to add VeloC include and link. Use write_code_file only for creating a new file (e.g. "
        "a new CMakeLists.txt in the workspace) or full content of a new file."
    )
    return await _run_workflow_step(state, STEP_ADD_BUILD, instruction)


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
) -> AgentState:
    """Generic runner for one workflow step: call LLM, parse, update state."""
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
        step_mcp = []
        for i, s in enumerate(mcp_steps):
            if isinstance(s, dict):
                step_mcp.append({
                    "id": s.get("id") or f"{step_name}_{i}",
                    "name": s.get("name") or step_name,
                    "description": s.get("description", ""),
                    "tool_used": s.get("tool_used"),
                    "tool_args": s.get("tool_args") or {},
                    "order": i,
                })
        step_result["_mcp_steps"] = step_mcp
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


# --- identify_and_fix --------------------------------------------------------

async def run_identify_and_fix(state: AgentState) -> AgentState:
    """Identify which step is wrong and update plan; set step_to_return_to."""
    out: AgentState = dict(state)
    plan = dict(out.get("workflow_plan") or {})
    err = out.get("workflow_error") or "Unknown error"

    prompt = f"""The workflow reported an issue. Identify which step is wrong and how to fix it.

{_workflow_diagram_instruction()}

Current workflow results:
{json.dumps(plan, indent=2)}

Error: {err}

{_conversation_and_context(state)}

Respond with JSON only (no markdown fences):
{{ "wrong_step": "discover_sources"|"identify_data"|"code_injection"|"add_build", "fix_description": "...", "plan_updates": {{ "step_name": {{ ... revised result for that step ... }} }} }}

Use plan_updates to correct the workflow_plan for the step(s) that were wrong."""

    raw = await _call_llm(prompt)
    out["raw_llm_response"] = raw
    trace = list(out.get("llm_trace") or [])
    trace.append(
        {
            "step": STEP_IDENTIFY_AND_FIX,
            "prompt": prompt,
            "response": raw,
        }
    )
    out["llm_trace"] = trace
    text = _extract_json(raw)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        out["step_to_return_to"] = STEP_IDENTIFY_DATA
        out["workflow_error"] = ""
        return out

    wrong = (data.get("wrong_step") or "").strip().lower()
    out["step_to_return_to"] = wrong if wrong in WORKFLOW_ORDER else STEP_DISCOVER_SOURCES
    updates = data.get("plan_updates") or {}
    if isinstance(updates, dict):
        for k, v in updates.items():
            if k in WORKFLOW_ORDER:
                plan[k] = v
    out["workflow_plan"] = plan
    out["workflow_error"] = ""
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
        "transformed_code": plan.get("code_injection", {}).get("snippet") if isinstance(plan.get("code_injection"), dict) else None,
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
    "identify_and_fix",
    "discover_sources",
    "identify_data",
    "code_injection",
    "add_build",
    "recheck",
    "complete",
]:
    """From a step node: go to identify_and_fix on error, else next step or complete."""
    if state.get("workflow_error"):
        return "identify_and_fix"
    plan = state.get("workflow_plan") or {}
    if STEP_RECHECK in plan:
        return "complete"
    if STEP_ADD_BUILD in plan:
        return "recheck"
    if STEP_CODE_INJECTION in plan:
        return "add_build"
    if STEP_IDENTIFY_DATA in plan:
        return "code_injection"
    if STEP_DISCOVER_SOURCES in plan:
        return "identify_data"
    return "identify_data"


def route_after_fix(state: AgentState) -> str:
    """After identify_and_fix: go back to the step indicated."""
    return state.get("step_to_return_to") or STEP_DISCOVER_SOURCES


def route_ask_end(_state: AgentState) -> Literal["__end__"]:
    return "__end__"


# --- Graph build --------------------------------------------------------------

def build_agent_graph():
    """Build the VeloC injection workflow graph with error-correction loop."""
    workflow = StateGraph(AgentState)

    workflow.add_node(STEP_CHECK_INPUT, check_input)
    workflow.add_node(STEP_DISCOVER_SOURCES, run_discover_sources)
    workflow.add_node(STEP_IDENTIFY_DATA, run_identify_data)
    workflow.add_node(STEP_CODE_INJECTION, run_code_injection)
    workflow.add_node(STEP_ADD_BUILD, run_add_build)
    workflow.add_node(STEP_RECHECK, run_recheck)
    workflow.add_node(STEP_IDENTIFY_AND_FIX, run_identify_and_fix)
    workflow.add_node(STEP_COMPLETE, run_complete)

    workflow.set_entry_point(STEP_CHECK_INPUT)

    # check_input → ask (END) or discover_sources
    workflow.add_conditional_edges(STEP_CHECK_INPUT, route_after_check_input, {
        "ask": END,
        "discover_sources": STEP_DISCOVER_SOURCES,
    })

    # discover_sources → identify_data or identify_and_fix
    workflow.add_conditional_edges(STEP_DISCOVER_SOURCES, route_after_step, {
        "identify_and_fix": STEP_IDENTIFY_AND_FIX,
        "discover_sources": STEP_DISCOVER_SOURCES,
        "identify_data": STEP_IDENTIFY_DATA,
        "code_injection": STEP_CODE_INJECTION,
        "add_build": STEP_ADD_BUILD,
        "recheck": STEP_RECHECK,
        "complete": STEP_COMPLETE,
    })

    # Step chain with error branch
    workflow.add_conditional_edges(STEP_IDENTIFY_DATA, route_after_step, {
        "identify_and_fix": STEP_IDENTIFY_AND_FIX,
        "code_injection": STEP_CODE_INJECTION,
        "add_build": STEP_ADD_BUILD,
        "recheck": STEP_RECHECK,
        "complete": STEP_COMPLETE,
    })
    workflow.add_conditional_edges(STEP_CODE_INJECTION, route_after_step, {
        "identify_and_fix": STEP_IDENTIFY_AND_FIX,
        "code_injection": STEP_CODE_INJECTION,
        "add_build": STEP_ADD_BUILD,
        "recheck": STEP_RECHECK,
        "complete": STEP_COMPLETE,
    })
    workflow.add_conditional_edges(STEP_ADD_BUILD, route_after_step, {
        "identify_and_fix": STEP_IDENTIFY_AND_FIX,
        "code_injection": STEP_CODE_INJECTION,
        "add_build": STEP_ADD_BUILD,
        "recheck": STEP_RECHECK,
        "complete": STEP_COMPLETE,
    })
    workflow.add_conditional_edges(STEP_RECHECK, route_after_step, {
        "identify_and_fix": STEP_IDENTIFY_AND_FIX,
        "code_injection": STEP_CODE_INJECTION,
        "add_build": STEP_ADD_BUILD,
        "recheck": STEP_RECHECK,
        "complete": STEP_COMPLETE,
    })

    workflow.add_conditional_edges(STEP_IDENTIFY_AND_FIX, route_after_fix, {
        STEP_DISCOVER_SOURCES: STEP_DISCOVER_SOURCES,
        STEP_IDENTIFY_DATA: STEP_IDENTIFY_DATA,
        STEP_CODE_INJECTION: STEP_CODE_INJECTION,
        STEP_ADD_BUILD: STEP_ADD_BUILD,
    })

    workflow.add_edge(STEP_COMPLETE, END)

    return workflow.compile()
