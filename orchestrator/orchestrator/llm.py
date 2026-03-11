"""
Orchestrator LLM: produce deployment plans using the OpenAI Agents SDK.

Uses Agent + Runner with SDK-hosted tools only (WebSearchTool, CodeInterpreterTool, etc.).
See https://openai.github.io/openai-agents-python/tools/#hosted-tools
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from agents.veloc._sdk_loader import get_sdk_tools_list


def _get_settings() -> Dict[str, Any]:
    """Orchestrator LLM settings from environment."""
    return {
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "llm_model": os.getenv("ORCHESTRATOR_LLM_MODEL", "gpt-4o"),
    }


async def get_deployment_plan_from_llm(
    code: str,
    description: str,
    resilience_requirements: List[Dict[str, Any]],
    environment: str,
) -> Dict[str, Any]:
    """
    Call the LLM with resilience tools via the OpenAI Agents SDK (Agent + Runner).
    Returns a dict with: summary, steps, transformed_code, raw_llm_response; or error key.
    """
    settings = _get_settings()
    if not settings.get("openai_api_key"):
        return {"error": "OPENAI_API_KEY not set"}

    try:
        from agents.veloc._sdk_loader import Agent, Runner
    except ImportError:
        return {"error": "openai-agents not installed"}

    reqs_text = (
        "\n".join(
            f"- {r.get('name', '')}: {r.get('value', '')} {r.get('unit', '') or ''}"
            for r in resilience_requirements
        )
        if resilience_requirements
        else "None specified."
    )

    user_content = f"""You are an expert in resilient HPC/cloud deployments. Given the following inputs, produce a deployment plan that integrates checkpointing/resilience (e.g. VeloC) where appropriate.

## Code or code reference
{code}

## Description
{description}

## Resilience / QoS requirements
{reqs_text}

## Target environment
{environment}

You may use the provided SDK tools (e.g. web search, code interpreter) when helpful. When you are done, respond with a single JSON object (no markdown fences) with this shape:
{{ "summary": "Short summary of the plan", "steps": [ {{ "id": "...", "name": "...", "description": "...", "order": 0 }} ], "transformed_code": "optional code snippet or null" }}
"""

    agent = Agent(
        name="Orchestrator",
        instructions="Use the provided tools when helpful. Respond with the requested JSON when done.",
        model=settings["llm_model"],
        tools=get_sdk_tools_list(),
    )
    result = await Runner.run(agent, user_content)
    raw = (result.final_output or "").strip()
    if not raw:
        return {
            "summary": "No plan generated.",
            "steps": [],
            "transformed_code": None,
            "raw_llm_response": raw,
        }

    # Strip markdown code fence if present
    text = raw
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
        data = json.loads(text)
    except json.JSONDecodeError:
        return {
            "summary": raw[:500] + ("..." if len(raw) > 500 else ""),
            "steps": [],
            "transformed_code": None,
            "raw_llm_response": raw,
        }

    summary = data.get("summary", "")
    steps = data.get("steps") or []
    if not isinstance(steps, list):
        steps = []
    transformed_code = data.get("transformed_code")

    return {
        "summary": summary,
        "steps": steps,
        "transformed_code": transformed_code,
        "raw_llm_response": raw,
    }
