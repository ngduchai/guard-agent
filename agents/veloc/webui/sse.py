"""
SSE (Server-Sent Events) helper and in-memory session metrics store.

Provides:
- ``_store_session_metrics`` – persist metrics from a completed agent run.
- ``_sse_generator``         – async generator that streams agent events as SSE.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator, Dict, List

from agents.veloc.agent import stream_veloc_agent

# ---------------------------------------------------------------------------
# In-memory metrics store
# ---------------------------------------------------------------------------
# Maps session_id → full metrics dict (from the "done" SSE event).
# Keeps the last 20 sessions to avoid unbounded memory growth.
_MAX_STORED_SESSIONS = 20
_session_metrics: Dict[str, Dict[str, Any]] = {}
_session_order: List[str] = []   # insertion-order list of session IDs

# Interval (seconds) between SSE keep-alive comments sent while waiting for
# the LLM to respond.  Browsers and proxies typically time out idle SSE
# connections after 30–60 s; 15 s is a safe default.
_SSE_HEARTBEAT_INTERVAL = 15


def _store_session_metrics(metrics: Dict[str, Any]) -> None:
    """Store metrics for a session, evicting the oldest if over the limit."""
    session_id = metrics.get("session_id")
    if not session_id:
        return
    if session_id not in _session_metrics:
        _session_order.append(session_id)
    _session_metrics[session_id] = metrics
    # Evict oldest sessions beyond the cap.
    while len(_session_order) > _MAX_STORED_SESSIONS:
        oldest = _session_order.pop(0)
        _session_metrics.pop(oldest, None)


async def _sse_generator(messages: List[Dict[str, str]]) -> AsyncIterator[str]:
    """Yield SSE-formatted strings from stream_veloc_agent events.

    Interleaves periodic SSE keep-alive comments (`: keep-alive`) so that
    browsers and reverse-proxies do not close the connection while the LLM
    is thinking (which can take 30–120 s per turn).
    """
    # Use an asyncio.Queue to decouple the agent coroutine from the SSE
    # generator.  The agent pushes events into the queue; the generator
    # drains the queue and sends heartbeats whenever the queue is empty.
    queue: asyncio.Queue = asyncio.Queue()
    _DONE = object()  # sentinel value

    async def _run_agent() -> None:
        """Run the agent and push events into the queue; push _DONE when done."""
        try:
            async for event in stream_veloc_agent(messages):
                await queue.put(event)
        except Exception as exc:
            await queue.put({"type": "error", "message": str(exc)})
        finally:
            await queue.put(_DONE)  # sentinel: agent finished

    agent_task = asyncio.ensure_future(_run_agent())
    try:
        while True:
            # Wait for the next item with a heartbeat timeout.
            # asyncio.wait_for cancels queue.get() on timeout; the item (if any
            # arrived just before cancellation) stays in the queue because
            # queue.get() only removes an item on successful completion.
            try:
                item = await asyncio.wait_for(
                    queue.get(), timeout=_SSE_HEARTBEAT_INTERVAL
                )
            except asyncio.TimeoutError:
                # No event arrived within the heartbeat window — send a
                # keep-alive comment so the connection stays open.
                yield ": keep-alive\n\n"
                continue

            if item is _DONE:
                # Sentinel: agent has finished.
                break

            # Capture full metrics from the "done" event for later download.
            # Prefer "full_metrics" (complete SessionMetrics dict with turns,
            # conversation, conversation_events) over the compact "metrics" summary.
            if isinstance(item, dict) and item.get("type") == "done":
                m = (
                    item.get("full_metrics")
                    or item.get("metrics")
                    or (item.get("result") or {}).get("metrics")
                )
                if m:
                    _store_session_metrics(m)

            data = json.dumps(item, ensure_ascii=False)
            yield f"data: {data}\n\n"
    finally:
        agent_task.cancel()
        try:
            await agent_task
        except (asyncio.CancelledError, Exception):
            pass
