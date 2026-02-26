"""
LLM integration: build prompts and call OpenAI or Anthropic to produce a deployment plan.
"""

import json
from typing import Any

from orchestrator.config import get_settings
from orchestrator.mcp_client import list_tools


# Static fallback when MCP server is not configured (e.g. MCP_SERVER_ARGS unset)
STATIC_TOOLS = [
    {
        "name": "veloc_configure_checkpoint",
        "description": "Configure VeLoC checkpointing (interval, dir, compression) for fault tolerance.",
        "inputSchema": {"properties": {"checkpoint_interval_seconds": {}, "checkpoint_dir": {}}, "required": ["checkpoint_interval_seconds", "checkpoint_dir"]},
    },
    {
        "name": "load_balance_configure",
        "description": "Configure load balancing (strategy, health check) for availability.",
        "inputSchema": {"properties": {"strategy": {}}, "required": ["strategy"]},
    },
    {
        "name": "scaler_configure",
        "description": "Configure auto-scaling (min/max replicas, metric) for elasticity.",
        "inputSchema": {"properties": {"min_replicas": {}, "max_replicas": {}}, "required": ["min_replicas", "max_replicas"]},
    },
]


def _tools_context() -> str:
    tools = list_tools()
    if not tools:
        tools = STATIC_TOOLS
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


def build_transform_prompt(
    code: str,
    description: str,
    resilience_requirements: list[dict[str, Any]],
    environment: str,
) -> str:
    req_text = "\n".join(
        f"- {r.get('name', '')}: {r.get('value')} {r.get('unit', '') or ''}".strip()
        for r in resilience_requirements
    ) if resilience_requirements else "None specified."

    return f"""You are an expert in resilient deployments for HPC and cloud. Given the user's code and resilience/QoS requirements, produce a deployment plan that integrates the following resilience tools where appropriate.

## Available resilience tools
{_tools_context()}

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
1. Decide which of the available tools (if any) to use to meet the resilience/QoS requirements.
2. Output a JSON object with this exact structure (no markdown fence):
{{
  "summary": "Short summary of the deployment plan",
  "steps": [
    {{ "id": "step1", "name": "...", "description": "...", "tool_used": "tool_name_or_null", "tool_args": {{}}, "order": 1 }}
  ],
  "transformed_code": "optional code snippet or null"
}}
If you use a tool, set "tool_used" to the tool name and "tool_args" to the arguments for that tool. Order steps by execution order. Output only the JSON object."""


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
