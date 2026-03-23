"""
VeloC code-injection agent.

The agent receives a user prompt describing an application codebase and its
checkpoint/resilience requirements, then:
  1. Explores the codebase using filesystem tools.
  2. Injects VeloC checkpoint calls where needed.
  3. Writes the modified files back to the output directory.
  4. Designs and writes a validation script tailored to the application's
     structure, then asks the user to run it and report results.

Implementation uses the ``openai`` Python client directly with a manual
tool-calling loop, so it works with **any OpenAI-compatible API endpoint**:
  - ``openai``  – real OpenAI (set OPENAI_API_KEY)
  - ``argo``    – Argonne proxy (set ARGO_API_KEY + ARGO_BASE_URL)
  - ``generic`` – any custom endpoint (set LLM_API_KEY + LLM_BASE_URL)

Provider selection is controlled by the ``LLM_PROVIDER`` env var / .env key.

Streaming / observability
-------------------------
``stream_veloc_agent`` is an async generator that yields structured event dicts
so callers (e.g. the web UI) can show live progress:

  {"type": "thinking",      "turn": N, "text": "..."}
  {"type": "step_summary",  "turn": N, "step": N, "name": "...", "why": "...",
                             "how": "...", "tools": [...], "result": "..."}
  {"type": "tool_call",     "turn": N, "name": "...", "args": {...}}
  {"type": "tool_result",   "turn": N, "name": "...", "result": "..."}
  {"type": "done",          "result": {...}}   # final structured result dict
  {"type": "error",         "message": "..."}
"""

from __future__ import annotations

import asyncio
import json
import re
import os
import time
from dataclasses import asdict
from typing import Any, AsyncIterator, Callable, Dict, List, Tuple

from agents.veloc.config import get_llm_client, get_project_root, get_settings
from agents.veloc.filesync_tools import execute_script, list_directory, read_file, remove_file, write_file
from agents.veloc.metrics import (
    MetricsCollector,
    extract_codebase_name,
    log_session,
    metrics_summary,
)
from agents.veloc.vector_db import (
    query_knowledge_base,
    store_insight,
    update_insight,
    _is_rag_enabled,
)


# ---------------------------------------------------------------------------
# VeloC guide tool
# ---------------------------------------------------------------------------

_VELOC_GUIDE_PATH = os.path.join(os.path.dirname(__file__), "guides", "veloc_guide.md")


def get_veloc_guide(section: str = "", list_sections: bool = False) -> str:
    """Return the VeloC guide Markdown document, a named section, or the section index.

    Args:
        section: Optional section heading to retrieve (e.g. "C API Reference",
                 "Configuration File Reference", "Complete Code Examples").
                 When empty and list_sections is False, the full guide is returned.
        list_sections: When True, return only the list of available top-level section
                 headings so the caller can decide which section to fetch next.
                 Ignores the ``section`` argument when True.

    Returns:
        A JSON string with one of:
        - ``{"sections": [...]}``  – when list_sections=True
        - ``{"content": "..."}``   – the requested (or full) guide text
        - ``{"error": "..."}``     – if the guide file cannot be read
    """
    try:
        with open(_VELOC_GUIDE_PATH, "r", encoding="utf-8") as fh:
            full_text = fh.read()
    except OSError as exc:
        return json.dumps({"error": f"Cannot read VeloC guide: {exc}"})

    # Return the list of top-level (##) section headings.
    if list_sections:
        import re as _re
        headings = _re.findall(r"^##\s+(.+)$", full_text, _re.MULTILINE)
        return json.dumps({"sections": headings})

    if not section:
        return json.dumps({"content": full_text})

    # Try to extract the requested section by heading.
    # A section starts at a line beginning with "## <section>" and ends at the
    # next "## " heading (or end of file).
    import re as _re
    pattern = _re.compile(
        r"(^##\s+" + _re.escape(section) + r".*?)(?=^##\s|\Z)",
        _re.MULTILINE | _re.DOTALL | _re.IGNORECASE,
    )
    match = pattern.search(full_text)
    if match:
        return json.dumps({"content": match.group(1).strip()})

    # Section not found — return the full guide with a note.
    return json.dumps({
        "content": full_text,
        "note": f"Section '{section}' not found; returning full guide.",
    })


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

