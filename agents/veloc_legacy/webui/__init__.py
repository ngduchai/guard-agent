"""
Guard Agent Web UI package.

Re-exports the FastAPI ``app`` object so that uvicorn can be pointed at
``agents.veloc.webui:app`` without any changes to existing launch scripts.

Usage (from ``build/run_deploy_webui.sh``)::

    python -m uvicorn agents.veloc.webui:app --host 0.0.0.0 --port 8010
"""

from agents.veloc.webui.app import app  # noqa: F401

__all__ = ["app"]
