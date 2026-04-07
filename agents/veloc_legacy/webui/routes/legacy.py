"""
Legacy and utility routes.

Routes:
  GET  /api/logs   – list session log files under BUILD_DIR/log/
  POST /api/chat   – single-step batch interaction (kept for backward compat)
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from agents.veloc.config import get_project_root

router = APIRouter()

# GRAPH is imported lazily inside the route to avoid a circular import at
# module load time (build_agent_graph may import from this package).
_GRAPH = None


def _get_graph():
    """Return the singleton agent graph, building it on first call."""
    global _GRAPH
    if _GRAPH is None:
        from agents.veloc.agent_graph import build_agent_graph
        _GRAPH = build_agent_graph()
    return _GRAPH


@router.get("/api/logs")
async def api_logs() -> JSONResponse:
    """
    List all session log files saved under ``BUILD_DIR/log/``.

    Each entry contains:
      - ``filename``   – the JSON filename (e.g. ``art_simple_20260320.json``).
      - ``path``       – absolute path on the server.
      - ``size_bytes`` – file size.
      - ``modified_at``– ISO-8601 UTC last-modified timestamp.
      - ``codebase``   – extracted from the filename (part before the date).
      - ``date``       – date string from the filename (YYYYMMDD).
    """
    log_dir = Path(get_project_root()) / "log"
    if not log_dir.exists():
        return JSONResponse({"logs": []})

    entries = []
    for p in sorted(log_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
        stat = p.stat()
        # Parse codebase and date from filename: <codebase>_<YYYYMMDD>[_N].json
        stem = p.stem  # e.g. "art_simple_20260320" or "art_simple_20260320_2"
        m = re.match(r"^(.+?)_(\d{8})(?:_\d+)?$", stem)
        codebase = m.group(1) if m else stem
        date_str = m.group(2) if m else ""
        modified_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        entries.append({
            "filename": p.name,
            "path": str(p),
            "size_bytes": stat.st_size,
            "modified_at": modified_at,
            "codebase": codebase,
            "date": date_str,
        })
    return JSONResponse({"logs": entries})


@router.post("/api/chat", response_class=JSONResponse)
async def api_chat(request: Request) -> JSONResponse:
    """Single-step interaction with the deployment agent (OpenAI Agents SDK)."""
    payload: Dict[str, Any] = await request.json()
    message: str = (payload.get("message") or "").strip()
    state: Dict[str, Any] = payload.get("state") or {}
    if "messages" not in state or not isinstance(state["messages"], list):
        state["messages"] = []

    if not message:
        return JSONResponse(
            {
                "status": "error",
                "assistant_question": "Empty message; please provide a description of your code and resilience goals.",
                "state": state,
            },
            status_code=400,
        )

    state["messages"].append({"role": "user", "content": message})

    graph = _get_graph()
    result = await graph.ainvoke(state)
    combined_state: Dict[str, Any] = dict(state)
    combined_state.update(result)

    status = result.get("status", "error")
    assistant_question = result.get("assistant_question")
    plan = result.get("plan")
    summary = result.get("summary")
    raw_llm = result.get("raw_llm_response")
    llm_trace = result.get("llm_trace")

    return JSONResponse(
        {
            "status": status,
            "assistant_question": assistant_question,
            "plan": plan,
            "summary": summary,
            "raw_llm_response": raw_llm,
            "llm_trace": llm_trace,
            "state": combined_state,
        }
    )
