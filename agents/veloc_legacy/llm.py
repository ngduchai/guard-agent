"""
LLM integration for the VeloC agent.

The agent uses the ``openai`` Python client directly with a manual tool-calling
loop, so it works with any OpenAI-compatible API endpoint.

Provider selection (LLM_PROVIDER env var):
  - ``openai``  – real OpenAI endpoint.
  - ``argo``    – Argonne OpenAI-compatible proxy.
  - ``generic`` – any custom OpenAI-compatible endpoint (set LLM_BASE_URL + LLM_API_KEY).

See ``agents.veloc.config.get_llm_client`` for client construction and
``agents.veloc.agent.run_veloc_agent`` for the agentic loop.
"""

from __future__ import annotations

from pathlib import Path

from agents.veloc.config import get_settings  # noqa: F401 – re-exported for convenience

_REPO_ROOT = Path(__file__).resolve().parents[2]
