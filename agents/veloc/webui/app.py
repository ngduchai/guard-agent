"""
FastAPI application factory for the Guard Agent Web UI.

Creates the ``app`` instance and registers all route modules.

The ``app`` object is re-exported from ``agents.veloc.webui`` (the package
``__init__.py``) so that uvicorn can be pointed at ``agents.veloc.webui:app``
without any changes to the existing launch scripts.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from agents.veloc.webui.pages.index import index_html
from agents.veloc.webui.pages.replay import replay_html
from agents.veloc.webui.routes import files, knowledge, legacy, metrics, stream

app = FastAPI(title="Guard Agent Deployment Web UI")

# ── Page routes ──────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    """Serve the main chat-style single-page web UI."""
    return index_html()


@app.get("/replay", response_class=HTMLResponse)
async def replay_page() -> str:
    """Serve the session replay page."""
    return replay_html()


# ── API / browser routes ──────────────────────────────────────────────────────

app.include_router(stream.router)
app.include_router(metrics.router)
app.include_router(files.router)
app.include_router(knowledge.router)
app.include_router(legacy.router)
