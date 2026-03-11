"""
VeloC code-injection agent using the OpenAI Agents SDK.

Orchestration is done by the LLM via tools. See:
https://openai.github.io/openai-agents-python/multi_agent/
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from agents.veloc.config import get_settings
from agents.veloc._sdk_loader import get_sdk_tools_list

VELOC_AGENT_INSTRUCTIONS = """You are an expert in resilient HPC/cloud deployments and in integrating the VeloC API into existing codebases. You help users understand how to transform their code into VeloC-checkpointed, fault-tolerant applications.

You have SDK-hosted tools available (e.g. web search, code interpreter). Use them when helpful to look up VeloC documentation, checkpoint/restart patterns, and resilience best practices.

## Workflow

1. **Check input.** If the user has not clearly described their application, target environment, or resilience requirements, respond with a single JSON object and nothing else:
   { "status": "ask", "assistant_question": "One clear question asking for ALL missing information (code location, environment, resilience goals)." }

2. **If you have enough information**, use your tools to research VeloC API usage, configuration, and integration patterns as needed. Then respond with a single JSON object and nothing else:
   { "status": "plan", "plan": { "summary": "Short summary of the recommended approach", "steps": [ { "id": "...", "name": "...", "description": "...", "order": 0 } ], "transformed_code": "optional code snippet or null" } }

3. **Output format.** You must end your final reply with exactly one JSON object (no markdown fences, no extra text after it). Either:
   { "status": "ask", "assistant_question": "..." } when you need more information, or
   { "status": "plan", "plan": { "summary": "...", "steps": [...], "transformed_code": "..." or null } } when done.
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
    return Agent(
        name="VeloC injection",
        instructions=VELOC_AGENT_INSTRUCTIONS,
        model=settings.llm_model,
        tools=get_sdk_tools_list(),
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
    result = await Runner.run(agent, user_message)
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

    return {
        "status": "error",
        "assistant_question": str(data.get("assistant_question", raw[:500])),
        "plan": None,
        "raw_llm_response": raw,
        "llm_trace": llm_trace,
    }
