"""
VeloC deployment agent entrypoint (OpenAI Agents SDK).

This module exposes build_agent_graph() returning an object with ainvoke(state)
so that start_agent and webui can keep the same API. Orchestration is done
by the LLM inside the single agent (see agents/veloc/agent.py); no LangGraph.
"""

from __future__ import annotations

from typing import Any, Dict

from agents.veloc.agent import run_veloc_agent


class _AgentRunner:
    """Thin wrapper that provides ainvoke(state) for compatibility with existing entrypoints."""

    async def ainvoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        messages = state.get("messages") or []
        result = await run_veloc_agent(messages)
        out = dict(state)
        out.update(result)
        if result.get("status") == "ask" and result.get("assistant_question"):
            out.setdefault("messages", [])
            out["messages"].append({
                "role": "assistant",
                "content": result["assistant_question"],
            })
        return out


def build_agent_graph() -> _AgentRunner:
    """Build the VeloC agent runner (OpenAI Agents SDK). Returns an object with ainvoke(state)."""
    return _AgentRunner()
