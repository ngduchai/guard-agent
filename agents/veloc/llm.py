"""
LLM integration for deployment agents: build prompts and call OpenAI or Anthropic
to produce resilience-aware deployment plans. Tools are SDK-hosted only
(WebSearchTool, CodeInterpreterTool, etc.); see agents.veloc._sdk_loader.
"""

from __future__ import annotations

from pathlib import Path

from agents.veloc.config import get_settings

_REPO_ROOT = Path(__file__).resolve().parents[2]