def _system_prompt() -> str:
    root = get_project_root()
    rag_enabled = _is_rag_enabled()
    rag_section = ""
    if rag_enabled:
        rag_section = """
## Knowledge Base (RAG) — MANDATORY USAGE
You have access to a persistent knowledge base that accumulates insights from every VeloC integration session.
**You MUST use it actively — it makes you faster and more accurate.**

### Reading from the knowledge base
- **At the very start of every session**, call `query_knowledge_base(query="VeloC best practices checkpoint state")` to load general guidance.
- **Before writing any VeloC code**, call `query_knowledge_base` with a query describing what you are about to do (e.g. "MPI checkpoint restart pattern", "protect array state VeloC", "veloc.cfg configuration keys").
- **When you encounter an error or unexpected behaviour**, call `query_knowledge_base` with a description of the error to find known solutions.
- Use the returned insights to guide your implementation. High-confidence entries are especially reliable.

### Writing to the knowledge base
You MUST store insights whenever you discover something useful. Store insights for:
- **Best practices**: correct VeloC API call ordering, initialisation patterns, finalisation patterns.
- **State identification**: how to identify and protect critical state in a given type of application (MPI, OpenMP, serial, etc.).
- **Checkpoint timing**: when to checkpoint (loop boundaries, after expensive computation, Young-Daly formula results).
- **Error solutions**: if a build or runtime error occurs and you find the fix, store the error description and its solution.
- **Code patterns**: reusable VeloC code snippets that work correctly.
- **Configuration**: which `veloc.cfg` keys matter for which scenarios.

Call `store_insight(title, content, category, tags, confidence)` to add a new entry.
Valid categories: `best_practice`, `api_usage`, `error_solution`, `state_identification`, `checkpoint_timing`, `code_pattern`.

### Correcting the knowledge base
If you apply an insight from the knowledge base and it does **not** work as expected:
- Call `update_insight(insight_id, content, confidence)` to correct or downgrade the entry.
- Include what actually happened and what the correct approach is.

### Knowledge base tools
- `query_knowledge_base(query, top_k, min_score, category)` – semantic search; returns ranked insights.
- `store_insight(title, content, category, tags, confidence)` – add a new insight (confidence 0.0–1.0).
- `update_insight(insight_id, title, content, tags, confidence, verified)` – update an existing insight.
"""
    return f"""You are an expert in resilient HPC/cloud deployments and in integrating the VeloC checkpointing API into existing C/C++ codebases.

**Project root on the user's machine:** `{root}`
All file paths you use with the filesystem tools must be relative to this root.
{rag_section}
## Your tools
- `list_directory(dir_path)` – list files and subdirectories.
- `read_file(file_path)` – read a source file.
- `write_file(file_path, contents)` – write a file (creates parent dirs).
- `remove_file(file_path)` – delete a file **or an empty directory** inside BUILD_DIR.
  Returns `removed` (True/False), `kind` ("file" or "directory"), and, on failure, an `error` message.
  Only paths inside BUILD_DIR may be removed; any other path returns an error.
  Non-empty directories are rejected — remove their contents first, or use `execute_script` with `rm -rf`.
- `execute_script(script_path, timeout)` – execute a bash script that already exists inside BUILD_DIR.
  Returns `returncode`, `stdout`, `stderr`, and `timed_out`.
  The script runs with `cwd=BUILD_DIR`, `HOME=BUILD_DIR`, and a restricted `PATH`.
  It **cannot** access or modify files outside BUILD_DIR.
  Use `write_file` first to create the script, then `execute_script` to run it.
  Set `timeout` (seconds, default 120) to a larger value for long builds or MPI runs.
- `get_veloc_guide(list_sections, section)` – return the local VeloC reference guide as Markdown.
  The guide contains the **complete C API** (all function signatures, parameters, return codes),
  the **C++ `veloc::client_t` API**, the **INI configuration file specification** (all keys and defaults),
  **full code examples** for both memory-based and file-based modes, **CMakeLists.txt integration**,
  and **best practices** (Young-Daly formula, checkpoint placement patterns).
  **Usage pattern:**
  1. Call `get_veloc_guide(list_sections=true)` → returns `{{"sections": [...]}}` listing all available headings.
  2. Call `get_veloc_guide(section="<heading>")` → returns `{{"content": "..."}}` for that section only.
  3. Or call `get_veloc_guide()` (no args) to get the entire guide at once.
  **You MUST call this tool before writing any VeloC code or configuration** to ensure you use
  correct API signatures, parameter order, and configuration keys.

## Step-by-step transparency protocol (MANDATORY)
You MUST break your work into clear, named steps. Before executing each step, you MUST emit a step-summary block in your response text using this exact JSON format (on its own line, no markdown fences):

STEP_SUMMARY: {{"step": <number>, "name": "<short step name>", "why": "<why this step is needed>", "how": "<how you will do it>", "tools": [<list of tool names you plan to call, or empty list>]}}

After completing the step (after any tool calls for that step), emit a completion block:

STEP_RESULT: {{"step": <number>, "result": "<brief summary of what was found or done>"}}

Rules:
- Always emit STEP_SUMMARY before any tool calls for that step.
- Always emit STEP_RESULT after the tool calls for that step complete.
- Keep each step focused on one logical action.
- Do NOT ask the user for input between steps — proceed automatically.
- Only emit a question to the user if you genuinely cannot proceed without missing information (e.g. unknown code path, missing environment details).
- Keep track of temporary/intermediate files you create during the whole process and remember to remove them once complete
- The resiliency support must be **TRANSPARENT** to the user: **DO NOT** change the original application's existing command-line parameters or behaviour. The only permitted addition is an **optional** `--veloc-cfg <path>` argument (or equivalent) for the VeloC configuration file path, which must default to `veloc.cfg` in the current working directory when omitted.

## Workflow
1. **Understand the request.** If the user's prompt is missing the code path, target environment, or resilience requirements, ask for the missing information.
2. **Explore the codebase.** Use `list_directory` and `read_file` to understand the structure of the code given by user; if the code location is not clear, ask the user for the path relative to the project root.
3. **Identify critical state.** From your understanding of the codebase, identify the critical data structures and variables that must be checkpointed across executions.
4. **Identify optimal checkpoint timing.** Determine when to checkpoint to minimise overhead while maximising resilience (e.g. applying the Young-Daly formula).
5. **Consult the VeloC guide.** Before writing any VeloC code or configuration, retrieve the relevant parts of the guide:
   - Call `get_veloc_guide(list_sections=true)` to discover all available section headings.
   - Then call `get_veloc_guide(section="<heading>")` for each section you need (e.g. `"C API Reference"`, `"Configuration File Reference"`, `"Complete Code Examples"`).
   - Alternatively, call `get_veloc_guide()` (no arguments) to get the entire guide at once.
   Use the retrieved content to select the correct API mode (memory-based vs. file-based), verify all function signatures and parameter order, and choose the right configuration keys.
6. **Inject VeloC.** Modify the source files to add VeloC checkpoint/restart calls and write a `veloc.cfg` configuration file, using the API signatures and configuration keys from the guide retrieved in the previous step. Use `write_file` to save all modified sources and the config.
   **Optional `veloc.cfg` path argument (REQUIRED):** The modified executable **must** accept the path to `veloc.cfg` as an optional command-line argument so that users can supply a custom config location without changing the binary. Implement it as follows:
   - Add an optional positional or named argument (e.g. `--veloc-cfg <path>` for C++ with a simple loop over `argv`, or a positional last argument) that the user may pass when launching the program.
   - If the argument is **not** provided, default to the string `"veloc.cfg"` (i.e. the file is looked up in the current working directory at runtime).
   - Pass the resolved path string to `VELOC_Init` (C API) or `veloc::client_t` constructor (C++ API) instead of a hard-coded literal.
   - **Do not** remove or rename any of the original application's existing command-line arguments; only append this new optional one.
   - Document the new argument in a comment near `main()` so it is easy to discover.
   - In the validation script, explicitly test both cases: (a) run without the argument (config file named `veloc.cfg` placed in the working directory) and (b) run with `--veloc-cfg <explicit_path>` pointing to the same config file at a different path, and verify both succeed.
7. **Validate.** This step is **REQUIRED**. Based on your understanding of the application's structure and output, design and write a validation script tailored to this specific application that:
   - Builds both the original and the resilient version.
   - Runs the resilient version with a simulated failure (e.g. kill the process mid-run, then restart it).
   - Compares the output of the resilient run against the baseline to confirm correctness.
   - **Before starting each independent resilient test scenario** (e.g. before the failure-injection run, and before the failure-free run), the validation script **must** purge any leftover VeloC checkpoint data to guarantee a clean state. Do this by:
     1. Parsing the `veloc.cfg` file (INI format) located in the working directory where the executable is launched (or at the path passed via `--veloc-cfg`).
     2. Reading the `scratch` and `persistent` directory paths from the `[veloc]` section.
     3. Deleting all files and subdirectories inside both directories (e.g. `rm -rf "$SCRATCH"/* "$PERSISTENT"/*`) **once, before the first attempt** of that scenario.
     **Important:** Do NOT clear checkpoints between retry attempts within the same failure-injection scenario. The retry loop relies on the checkpoint written by the previous (killed) attempt to restart from — clearing between attempts would destroy the checkpoint and prevent recovery.
     This prevents checkpoint files from a previous independent run from being accidentally picked up by a subsequent run, which would produce incorrect validation results.
   Write the validation script using `write_file` (save it inside BUILD_DIR), then run it autonomously with `execute_script`.
   Inspect the returned `returncode`, `stdout`, and `stderr`. If validation fails, analyse the error, fix the code, and run again.
   If the script needs more than 120 s (e.g. for a large MPI job), pass a larger `timeout` value.
   Only ask the user for input if the script requires information you genuinely cannot determine (e.g. unknown MPI rank count, missing dataset path).
8. **Clean-up** remove **ALL** temporary/intermediate files you created throughout the execution using `remove_file`, keep the original implementation and your generated resilient code intact.
    Clean not only temporary/intermediate files created in the original codebase and the generated codebase, but also **ALL** files and directories you created within the project root.
9. **Report.** Return **ONLY** JSON object (no markdown fences) with one of these shapes:
   - `{{"status": "ask", "assistant_question": "..."}}` – need more information.
   - `{{"status": "success", "summary": "..."}}` – task completed successfully.
   - `{{"status": "error", "error_message": "..."}}` – unrecoverable error.
"""


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

