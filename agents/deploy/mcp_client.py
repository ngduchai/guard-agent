"""
Minimal MCP client over stdio (JSON-RPC 2.0) for deployment agents.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
from pathlib import Path
from queue import Queue
from typing import Any

from agents.deploy.config import get_settings

_REPO_ROOT = Path(__file__).resolve().parents[2]

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
    if "python" in (settings.mcp_server_command or "").lower() and "-m resilience_mcp" in (
        settings.mcp_server_args or ""
    ):
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

    send(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "guard-agent-deploy-agent", "version": "0.1.0"},
            },
        }
    )
    init_resp = recv()
    if not init_resp or "result" not in init_resp:
        err = (init_resp or {}).get("error", {})
        proc.terminate()
        return {"error": err.get("message", "Initialize failed")}

    send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
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
    debug_env = os.getenv("DEPLOY_AGENT_DEBUG_LLM", "").lower() in {"1", "true", "yes", "on"}
    cmd = [settings.mcp_server_command]
    if settings.mcp_server_args:
        cmd.extend(settings.mcp_server_args.strip().split())
    else:
        return {"content": [{"type": "text", "text": "MCP_SERVER_ARGS not set"}], "isError": True}

    env = os.environ.copy()
    if "python" in (settings.mcp_server_command or "").lower() and "-m resilience_mcp" in (
        settings.mcp_server_args or ""
    ):
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
        return {
            "content": [{"type": "text", "text": f"Command not found: {settings.mcp_server_command}"}],
            "isError": True,
        }

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

    if debug_env:
        try:
            args_snip = json.dumps(arguments, indent=2)
        except TypeError:
            args_snip = str(arguments)
        if len(args_snip) > 2000:
            args_snip = args_snip[:2000] + "\n...[args truncated]..."
        print(f"\n[MCP Debug] Calling tool '{name}' with arguments:\n{args_snip}\n")

    send(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "guard-agent-deploy-agent", "version": "0.1.0"},
            },
        }
    )
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
        if debug_env:
            print(f"[MCP Debug] Tool '{name}' returned no result or unexpected response: {resp!r}\n")
        return {"content": [{"type": "text", "text": str(resp or "No response")}], "isError": True}

    result = resp["result"]
    if debug_env:
        try:
            res_snip = json.dumps(result, indent=2)
        except TypeError:
            res_snip = str(result)
        if len(res_snip) > 2000:
            res_snip = res_snip[:2000] + "\n...[result truncated]..."
        print(f"[MCP Debug] Tool '{name}' result:\n{res_snip}\n")
    return result

