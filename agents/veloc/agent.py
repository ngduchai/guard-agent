"""
VeloC code-injection agent.

The agent receives a user prompt describing an application codebase and its
checkpoint/resilience requirements, then:
  1. Explores the codebase using filesystem tools.
  2. Injects VeloC checkpoint calls where needed.
  3. Writes the modified files back to the output directory.
  4. Validates the resilient version against the baseline. 

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

  {"type": "thinking",   "turn": N, "text": "..."}
  {"type": "tool_call",  "turn": N, "name": "...", "args": {...}}
  {"type": "tool_result","turn": N, "name": "...", "result": "..."}
  {"type": "done",       "result": {...}}   # final structured result dict
  {"type": "error",      "message": "..."}
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, AsyncIterator, Callable, Dict, List, Tuple

from agents.veloc.config import get_llm_client, get_project_root, get_settings
from agents.veloc.filesync_tools import list_directory, read_file, write_file
from agents.veloc.validation_tools import validate_resilient_output


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

## Workflow
1. **Understand the request.** If the user's prompt is missing the code path, target environment, or resilience requirements, ask for the missing information.
2. **Explore the codebase.** Use `list_directory` and `read_file` to understand the code structure and identify where checkpoints should be added.
3. **Inject VeloC.** Modify the source files to add VeloC checkpoint/restart calls and write a `veloc.cfg` configuration file. Follow the VeloC C API (VELOC_Init, VELOC_Mem_protect, VELOC_Checkpoint, VELOC_Restart, VELOC_Finalize).
4. **Write files.** Use `write_file` to save all modified sources and the config.
5. **Validate.** This step is **REQUIRED** Build and run both original code and your generated code. For the generated code, inject failures in the middle of execution then restart the execution (if needed) to test resiliency. Compare the output of both execution, validation passes if two outputs are similar. May ask user for execution instruction and output comparision if needed. If validation fails, check the error log, fix error, then run the validation again.
6. **Report.** Return **ONLY** JSON object (no markdown fences) with one of these shapes:
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
    # "validate_resilient_output": validate_resilient_output,
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
                "name": "validate_resilient_output",
                "description": (
                    "Build and run baseline and resilient applications with failure injection, "
                    "then compare their outputs. Returns status, exit_code, and log tails."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "baseline_source_dir":       {"type": "string"},
                        "baseline_build_dir":        {"type": "string"},
                        "baseline_executable_name":  {"type": "string"},
                        "resilient_source_dir":      {"type": "string"},
                        "resilient_build_dir":       {"type": "string"},
                        "resilient_executable_name": {"type": "string"},
                        "output_dir":                {"type": "string"},
                        "baseline_args":             {"type": "string", "default": ""},
                        "resilient_args":            {"type": "string", "default": ""},
                        "num_procs":                 {"type": "integer", "default": 4},
                        "max_attempts":              {"type": "integer", "default": 10},
                        "injection_delay":           {"type": "number",  "default": 5.0},
                        "output_file_name":          {"type": "string",  "default": "recon.h5"},
                        "comparison_method":         {"type": "string",  "enum": ["ssim", "sha256"], "default": "ssim"},
                        "ssim_threshold":            {"type": "number",  "default": 0.9999},
                        "hdf5_dataset":              {"type": "string",  "default": "data"},
                        "install_resilient":         {"type": "boolean", "default": False},
                        "veloc_config_name":         {"type": "string",  "default": "veloc.cfg"},
                    },
                    "required": [
                        "baseline_source_dir", "baseline_build_dir", "baseline_executable_name",
                        "resilient_source_dir", "resilient_build_dir", "resilient_executable_name",
                        "output_dir",
                    ],
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
        tool calls.

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

def _extract_json(raw: str) -> str:
    """Extract the first top-level JSON object from *raw*.

    The LLM sometimes wraps its JSON in a markdown code fence (```json ... ```)
    and may also include prose before/after the fence.  Nested code fences
    inside the JSON string values (e.g. bash examples in a ``summary`` field)
    make it unsafe to locate the closing fence by simple string search.

    Strategy: ignore fences entirely and use brace-depth tracking on the full
    text to find the first complete ``{...}`` object.  This is robust against
    nested fences, prose preambles, and trailing text.
    """
    text = raw.strip()
    start = text.find("{")
    if start == -1:
        return text
    depth, in_str, escape = 0, False, False
    for i, c in enumerate(text[start:], start):
        if escape:
            escape = False; continue
        if c == "\\" and in_str:
            escape = True; continue
        if c == '"':
            in_str = not in_str; continue
        if not in_str:
            if c == "{": depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
    brace = text.rfind("}")
    return text[start:brace + 1] if brace != -1 else text[start:]


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
