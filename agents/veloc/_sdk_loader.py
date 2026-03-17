"""
Load the OpenAI Agents SDK (openai-agents) without conflicting with this package name.

Use: from agents.veloc._sdk_loader import Agent, Runner, get_sdk_tools_list

SDK hosted tools only (https://openai.github.io/openai-agents-python/tools/#hosted-tools).
No custom function tools; tools come from the SDK.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, List

_repo_root = str(Path(__file__).resolve().parents[2])
_our_agents = sys.modules.pop("agents", None)
_old_path = list(sys.path)
# Remove repo root (and cwd if it is repo) so "import agents" loads the SDK from site-packages
_cwd = str(Path(".").resolve())
sys.path = [p for p in sys.path if p != _repo_root and (p != "" or _cwd != _repo_root)]
try:
    import agents as _sdk_module
    Agent = getattr(_sdk_module, "Agent", None)
    Runner = getattr(_sdk_module, "Runner", None)
    WebSearchTool = getattr(_sdk_module, "WebSearchTool", None)
    FileSearchTool = getattr(_sdk_module, "FileSearchTool", None)
    CodeInterpreterTool = getattr(_sdk_module, "CodeInterpreterTool", None)
    FunctionTool = getattr(_sdk_module, "FunctionTool", None)
    function_tool = getattr(_sdk_module, "function_tool", None)
except ImportError:
    Agent = Runner = WebSearchTool = FileSearchTool = CodeInterpreterTool = None
    FunctionTool = function_tool = None
finally:
    sys.path[:] = _old_path
    if _our_agents is not None:
        sys.modules["agents"] = _our_agents


def get_sdk_tools_list() -> List[Any]:
    """
    Return the list of SDK-hosted tools to pass to Agent(tools=...).
    Uses only tools implemented by the SDK (WebSearchTool, CodeInterpreterTool
    if supported, optionally FileSearchTool if OPENAI_VECTOR_STORE_IDS is set).
    """
    out: List[Any] = []
    if WebSearchTool is not None:
        out.append(WebSearchTool())
    if CodeInterpreterTool is not None:
        try:
            # Responses API requires tool_config with type and container (auto or container ID)
            out.append(
                CodeInterpreterTool(
                    tool_config={
                        "type": "code_interpreter",
                        "container": {"type": "auto", "memory_limit": "4g"},
                    }
                )
            )
        except (TypeError, Exception):
            pass
    vs = os.getenv("OPENAI_VECTOR_STORE_IDS", "").strip()
    if vs and FileSearchTool is not None:
        ids = [x.strip() for x in vs.split(",") if x.strip()]
        if ids:
            out.append(FileSearchTool(max_num_results=3, vector_store_ids=ids))
    return out
