"""
VeloC agent entrypoint.

Exposes ``build_agent_graph()`` which returns an object with ``ainvoke(state)``
so that ``start_agent`` and ``webui`` share the same interface.

Orchestration (tool-calling loop, provider routing) is handled inside
``agents.veloc.agent.run_veloc_agent``.
"""

from __future__ import annotations

from typing import Any, Dict

from agents.veloc.agent import run_veloc_agent


class _AgentRunner:
    """Thin wrapper that provides ``ainvoke(state)`` for compatibility with existing entrypoints."""

    async def ainvoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        messages = state.get("messages") or []
        result = await run_veloc_agent(messages)
        out = dict(state)
        out.update(result)
        # Append the agent's follow-up question to the conversation history.
        if result.get("status") == "ask" and result.get("assistant_question"):
            out.setdefault("messages", [])
            out["messages"].append({
                "role": "assistant",
                "content": result["assistant_question"],
            })
        return out


def build_agent_graph() -> _AgentRunner:
    """Return an agent runner with an ``ainvoke(state)`` method."""
    return _AgentRunner()
