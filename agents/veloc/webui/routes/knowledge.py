"""
Knowledge base routes.

Routes:
  GET /api/knowledge  – return all KB entries and stats as JSON
  GET /knowledge      – serve the human-readable knowledge browser page
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, JSONResponse

from agents.veloc.vector_db import get_knowledge_db_entries, get_knowledge_db_stats
from agents.veloc.webui.pages.knowledge import knowledge_browser_html

router = APIRouter()


@router.get("/api/knowledge")
async def api_knowledge(
    category: Optional[str] = Query(default=None),
) -> JSONResponse:
    """Return all knowledge base entries and stats as JSON."""
    try:
        stats = get_knowledge_db_stats()
        entries = get_knowledge_db_entries(category=category)
        return JSONResponse({"stats": stats, "entries": entries})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.get("/knowledge", response_class=HTMLResponse)
async def knowledge_browser() -> HTMLResponse:
    """Serve a human-readable, searchable browser for the knowledge base."""
    return HTMLResponse(content=knowledge_browser_html())