# Map tool name → Python callable.  Add new tools here to expose them to the LLM.
_TOOLS: Dict[str, Callable] = {
    "list_directory": list_directory,
    "read_file": read_file,
    "write_file": write_file,
    "remove_file": remove_file,
    "execute_script": execute_script,
    "get_veloc_guide": get_veloc_guide,
    # RAG / knowledge base tools
    "query_knowledge_base": query_knowledge_base,
    "store_insight": store_insight,
    "update_insight": update_insight,
}


def _build_tool_schemas() -> List[Dict[str, Any]]:
    """
    Auto-generate OpenAI function-calling schemas from the tool callables.

    Each tool must have a Google-style docstring whose first line is the
    description, and typed parameters.  For tools that need richer schemas
    (e.g. nested objects), override the schema here.
    """
    # Hand-written schemas for clarity and correctness.
    return [
        {
            "type": "function",
            "function": {
                "name": "list_directory",
                "description": "List files and subdirectories in a directory (relative to project root).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "dir_path": {"type": "string", "description": "Directory path relative to project root."},
                    },
                    "required": ["dir_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the full text contents of a file (relative to project root).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "File path relative to project root."},
                    },
                    "required": ["file_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write text contents to a file, creating parent directories as needed.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "File path relative to output root."},
                        "contents": {"type": "string", "description": "Full text content to write."},
                    },
                    "required": ["file_path", "contents"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "remove_file",
                "description": (
                    "Delete a file or an empty directory that lives inside the BUILD_DIR sandbox. "
                    "Any path that resolves outside BUILD_DIR is rejected and returns an error — "
                    "the path is never touched. "
                    "Non-empty directories are also rejected; remove their contents first, "
                    "or use execute_script with 'rm -rf' for non-empty trees. "
                    "Returns 'removed' (True/False), 'kind' ('file' or 'directory'), "
                    "and on failure an 'error' message."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": (
                                "Path to the file or empty directory to delete, "
                                "relative to BUILD_DIR or absolute. "
                                "Must resolve inside BUILD_DIR."
                            ),
                        },
                    },
                    "required": ["file_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "execute_script",
                "description": (
                    "Execute a bash script file that already exists inside the BUILD_DIR sandbox. "
                    "The script runs with cwd=BUILD_DIR, HOME=BUILD_DIR, and a restricted PATH. "
                    "Returns returncode, stdout, stderr, and timed_out flag. "
                    "Use write_file first to create the script, then call execute_script to run it. "
                    "The script cannot access or modify files outside BUILD_DIR."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "script_path": {
                            "type": "string",
                            "description": (
                                "Path to the bash script file, relative to BUILD_DIR or absolute. "
                                "Must resolve inside BUILD_DIR."
                            ),
                        },
                        "timeout": {
                            "type": "number",
                            "description": (
                                "Maximum wall-clock seconds to allow before killing the process. "
                                "Defaults to 120. Use a larger value for long builds or MPI runs."
                            ),
                            "default": 120.0,
                        },
                    },
                    "required": ["script_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_veloc_guide",
                "description": (
                    "Return the VeloC reference guide as Markdown. "
                    "The guide covers the full C API (VELOC_Init, VELOC_Mem_protect, "
                    "VELOC_Checkpoint, VELOC_Restart, VELOC_Finalize, etc.), the C++ "
                    "client API (veloc::client_t), the INI configuration file format "
                    "(scratch, persistent, mode, intervals, versions, checksums), "
                    "complete code examples for both memory-based and file-based modes, "
                    "CMakeLists.txt integration, and best practices. "
                    "Call this tool before writing any VeloC code or configuration to "
                    "ensure you use the correct API signatures and config keys. "
                    "Workflow: (1) call with list_sections=true to discover available "
                    "section headings, then (2) call with the desired section name to "
                    "retrieve only that section, or omit both to get the full guide."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "list_sections": {
                            "type": "boolean",
                            "description": (
                                "When true, return only the list of available top-level section "
                                "headings (e.g. 'C API Reference', 'Configuration File Reference', "
                                "'Complete Code Examples', etc.) so you can decide which section "
                                "to fetch next. Ignores the 'section' argument when true."
                            ),
                        },
                        "section": {
                            "type": "string",
                            "description": (
                                "Name of the section to retrieve. Must match one of the headings "
                                "returned by list_sections=true (case-insensitive). "
                                "Leave empty (and list_sections=false) to retrieve the full guide."
                            ),
                        },
                    },
                    "required": [],
                },
            },
        },
        # ── RAG / knowledge base tools ────────────────────────────────────────
        {
            "type": "function",
            "function": {
                "name": "query_knowledge_base",
                "description": (
                    "Search the persistent VeloC knowledge base for insights relevant to your current task. "
                    "Returns the top-k most similar entries ranked by TF-IDF cosine similarity. "
                    "Call this at session start and before writing any VeloC code to retrieve "
                    "best practices, known error solutions, and reusable code patterns. "
                    "Also call it when you encounter an error to find known fixes."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": (
                                "Natural-language description of what you are looking for. "
                                "E.g. 'MPI checkpoint restart pattern', 'veloc.cfg scratch key', "
                                "'VELOC_Mem_protect array', 'build error undefined reference veloc'."
                            ),
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default 5, max 20).",
                            "default": 5,
                        },
                        "min_score": {
                            "type": "number",
                            "description": "Minimum similarity score threshold 0.0–1.0 (default 0.1).",
                            "default": 0.1,
                        },
                        "category": {
                            "type": "string",
                            "description": (
                                "Optional category filter. One of: best_practice, api_usage, "
                                "error_solution, state_identification, checkpoint_timing, code_pattern."
                            ),
                        },
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "store_insight",
                "description": (
                    "Store a new insight in the persistent VeloC knowledge base. "
                    "Call this whenever you discover something useful: a correct API pattern, "
                    "a working code snippet, a solution to a build/runtime error, a best practice "
                    "for checkpoint timing or state identification, or a useful configuration tip. "
                    "The insight will be available to future sessions to speed up code generation."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Short descriptive title for the insight (max 120 chars).",
                        },
                        "content": {
                            "type": "string",
                            "description": (
                                "Full text of the insight. Include concrete details: "
                                "code snippets, exact error messages, parameter values, "
                                "and the reasoning behind the recommendation."
                            ),
                        },
                        "category": {
                            "type": "string",
                            "description": (
                                "Category for this insight. Must be one of: "
                                "best_practice, api_usage, error_solution, "
                                "state_identification, checkpoint_timing, code_pattern."
                            ),
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "List of keyword tags to improve searchability "
                                "(e.g. ['MPI', 'VELOC_Init', 'memory-based'])."
                            ),
                        },
                        "confidence": {
                            "type": "number",
                            "description": (
                                "Confidence score 0.0–1.0. Use 0.9+ for verified working patterns, "
                                "0.7 for likely-correct patterns, 0.5 for uncertain hints."
                            ),
                            "default": 0.8,
                        },
                    },
                    "required": ["title", "content", "category"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "update_insight",
                "description": (
                    "Update an existing insight in the knowledge base. "
                    "Call this when you applied an insight and it did NOT work as expected — "
                    "correct the content and lower the confidence. "
                    "Also call it to add new information to an existing entry or mark it as verified. "
                    "The insight_id comes from a previous query_knowledge_base result."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "insight_id": {
                            "type": "string",
                            "description": "UUID of the insight to update (from query_knowledge_base results).",
                        },
                        "title": {
                            "type": "string",
                            "description": "Updated title (leave empty to keep existing).",
                        },
                        "content": {
                            "type": "string",
                            "description": "Updated content (leave empty to keep existing).",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Updated tags list (leave empty to keep existing).",
                        },
                        "confidence": {
                            "type": "number",
                            "description": (
                                "Updated confidence 0.0–1.0. Lower this if the insight was incorrect. "
                                "Leave as null to keep existing."
                            ),
                        },
                        "verified": {
                            "type": "boolean",
                            "description": "Set to true if you have confirmed this insight works correctly.",
                        },
                    },
                    "required": ["insight_id"],
                },
            },
        },
    ]


