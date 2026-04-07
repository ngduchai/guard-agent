"""
Metrics routes: ``GET /api/metrics/export`` and ``GET /api/metrics/list``.

Provides download and listing of in-memory session performance metrics.
"""

from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, Response

from agents.veloc.webui.sse import _session_metrics, _session_order

router = APIRouter()


@router.get("/api/metrics/export")
async def api_metrics_export(
    session_id: Optional[str] = Query(default=None, description="Session ID to export"),
) -> Response:
    """
    Download the full metrics JSON for a completed session.

    Query parameter:
      ``session_id`` – the UUID returned in the ``done`` SSE event's
      ``metrics.session_id`` field.  If omitted, the most recent session is
      returned.

    Returns a JSON file download (``Content-Disposition: attachment``).
    The download filename matches the log file naming convention:
    ``<codebase>_<YYYYMMDD>.json``.
    """
    if session_id and session_id in _session_metrics:
        data = _session_metrics[session_id]
    elif _session_order:
        # Fall back to the most recent session.
        data = _session_metrics.get(_session_order[-1])
    else:
        data = None

    if data is None:
        return JSONResponse(
            {"error": "No metrics available. Run the agent first."},
            status_code=404,
        )

    # Build a filename that matches the log/ file naming convention.
    codebase = data.get("codebase") or data.get("session_id", "unknown")
    started_at = data.get("started_at", "")
    date_str = started_at[:10].replace("-", "") if started_at else "unknown"
    filename = f"{codebase}_{date_str}.json"
    content = json.dumps(data, indent=2, ensure_ascii=False)
    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/api/metrics/list")
async def api_metrics_list() -> JSONResponse:
    """Return a list of available session IDs with their summary stats."""
    sessions = []
    for sid in reversed(_session_order):
        m = _session_metrics.get(sid, {})
        # Support both full format (summary nested under "summary") and compact
        # format (aggregate fields at the top level).
        s = m.get("summary") or {}
        sessions.append({
            "session_id": sid,
            "started_at": m.get("started_at"),
            "finished_at": m.get("finished_at"),
            "total_elapsed_s": m.get("total_elapsed_s"),
            "total_turns": s.get("total_turns") or m.get("total_turns"),
            "total_tool_calls": s.get("total_tool_calls") or m.get("total_tool_calls"),
            "total_tokens": s.get("total_tokens") or m.get("total_tokens"),
            "final_status": s.get("final_status") or m.get("final_status"),
            "codebase": m.get("codebase"),
        })
    return JSONResponse({"sessions": sessions})
