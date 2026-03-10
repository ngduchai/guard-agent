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
