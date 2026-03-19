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
from typing import Any, AsyncIterator, Callable, Dict, List, Tuple

from agents.veloc.config import get_llm_client, get_project_root, get_settings
from agents.veloc.filesync_tools import execute_script, list_directory, read_file, remove_file, write_file


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

def _system_prompt() -> str:
    root = get_project_root()
    return f"""You are an expert in resilient HPC/cloud deployments and in integrating the VeloC checkpointing API into existing C/C++ codebases.

**Project root on the user's machine:** `{root}`
All file paths you use with the filesystem tools must be relative to this root.

## Your tools
- `list_directory(dir_path)` – list files and subdirectories.
- `read_file(file_path)` – read a source file.
- `write_file(file_path, contents)` – write a file (creates parent dirs).
- `remove_file(file_path)` – delete a single file inside BUILD_DIR.
  Returns `removed` (True/False) and, on failure, an `error` message.
  Only files inside BUILD_DIR may be removed; any other path returns an error.
  Directories cannot be removed with this tool.
- `execute_script(script_path, timeout)` – execute a bash script that already exists inside BUILD_DIR.
  Returns `returncode`, `stdout`, `stderr`, and `timed_out`.
  The script runs with `cwd=BUILD_DIR`, `HOME=BUILD_DIR`, and a restricted `PATH`.
  It **cannot** access or modify files outside BUILD_DIR.
  Use `write_file` first to create the script, then `execute_script` to run it.
  Set `timeout` (seconds, default 120) to a larger value for long builds or MPI runs.

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

## Workflow
1. **Understand the request.** If the user's prompt is missing the code path, target environment, or resilience requirements, ask for the missing information.
2. **Explore the codebase.** Use `list_directory` and `read_file` to understand the structure of the code given by user; if the code location is not clear, ask the user for the path relative to the project root.
3. **Identify critical state.** From your understanding of the codebase, identify the critical data structures and variables that must be checkpointed across executions.
4. **Identify optimal checkpoint timing.** Determine when to checkpoint to minimise overhead while maximising resilience (e.g. applying the Young-Daly formula).
5. **Inject VeloC.** Modify the source files to add VeloC checkpoint/restart calls and write a `veloc.cfg` configuration file. Follow the VeloC C API (VELOC_Init, VELOC_Mem_protect, VELOC_Checkpoint, VELOC_Restart, VELOC_Finalize).
6. **Write files.** Use `write_file` to save all modified sources and the config.
7. **Validate.** This step is **REQUIRED**. Based on your understanding of the application's structure and output, design and write a validation script tailored to this specific application that:
   - Builds both the original and the resilient version.
   - Runs the resilient version with a simulated failure (e.g. kill the process mid-run, then restart it).
   - Compares the output of the resilient run against the baseline to confirm correctness.
   Write the validation script using `write_file` (save it inside BUILD_DIR), then run it autonomously with `execute_script`.
   Inspect the returned `returncode`, `stdout`, and `stderr`. If validation fails, analyse the error, fix the code, and run again.
   If the script needs more than 120 s (e.g. for a large MPI job), pass a larger `timeout` value.
   Only ask the user for input if the script requires information you genuinely cannot determine (e.g. unknown MPI rank count, missing dataset path).
8. **Clean-up** remove **ALL** intermadiate files you created throughout the execution using `remove_file`, keep the original implementation and your generated resilient code intact.
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
                    "Delete a single file that lives inside the BUILD_DIR sandbox. "
                    "Any path that resolves outside BUILD_DIR is rejected and returns an error — "
                    "the file is never touched. Directories cannot be removed with this tool."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": (
                                "Path to the file to delete, relative to BUILD_DIR or absolute. "
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


def _parse_step_events(text: str, turn: int) -> List[Dict[str, Any]]:
    """
    Scan *text* for STEP_SUMMARY and STEP_RESULT markers and return a list of
    structured event dicts in the order they appear.

    Each STEP_SUMMARY becomes a ``step_summary`` event (result field empty until
    the matching STEP_RESULT arrives).  Each STEP_RESULT updates the result field
    of the most recent step_summary with the same step number.

    Returns a flat list of events to yield, in document order.
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
    max_turns: int = 50,
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
    """
    client = get_llm_client()
    model = get_settings().llm_model
    tool_schemas = _build_tool_schemas()
    loop = asyncio.get_running_loop()

    for turn in range(1, max_turns + 1):
        # Offload the blocking HTTP call to a thread pool.
        try:
            response = await loop.run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=tool_schemas,
                    tool_choice="auto",
                ),
            )
        except Exception as exc:
            yield {"type": "error", "message": f"LLM call failed: {exc!r}"}
            return

        msg = response.choices[0].message

        # Emit any thinking/reasoning text the model produced.
        if msg.content:
            # Parse step-summary / step-result markers from the content.
            step_events = _parse_step_events(msg.content, turn)
            for ev in step_events:
                yield ev

            if msg.tool_calls:
                yield {"type": "thinking", "turn": turn, "text": msg.content}
            else:
                yield {"type": "final", "turn": turn, "text": msg.content}

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

        # Dispatch each tool call, emit events, append results.
        for tc in msg.tool_calls:
            # Parse args for display (best-effort).
            try:
                args_display = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except (json.JSONDecodeError, ValueError):
                args_display = {"raw": tc.function.arguments}

            yield {"type": "tool_call", "turn": turn, "name": tc.function.name, "args": args_display}

            # Offload blocking tool execution (e.g. cmake/make/MPI) to a thread pool
            # so the event loop stays responsive for SSE heartbeats.
            result_str = await loop.run_in_executor(
                None, _dispatch_tool, tc.function.name, tc.function.arguments
            )
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_str})

            # Truncate large results for display only.
            display_result = result_str if len(result_str) <= 2048 else result_str[:2048] + "…[truncated]"
            yield {"type": "tool_result", "turn": turn, "name": tc.function.name, "result": display_result}

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
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Run the LLM + tool-calling loop until the model produces a final text answer.

    Returns ``(final_text, llm_trace)`` where *llm_trace* is a list of event
    dicts (same format as ``_stream_agent_loop``) for debugging.
    """
    final_text = ""
    llm_trace: List[Dict[str, Any]] = []

    async for event in _stream_agent_loop(messages, max_turns=max_turns):
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
    """Parse the LLM's final JSON response and return a structured result dict."""
    if not raw:
        return {
            "status": "error",
            "assistant_question": "Agent returned no output.",
            "plan": None, "raw_llm_response": raw, "llm_trace": llm_trace,
        }

    try:
        data = _parse_json(_extract_json(raw))
    except json.JSONDecodeError:
        return {
            "status": "error",
            "assistant_question": "Agent output could not be parsed as JSON. Please try again.",
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

    # error or unknown
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
        ``raw_llm_response``, ``llm_trace``.
    """
    if not messages:
        return {
            "status": "ask",
            "assistant_question": (
                "Please describe your application: which code path should be made resilient, "
                "the target environment (e.g. HPC cluster), and where to write the output."
            ),
            "plan": None, "raw_llm_response": "", "llm_trace": [],
        }

    # Build the full message list: system prompt + conversation history.
    chat: List[Dict[str, Any]] = [{"role": "system", "content": _system_prompt()}]
    chat.extend({"role": m.get("role", "user"), "content": m.get("content", "")} for m in messages)

    raw, llm_trace = await _run_agent_loop(chat)
    return _build_result(raw, llm_trace)


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
                "plan": None, "raw_llm_response": "", "llm_trace": [],
            },
        }
        return

    # Build the full message list: system prompt + conversation history.
    chat: List[Dict[str, Any]] = [{"role": "system", "content": _system_prompt()}]
    chat.extend({"role": m.get("role", "user"), "content": m.get("content", "")} for m in messages)

    final_text = ""
    llm_trace: List[Dict[str, Any]] = []

    async for event in _stream_agent_loop(chat):
        llm_trace.append(event)
        yield event  # forward every event to the caller

        if event["type"] == "final":
            final_text = event.get("text", "")
        elif event["type"] == "error":
            yield {
                "type": "done",
                "result": {
                    "status": "error",
                    "assistant_question": event["message"],
                    "plan": None, "raw_llm_response": "", "llm_trace": llm_trace,
                },
            }
            return

    result = _build_result(final_text, llm_trace)
    yield {"type": "done", "result": result}
