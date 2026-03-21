"""
SSE streaming route: ``POST /api/stream``.

Streams agent events as Server-Sent Events to the browser.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from agents.veloc.webui.sse import _sse_generator

router = APIRouter()


@router.post("/api/stream")
async def api_stream(request: Request) -> StreamingResponse:
    """
    Stream agent events as Server-Sent Events.

    Accepts JSON body: ``{"messages": [{"role": "user"|"assistant", "content": "..."}]}``

    Each SSE event is a JSON-encoded agent event dict.  The final event has
    ``type == "done"`` and contains the structured result.
    """
    payload: Dict[str, Any] = await request.json()
    messages: List[Dict[str, str]] = payload.get("messages") or []

    return StreamingResponse(
        _sse_generator(messages),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
