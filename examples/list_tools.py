#!/usr/bin/env python3
"""
Example: List resilience tools from the MCP server.

No API key required. The script spawns the Python MCP server (resilience_mcp)
via the orchestrator's MCP client and prints the registered tools.
"""

import sys
from pathlib import Path

# Ensure repo root is on path so orchestrator and shared can be imported
_repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_repo_root))
sys.path.insert(0, str(_repo_root / "orchestrator"))

from orchestrator.mcp_client import list_tools


def main() -> None:
    print("Fetching resilience tools from MCP server...\n")
    tools = list_tools()
    if not tools:
        print("No tools returned (is MCP_SERVER_COMMAND / MCP_SERVER_ARGS set?)")
        return
    for t in tools:
        name = t.get("name", "?")
        desc = t.get("description", "") or "(no description)"
        print(f"  {name}")
        print(f"    {desc[:80]}{'...' if len(desc) > 80 else ''}")
        print()
    print(f"Total: {len(tools)} tool(s)")


if __name__ == "__main__":
    main()