def _dispatch_tool(name: str, arguments_json: str) -> str:
    """Call the named tool with the given JSON arguments and return the result as JSON."""
    fn = _TOOLS.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        kwargs = json.loads(arguments_json) if arguments_json else {}
        result = fn(**kwargs)
        return result if isinstance(result, str) else json.dumps(result)
    except Exception as exc:
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Step-summary parsing helpers
# ---------------------------------------------------------------------------

# Matches:  STEP_SUMMARY: { ... }   (single-line JSON object)
_STEP_SUMMARY_RE = re.compile(
    r"STEP_SUMMARY:\s*(\{[^\n]+\})", re.MULTILINE
)
# Matches:  STEP_RESULT: { ... }   (single-line JSON object)
_STEP_RESULT_RE = re.compile(
    r"STEP_RESULT:\s*(\{[^\n]+\})", re.MULTILINE
)
# Matches either marker line (used for splitting thinking text into chunks)
_STEP_MARKER_LINE_RE = re.compile(
    r"^[ \t]*(STEP_SUMMARY|STEP_RESULT):[ \t]*\{[^\n]+\}[ \t]*$", re.MULTILINE
)


def _parse_interleaved_events(text: str, turn: int, has_tool_calls: bool) -> List[Dict[str, Any]]:
    """
    Parse *text* and return a list of events that interleave thinking chunks
    with step_summary / step_result events in the order they appear in the text.

    This preserves the LLM's reasoning flow: a thinking chunk may appear before
    a STEP_SUMMARY (pre-step reasoning), between markers (inter-step reasoning),
    or after the last marker (post-step reasoning before tool calls).

    Event types returned:
      - ``{"type": "thinking", "turn": N, "text": "..."}``   – reasoning chunk
      - ``{"type": "step_summary", "turn": N, ...}``          – step announcement
      - ``{"type": "step_result",  "turn": N, ...}``          – step outcome

    When *has_tool_calls* is False the text is the final answer; in that case
    thinking chunks are emitted as ``"final"`` events instead.
    """
    events: List[Dict[str, Any]] = []

    # Collect all marker matches with their span so we can split the text.
    markers: List[Tuple[int, int, str, str]] = []  # (start, end, kind, json_str)
    for m in _STEP_SUMMARY_RE.finditer(text):
        markers.append((m.start(), m.end(), "summary", m.group(1)))
    for m in _STEP_RESULT_RE.finditer(text):
        markers.append((m.start(), m.end(), "result", m.group(1)))
    markers.sort(key=lambda x: x[0])

    # Track step_summary events by step number so we can attach results.
    step_events: Dict[int, Dict[str, Any]] = {}

    # Helper: strip marker lines from a text chunk and return cleaned text.
    def _strip_markers(chunk: str) -> str:
        return _STEP_MARKER_LINE_RE.sub("", chunk).strip()

    # Helper: emit a thinking/final event for a text chunk (if non-empty).
    def _emit_text(chunk: str) -> None:
        cleaned = _strip_markers(chunk)
        if not cleaned:
            return
        ev_type = "thinking" if has_tool_calls else "final"
        events.append({"type": ev_type, "turn": turn, "text": cleaned})

    if not markers:
        # No markers — emit the whole text as a single thinking/final event.
        _emit_text(text)
        return events

    # Emit text before the first marker.
    _emit_text(text[: markers[0][0]])

    for i, (start, end, kind, json_str) in enumerate(markers):
        # Parse and emit the marker event.
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            pass
        else:
            if kind == "summary":
                step_num = int(data.get("step", 0))
                ev = {
                    "type": "step_summary",
                    "turn": turn,
                    "step": step_num,
                    "name": str(data.get("name", "")),
                    "why": str(data.get("why", "")),
                    "how": str(data.get("how", "")),
                    "tools": data.get("tools", []),
                    "result": "",  # filled in when STEP_RESULT arrives
                }
                step_events[step_num] = ev
                events.append(ev)
            elif kind == "result":
                step_num = int(data.get("step", 0))
                result_text = str(data.get("result", ""))
                if step_num in step_events:
                    step_events[step_num]["result"] = result_text
                events.append({
                    "type": "step_result",
                    "turn": turn,
                    "step": step_num,
                    "result": result_text,
                })

        # Emit text between this marker and the next (or end of text).
        next_start = markers[i + 1][0] if i + 1 < len(markers) else len(text)
        _emit_text(text[end: next_start])

    return events


