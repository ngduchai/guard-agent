"""
Knowledge base routes.

Routes:
  GET    /api/knowledge          – return all KB entries and stats as JSON
  POST   /api/knowledge          – add a new entry
  PUT    /api/knowledge/{id}     – update an existing entry
  DELETE /api/knowledge/{id}     – delete an entry
  GET    /knowledge              – serve the human-readable knowledge browser page
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from agents.veloc.vector_db import (
    add_knowledge_db_entry,
    delete_knowledge_db_entry,
    get_knowledge_db_entries,
    get_knowledge_db_stats,
    update_knowledge_db_entry,
)
from agents.veloc.webui.pages.knowledge import knowledge_browser_html

router = APIRouter()


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class AddEntryBody(BaseModel):
    category: str = Field(default="best_practice")
    title: str
    content: str
    tags: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source: str = Field(default="webui")


class UpdateEntryBody(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    verified: Optional[bool] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

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


@router.post("/api/knowledge")
async def api_knowledge_add(body: AddEntryBody) -> JSONResponse:
    """Add a new knowledge base entry."""
    try:
        entry = add_knowledge_db_entry(
            category=body.category,
            title=body.title,
            content=body.content,
            tags=body.tags,
            confidence=body.confidence,
            source=body.source,
        )
        return JSONResponse({"ok": True, "entry": entry}, status_code=201)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


@router.put("/api/knowledge/{entry_id}")
async def api_knowledge_update(entry_id: str, body: UpdateEntryBody) -> JSONResponse:
    """Update an existing knowledge base entry."""
    try:
        entry = update_knowledge_db_entry(
            insight_id=entry_id,
            title=body.title,
            category=body.category,
            content=body.content,
            tags=body.tags,
            confidence=body.confidence,
            verified=body.verified,
        )
        if entry is None:
            return JSONResponse({"ok": False, "error": f"Entry '{entry_id}' not found."}, status_code=404)
        return JSONResponse({"ok": True, "entry": entry})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


@router.delete("/api/knowledge/{entry_id}")
async def api_knowledge_delete(entry_id: str) -> JSONResponse:
    """Delete a knowledge base entry."""
    try:
        deleted = delete_knowledge_db_entry(entry_id)
        if not deleted:
            return JSONResponse({"ok": False, "error": f"Entry '{entry_id}' not found."}, status_code=404)
        return JSONResponse({"ok": True, "deleted_id": entry_id})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


@router.get("/knowledge", response_class=HTMLResponse)
async def knowledge_browser() -> HTMLResponse:
    """Serve a human-readable, searchable browser for the knowledge base."""
    return HTMLResponse(content=knowledge_browser_html())
