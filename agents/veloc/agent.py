"""
VeloC code-injection agent using the OpenAI Agents SDK.

Orchestration is done by the LLM via tools. See:
https://openai.github.io/openai-agents-python/multi_agent/
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from agents.veloc.config import get_settings, get_project_root
from agents.veloc._sdk_loader import get_sdk_tools_list
from agents.veloc.filesync_tools import list_directory, read_file, write_file


def _veloc_agent_instructions() -> str:
    root = get_project_root()
    return f"""You are an expert in resilient HPC/cloud deployments and in integrating the VeloC API into existing codebases. You help users understand how to transform their code into VeloC-checkpointed, fault-tolerant applications.

**Project root (user's machine).** The user's project root on their machine is `{root}`. You run in a separate environment (e.g. a sandbox) and **cannot access the user's filesystem** or that path. Always use **relative path names** when referring to files (e.g. `examples/matrix_mul_mpi`, `examples/matrix_mul_mpi/code.c`) so the user knows where to place outputs. Create workspaces and files **in your own environment** (e.g. in your current working directory). When the user asks to transform code under e.g. `examples/matrix_mul_mpi`, either: (1) ask them to paste the relevant file contents so you can transform and return the new contents, or (2) generate the VeloC-instrumented code and config yourself and return the full file contents in your response with the relative path (e.g. "Save as examples/matrix_mul_mpi/code.c"). Do not claim that the user's path "does not exist"; it exists on the user's machine.

You have SDK-hosted tools available (e.g. web search, code interpreter). Use them when helpful to look up VeloC documentation, checkpoint/restart patterns, and resilience best practices.

You have custom tools to access and modify files on the user's machine (paths are relative to the project root):
- list_directory(dir_path): List files and subdirectories in a directory. Returns entry names, type (file/dir), and file sizes.
- read_file(file_path): Read the full contents of a text file.
- write_file(file_path, contents): Write contents to a file; creates parent directories if needed.
Use these tools to read the user's code, then write back modified or new files (e.g. VeloC-instrumented code and config) under the output path they specify.

## Workflow

Step1. **Check input.**
If the user has not clearly described their application, target environment, or resilience
requirements, ask the user to provide the missing information until all information is provided.

Step 2. **If you have enough information, then Prepare the workspace.**
Use list_directory and read_file on the user's input path (e.g. examples/matrix_mul_mpi) to load the code. Ask for the path if not provided.

Step 3. ** Apply VeloC for resiliency**,
Using the code you read from the user's machine, discover:
- the workflow structure of the code
- critical data that needs to be checkpointed
- identify the control patterns to detect where and when to checkpoint the critical data
apply VeloC checkpoints and configuration to the code to meet the user's resilience requirements.
The VeloC API are available at [VeloC API](https://veloc.readthedocs.io/en/latest/api.html#api-specifications).
The VeloC Configuration is available at [VeloC Configuration](https://veloc.readthedocs.io/en/latest/userguide.html#execution).

Step 4. **Build the code.**
Write the VeloC-instrumented files with write_file to the user's output path. Check if the project has a build system (e.g. CMakeLists.txt, Makefile).
If there is a build system, use your tools to build the code with this build system.
If there is no build system, use your tools to build the code with the CMake build system.
For VeloC, if it is not installed, download it from the
[VeloC GitHub repository](https://github.com/ECP-VeloC/VELOC)
and install it in the workspace directory then integrate it into the build system.

Step 5. **Run the code.**
Use your tools to run the code in the workspace directory.
If the code is not running, use your tools to debug the code until it is running.

Step 6. **Complete the task.**
Ensure all modified and new files have been written to the user's output path with write_file. Return a summary of the task and the paths written.

**After completing a step, return a summary of the task and plan for the next step, then ask the user if they want to continue or stop.**

**Output format.** For every step above, unless you need to ask the user for more information,
silently proceed to the next step until complete with sucess status.
If you got errors, or need to return before completing the task, return with error status.
If you need to ask the user for more information, return with ask status.
The return response should be a single JSON object (no markdown fences, no extra text after it)
with the following format:
   {{ "status": "ask", "assistant_question": "..." }} when you need more information, or
   {{ "status": "success", "summary": "..." }} when the task is completed successfully, or
   {{ "status": "error", "error_message": "..." }} when the task is completed with errors.
"""


def _extract_json(raw: str) -> str:
    """Strip markdown code fences and return the first top-level JSON object (brace-matched)."""
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
    # Find first '{' and its matching '}' so we don't include extra trailing braces
    start = text.find("{")
    if start == -1:
        return text
    depth = 0
    in_string = False
    escape = False
    quote = '"'
    i = start
    n = len(text)
    while i < n:
        c = text[i]
        if escape:
            escape = False
            i += 1
            continue
        if c == "\\" and in_string:
            escape = True
            i += 1
            continue
        if c == quote and not escape:
            in_string = not in_string
            i += 1
            continue
        if not in_string:
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
        i += 1
    # Fallback: first { to last } (original behavior)
    brace = text.rfind("}")
    if brace != -1:
        return text[start : brace + 1]
    return text[start:]


def _repair_json_string_values(text: str) -> str:
    """Replace unescaped newlines/tabs inside JSON string values so parsing can succeed."""
    result = []
    i = 0
    n = len(text)
    in_string = False
    escape_next = False
    # Track whether we're in a key or value (value can be string with code blocks)
    while i < n:
        c = text[i]
        if escape_next:
            result.append(c)
            escape_next = False
            i += 1
            continue
        if c == "\\" and in_string:
            result.append(c)
            escape_next = True
            i += 1
            continue
        if c == '"':
            in_string = not in_string
            result.append(c)
            i += 1
            continue
        if in_string and c in ("\n", "\r", "\t"):
            result.append("\\n" if c == "\n" else ("\\r" if c == "\r" else "\\t"))
            i += 1
            continue
        result.append(c)
        i += 1
    return "".join(result)


def _parse_agent_json(text: str):
    """Parse extracted JSON, with fallbacks for double-encoding and unescaped newlines."""
    text = text.strip()
    # Fallback 1: whole response might be a JSON-encoded string (double-encoded)
    if text.startswith('"') and text.endswith('"'):
        try:
            decoded = json.loads(text)
            if isinstance(decoded, str):
                return json.loads(decoded)
        except (json.JSONDecodeError, TypeError):
            pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fallback 2: repair unescaped newlines inside string values (e.g. transformed_code)
    repaired = _repair_json_string_values(text)
    return json.loads(repaired)


def get_veloc_agent():
    """Build the VeloC agent (OpenAI Agents SDK) with tools."""
    from agents.veloc._sdk_loader import Agent

    if Agent is None:
        raise RuntimeError("OpenAI Agents SDK (openai-agents) is not installed")
    settings = get_settings()
    tools = get_sdk_tools_list() + [list_directory, read_file, write_file]
    return Agent(
        name="VeloC injection",
        instructions=_veloc_agent_instructions(),
        model=settings.llm_model,
        tools=tools,
    )


async def run_veloc_agent(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Run the VeloC agent on a conversation. Uses OpenAI Agents SDK Runner.
    Returns a dict with status, assistant_question, plan, raw_llm_response, llm_trace.
    """
    from agents.veloc._sdk_loader import Runner

    if Runner is None:
        return {
            "status": "error",
            "assistant_question": "OpenAI Agents SDK (openai-agents) is not installed.",
            "plan": None,
            "raw_llm_response": "",
            "llm_trace": [],
        }
    settings = get_settings()
    if not messages:
        return {
            "status": "ask",
            "assistant_question": (
                "Please describe your application: which code or code path should be made resilient, "
                "target environment (e.g. HPC cluster), and where to put the transformed code (workspace path)."
            ),
            "plan": None,
            "raw_llm_response": "",
            "llm_trace": [],
        }
    # Non-OpenAI: we could fall back to a simple LLM call; for now require OpenAI for tools
    if settings.llm_provider != "openai":
        return {
            "status": "error",
            "assistant_question": "VeloC agent requires OpenAI provider (tool-calling). Set llm_provider=openai.",
            "plan": None,
            "raw_llm_response": "",
            "llm_trace": [],
        }
    if not settings.openai_api_key:
        return {
            "status": "error",
            "assistant_question": "OPENAI_API_KEY is not set.",
            "plan": None,
            "raw_llm_response": "",
            "llm_trace": [],
        }

    # Single user message: last user content or concatenate conversation
    parts = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "user":
            parts.append(content)
        else:
            parts.append(f"[Assistant]: {content}")
    user_message = "\n\n".join(parts) if parts else ""

    agent = get_veloc_agent()
    try:
        result = await Runner.run(agent, user_message, max_turns=20)
    except Exception as exc:
        # Surface MaxTurnsExceeded and similar errors back to the user as a structured error.
        return {
            "status": "error",
            "assistant_question": f"Agent run failed: {exc!r}",
            "plan": None,
            "raw_llm_response": "",
            "llm_trace": [],
        }
    raw = (result.final_output or "").strip()
    llm_trace = []  # SDK doesn't expose per-step trace the same way; optional: from result.new_items

    if not raw:
        return {
            "status": "error",
            "assistant_question": "Agent returned no output.",
            "plan": None,
            "raw_llm_response": raw,
            "llm_trace": llm_trace,
        }

    text = _extract_json(raw)
    try:
        data = _parse_agent_json(text)
    except json.JSONDecodeError:
        return {
            "status": "error",
            "assistant_question": "Agent output could not be parsed as JSON. Please try again.",
            "plan": None,
            "raw_llm_response": raw,
            "llm_trace": llm_trace,
        }

    status = str(data.get("status", "")).lower()
    if status == "ask":
        return {
            "status": "ask",
            "assistant_question": str(data.get("assistant_question", "Please provide more details.")),
            "plan": None,
            "raw_llm_response": raw,
            "llm_trace": llm_trace,
        }
    if status == "plan":
        plan = data.get("plan")
        if not isinstance(plan, dict):
            plan = {"summary": raw[:500], "steps": [], "transformed_code": None}
        return {
            "status": "plan",
            "assistant_question": None,
            "plan": plan,
            "raw_llm_response": raw,
            "llm_trace": llm_trace,
        }
    if status == "success":
        return {
            "status": "success",
            "assistant_question": None,
            "summary": str(data.get("summary", "")),
            "plan": None,
            "raw_llm_response": raw,
            "llm_trace": llm_trace,
        }

    return {
        "status": "error",
        "assistant_question": str(data.get("assistant_question", data.get("error_message", raw[:500]))),
        "plan": None,
        "raw_llm_response": raw,
        "llm_trace": llm_trace,
    }