def _parse_step_events(text: str, turn: int) -> List[Dict[str, Any]]:
    """
    Scan *text* for STEP_SUMMARY and STEP_RESULT markers and return a list of
    structured event dicts in the order they appear.

    Each STEP_SUMMARY becomes a ``step_summary`` event (result field empty until
    the matching STEP_RESULT arrives).  Each STEP_RESULT updates the result field
    of the most recent step_summary with the same step number.

    Returns a flat list of events to yield, in document order.

    .. deprecated::
        Use :func:`_parse_interleaved_events` instead, which also interleaves
        thinking chunks between step markers.
    """
    events: List[Dict[str, Any]] = []
    # Collect all markers with their positions.
    markers: List[Tuple[int, str, str]] = []  # (pos, kind, json_str)
    for m in _STEP_SUMMARY_RE.finditer(text):
        markers.append((m.start(), "summary", m.group(1)))
    for m in _STEP_RESULT_RE.finditer(text):
        markers.append((m.start(), "result", m.group(1)))
    markers.sort(key=lambda x: x[0])

    # Track step_summary events by step number so we can attach results.
    step_events: Dict[int, Dict[str, Any]] = {}

    for _pos, kind, json_str in markers:
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            continue

        if kind == "summary":
            step_num = int(data.get("step", 0))
            ev = {
                "type": "step_summary",
                "turn": turn,
                "step": step_num,
                "name": str(data.get("name", "")),
                "why": str(data.get("why", "")),
                "how": str(data.get("how", "")),
                "tools": data.get("tools", []),
                "result": "",  # filled in when STEP_RESULT arrives
            }
            step_events[step_num] = ev
            events.append(ev)
        elif kind == "result":
            step_num = int(data.get("step", 0))
            result_text = str(data.get("result", ""))
            if step_num in step_events:
                # Update the existing event in-place (it's already in events list).
                step_events[step_num]["result"] = result_text
                # Also emit a dedicated step_result event so callers can update UI.
                events.append({
                    "type": "step_result",
                    "turn": turn,
                    "step": step_num,
                    "result": result_text,
                })
            else:
                events.append({
                    "type": "step_result",
                    "turn": turn,
                    "step": step_num,
                    "result": result_text,
                })

    return events


# ---------------------------------------------------------------------------
# Agentic loop — streaming (async generator)
# ---------------------------------------------------------------------------

