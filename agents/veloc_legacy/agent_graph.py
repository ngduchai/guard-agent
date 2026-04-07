"""
VeloC agent entrypoint.

Exposes ``build_agent_graph()`` which returns an object with:
  - ``ainvoke(state)``  – batch mode (used by legacy /api/chat endpoint)
  - ``astream(state)``  – streaming mode (yields event dicts)

Orchestration (tool-calling loop, provider routing) is handled inside
``agents.veloc.agent``.

The primary streaming path is now ``stream_veloc_agent`` in ``agents.veloc.agent``,
consumed directly by the ``/api/stream`` SSE endpoint in ``webui.py`` and by
``start_agent.py``.  The ``_AgentRunner`` wrapper is kept for backward
compatibility with any callers that use the ``ainvoke`` interface.
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Dict

from agents.veloc.agent import run_veloc_agent, stream_veloc_agent


class _AgentRunner:
    """Thin wrapper that provides ``ainvoke`` and ``astream`` for compatibility."""

    async def ainvoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Run the agent in batch mode and return a structured result dict."""
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

    async def astream(self, state: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        """
        Run the agent in streaming mode, yielding event dicts.

        Event types: ``step_summary``, ``step_result``, ``thinking``,
        ``tool_call``, ``tool_result``, ``final``, ``done``, ``error``.
        """
        messages = state.get("messages") or []
        async for event in stream_veloc_agent(messages):
            yield event


def build_agent_graph() -> _AgentRunner:
    """Return an agent runner with ``ainvoke`` and ``astream`` methods."""
    return _AgentRunner()
