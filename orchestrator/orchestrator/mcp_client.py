"""
Minimal MCP client over stdio (JSON-RPC 2.0).
Spawns the resilience MCP server (Python or Node), does initialize handshake, then list_tools / call_tool.
"""

import json
import os
import subprocess
import threading
from pathlib import Path
from queue import Queue
from typing import Any

from orchestrator.config import get_settings

# Repo root so the Python MCP server (resilience_mcp) can be found when using -m resilience_mcp
_REPO_ROOT = Path(__file__).resolve().parents[2]

# Optional: cache tool list per process to avoid re-spawning
_tools_cache: list[dict[str, Any]] | None = None


def _read_response_line(proc: subprocess.Popen, out_queue: Queue) -> None:
    """Consume stdout line by line and put parsed JSON into queue."""
    for line in proc.stdout:
        line = line.decode("utf-8", errors="replace").strip()
        if not line or not line.startswith("{"):
            continue
        try:
            data = json.loads(line)
            out_queue.put(data)
        except json.JSONDecodeError:
            pass


def _spawn_and_request(_method: str | None, _params: dict[str, Any] | None) -> dict[str, Any]:
    """Spawn MCP server, do initialize handshake, send tools/list, return result."""
    settings = get_settings()
    cmd = [settings.mcp_server_command]
    if settings.mcp_server_args:
        cmd.extend(settings.mcp_server_args.strip().split())
    else:
        return {"error": "MCP_SERVER_ARGS not set (e.g. -m resilience_mcp or path to Node server)"}

    env = os.environ.copy()
    if "python" in (settings.mcp_server_command or "").lower() and "-m resilience_mcp" in (settings.mcp_server_args or ""):
        env["PYTHONPATH"] = str(_REPO_ROOT)
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            cwd=str(_REPO_ROOT),
            env=env,
        )
    except FileNotFoundError:
        return {"error": f"Command not found: {settings.mcp_server_command}"}

    out_queue: Queue = Queue()
    reader = threading.Thread(target=_read_response_line, args=(proc, out_queue), daemon=True)
    reader.start()

    def send(msg: dict) -> None:
        proc.stdin.write((json.dumps(msg) + "\n").encode())
        proc.stdin.flush()

    def recv(timeout: float = 10.0) -> dict | None:
        try:
            return out_queue.get(timeout=timeout)
        except Exception:
            return None

    # 1. Initialize
    send({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "guard-agent-orchestrator", "version": "0.1.0"},
        },
    })
    init_resp = recv()
    if not init_resp or "result" not in init_resp:
        err = (init_resp or {}).get("error", {})
        proc.terminate()
        return {"error": err.get("message", "Initialize failed")}

    # 2. Notifications/initialized
    send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    # 3. tools/list
    req_id = 2
    send({"jsonrpc": "2.0", "id": req_id, "method": "tools/list", "params": {}})
    resp = recv()
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()

    if not resp:
        return {"error": "No response to tools/list"}
    if "result" in resp:
        return resp["result"]
    if "error" in resp:
        return {"error": resp["error"].get("message", "tools/list failed")}
    return {"error": "Unknown response"}


def list_tools() -> list[dict[str, Any]]:
    """Return list of tool descriptors from the resilience MCP server."""
    global _tools_cache
    if _tools_cache is not None:
        return _tools_cache
    result = _spawn_and_request(None, None)
    if "error" in result:
        return []
    tools = result.get("tools", [])
    _tools_cache = tools
    return tools


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Invoke a tool by name. Spawns server, initialize, then tools/call."""
    settings = get_settings()
    cmd = [settings.mcp_server_command]
    if settings.mcp_server_args:
        cmd.extend(settings.mcp_server_args.strip().split())
    else:
        return {"content": [{"type": "text", "text": "MCP_SERVER_ARGS not set"}], "isError": True}

    env = os.environ.copy()
    if "python" in (settings.mcp_server_command or "").lower() and "-m resilience_mcp" in (settings.mcp_server_args or ""):
        env["PYTHONPATH"] = str(_REPO_ROOT)
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            cwd=str(_REPO_ROOT),
            env=env,
        )
    except FileNotFoundError:
        return {"content": [{"type": "text", "text": f"Command not found: {settings.mcp_server_command}"}], "isError": True}

    out_queue: Queue = Queue()
    reader = threading.Thread(target=_read_response_line, args=(proc, out_queue), daemon=True)
    reader.start()

    def send(msg: dict) -> None:
        proc.stdin.write((json.dumps(msg) + "\n").encode())
        proc.stdin.flush()

    def recv(timeout: float = 10.0) -> dict | None:
        try:
            return out_queue.get(timeout=timeout)
        except Exception:
            return None

    send({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "guard-agent-orchestrator", "version": "0.1.0"},
        },
    })
    recv()
    send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": name, "arguments": arguments}})
    resp = recv()
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()

    if not resp or "result" not in resp:
        return {"content": [{"type": "text", "text": str(resp or "No response")}], "isError": True}
    return resp["result"]