async def _stream_agent_loop(
    messages: List[Dict[str, Any]],
    max_turns: int = 100,
    collector: MetricsCollector | None = None,
) -> AsyncIterator[Dict[str, Any]]:
    """
    Run the LLM + tool-calling loop and **yield** structured event dicts for
    each observable step so callers can stream live progress to the UI.

    Event shapes
    ------------
    ``{"type": "thinking",    "turn": N, "text": "..."}``
        The LLM produced a text chunk (thinking / reasoning) before or between
        tool calls.  May contain STEP_SUMMARY / STEP_RESULT markers which are
        also parsed and emitted as separate events.

    ``{"type": "step_summary","turn": N, "step": N, "name": "...", "why": "...",
                               "how": "...", "tools": [...], "result": ""}``
        The LLM announced a new processing step (parsed from STEP_SUMMARY marker).

    ``{"type": "step_result", "turn": N, "step": N, "result": "..."}``
        The LLM reported the outcome of a step (parsed from STEP_RESULT marker).

    ``{"type": "tool_call",   "turn": N, "name": "...", "args": {...}}``
        The LLM requested a tool call.

    ``{"type": "tool_result", "turn": N, "name": "...", "result": "..."}``
        The tool returned a result (truncated to 2 KB for display).

    ``{"type": "final",       "turn": N, "text": "..."}``
        The LLM produced its final answer (no more tool calls).

    ``{"type": "error",       "message": "..."}``
        An unrecoverable error occurred.

    Parameters
    ----------
    messages:
        Full chat message list (system prompt + conversation history).
    max_turns:
        Maximum number of LLM API calls before giving up.
    collector:
        Optional :class:`MetricsCollector` instance.  When provided, per-turn
        latency, token counts, tool call timing, and step timing are recorded.
    """
    client = get_llm_client()
    model = get_settings().llm_model
    tool_schemas = _build_tool_schemas()
    loop = asyncio.get_running_loop()

    # Maximum seconds to wait for a single LLM API response.  Long enough for
    # slow models / large contexts, but prevents an indefinite hang if the
    # endpoint is unreachable or stalled.
    LLM_TIMEOUT = 300  # 5 minutes

    for turn in range(1, max_turns + 1):
        # Snapshot the message list for the lambda so each turn uses the
        # correct history even if the list is mutated before the executor
        # thread starts (avoids a subtle closure/race condition).
        messages_snapshot = list(messages)

        # ── Record turn start ────────────────────────────────────────────────
        if collector is not None:
            collector.start_turn(turn)

        # Offload the blocking HTTP call to a thread pool.
        try:
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: client.chat.completions.create(
                        model=model,
                        messages=messages_snapshot,
                        tools=tool_schemas,
                        tool_choice="auto",
                    ),
                ),
                timeout=LLM_TIMEOUT,
            )
        except asyncio.TimeoutError:
            yield {
                "type": "error",
                "message": (
                    f"LLM API call timed out after {LLM_TIMEOUT} s on turn {turn}. "
                    "The endpoint may be slow or unreachable. Please try again."
                ),
            }
            return
        except Exception as exc:
            yield {"type": "error", "message": f"LLM call failed: {exc!r}"}
            return

        # ── Record turn end (token counts from response.usage) ───────────────
        if collector is not None:
            collector.end_turn(turn, getattr(response, "usage", None))
            # Record the messages that were in context for this turn.
            collector.record_context_messages(turn, messages_snapshot)

        msg = response.choices[0].message

        # Emit any thinking/reasoning text the model produced.
        if msg.content:
            # Record the model's text response for this turn.
            if collector is not None:
                collector.record_model_response(turn, msg.content)

            # Parse the content into interleaved thinking chunks and step events
            # so the UI shows them in the order the LLM actually reasoned:
            #   thinking chunk → step_summary → thinking chunk → step_summary → …
            # Tool calls follow after all text events (OpenAI API constraint).
            interleaved = _parse_interleaved_events(
                msg.content, turn, has_tool_calls=bool(msg.tool_calls)
            )
            for ev in interleaved:
                # ── Record events in the collector (interleaved order) ────────
                if collector is not None:
                    if ev["type"] == "step_summary":
                        collector.record_step_summary(
                            turn,
                            ev["step"],
                            ev.get("name", ""),
                            why=ev.get("why", ""),
                            how=ev.get("how", ""),
                            tools=ev.get("tools", []),
                        )
                    elif ev["type"] == "step_result":
                        collector.record_step_result(turn, ev["step"], ev.get("result", ""))
                    elif ev["type"] in ("thinking", "final"):
                        collector.record_thinking_chunk(turn, ev["text"])
                yield ev

        # Build the assistant message dict for history.
        assistant_msg: Dict[str, Any] = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ]
        messages.append(assistant_msg)

        if not msg.tool_calls:
            # No tool calls → final answer already emitted above.
            return

        # Build a queue mapping tool names → step numbers from the step_summary
        # events emitted above.  This lets us associate each tool call with the
        # step that announced it, so the UI can place tool-call boxes inside the
        # correct step card rather than always in the last one.
        # The queue preserves order so that if the same tool is used in multiple
        # steps, each call is assigned to the earliest unmatched step.
        _tool_step_queue: List[Tuple[str, int]] = []  # [(tool_name, step_num), ...]
        if msg.content:
            for ev in _parse_interleaved_events(msg.content, turn, has_tool_calls=True):
                if ev["type"] == "step_summary":
                    for _t in ev.get("tools", []):
                        _tool_step_queue.append((_t, ev["step"]))

        def _pop_step_for_tool(tool_name: str) -> int | None:
            """Return the step number for the next unmatched occurrence of tool_name."""
            for i, (tname, snum) in enumerate(_tool_step_queue):
                if tname == tool_name:
                    _tool_step_queue.pop(i)
                    return snum
            return None

        # Dispatch each tool call, emit events, append results.
        for tc in msg.tool_calls:
            # Parse args for display (best-effort).
            try:
                args_display = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except (json.JSONDecodeError, ValueError):
                args_display = {"raw": tc.function.arguments}

            # Determine which step this tool call belongs to.
            _tc_step = _pop_step_for_tool(tc.function.name)

            _tool_call_ev: Dict[str, Any] = {
                "type": "tool_call",
                "turn": turn,
                "name": tc.function.name,
                "args": args_display,
            }
            if _tc_step is not None:
                _tool_call_ev["step"] = _tc_step
            yield _tool_call_ev

            # Offload blocking tool execution (e.g. cmake/make/MPI) to a thread pool
            # so the event loop stays responsive for SSE heartbeats.
            # ── Time the tool call for metrics ───────────────────────────────
            _tool_t0 = time.monotonic()
            result_str = await loop.run_in_executor(
                None, _dispatch_tool, tc.function.name, tc.function.arguments
            )
            _tool_elapsed = time.monotonic() - _tool_t0
            if collector is not None:
                collector.record_tool_call(
                    tc.function.name,
                    _tool_elapsed,
                    args=args_display,
                    result=result_str,
                    step=_tc_step,
                )

            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_str})

            # Truncate large results for display only.
            display_result = result_str if len(result_str) <= 2048 else result_str[:2048] + "…[truncated]"
            _tool_result_ev: Dict[str, Any] = {
                "type": "tool_result",
                "turn": turn,
                "name": tc.function.name,
                "result": display_result,
            }
            if _tc_step is not None:
                _tool_result_ev["step"] = _tc_step
            yield _tool_result_ev

            # ── Emit RAG-specific events for knowledge base interactions ──────
            _rag_tool_name = tc.function.name
            if _rag_tool_name in ("query_knowledge_base", "store_insight", "update_insight"):
                try:
                    _rag_result = json.loads(result_str)
                except (json.JSONDecodeError, ValueError):
                    _rag_result = {}
                _rag_enabled_flag = _rag_result.get("rag_enabled", True)

                if _rag_tool_name == "query_knowledge_base":
                    _results = _rag_result.get("results", [])
                    _rag_ev = {
                        "type": "rag_query",
                        "turn": turn,
                        "query": args_display.get("query", ""),
                        "results_count": len(_results),
                        "results": _results,
                        "rag_enabled": _rag_enabled_flag,
                    }
                    yield _rag_ev
                    if collector is not None:
                        collector.record_rag_interaction(
                            kind="query",
                            elapsed_s=_tool_elapsed,
                            rag_enabled=_rag_enabled_flag,
                            query=args_display.get("query", ""),
                            results_count=len(_results),
                        )

                elif _rag_tool_name == "store_insight":
                    _rag_ev = {
                        "type": "rag_store",
                        "turn": turn,
                        "insight_id": _rag_result.get("id", ""),
                        "title": _rag_result.get("title", args_display.get("title", "")),
                        "category": _rag_result.get("category", args_display.get("category", "")),
                        "confidence": _rag_result.get("confidence", args_display.get("confidence", 0.8)),
                        "rag_enabled": _rag_enabled_flag,
                    }
                    yield _rag_ev
                    if collector is not None:
                        collector.record_rag_interaction(
                            kind="store",
                            elapsed_s=_tool_elapsed,
                            rag_enabled=_rag_enabled_flag,
                            title=_rag_result.get("title", args_display.get("title", "")),
                            insight_id=_rag_result.get("id", ""),
                            category=_rag_result.get("category", args_display.get("category", "")),
                            confidence=_rag_result.get("confidence", args_display.get("confidence")),
                        )

                elif _rag_tool_name == "update_insight":
                    _rag_ev = {
                        "type": "rag_update",
                        "turn": turn,
                        "insight_id": _rag_result.get("id", args_display.get("insight_id", "")),
                        "title": _rag_result.get("title", ""),
                        "confidence": _rag_result.get("confidence"),
                        "rag_enabled": _rag_enabled_flag,
                    }
                    yield _rag_ev
                    if collector is not None:
                        collector.record_rag_interaction(
                            kind="update",
                            elapsed_s=_tool_elapsed,
                            rag_enabled=_rag_enabled_flag,
                            title=_rag_result.get("title", ""),
                            insight_id=_rag_result.get("id", args_display.get("insight_id", "")),
                            confidence=_rag_result.get("confidence"),
                        )

    # Exceeded max_turns.
    yield {
        "type": "error",
        "message": f"Agent exceeded {max_turns} turns without a final answer.",
    }


