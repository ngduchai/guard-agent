#!/usr/bin/env python3
"""
Example: Send a transform request to the orchestrator API.

Requires the orchestrator server to be running, e.g.:
  PYTHONPATH=orchestrator:. python -m uvicorn orchestrator.main:app --port 8000

For a real deployment plan you also need OPENAI_API_KEY or ANTHROPIC_API_KEY
set in the orchestrator's environment (or .env in orchestrator/).

Usage:
  python examples/transform_request.py [BASE_URL]
  Default BASE_URL is http://127.0.0.1:8000
"""

import json
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)

BASE_URL = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")


def main() -> None:
    payload = {
        "code": "def main():\n    for i in range(100):\n        compute(i)\n",
        "description": "Long-running HPC simulation that should tolerate node failures.",
        "resilience_requirements": [
            {"name": "checkpoint_interval", "value": 300, "unit": "seconds"},
            {"name": "max_failures", "value": 3},
        ],
        "environment": "hpc",
    }
    print(f"POST {BASE_URL}/v1/transform")
    print("Request body:", json.dumps(payload, indent=2)[:400], "...\n")
    try:
        r = httpx.post(f"{BASE_URL}/v1/transform", json=payload, timeout=60.0)
        r.raise_for_status()
        plan = r.json()
        print("Deployment plan:")
        print("  Summary:", plan.get("summary", ""))
        for step in plan.get("steps", []):
            print(f"  - {step.get('name')}: {step.get('description', '')[:60]}...")
        if plan.get("transformed_code"):
            print("\nTransformed code (excerpt):", plan["transformed_code"][:200], "...")
    except httpx.ConnectError:
        print("Could not connect. Is the orchestrator running?")
        print("  PYTHONPATH=orchestrator:. python -m uvicorn orchestrator.main:app --port 8000")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print("HTTP error:", e.response.status_code, e.response.text)
        sys.exit(1)


if __name__ == "__main__":
    main()
