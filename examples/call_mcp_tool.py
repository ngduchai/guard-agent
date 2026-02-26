#!/usr/bin/env python3
"""
Example: Call a single resilience MCP tool.

Calls veloc_configure_checkpoint with sample arguments and prints the
configuration snippet returned by the tool. No API key required.
"""

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_repo_root))
sys.path.insert(0, str(_repo_root / "orchestrator"))

from orchestrator.mcp_client import call_tool


def main() -> None:
    print("Calling MCP tool: veloc_configure_checkpoint\n")
    result = call_tool(
        "veloc_configure_checkpoint",
        {
            "checkpoint_interval_seconds": 300,
            "checkpoint_dir": "/scratch/checkpoints",
            "compression": "gzip",
        },
    )
    if result.get("isError"):
        print("Error:", result.get("content", [{}])[0].get("text", result))
        return
    for block in result.get("content", []):
        if block.get("type") == "text":
            print(block["text"])
            break


if __name__ == "__main__":
    main()