# ---------------------------------------------------------------------------
# Agentic loop — batch (collects all events, returns final text + trace)
# ---------------------------------------------------------------------------

async def _run_agent_loop(
    messages: List[Dict[str, Any]],
    max_turns: int = 50,
    collector: MetricsCollector | None = None,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Run the LLM + tool-calling loop until the model produces a final text answer.

    Returns ``(final_text, llm_trace)`` where *llm_trace* is a list of event
    dicts (same format as ``_stream_agent_loop``) for debugging.
    """
    final_text = ""
    llm_trace: List[Dict[str, Any]] = []

    async for event in _stream_agent_loop(messages, max_turns=max_turns, collector=collector):
        llm_trace.append(event)
        if event["type"] == "final":
            final_text = event.get("text", "")
        elif event["type"] == "error":
            return json.dumps({"status": "error", "error_message": event["message"]}), llm_trace

    return final_text, llm_trace


# ---------------------------------------------------------------------------
# JSON output helpers
# ---------------------------------------------------------------------------

_STATUS_VALUES = frozenset({"ask", "success", "error", "plan"})


def _iter_json_objects(text: str):
    """Yield every top-level ``{...}`` JSON object found in *text* as a string.

    Uses brace-depth tracking so nested objects and string literals containing
    braces are handled correctly.  Yields each complete object in document order.
    """
    pos = 0
    length = len(text)
    while pos < length:
        start = text.find("{", pos)
        if start == -1:
            break
        depth, in_str, escape = 0, False, False
        end = None
        for i, c in enumerate(text[start:], start):
            if escape:
                escape = False
                continue
            if c == "\\" and in_str:
                escape = True
                continue
            if c == '"':
                in_str = not in_str
                continue
            if not in_str:
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
        if end is not None:
            yield text[start:end + 1]
            pos = end + 1
        else:
            break


def _extract_json(raw: str) -> str:
    """Extract the best top-level JSON object from *raw*.

    The LLM's final message may contain STEP_SUMMARY / STEP_RESULT markers
    (which are also JSON objects) before the actual ``{"status": ...}`` result.
    Naively returning the *first* ``{...}`` object would pick up a step marker
    instead of the status object.

    Strategy:
    1. Iterate over all top-level ``{...}`` objects in the text.
    2. Return the first one whose ``"status"`` key has a recognised value
       (``ask`` | ``success`` | ``error`` | ``plan``).
    3. If none has a recognised status, return the last complete object found
       (preserving the original behaviour for simple responses).
    4. If no complete object is found at all, return the raw text so the caller
       can produce a meaningful error.
    """
    text = raw.strip()
    last_obj: str | None = None
    for obj_str in _iter_json_objects(text):
        last_obj = obj_str
        try:
            data = json.loads(obj_str)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and str(data.get("status", "")).lower() in _STATUS_VALUES:
            return obj_str
    # No object with a recognised status found — fall back to the last object.
    if last_obj is not None:
        return last_obj
    # No complete object at all — return the raw text.
    return text


def _parse_json(text: str) -> Any:
    """Parse JSON with fallbacks for double-encoding and unescaped newlines."""
    text = text.strip()
    if text.startswith('"') and text.endswith('"'):
        try:
            inner = json.loads(text)
            if isinstance(inner, str):
                return json.loads(inner)
        except (json.JSONDecodeError, TypeError):
            pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Repair unescaped newlines inside string values.
    repaired, in_str, escape = [], False, False
    for c in text:
        if escape:
            repaired.append(c); escape = False; continue
        if c == "\\" and in_str:
            repaired.append(c); escape = True; continue
        if c == '"':
            in_str = not in_str; repaired.append(c); continue
        if in_str and c in "\n\r\t":
            repaired.append({"\n": "\\n", "\r": "\\r", "\t": "\\t"}[c]); continue
        repaired.append(c)
    return json.loads("".join(repaired))


def _build_result(raw: str, llm_trace: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Parse the LLM's final JSON response and return a structured result dict.

    The LLM is instructed to return a JSON object with a ``"status"`` key.
    However, when the LLM asks a clarifying question conversationally (without
    using the JSON format), we treat the raw text as an ``ask`` response so the
    user sees the question rather than a confusing error message.
    """
    if not raw:
        return {
            "status": "error",
            "assistant_question": "Agent returned no output.",
            "plan": None, "raw_llm_response": raw, "llm_trace": llm_trace,
        }

    try:
        data = _parse_json(_extract_json(raw))
    except json.JSONDecodeError:
        # The LLM responded conversationally (no JSON).  Treat the full text as
        # an "ask" so the user sees the message and can reply.
        return {
            "status": "ask",
            "assistant_question": raw.strip(),
            "plan": None, "raw_llm_response": raw, "llm_trace": llm_trace,
        }

    status = str(data.get("status", "")).lower()

    if status == "ask":
        return {
            "status": "ask",
            "assistant_question": str(data.get("assistant_question", "Please provide more details.")),
            "plan": None, "raw_llm_response": raw, "llm_trace": llm_trace,
        }
    if status == "success":
        return {
            "status": "success",
            "assistant_question": None,
            "summary": str(data.get("summary", "")),
            "plan": None, "raw_llm_response": raw, "llm_trace": llm_trace,
        }
    if status == "plan":
        plan = data.get("plan")
        if not isinstance(plan, dict):
            plan = {"summary": raw[:500], "steps": [], "transformed_code": None}
        return {
            "status": "plan",
            "assistant_question": None,
            "plan": plan, "raw_llm_response": raw, "llm_trace": llm_trace,
        }

    if not status:
        # No "status" key at all — the LLM responded conversationally with a
        # JSON-like structure (e.g. a step marker).  Treat as ask.
        return {
            "status": "ask",
            "assistant_question": raw.strip(),
            "plan": None, "raw_llm_response": raw, "llm_trace": llm_trace,
        }

    # error or unknown status value
    return {
        "status": "error",
        "assistant_question": str(data.get("assistant_question", data.get("error_message", raw[:500]))),
        "plan": None, "raw_llm_response": raw, "llm_trace": llm_trace,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def run_veloc_agent(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Run the VeloC agent on a conversation and return a structured result dict.

    Args:
        messages: List of ``{"role": ..., "content": ...}`` dicts representing
                  the conversation so far.

    Returns:
        Dict with keys: ``status`` ('ask'|'success'|'error'|'plan'),
        ``assistant_question``, ``summary``, ``plan``,
        ``raw_llm_response``, ``llm_trace``, ``metrics``.
    """
    if not messages:
        return {
            "status": "ask",
            "assistant_question": (
                "Please describe your application: which code path should be made resilient, "
                "the target environment (e.g. HPC cluster), and where to write the output."
            ),
            "plan": None, "raw_llm_response": "", "llm_trace": [], "metrics": None,
        }

    # Build the full message list: system prompt + conversation history.
    chat: List[Dict[str, Any]] = [{"role": "system", "content": _system_prompt()}]
    chat.extend({"role": m.get("role", "user"), "content": m.get("content", "")} for m in messages)

    # Extract codebase name from the first user message for the log filename.
    codebase = extract_codebase_name(list(messages))

    # Initialise metrics collector.
    collector = MetricsCollector()
    collector.start_session()

    raw, llm_trace = await _run_agent_loop(chat, collector=collector)
    result = _build_result(raw, llm_trace)

    # Finalise metrics and auto-save to disk.
    session_metrics = collector.finish_session(chat, result, codebase=codebase)
    try:
        log_session(session_metrics, get_project_root())
    except Exception:
        pass  # Never let metrics log crash the agent.

    result["metrics"] = metrics_summary(session_metrics)
    return result


async def stream_veloc_agent(
    messages: List[Dict[str, str]],
) -> AsyncIterator[Dict[str, Any]]:
    """
    Streaming version of ``run_veloc_agent``.

    Yields structured event dicts as the agent thinks and calls tools, then
    yields a final ``{"type": "done", "result": {...}}`` event containing the
    same structured result dict that ``run_veloc_agent`` would return.

    Event types emitted:
      - ``step_summary``  – LLM announced a new processing step (why/how/tools)
      - ``step_result``   – LLM reported the outcome of a step
      - ``thinking``      – raw LLM reasoning text
      - ``tool_call``     – tool being invoked
      - ``tool_result``   – tool output
      - ``final``         – LLM final answer text
      - ``done``          – structured result dict (last event)
      - ``error``         – unrecoverable error

    Usage::

        async for event in stream_veloc_agent(messages):
            if event["type"] == "done":
                result = event["result"]
            else:
                # render live progress
                ...
    """
    if not messages:
        yield {
            "type": "done",
            "result": {
                "status": "ask",
                "assistant_question": (
                    "Please describe your application: which code path should be made resilient, "
                    "the target environment (e.g. HPC cluster), and where to write the output."
                ),
                "plan": None, "raw_llm_response": "", "llm_trace": [], "metrics": None,
            },
            "metrics": None,
        }
        return

    # Build the full message list: system prompt + conversation history.
    chat: List[Dict[str, Any]] = [{"role": "system", "content": _system_prompt()}]
    chat.extend({"role": m.get("role", "user"), "content": m.get("content", "")} for m in messages)

    # Extract codebase name from the first user message for the log filename.
    codebase = extract_codebase_name(list(messages))

    # Initialise metrics collector.
    collector = MetricsCollector()
    collector.start_session()

    final_text = ""
    llm_trace: List[Dict[str, Any]] = []

    async for event in _stream_agent_loop(chat, collector=collector):
        llm_trace.append(event)
        yield event  # forward every event to the caller

        if event["type"] == "final":
            final_text = event.get("text", "")
        elif event["type"] == "error":
            # Finalise metrics even on error.
            error_result: Dict[str, Any] = {
                "status": "error",
                "assistant_question": event["message"],
                "plan": None, "raw_llm_response": "", "llm_trace": llm_trace,
            }
            session_metrics = collector.finish_session(
                chat, error_result, codebase=codebase,
                llm_model=get_settings().llm_model,
            )
            try:
                saved_path = log_session(session_metrics, get_project_root())
                error_result["metrics_path"] = saved_path
            except Exception:
                pass
            m_summary = metrics_summary(session_metrics)
            m_full = asdict(session_metrics)
            error_result["metrics"] = m_summary
            yield {"type": "done", "result": error_result, "metrics": m_summary, "full_metrics": m_full}
            return

    result = _build_result(final_text, llm_trace)

    # Finalise metrics and auto-save to disk.
    session_metrics = collector.finish_session(
        chat, result, codebase=codebase,
        llm_model=get_settings().llm_model,
    )
    saved_path: str | None = None
    try:
        saved_path = log_session(session_metrics, get_project_root())
    except Exception:
        pass  # Never let metrics log crash the agent.

    m_summary = metrics_summary(session_metrics)
    m_full = asdict(session_metrics)
    result["metrics"] = m_summary
    if saved_path:
        result["metrics_path"] = saved_path

    yield {"type": "done", "result": result, "metrics": m_summary, "full_metrics": m_full}
