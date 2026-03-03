"""
LLM integration for deployment agents: build prompts and call OpenAI or Anthropic
to produce resilience-aware deployment plans and code transformation suggestions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agents.deploy.config import get_settings
from agents.deploy.mcp_client import list_tools

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _tools_context() -> str:
    tools = list_tools()
    if not tools:
        return "No resilience tools are currently available (MCP server not configured or unreachable)."
    parts = ["Available resilience tools (use these to integrate into the deployment plan):"]
    for t in tools:
        name = t.get("name", "?")
        desc = t.get("description", "")
        schema = t.get("inputSchema", {})
        params = schema.get("properties", {})
        required = schema.get("required", [])
        parts.append(f"- **{name}**: {desc}")
        if params:
            parts.append(f"  Parameters: {json.dumps(params)}")
        if required:
            parts.append(f"  Required: {required}")
    return "\n".join(parts)


def _veloc_guide_context(max_chars: int = 4000) -> str:
    """
    Load a summarized VeloC integration guide that teaches the model
    how to inject checkpointing and keep the code compilable.
    """
    guide_path = _REPO_ROOT / "shared" / "veloc_llm_guide.md"
    if not guide_path.exists():
        return "VeloC integration guide not found; rely on general checkpoint/restart best practices."
    text = guide_path.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n[... guide truncated for brevity ...]"
    return text


def build_transform_prompt(
    code: str,
    description: str,
    resilience_requirements: list[dict[str, Any]],
    environment: str,
) -> str:
    req_text = (
        "\n".join(
            f"- {r.get('name', '')}: {r.get('value')} {r.get('unit', '') or ''}".strip()
            for r in resilience_requirements
        )
        if resilience_requirements
        else "None specified."
    )

    return f"""You are an expert in resilient HPC and cloud deployments and in integrating the VeloC checkpointing runtime into existing codebases. Given the user's code and resilience/QoS requirements, you must propose a concrete, **compilable** transformation of the code and a deployment plan that uses the resilience tools where appropriate.

## Available MCP resilience and code tools
The following MCP tools are available to the orchestrator/agent. Use them conceptually in your plan by naming the tool in `tool_used` and giving `tool_args`:

{_tools_context()}

## VeloC integration guide (for this task)
The following guide describes how to inject VeloC checkpoint/restart into HPC applications, where to place VELOC_Init / VELOC_Checkpoint / VELOC_Restart / VELOC_Finalize, and how to adjust the build system:

{_veloc_guide_context()}

## User input
- **Description**: {description}
- **Target environment**: {environment}
- **Resilience/QoS requirements**:
{req_text}

## Code (excerpt)
``` 
{code[:8000]}
```

## Your task
1. Decide how to integrate VeloC-based checkpoint/restart into this codebase so that it remains compilable and runnable on the target environment. Use the guide above and the available MCP tools (especially the code-edit tools and veloc_configure_checkpoint).
2. Describe which files and functions should be changed, what VeloC calls to insert (and where), and what build-system changes (e.g. includes, link flags, CMake/Makefile edits) are needed to produce a resilient executable.
3. Output a JSON object with this exact structure (no markdown fence):
{{
  "summary": "Short summary of the resilient deployment plan and code changes",
  "steps": [
    {{
      "id": "step1",
      "name": "High-level change description",
      "description": "Detailed instructions, including which files/functions to modify, which VeloC calls to insert, and any MCP tools to call (e.g. read_code_file, apply_text_patch, veloc_configure_checkpoint).",
      "tool_used": "tool_name_or_null",
      "tool_args": {{}},
      "order": 1
    }}
  ],
  "transformed_code": "Optional code snippet or patch-style example showing how to instrument a representative function or main loop; null if too large."
}}

Rules:
- If you use an MCP tool in a step, set "tool_used" to the exact tool name and "tool_args" to the arguments for that tool.
- Focus on changes that keep the code compilable: preserve necessary includes, types, and build configuration.
- Order steps by execution order from planning, through code edits, to build and run.
- Output only the JSON object (no extra text or markdown)."""


async def get_deployment_plan_from_llm(
    code: str,
    description: str,
    resilience_requirements: list[dict[str, Any]],
    environment: str,
) -> dict[str, Any]:
    """Call the configured LLM and return the parsed deployment plan."""
    settings = get_settings()
    prompt = build_transform_prompt(code, description, resilience_requirements, environment)

    if settings.llm_provider == "anthropic":
        return await _call_anthropic(prompt, settings)
    return await _call_openai(prompt, settings)


async def _call_openai(prompt: str, settings: Any) -> dict[str, Any]:
    try:
        from openai import AsyncOpenAI
    except ImportError:
        return {"error": "openai package not installed", "raw": ""}
    if not settings.openai_api_key:
        return {"error": "OPENAI_API_KEY not set", "raw": ""}
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.choices[0].message.content or ""
    return _parse_plan_response(raw)


async def _call_anthropic(prompt: str, settings: Any) -> dict[str, Any]:
    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        return {"error": "anthropic package not installed", "raw": ""}
    if not settings.anthropic_api_key:
        return {"error": "ANTHROPIC_API_KEY not set", "raw": ""}
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    msg = await client.messages.create(
        model=settings.llm_model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = (msg.content[0].text if msg.content else "") or ""
    return _parse_plan_response(raw)


def _parse_plan_response(raw: str) -> dict[str, Any]:
    """Extract JSON from model output (allow markdown code block)."""
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
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"summary": "Parse failed", "steps": [], "transformed_code": None, "raw_llm_response": raw}

