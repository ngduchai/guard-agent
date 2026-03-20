"""
Simple web UI for the deployment agent (OpenAI Agents SDK + VeloC).

Run from the build directory with:
    ./build/run_deploy_webui.sh

Changes from original:
- Added /api/stream SSE endpoint that streams step-by-step LLM events live.
- Frontend now consumes SSE and renders each step card (why/how/tools/result)
  as it arrives, giving users full visibility into LLM reasoning.
- User input is only requested when the LLM explicitly asks (status=ask).
- Old /api/chat POST endpoint kept for backward compatibility.
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

from fastapi import FastAPI, File, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse

from agents.veloc.agent import stream_veloc_agent
from agents.veloc.agent_graph import build_agent_graph
from agents.veloc.config import get_project_root

app = FastAPI(title="Guard Agent Deployment Web UI")

GRAPH = build_agent_graph()

# Interval (seconds) between SSE keep-alive comments sent while waiting for
# the LLM to respond.  Browsers and proxies typically time out idle SSE
# connections after 30–60 s; 15 s is a safe default.
_SSE_HEARTBEAT_INTERVAL = 15

# ---------------------------------------------------------------------------
# In-memory metrics store
# ---------------------------------------------------------------------------
# Maps session_id → full metrics dict (from the "done" SSE event).
# Keeps the last 20 sessions to avoid unbounded memory growth.
_MAX_STORED_SESSIONS = 20
_session_metrics: Dict[str, Dict[str, Any]] = {}
_session_order: List[str] = []   # insertion-order list of session IDs


# ---------------------------------------------------------------------------
# SSE helper
# ---------------------------------------------------------------------------

def _store_session_metrics(metrics: Dict[str, Any]) -> None:
    """Store metrics for a session, evicting the oldest if over the limit."""
    session_id = metrics.get("session_id")
    if not session_id:
        return
    if session_id not in _session_metrics:
        _session_order.append(session_id)
    _session_metrics[session_id] = metrics
    # Evict oldest sessions beyond the cap.
    while len(_session_order) > _MAX_STORED_SESSIONS:
        oldest = _session_order.pop(0)
        _session_metrics.pop(oldest, None)


async def _sse_generator(messages: List[Dict[str, str]]) -> AsyncIterator[str]:
    """Yield SSE-formatted strings from stream_veloc_agent events.

    Interleaves periodic SSE keep-alive comments (`: keep-alive`) so that
    browsers and reverse-proxies do not close the connection while the LLM
    is thinking (which can take 30–120 s per turn).
    """
    # Use an asyncio.Queue to decouple the agent coroutine from the SSE
    # generator.  The agent pushes events into the queue; the generator
    # drains the queue and sends heartbeats whenever the queue is empty.
    queue: asyncio.Queue = asyncio.Queue()
    _DONE = object()  # sentinel value

    async def _run_agent() -> None:
        """Run the agent and push events into the queue; push _DONE when done."""
        try:
            async for event in stream_veloc_agent(messages):
                await queue.put(event)
        except Exception as exc:
            await queue.put({"type": "error", "message": str(exc)})
        finally:
            await queue.put(_DONE)  # sentinel: agent finished

    agent_task = asyncio.ensure_future(_run_agent())
    try:
        while True:
            # Wait for the next item with a heartbeat timeout.
            # asyncio.wait_for cancels queue.get() on timeout; the item (if any
            # arrived just before cancellation) stays in the queue because
            # queue.get() only removes an item on successful completion.
            try:
                item = await asyncio.wait_for(
                    queue.get(), timeout=_SSE_HEARTBEAT_INTERVAL
                )
            except asyncio.TimeoutError:
                # No event arrived within the heartbeat window — send a
                # keep-alive comment so the connection stays open.
                yield ": keep-alive\n\n"
                continue

            if item is _DONE:
                # Sentinel: agent has finished.
                break

            # Capture full metrics from the "done" event for later download.
            # Prefer "full_metrics" (complete SessionMetrics dict with turns,
            # conversation, conversation_events) over the compact "metrics" summary.
            if isinstance(item, dict) and item.get("type") == "done":
                m = (
                    item.get("full_metrics")
                    or item.get("metrics")
                    or (item.get("result") or {}).get("metrics")
                )
                if m:
                    _store_session_metrics(m)

            data = json.dumps(item, ensure_ascii=False)
            yield f"data: {data}\n\n"
    finally:
        agent_task.cancel()
        try:
            await agent_task
        except (asyncio.CancelledError, Exception):
            pass


# ---------------------------------------------------------------------------
# Web UI HTML
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    """Serve a chat-style single-page web UI with live step-by-step LLM transparency."""
    return r"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Guard Agent – Deployment Assistant</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #050812;
      --panel: #0f172a;
      --accent: #38bdf8;
      --accent-soft: rgba(56, 189, 248, 0.16);
      --border: #1e293b;
      --text: #e5e7eb;
      --muted: #9ca3af;
      --danger: #f97373;
      --success: #86efac;
      --warn: #fbbf24;
      --tool-color: #a5b4fc;
      --mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      --sans: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      padding: 0;
      font-family: var(--sans);
      background: radial-gradient(circle at top, #0f172a 0, #020617 55%);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      align-items: stretch;
      justify-content: center;
    }
    .shell {
      max-width: 1120px;
      width: 100%;
      padding: 24px 16px 32px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      flex: 1;
      min-height: 100vh;
    }
    .card {
      background: radial-gradient(circle at top left, rgba(56,189,248,0.08), transparent 55%), var(--panel);
      border-radius: 16px;
      border: 1px solid var(--border);
      box-shadow: 0 32px 80px rgba(15,23,42,0.9);
      padding: 18px 18px 12px;
      backdrop-filter: blur(18px);
      display: flex;
      flex-direction: column;
      flex: 1;
      min-height: 0;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 8px;
    }
    .title { font-size: 18px; font-weight: 600; letter-spacing: 0.02em; }
    .subtitle { font-size: 13px; color: var(--muted); }
    .badge {
      border-radius: 999px;
      padding: 4px 10px;
      border: 1px solid rgba(148,163,184,0.5);
      font-size: 11px;
      color: var(--muted);
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .badge-dot {
      width: 8px; height: 8px;
      border-radius: 999px;
      background: #22c55e;
      box-shadow: 0 0 0 4px rgba(34,197,94,0.2);
    }
    .panel {
      background: rgba(15,23,42,0.82);
      border-radius: 14px;
      border: 1px solid rgba(30,64,175,0.65);
      padding: 10px 12px 12px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .panel-header {
      font-size: 13px;
      font-weight: 500;
      color: #e5e7eb;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    .panel-header small { font-weight: 400; color: var(--muted); font-size: 11px; }
    textarea {
      width: 100%;
      min-height: 110px;
      max-height: 220px;
      resize: vertical;
      border-radius: 10px;
      border: 1px solid rgba(51,65,85,0.9);
      background: rgba(15,23,42,0.95);
      color: var(--text);
      padding: 8px 9px;
      font-family: var(--mono);
      font-size: 12px;
      line-height: 1.45;
      outline: none;
      box-shadow: inset 0 0 0 1px rgba(15,23,42,0.4);
    }
    textarea:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 1px rgba(56,189,248,0.7), 0 0 0 6px rgba(56,189,248,0.1);
    }
    textarea:disabled { opacity: 0.45; cursor: not-allowed; }
    .controls {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 6px;
      gap: 8px;
      font-size: 11px;
      color: var(--muted);
    }
    .button {
      border-radius: 999px;
      border: none;
      padding: 6px 14px;
      background: linear-gradient(to right, #0ea5e9, #6366f1);
      color: white;
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      box-shadow: 0 14px 35px rgba(37,99,235,0.55);
    }
    .button:disabled { opacity: 0.55; cursor: default; box-shadow: none; }
    .button-secondary {
      background: transparent;
      border: 1px solid rgba(148,163,184,0.65);
      color: var(--muted);
      box-shadow: none;
      padding-inline: 10px;
    }
    .status { font-size: 11px; color: var(--muted); }
    .status-dot {
      width: 7px; height: 7px;
      border-radius: 999px;
      background: var(--accent);
      display: inline-block;
      margin-right: 5px;
    }
    .status-dot.idle { background: #4b5563; }
    .status-dot.error { background: var(--danger); }
    .status-dot.busy { background: var(--accent); animation: pulse 1.2s infinite; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }

    /* ── Chat layout ── */
    .chat-panel { margin-top: 6px; margin-bottom: 10px; flex: 1; min-height: 0; }
    .chat-output { flex: 1; min-height: 0; overflow-y: auto; padding: 4px 2px 2px 2px; }
    .input-panel { margin-top: 6px; flex-shrink: 0; }

    /* ── Message bubbles ── */
    .msg-user {
      margin-top: 8px;
      display: flex;
      justify-content: flex-end;
    }
    .msg-user-bubble {
      max-width: 82%;
      border-radius: 14px;
      padding: 7px 10px;
      background: linear-gradient(to right, #0ea5e9, #6366f1);
      color: white;
      font-size: 12px;
      white-space: pre-wrap;
    }
    .msg-agent {
      margin-top: 8px;
      display: flex;
      justify-content: flex-start;
    }
    .msg-agent-bubble {
      max-width: 96%;
      border-radius: 14px;
      padding: 7px 9px;
      background: rgba(15,23,42,0.96);
      border: 1px solid rgba(30,64,175,0.85);
      font-size: 12px;
    }

    /* ── Step cards ── */
    .step-card {
      border-radius: 10px;
      border: 1px solid rgba(30,64,175,0.7);
      background: radial-gradient(circle at top left, rgba(59,130,246,0.10), transparent 60%), rgba(15,23,42,0.97);
      padding: 8px 10px;
      margin-top: 6px;
      font-size: 12px;
    }
    .step-card-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 5px;
    }
    .step-num {
      background: rgba(56,189,248,0.18);
      color: var(--accent);
      border-radius: 999px;
      padding: 1px 7px;
      font-size: 11px;
      font-weight: 600;
      white-space: nowrap;
    }
    .step-name {
      font-weight: 600;
      color: #e5e7eb;
      flex: 1;
    }
    .step-status-badge {
      font-size: 10px;
      border-radius: 999px;
      padding: 1px 7px;
      border: 1px solid;
    }
    .step-status-badge.running {
      color: var(--warn);
      border-color: var(--warn);
      animation: pulse 1.2s infinite;
    }
    .step-status-badge.done {
      color: var(--success);
      border-color: var(--success);
    }
    .step-row {
      display: flex;
      gap: 6px;
      margin-top: 3px;
      font-size: 11px;
      color: var(--muted);
    }
    .step-label {
      color: var(--accent);
      font-weight: 600;
      min-width: 42px;
    }
    .step-value { flex: 1; white-space: pre-wrap; }
    .tool-badge {
      display: inline-flex;
      align-items: center;
      gap: 3px;
      background: rgba(165,180,252,0.12);
      color: var(--tool-color);
      border: 1px solid rgba(165,180,252,0.3);
      border-radius: 999px;
      padding: 1px 7px;
      font-size: 10px;
      font-family: var(--mono);
      margin-right: 3px;
      margin-top: 2px;
    }
    .tool-call-inline {
      margin-top: 4px;
      padding: 4px 7px;
      border-radius: 7px;
      background: rgba(165,180,252,0.07);
      border: 1px dashed rgba(165,180,252,0.25);
      font-size: 11px;
      color: var(--tool-color);
      font-family: var(--mono);
    }
    .tool-result-inline {
      margin-top: 2px;
      padding: 3px 7px;
      border-radius: 7px;
      background: rgba(15,23,42,0.9);
      border: 1px solid rgba(51,65,85,0.7);
      font-size: 10px;
      color: var(--muted);
      font-family: var(--mono);
      max-height: 120px;
      overflow: auto;
      white-space: pre;
    }
    .step-result-box {
      margin-top: 5px;
      padding: 4px 7px;
      border-radius: 7px;
      background: rgba(34,197,94,0.06);
      border: 1px solid rgba(34,197,94,0.2);
      font-size: 11px;
      color: #bbf7d0;
      white-space: pre-wrap;
    }

    /* ── Summary / final blocks ── */
    .summary-box {
      font-size: 13px;
      color: var(--text);
      padding: 6px 8px;
      border-radius: 10px;
      border: 1px solid rgba(51,65,85,0.9);
      background: radial-gradient(circle at top left, rgba(56,189,248,0.12), transparent 55%), #020617;
      white-space: pre-wrap;
    }
    .summary-box.success {
      border-color: #166534;
      background: rgba(22,101,52,0.1);
    }
    .summary-box.error {
      border-color: #7f1d1d;
      background: rgba(127,29,29,0.1);
    }
    .summary-box.ask {
      border-color: rgba(251,191,36,0.5);
      background: rgba(251,191,36,0.05);
    }

    details {
      margin-top: 6px;
      border-radius: 8px;
      background: rgba(15,23,42,0.9);
      border: 1px dashed rgba(55,65,81,0.9);
      padding: 4px 6px;
    }
    summary { cursor: pointer; font-size: 11px; color: var(--muted); outline: none; }
    .code-block {
      margin-top: 4px;
      border-radius: 10px;
      background: #020617;
      border: 1px solid rgba(51,65,85,0.9);
      max-height: 240px;
      overflow: auto;
      font-family: var(--mono);
      font-size: 11px;
      padding: 6px 8px;
      white-space: pre;
    }
    .tiny { font-size: 11px; color: var(--muted); }

    /* ── Performance metrics panel ── */
    .metrics-panel {
      margin-top: 10px;
      border-radius: 12px;
      border: 1px solid rgba(99,102,241,0.45);
      background: radial-gradient(circle at top left, rgba(99,102,241,0.08), transparent 60%), rgba(15,23,42,0.97);
      padding: 10px 12px 12px;
      font-size: 12px;
      display: none;   /* hidden until metrics arrive */
    }
    .metrics-panel.visible { display: block; }
    .metrics-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 8px;
    }
    .metrics-title {
      font-size: 13px;
      font-weight: 600;
      color: #a5b4fc;
    }
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
      gap: 6px;
      margin-bottom: 8px;
    }
    .metrics-stat {
      background: rgba(15,23,42,0.9);
      border: 1px solid rgba(51,65,85,0.8);
      border-radius: 8px;
      padding: 6px 8px;
    }
    .metrics-stat-label {
      font-size: 10px;
      color: var(--muted);
      margin-bottom: 2px;
    }
    .metrics-stat-value {
      font-size: 14px;
      font-weight: 600;
      color: #a5b4fc;
      font-family: var(--mono);
    }
    .metrics-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 11px;
      font-family: var(--mono);
    }
    .metrics-table th {
      text-align: left;
      color: var(--muted);
      font-weight: 500;
      padding: 3px 6px;
      border-bottom: 1px solid rgba(51,65,85,0.7);
    }
    .metrics-table td {
      padding: 3px 6px;
      color: var(--text);
      border-bottom: 1px solid rgba(30,41,59,0.6);
    }
    .metrics-table tr:last-child td { border-bottom: none; }
    .metrics-dl-btn {
      border-radius: 999px;
      border: 1px solid rgba(165,180,252,0.5);
      padding: 4px 10px;
      background: transparent;
      color: #a5b4fc;
      font-size: 11px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }
    .metrics-dl-btn:hover { background: rgba(165,180,252,0.1); }

    /* ── Upload section ── */
    .upload-section {
      margin-bottom: 8px;
      padding: 10px 12px;
      border-radius: 12px;
      border: 1px dashed rgba(56,189,248,0.4);
      background: rgba(56,189,248,0.04);
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .upload-row {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
    .upload-label {
      font-size: 12px;
      font-weight: 500;
      color: var(--accent);
      white-space: nowrap;
    }
    .upload-file-input {
      flex: 1;
      min-width: 0;
      font-size: 11px;
      color: var(--muted);
      background: rgba(15,23,42,0.9);
      border: 1px solid rgba(51,65,85,0.9);
      border-radius: 8px;
      padding: 4px 8px;
      cursor: pointer;
    }
    .upload-file-input:disabled {
      opacity: 0.45;
      cursor: not-allowed;
      pointer-events: none;
    }
    .upload-file-input::file-selector-button {
      background: rgba(56,189,248,0.15);
      border: 1px solid rgba(56,189,248,0.4);
      border-radius: 6px;
      color: var(--accent);
      font-size: 11px;
      padding: 2px 8px;
      cursor: pointer;
      margin-right: 8px;
    }
    .upload-status {
      font-size: 11px;
      color: var(--muted);
    }
    .upload-status.ok   { color: var(--success); }
    .upload-status.err  { color: var(--danger); }
    .upload-status.busy { color: var(--warn); animation: pulse 1.2s infinite; }

    /* ── Download generated code button ── */
    .download-panel {
      margin-top: 8px;
      padding: 10px 12px;
      border-radius: 12px;
      border: 1px solid rgba(134,239,172,0.35);
      background: rgba(34,197,94,0.05);
      display: none;
      align-items: center;
      gap: 10px;
    }
    .download-panel.visible { display: flex; }
    .download-panel-label {
      flex: 1;
      font-size: 12px;
      color: var(--success);
    }
    .download-btn {
      border-radius: 999px;
      border: 1px solid rgba(134,239,172,0.5);
      padding: 5px 14px;
      background: rgba(34,197,94,0.12);
      color: var(--success);
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .download-btn:hover { background: rgba(34,197,94,0.22); }

    /* ── Markdown rendered content ── */
    .md-content { font-size: 12px; color: var(--text); line-height: 1.6; }
    .md-content p { margin: 0.4em 0; }
    .md-content p:first-child { margin-top: 0; }
    .md-content p:last-child { margin-bottom: 0; }
    .md-content h1, .md-content h2, .md-content h3,
    .md-content h4, .md-content h5, .md-content h6 {
      margin: 0.6em 0 0.3em; color: #e5e7eb; font-weight: 600;
    }
    .md-content ul, .md-content ol { margin: 0.3em 0; padding-left: 1.4em; }
    .md-content li { margin: 0.15em 0; }
    .md-content code {
      font-family: var(--mono); font-size: 11px;
      background: rgba(56,189,248,0.1); border-radius: 4px;
      padding: 1px 4px; color: var(--accent);
    }
    .md-content pre {
      background: rgba(15,23,42,0.95); border: 1px solid rgba(51,65,85,0.9);
      border-radius: 8px; padding: 8px 10px; overflow-x: auto; margin: 0.4em 0;
    }
    .md-content pre code { background: none; padding: 0; color: var(--text); }
    .md-content strong { color: #e5e7eb; }
    .md-content em { color: var(--muted); }
    .md-content blockquote {
      border-left: 3px solid var(--accent); margin: 0.4em 0;
      padding: 2px 10px; color: var(--muted);
    }
    .md-content a { color: var(--accent); }
    .md-content hr { border: none; border-top: 1px solid rgba(51,65,85,0.7); margin: 0.5em 0; }
  </style>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
</head>
<body>
  <div class="shell">
    <div class="card">
      <div class="header">
        <div>
          <div class="title">Deployment Resilience Agent</div>
          <div class="subtitle">Describe your HPC/cloud code and resiliency goals; the agent will guide and propose a VeloC-enabled deployment plan.</div>
        </div>
        <div style="display:flex; flex-direction:column; align-items:flex-end; gap:4px;">
          <a href="/replay" class="button button-secondary" style="text-decoration:none; font-size:12px; padding:5px 14px;">🔁 Replay</a>
        </div>
      </div>

      <div class="panel chat-panel">
        <div class="panel-header">
          <span>Conversation</span>
          <small id="outputMode">Waiting for first response…</small>
        </div>
        <div id="output" class="chat-output">
          <div class="tiny">Responses from the agent will appear here. You will see each reasoning step live as the agent works.</div>
        </div>
      </div>

      <div class="panel input-panel">
        <div class="panel-header">
          <span>Prompt</span>
          <small>Describe code, environment, and resilience/QoS needs in natural language.</small>
        </div>

        <!-- ── Code directory upload ── -->
        <div class="upload-section">
          <div class="upload-row">
            <span class="upload-label">📁 Upload code directory (ZIP):</span>
            <input type="file" id="codeZipInput" class="upload-file-input" accept=".zip">
            <button class="button button-secondary" id="uploadBtn" type="button" style="padding:4px 12px; font-size:11px;">Upload</button>
          </div>
          <div class="upload-row">
            <span class="upload-status" id="uploadStatus">No file uploaded. Upload a ZIP of your code directory to let the agent read it.</span>
          </div>
        </div>

        <textarea id="prompt" placeholder="Example:
I have an MPI matrix multiplication code in examples/matrix_mul_mpi/code.c.
It should run on an HPC cluster with VeLoC-based checkpointing every 600 seconds
and tolerate up to 2 node failures. Help me transform it into a resilient deployment."></textarea>
        <div class="controls">
          <div class="status" id="status"><span class="status-dot idle"></span>Idle</div>
          <div style="display:flex; gap:6px; align-items:center;">
            <button class="button-secondary" id="resetBtn" type="button">Reset session</button>
            <button class="button-secondary" id="stopBtn" type="button" style="display:none;">Stop</button>
            <button class="button" id="sendBtn" type="button">
              <span>Send</span>
            </button>
          </div>
        </div>
      </div>

      <!-- ── Download generated code panel ── -->
      <div class="download-panel" id="downloadPanel">
        <span class="download-panel-label">✅ Generated code is ready!</span>
        <button class="download-btn" id="downloadBtn" type="button">⬇ Download generated code</button>
      </div>

      <!-- ── Performance Metrics Panel ── -->
      <div class="metrics-panel" id="metricsPanel">
        <div class="metrics-header">
          <span class="metrics-title">📊 Performance Metrics</span>
          <button class="metrics-dl-btn" id="metricsDownloadBtn" type="button">
            ⬇ Download JSON
          </button>
        </div>
        <div class="metrics-grid" id="metricsGrid"></div>
        <details>
          <summary>Per-turn breakdown</summary>
          <table class="metrics-table" id="metricsTable">
            <thead>
              <tr>
                <th>Turn</th>
                <th>Elapsed (s)</th>
                <th>Prompt tok</th>
                <th>Completion tok</th>
                <th>Total tok</th>
                <th>Tool calls</th>
                <th>Step #(s)</th>
                <th>Tools used</th>
              </tr>
            </thead>
            <tbody id="metricsTableBody"></tbody>
          </table>
        </details>
      </div>
    </div>

    <div class="tiny">
      Tip: the agent narrates each step of its reasoning live. It will only ask you a question if it genuinely needs more information to proceed.
    </div>
  </div>

  <script>
    const sendBtn    = document.getElementById('sendBtn');
    const resetBtn   = document.getElementById('resetBtn');
    const stopBtn    = document.getElementById('stopBtn');
    const promptEl   = document.getElementById('prompt');
    const statusEl   = document.getElementById('status');
    const outputEl   = document.getElementById('output');
    const outputMode = document.getElementById('outputMode');

    // ── Upload state ───────────────────────────────────────────────────────
    const codeZipInput   = document.getElementById('codeZipInput');
    const uploadBtn      = document.getElementById('uploadBtn');
    const uploadStatusEl = document.getElementById('uploadStatus');
    const downloadPanel  = document.getElementById('downloadPanel');
    const downloadBtn    = document.getElementById('downloadBtn');

    // Holds the result of the last successful upload
    let uploadInfo = null;   // { upload_id, upload_path, generated_code_path }
    let writtenFiles = [];   // file paths written by the LLM via write_file tool calls

    function setUploadStatus(text, cls) {
      uploadStatusEl.textContent = text;
      uploadStatusEl.className = 'upload-status' + (cls ? ' ' + cls : '');
    }

    uploadBtn.addEventListener('click', async () => {
      const file = codeZipInput.files[0];
      if (!file) {
        setUploadStatus('Please select a ZIP file first.', 'err');
        return;
      }
      setUploadStatus('Uploading…', 'busy');
      uploadBtn.disabled = true;
      try {
        const fd = new FormData();
        fd.append('file', file);
        const res = await fetch('/api/upload', { method: 'POST', body: fd });
        const data = await res.json();
        if (!res.ok) {
          setUploadStatus('Upload failed: ' + (data.error || res.status), 'err');
          uploadInfo = null;
        } else {
          uploadInfo = data;
          setUploadStatus(
            '✓ Uploaded: ' + file.name + ' → ' + data.upload_path,
            'ok'
          );
        }
      } catch (err) {
        setUploadStatus('Upload error: ' + err, 'err');
        uploadInfo = null;
      } finally {
        uploadBtn.disabled = false;
      }
    });

    // Show download panel and wire up the download button.
    // If uploadId is provided, download from the generated_code directory.
    // Otherwise, download the files written by the LLM during this session.
    function showDownloadPanel(uploadId) {
      downloadPanel.classList.add('visible');
      if (uploadId) {
        downloadBtn.onclick = () => {
          const a = document.createElement('a');
          a.href = '/api/download/' + encodeURIComponent(uploadId);
          a.download = 'generated_code_' + uploadId.slice(0, 8) + '.zip';
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
        };
      } else {
        // Download the files written by the LLM via write_file tool calls
        downloadBtn.onclick = async () => {
          if (!writtenFiles.length) {
            alert('No files were written by the agent in this session.');
            return;
          }
          try {
            const res = await fetch('/api/download-written-files', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ file_paths: writtenFiles }),
            });
            if (!res.ok) {
              const err = await res.json().catch(() => ({}));
              alert('Download failed: ' + (err.error || res.status));
              return;
            }
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'generated_code.zip';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
          } catch (err) {
            alert('Download error: ' + err);
          }
        };
      }
    }

    let state = { messages: [] };
    let busy  = false;
    let currentES = null;   // EventSource for SSE

    // ── Utilities ──────────────────────────────────────────────────────────

    function setStatus(text, mode) {
      statusEl.innerHTML = '<span class="status-dot ' + (mode || 'idle') + '"></span>' + text;
    }

    function escapeHtml(str) {
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }

    // Render text as markdown HTML (uses marked.js if available, falls back to pre-wrap).
    function renderMarkdown(text) {
      if (!text) return '';
      if (typeof marked !== 'undefined') {
        try {
          return marked.parse(String(text), { breaks: true, gfm: true });
        } catch(e) { /* fall through */ }
      }
      return '<pre style="white-space:pre-wrap; margin:0;">' + escapeHtml(String(text)) + '</pre>';
    }

    function scrollBottom() {
      outputEl.scrollTop = outputEl.scrollHeight;
    }

    // ── Message rendering ──────────────────────────────────────────────────

    function appendUserMessage(text) {
      outputEl.insertAdjacentHTML('beforeend', `
        <div class="msg-user">
          <div class="msg-user-bubble">${escapeHtml(text)}</div>
        </div>
      `);
      scrollBottom();
    }

    function appendAgentBubble(innerHtml) {
      const wrap = document.createElement('div');
      wrap.className = 'msg-agent';
      wrap.innerHTML = `<div class="msg-agent-bubble">${innerHtml}</div>`;
      outputEl.appendChild(wrap);
      scrollBottom();
      return wrap.querySelector('.msg-agent-bubble');
    }

    // ── Step card management ───────────────────────────────────────────────

    // Map step number → DOM element for the step card body
    const stepCards = {};
    // The current agent bubble that holds step cards
    let agentBubble = null;

    function ensureAgentBubble() {
      if (!agentBubble) {
        agentBubble = appendAgentBubble('<div class="tiny" style="margin-bottom:4px;">Agent is working…</div>');
      }
      return agentBubble;
    }

    function renderStepSummary(ev) {
      const bubble = ensureAgentBubble();
      const stepNum = ev.step || '?';
      const tools = Array.isArray(ev.tools) && ev.tools.length
        ? ev.tools.map(t => `<span class="tool-badge">⚙ ${escapeHtml(t)}</span>`).join('')
        : '<span style="color:var(--muted);font-size:10px;">none</span>';

      const card = document.createElement('div');
      card.className = 'step-card';
      card.id = 'step-card-' + stepNum;
      card.innerHTML = `
        <div class="step-card-header">
          <span class="step-num">Step ${escapeHtml(String(stepNum))}</span>
          <span class="step-name">${escapeHtml(ev.name || '')}</span>
          <span class="step-status-badge running" id="step-badge-${stepNum}">running…</span>
        </div>
        <div class="step-row">
          <span class="step-label">Why</span>
          <span class="step-value">${escapeHtml(ev.why || '')}</span>
        </div>
        <div class="step-row">
          <span class="step-label">How</span>
          <span class="step-value">${escapeHtml(ev.how || '')}</span>
        </div>
        <div class="step-row">
          <span class="step-label">Tools</span>
          <span class="step-value" id="step-tools-${stepNum}">${tools}</span>
        </div>
        <div id="step-calls-${stepNum}"></div>
        <div id="step-result-${stepNum}"></div>
      `;
      bubble.appendChild(card);
      stepCards[stepNum] = card;
      scrollBottom();
    }

    function renderStepResult(ev) {
      const stepNum = ev.step || '?';
      const resultEl = document.getElementById('step-result-' + stepNum);
      if (resultEl && ev.result) {
        resultEl.innerHTML = `<div class="step-result-box">${escapeHtml(ev.result)}</div>`;
      }
      const badge = document.getElementById('step-badge-' + stepNum);
      if (badge) {
        badge.textContent = 'done';
        badge.className = 'step-status-badge done';
      }
      scrollBottom();
    }

    // Track which step number the most recent tool_call belongs to
    let lastToolCallStep = null;

    function renderToolCall(ev) {
      lastToolCallStep = ev.turn;  // use turn as proxy; step cards track by step num
      // Find the most recently opened step card (highest step num)
      const stepNums = Object.keys(stepCards).map(Number).sort((a,b)=>b-a);
      const targetStep = stepNums.length ? stepNums[0] : null;
      const callsEl = targetStep !== null ? document.getElementById('step-calls-' + targetStep) : null;

      const argsStr = ev.args ? JSON.stringify(ev.args, null, 2) : '';
      const callHtml = `
        <div class="tool-call-inline" id="tool-call-${escapeHtml(ev.name)}-${ev.turn}">
          ▶ <strong>${escapeHtml(ev.name)}</strong>
          ${argsStr ? `<details style="margin-top:2px;"><summary>args</summary><pre class="code-block">${escapeHtml(argsStr)}</pre></details>` : ''}
        </div>
      `;
      if (callsEl) {
        callsEl.insertAdjacentHTML('beforeend', callHtml);
      } else {
        ensureAgentBubble().insertAdjacentHTML('beforeend', callHtml);
      }
      scrollBottom();
    }

    function renderToolResult(ev) {
      // Attach result to the most recently opened step card
      const stepNums = Object.keys(stepCards).map(Number).sort((a,b)=>b-a);
      const targetStep = stepNums.length ? stepNums[0] : null;
      const callsEl = targetStep !== null ? document.getElementById('step-calls-' + targetStep) : null;

      const resultHtml = `
        <div class="tool-result-inline">${escapeHtml(ev.result || '')}</div>
      `;
      if (callsEl) {
        callsEl.insertAdjacentHTML('beforeend', resultHtml);
      } else {
        ensureAgentBubble().insertAdjacentHTML('beforeend', resultHtml);
      }
      scrollBottom();
    }

    function renderFinalDone(result) {
      const status = result.status || 'error';
      outputMode.textContent = status === 'success' ? 'Success' :
                               status === 'ask'     ? 'Agent needs more information' :
                               status === 'error'   ? 'Error' : status;

      if (status === 'success') {
        appendAgentBubble(`
          <div class="summary-box success">
            <strong style="color:var(--success);">✓ Task completed successfully</strong>
            <div class="md-content" style="margin-top:8px;">${renderMarkdown(result.summary || 'No summary provided.')}</div>
          </div>
        `);
        // Show download panel: prefer upload-based download, fall back to
        // tracking files written by the LLM via write_file tool calls.
        if (uploadInfo) {
          showDownloadPanel(uploadInfo.upload_id);
        } else if (writtenFiles.length > 0) {
          showDownloadPanel(null);
        }
      } else if (status === 'ask') {
        appendAgentBubble(`
          <div class="summary-box ask">
            <strong style="color:var(--warn);">⚠ Agent needs more information</strong>
            <div class="md-content" style="margin-top:8px;">${renderMarkdown(result.assistant_question || 'Please provide more details.')}</div>
          </div>
          <div class="tiny" style="margin-top:6px;">
            Answer this question in your next message. Try to include all missing details in a single reply.
          </div>
        `);
        // Re-enable input so user can answer
        enableInput();
        state.messages.push({ role: 'assistant', content: result.assistant_question || '' });
      } else {
        appendAgentBubble(`
          <div class="summary-box error">
            <strong style="color:var(--danger);">✗ Error from agent</strong>
            <div class="md-content" style="margin-top:8px;">${renderMarkdown(result.assistant_question || result.error_message || 'Unknown error.')}</div>
          </div>
        `);
      }
    }

    // ── Input enable/disable ───────────────────────────────────────────────

    function disableInput() {
      promptEl.disabled    = true;
      sendBtn.disabled     = true;
      codeZipInput.disabled = true;
      uploadBtn.disabled   = true;
      if (stopBtn) stopBtn.style.display = 'inline-block';
    }

    function enableInput() {
      promptEl.disabled    = false;
      sendBtn.disabled     = false;
      codeZipInput.disabled = false;
      uploadBtn.disabled   = false;
      if (stopBtn) stopBtn.style.display = 'none';
      busy = false;
      promptEl.focus();
    }

    // ── SSE streaming send ─────────────────────────────────────────────────

    async function send() {
      console.log('[send] called, busy=', busy);
      if (busy) return;
      const message = promptEl.value.trim();
      console.log('[send] message length=', message.length);
      if (!message) { promptEl.focus(); return; }

      if (message.toLowerCase() === 'quit' || message.toLowerCase() === 'exit') {
        setStatus('Session ended by user.', 'idle');
        outputMode.textContent = 'Session ended';
        return;
      }

      // If the user uploaded a code directory, inject path context into the
      // first user message of this session so the LLM knows where to find the
      // source code and where to write the generated output.
      let llmMessage = message;
      if (uploadInfo && state.messages.length === 0) {
        llmMessage =
          message +
          '\n\n[System context – do not repeat to the user]\n' +
          'The user has uploaded their code directory. It is available at:\n' +
          '  Source code path : ' + uploadInfo.upload_path + '\n' +
          '  Generated output path: ' + uploadInfo.generated_code_path + '\n' +
          'Treat the source code path as if the user provided it directly.\n' +
          'Write all generated/modified files under the generated output path.';
      }

      appendUserMessage(message);
      promptEl.value = '';
      state.messages.push({ role: 'user', content: llmMessage });

      busy = true;
      agentBubble = null;   // reset for new agent turn
      Object.keys(stepCards).forEach(k => delete stepCards[k]);
      writtenFiles = [];    // reset written files tracking for this turn
      if (downloadPanel) downloadPanel.classList.remove('visible');

      disableInput();
      setStatus('Connecting to agent…', 'busy');
      outputMode.textContent = 'Connecting…';

      // Show an immediate "thinking" placeholder so the user knows the request
      // was received, even before the first SSE event arrives.
      const thinkingBubble = appendAgentBubble(
        '<div class="tiny" id="agent-thinking" style="color:var(--muted);">⏳ Agent is processing your request… (this may take 30–60 s)</div>'
      );

      // Remove any stale thinking indicator
      const old = document.getElementById('agent-thinking');

      // POST the message list to start SSE streaming
      console.log('[send] POSTing to /api/stream');
      let streamEnded = false;
      try {
        const res = await fetch('/api/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ messages: state.messages }),
        });
        console.log('[send] fetch response status=', res.status);
        if (!res.ok) throw new Error('HTTP ' + res.status);

        setStatus('Agent is thinking…', 'busy');
        outputMode.textContent = 'Processing…';

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buf = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });

          // SSE lines: "data: {...}\n\n"
          const parts = buf.split('\n\n');
          buf = parts.pop();   // keep incomplete chunk

          for (const part of parts) {
            const line = part.trim();
            if (!line.startsWith('data:')) continue;
            const jsonStr = line.slice(5).trim();
            let ev;
            try { ev = JSON.parse(jsonStr); } catch { continue; }
            // Remove the thinking placeholder on first real event
            const th = document.getElementById('agent-thinking');
            if (th) th.closest('.msg-agent') ? th.closest('.msg-agent').remove() : th.remove();
            handleEvent(ev);
          }
        }
        // Stream ended cleanly without a 'done' event — re-enable input.
        streamEnded = true;
        if (busy) enableInput();
      } catch (err) {
        console.error('[send] error:', err);
        streamEnded = true;
        const isAbort = err && err.name === 'AbortError';
        if (!isAbort) {
          setStatus('Network or server error.', 'error');
          appendAgentBubble(`
            <div class="summary-box error">
              <strong style="color:var(--danger);">Network or server error</strong><br>
              ${escapeHtml(String(err))}
            </div>
          `);
          enableInput();
        }
      }
    }

    function handleEvent(ev) {
      if (!ev || !ev.type) return;

      switch (ev.type) {
        case 'step_summary':
          setStatus('Step ' + ev.step + ': ' + (ev.name || ''), 'busy');
          renderStepSummary(ev);
          break;

        case 'step_result':
          renderStepResult(ev);
          break;

        case 'tool_call':
          renderToolCall(ev);
          // Track files written by the LLM so we can offer a download later
          if (ev.name === 'write_file' && ev.args && ev.args.file_path) {
            const fp = ev.args.file_path;
            if (!writtenFiles.includes(fp)) writtenFiles.push(fp);
          }
          break;

        case 'tool_result':
          renderToolResult(ev);
          break;

        case 'thinking':
          // Raw LLM text — shown only if it contains no step markers (already rendered)
          // We skip rendering raw thinking to avoid duplication with step cards.
          break;

        case 'final':
          // The LLM's final text before done — skip; done event handles rendering.
          break;

        case 'done':
          setStatus('Idle', 'idle');
          renderFinalDone(ev.result || {});
          if ((ev.result || {}).status !== 'ask') {
            enableInput();
          }
          // Update state messages from result if available
          if (ev.result && ev.result.status === 'success') {
            state.messages.push({ role: 'assistant', content: ev.result.summary || '' });
          }
          // Render performance metrics panel
          {
            const metrics = ev.metrics || (ev.result && ev.result.metrics);
            if (metrics) renderMetrics(metrics);
          }
          break;

        case 'error':
          setStatus('Error', 'error');
          appendAgentBubble(`
            <div class="summary-box error">
              <strong style="color:var(--danger);">Error</strong><br>
              ${escapeHtml(ev.message || 'Unknown error')}
            </div>
          `);
          enableInput();
          break;
      }
    }

    // ── Event listeners ────────────────────────────────────────────────────

    sendBtn.addEventListener('click', send);

    if (stopBtn) {
      stopBtn.addEventListener('click', () => {
        if (currentES) { currentES.close(); currentES = null; }
        setStatus('Stopped by user.', 'idle');
        enableInput();
      });
    }

    promptEl.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter' && (ev.metaKey || ev.ctrlKey)) {
        ev.preventDefault();
        send();
      }
    });

    resetBtn.addEventListener('click', () => {
      state = { messages: [] };
      promptEl.value = '';
      outputEl.innerHTML = '<div class="tiny">Responses from the agent will appear here. You will see each reasoning step live as the agent works.</div>';
      outputMode.textContent = 'Waiting for first response…';
      setStatus('Idle', 'idle');
      agentBubble = null;
      Object.keys(stepCards).forEach(k => delete stepCards[k]);
      enableInput();
      promptEl.focus();
      // Hide metrics panel on reset
      const mp = document.getElementById('metricsPanel');
      if (mp) mp.classList.remove('visible');
      currentSessionId = null;
      // Reset upload state, written files list, and hide download panel
      uploadInfo = null;
      writtenFiles = [];
      codeZipInput.value = '';
      setUploadStatus('No file uploaded. Upload a ZIP of your code directory to let the agent read it.');
      if (downloadPanel) downloadPanel.classList.remove('visible');
    });

    // ── Performance Metrics ────────────────────────────────────────────────

    let currentSessionId = null;

    function renderMetrics(metrics) {
      if (!metrics) return;
      currentSessionId = metrics.session_id || null;

      const panel = document.getElementById('metricsPanel');
      const grid  = document.getElementById('metricsGrid');
      const tbody = document.getElementById('metricsTableBody');
      if (!panel || !grid || !tbody) return;

      // Helper: format number with commas, or 'n/a'
      function fmt(v) { return v != null ? Number(v).toLocaleString() : 'n/a'; }
      function fmtS(v) { return v != null ? Number(v).toFixed(2) + ' s' : 'n/a'; }

      // Build stat cards
      const perTurnArr = Array.isArray(metrics.per_turn) ? metrics.per_turn : [];
      const avgTokPerTurn = (metrics.total_turns && metrics.total_tokens)
        ? Math.round(metrics.total_tokens / metrics.total_turns) : null;
      const avgTimePerTurn = (metrics.total_turns && metrics.total_elapsed_s)
        ? (metrics.total_elapsed_s / metrics.total_turns) : null;
      const completionRatio = (metrics.total_tokens && metrics.total_completion_tokens)
        ? (metrics.total_completion_tokens / metrics.total_tokens * 100) : null;
      // Collect top tools from per_turn tool_call_names
      const toolCounts = {};
      perTurnArr.forEach(t => {
        const names = Array.isArray(t.tool_call_names) ? t.tool_call_names : [];
        names.forEach(n => { toolCounts[n] = (toolCounts[n] || 0) + 1; });
      });
      const topTools = Object.entries(toolCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3)
        .map(([n, c]) => n + '×' + c)
        .join(', ') || null;

      const stats = [
        { label: 'Total time',        value: fmtS(metrics.total_elapsed_s) },
        { label: 'LLM turns',         value: fmt(metrics.total_turns) },
        { label: 'Tool calls',        value: fmt(metrics.total_tool_calls) },
        { label: 'Total tokens',      value: fmt(metrics.total_tokens) },
        { label: 'Prompt tokens',     value: fmt(metrics.total_prompt_tokens) },
        { label: 'Completion tok',    value: fmt(metrics.total_completion_tokens) },
        { label: 'Avg tok/turn',      value: avgTokPerTurn != null ? fmt(avgTokPerTurn) : 'n/a' },
        { label: 'Avg time/turn',     value: avgTimePerTurn != null ? fmtS(avgTimePerTurn) : 'n/a' },
        { label: 'Completion ratio',  value: completionRatio != null ? completionRatio.toFixed(1) + '%' : 'n/a' },
        { label: 'Final status',      value: metrics.final_status || 'n/a' },
        { label: 'Codebase',          value: metrics.codebase || 'n/a' },
        { label: 'Top tools',         value: topTools || 'n/a' },
      ];
      grid.innerHTML = stats.map(s => `
        <div class="metrics-stat">
          <div class="metrics-stat-label">${escapeHtml(s.label)}</div>
          <div class="metrics-stat-value">${escapeHtml(s.value)}</div>
        </div>
      `).join('');

      // Build per-turn table
      tbody.innerHTML = perTurnArr.map(t => {
        // Show actual step numbers (e.g. "3", "4, 5") if available, else count.
        const stepNums = Array.isArray(t.step_numbers) && t.step_numbers.length > 0
          ? t.step_numbers.join(', ')
          : (t.step_count != null && t.step_count > 0 ? String(t.step_count) + ' step(s)' : '—');
        const toolNames = Array.isArray(t.tool_call_names) && t.tool_call_names.length > 0
          ? t.tool_call_names.join(', ')
          : '—';
        return `
          <tr>
            <td>${t.turn != null ? t.turn : '?'}</td>
            <td>${fmtS(t.elapsed_s)}</td>
            <td>${fmt(t.prompt_tokens)}</td>
            <td>${fmt(t.completion_tokens)}</td>
            <td>${fmt(t.total_tokens)}</td>
            <td>${t.tool_call_count != null ? t.tool_call_count : 0}</td>
            <td>${stepNums}</td>
            <td>${escapeHtml(toolNames)}</td>
          </tr>
        `;
      }).join('');

      panel.classList.add('visible');
    }

    // Wire up the download button
    const metricsDownloadBtn = document.getElementById('metricsDownloadBtn');
    if (metricsDownloadBtn) {
      metricsDownloadBtn.addEventListener('click', () => {
        const url = currentSessionId
          ? '/api/metrics/export?session_id=' + encodeURIComponent(currentSessionId)
          : '/api/metrics/export';
        const a = document.createElement('a');
        a.href = url;
        a.download = currentSessionId ? 'metrics_' + currentSessionId + '.json' : 'metrics.json';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      });
    }
  </script>
</body>
</html>
    """


# ---------------------------------------------------------------------------
# SSE streaming endpoint (new)
# ---------------------------------------------------------------------------

@app.post("/api/stream")
async def api_stream(request: Request) -> StreamingResponse:
    """
    Stream agent events as Server-Sent Events.

    Accepts JSON body: ``{"messages": [{"role": "user"|"assistant", "content": "..."}]}``

    Each SSE event is a JSON-encoded agent event dict.  The final event has
    ``type == "done"`` and contains the structured result.
    """
    payload: Dict[str, Any] = await request.json()
    messages: List[Dict[str, str]] = payload.get("messages") or []

    return StreamingResponse(
        _sse_generator(messages),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Metrics export endpoint
# ---------------------------------------------------------------------------

@app.get("/api/metrics/export")
async def api_metrics_export(
    session_id: Optional[str] = Query(default=None, description="Session ID to export"),
) -> Response:
    """
    Download the full metrics JSON for a completed session.

    Query parameter:
      ``session_id`` – the UUID returned in the ``done`` SSE event's
      ``metrics.session_id`` field.  If omitted, the most recent session is
      returned.

    Returns a JSON file download (``Content-Disposition: attachment``).
    The download filename matches the log file naming convention:
    ``<codebase>_<YYYYMMDD>.json``.
    """
    if session_id and session_id in _session_metrics:
        data = _session_metrics[session_id]
    elif _session_order:
        # Fall back to the most recent session.
        data = _session_metrics.get(_session_order[-1])
    else:
        data = None

    if data is None:
        return JSONResponse(
            {"error": "No metrics available. Run the agent first."},
            status_code=404,
        )

    # Build a filename that matches the log/ file naming convention.
    codebase = data.get("codebase") or data.get("session_id", "unknown")
    started_at = data.get("started_at", "")
    date_str = started_at[:10].replace("-", "") if started_at else "unknown"
    filename = f"{codebase}_{date_str}.json"
    content = json.dumps(data, indent=2, ensure_ascii=False)
    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@app.get("/api/metrics/list")
async def api_metrics_list() -> JSONResponse:
    """Return a list of available session IDs with their summary stats."""
    sessions = []
    for sid in reversed(_session_order):
        m = _session_metrics.get(sid, {})
        # Support both full format (summary nested under "summary") and compact
        # format (aggregate fields at the top level).
        s = m.get("summary") or {}
        sessions.append({
            "session_id": sid,
            "started_at": m.get("started_at"),
            "finished_at": m.get("finished_at"),
            "total_elapsed_s": m.get("total_elapsed_s"),
            "total_turns": s.get("total_turns") or m.get("total_turns"),
            "total_tool_calls": s.get("total_tool_calls") or m.get("total_tool_calls"),
            "total_tokens": s.get("total_tokens") or m.get("total_tokens"),
            "final_status": s.get("final_status") or m.get("final_status"),
            "codebase": m.get("codebase"),
        })
    return JSONResponse({"sessions": sessions})


# ---------------------------------------------------------------------------
# Log files listing endpoint
# ---------------------------------------------------------------------------

@app.get("/api/logs")
async def api_logs() -> JSONResponse:
    """
    List all session log files saved under ``BUILD_DIR/log/``.

    Each entry contains:
      - ``filename``   – the JSON filename (e.g. ``art_simple_20260320.json``).
      - ``path``       – absolute path on the server.
      - ``size_bytes`` – file size.
      - ``modified_at``– ISO-8601 UTC last-modified timestamp.
      - ``codebase``   – extracted from the filename (part before the date).
      - ``date``       – date string from the filename (YYYYMMDD).
    """
    log_dir = Path(get_project_root()) / "log"
    if not log_dir.exists():
        return JSONResponse({"logs": []})

    entries = []
    for p in sorted(log_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
        stat = p.stat()
        # Parse codebase and date from filename: <codebase>_<YYYYMMDD>[_N].json
        stem = p.stem  # e.g. "art_simple_20260320" or "art_simple_20260320_2"
        import re as _re
        m = _re.match(r"^(.+?)_(\d{8})(?:_\d+)?$", stem)
        codebase = m.group(1) if m else stem
        date_str = m.group(2) if m else ""
        from datetime import datetime as _dt, timezone as _tz
        modified_at = _dt.fromtimestamp(stat.st_mtime, tz=_tz.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        entries.append({
            "filename": p.name,
            "path": str(p),
            "size_bytes": stat.st_size,
            "modified_at": modified_at,
            "codebase": codebase,
            "date": date_str,
        })
    return JSONResponse({"logs": entries})


# ---------------------------------------------------------------------------
# Replay page – reconstruct a session from a downloaded JSON log
# ---------------------------------------------------------------------------

@app.get("/replay", response_class=HTMLResponse)
async def replay_page() -> str:
    """
    Serve a standalone replay page.

    The user uploads a session JSON log file (produced by ``log_session`` or
    downloaded via ``/api/metrics/export``).  The page reconstructs the full
    conversation (step cards, tool calls, tool results, final summary) and the
    performance metrics panel, exactly as the main UI displays them live.
    """
    return r"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Guard Agent – Session Replay</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #050812;
      --panel: #0f172a;
      --accent: #38bdf8;
      --accent-soft: rgba(56, 189, 248, 0.16);
      --border: #1e293b;
      --text: #e5e7eb;
      --muted: #9ca3af;
      --danger: #f97373;
      --success: #86efac;
      --warn: #fbbf24;
      --tool-color: #a5b4fc;
      --mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      --sans: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0; padding: 0;
      font-family: var(--sans);
      background: radial-gradient(circle at top, #0f172a 0, #020617 55%);
      color: var(--text);
      min-height: 100vh;
      display: flex; align-items: stretch; justify-content: center;
    }
    .shell {
      max-width: 1120px; width: 100%;
      padding: 24px 16px 32px;
      display: flex; flex-direction: column; gap: 16px;
      flex: 1; min-height: 100vh;
    }
    .card {
      background: radial-gradient(circle at top left, rgba(56,189,248,0.08), transparent 55%), var(--panel);
      border-radius: 16px; border: 1px solid var(--border);
      box-shadow: 0 32px 80px rgba(15,23,42,0.9);
      padding: 18px 18px 12px;
      backdrop-filter: blur(18px);
    }
    .header { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 12px; }
    .title { font-size: 18px; font-weight: 600; letter-spacing: 0.02em; }
    .subtitle { font-size: 13px; color: var(--muted); }
    .badge {
      border-radius: 999px; padding: 4px 10px;
      border: 1px solid rgba(148,163,184,0.5);
      font-size: 11px; color: var(--muted);
      display: inline-flex; align-items: center; gap: 6px;
    }
    .panel {
      background: rgba(15,23,42,0.82); border-radius: 14px;
      border: 1px solid rgba(30,64,175,0.65);
      padding: 10px 12px 12px;
    }
    .panel-header {
      font-size: 13px; font-weight: 500; color: #e5e7eb;
      display: flex; align-items: center; justify-content: space-between; gap: 8px;
      margin-bottom: 8px;
    }
    .panel-header small { font-weight: 400; color: var(--muted); font-size: 11px; }
    .button {
      border-radius: 999px; border: none; padding: 6px 14px;
      background: linear-gradient(to right, #0ea5e9, #6366f1);
      color: white; font-size: 12px; font-weight: 500; cursor: pointer;
      display: inline-flex; align-items: center; gap: 6px;
      box-shadow: 0 14px 35px rgba(37,99,235,0.55);
    }
    .button:disabled { opacity: 0.55; cursor: default; box-shadow: none; }
    .button-secondary {
      background: transparent; border: 1px solid rgba(148,163,184,0.65);
      color: var(--muted); box-shadow: none; padding-inline: 10px;
      border-radius: 999px; padding: 6px 14px; font-size: 12px; cursor: pointer;
    }
    .upload-section {
      margin-bottom: 12px; padding: 10px 12px; border-radius: 12px;
      border: 1px dashed rgba(56,189,248,0.4); background: rgba(56,189,248,0.04);
      display: flex; flex-direction: column; gap: 8px;
    }
    .upload-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    .upload-label { font-size: 12px; font-weight: 500; color: var(--accent); white-space: nowrap; }
    .upload-file-input {
      flex: 1; min-width: 0; font-size: 11px; color: var(--muted);
      background: rgba(15,23,42,0.9); border: 1px solid rgba(51,65,85,0.9);
      border-radius: 8px; padding: 4px 8px; cursor: pointer;
    }
    .upload-file-input::file-selector-button {
      background: rgba(56,189,248,0.15); border: 1px solid rgba(56,189,248,0.4);
      border-radius: 6px; color: var(--accent); font-size: 11px;
      padding: 2px 8px; cursor: pointer; margin-right: 8px;
    }
    .upload-status { font-size: 11px; color: var(--muted); }
    .upload-status.ok  { color: var(--success); }
    .upload-status.err { color: var(--danger); }
    .chat-output { overflow-y: auto; padding: 4px 2px 2px 2px; max-height: 70vh; }
    .msg-user { margin-top: 8px; display: flex; justify-content: flex-end; }
    .msg-user-bubble {
      max-width: 82%; border-radius: 14px; padding: 7px 10px;
      background: linear-gradient(to right, #0ea5e9, #6366f1);
      color: white; font-size: 12px; white-space: pre-wrap;
    }
    .msg-agent { margin-top: 8px; display: flex; justify-content: flex-start; }
    .msg-agent-bubble {
      max-width: 96%; border-radius: 14px; padding: 7px 9px;
      background: rgba(15,23,42,0.96); border: 1px solid rgba(30,64,175,0.85);
      font-size: 12px;
    }
    .step-card {
      border-radius: 10px; border: 1px solid rgba(30,64,175,0.7);
      background: radial-gradient(circle at top left, rgba(59,130,246,0.10), transparent 60%), rgba(15,23,42,0.97);
      padding: 8px 10px; margin-top: 6px; font-size: 12px;
    }
    .step-card-header { display: flex; align-items: center; gap: 8px; margin-bottom: 5px; }
    .step-num {
      background: rgba(56,189,248,0.18); color: var(--accent);
      border-radius: 999px; padding: 1px 7px; font-size: 11px; font-weight: 600; white-space: nowrap;
    }
    .step-name { font-weight: 600; color: #e5e7eb; flex: 1; }
    .step-status-badge {
      font-size: 10px; border-radius: 999px; padding: 1px 7px; border: 1px solid;
      color: var(--success); border-color: var(--success);
    }
    .step-row { display: flex; gap: 6px; margin-top: 3px; font-size: 11px; color: var(--muted); }
    .step-label { color: var(--accent); font-weight: 600; min-width: 42px; }
    .step-value { flex: 1; white-space: pre-wrap; }
    .tool-badge {
      display: inline-flex; align-items: center; gap: 3px;
      background: rgba(165,180,252,0.12); color: var(--tool-color);
      border: 1px solid rgba(165,180,252,0.3); border-radius: 999px;
      padding: 1px 7px; font-size: 10px; font-family: var(--mono);
      margin-right: 3px; margin-top: 2px;
    }
    .tool-call-inline {
      margin-top: 4px; padding: 4px 7px; border-radius: 7px;
      background: rgba(165,180,252,0.07); border: 1px dashed rgba(165,180,252,0.25);
      font-size: 11px; color: var(--tool-color); font-family: var(--mono);
    }
    .tool-result-inline {
      margin-top: 2px; padding: 3px 7px; border-radius: 7px;
      background: rgba(15,23,42,0.9); border: 1px solid rgba(51,65,85,0.7);
      font-size: 10px; color: var(--muted); font-family: var(--mono);
      max-height: 120px; overflow: auto; white-space: pre;
    }
    .step-result-box {
      margin-top: 5px; padding: 4px 7px; border-radius: 7px;
      background: rgba(34,197,94,0.06); border: 1px solid rgba(34,197,94,0.2);
      font-size: 11px; color: #bbf7d0; white-space: pre-wrap;
    }
    .summary-box {
      font-size: 13px; color: var(--text); padding: 6px 8px; border-radius: 10px;
      border: 1px solid rgba(51,65,85,0.9);
      background: radial-gradient(circle at top left, rgba(56,189,248,0.12), transparent 55%), #020617;
      white-space: pre-wrap;
    }
    .summary-box.success { border-color: #166534; background: rgba(22,101,52,0.1); }
    .summary-box.error   { border-color: #7f1d1d; background: rgba(127,29,29,0.1); }
    .summary-box.ask     { border-color: rgba(251,191,36,0.5); background: rgba(251,191,36,0.05); }
    details {
      margin-top: 6px; border-radius: 8px;
      background: rgba(15,23,42,0.9); border: 1px dashed rgba(55,65,81,0.9);
      padding: 4px 6px;
    }
    summary { cursor: pointer; font-size: 11px; color: var(--muted); outline: none; }
    .code-block {
      margin-top: 4px; border-radius: 10px; background: #020617;
      border: 1px solid rgba(51,65,85,0.9); max-height: 240px; overflow: auto;
      font-family: var(--mono); font-size: 11px; padding: 6px 8px; white-space: pre;
    }
    .tiny { font-size: 11px; color: var(--muted); }
    /* ── Metrics panel ── */
    .metrics-panel {
      margin-top: 10px; border-radius: 12px;
      border: 1px solid rgba(99,102,241,0.45);
      background: radial-gradient(circle at top left, rgba(99,102,241,0.08), transparent 60%), rgba(15,23,42,0.97);
      padding: 10px 12px 12px; font-size: 12px;
    }
    .metrics-header {
      display: flex; align-items: center; justify-content: space-between;
      gap: 8px; margin-bottom: 8px;
    }
    .metrics-title { font-size: 13px; font-weight: 600; color: #a5b4fc; }
    .metrics-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
      gap: 6px; margin-bottom: 8px;
    }
    .metrics-stat {
      background: rgba(15,23,42,0.9); border: 1px solid rgba(51,65,85,0.8);
      border-radius: 8px; padding: 6px 8px;
    }
    .metrics-stat-label { font-size: 10px; color: var(--muted); margin-bottom: 2px; }
    .metrics-stat-value { font-size: 14px; font-weight: 600; color: #a5b4fc; font-family: var(--mono); }
    .metrics-table { width: 100%; border-collapse: collapse; font-size: 11px; font-family: var(--mono); }
    .metrics-table th {
      text-align: left; color: var(--muted); font-weight: 500;
      padding: 3px 6px; border-bottom: 1px solid rgba(51,65,85,0.7);
    }
    .metrics-table td { padding: 3px 6px; color: var(--text); border-bottom: 1px solid rgba(30,41,59,0.6); }
    .metrics-table tr:last-child td { border-bottom: none; }
    /* ── Session info ── */
    .session-info {
      margin-bottom: 10px; padding: 8px 10px; border-radius: 10px;
      border: 1px solid rgba(51,65,85,0.7); background: rgba(15,23,42,0.8);
      font-size: 11px; color: var(--muted); display: flex; flex-wrap: wrap; gap: 12px;
    }
    .session-info span { display: flex; gap: 4px; }
    .session-info strong { color: var(--text); }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }

    /* ── Markdown rendered content ── */
    .md-content { font-size: 12px; color: var(--text); line-height: 1.6; }
    .md-content p { margin: 0.4em 0; }
    .md-content p:first-child { margin-top: 0; }
    .md-content p:last-child { margin-bottom: 0; }
    .md-content h1, .md-content h2, .md-content h3,
    .md-content h4, .md-content h5, .md-content h6 {
      margin: 0.6em 0 0.3em; color: #e5e7eb; font-weight: 600;
    }
    .md-content ul, .md-content ol { margin: 0.3em 0; padding-left: 1.4em; }
    .md-content li { margin: 0.15em 0; }
    .md-content code {
      font-family: var(--mono); font-size: 11px;
      background: rgba(56,189,248,0.1); border-radius: 4px;
      padding: 1px 4px; color: var(--accent);
    }
    .md-content pre {
      background: rgba(15,23,42,0.95); border: 1px solid rgba(51,65,85,0.9);
      border-radius: 8px; padding: 8px 10px; overflow-x: auto; margin: 0.4em 0;
    }
    .md-content pre code { background: none; padding: 0; color: var(--text); }
    .md-content strong { color: #e5e7eb; }
    .md-content em { color: var(--muted); }
    .md-content blockquote {
      border-left: 3px solid var(--accent); margin: 0.4em 0;
      padding: 2px 10px; color: var(--muted);
    }
    .md-content a { color: var(--accent); }
    .md-content hr { border: none; border-top: 1px solid rgba(51,65,85,0.7); margin: 0.5em 0; }
  </style>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
</head>
<body>
  <div class="shell">
    <div class="card">
      <div class="header">
        <div>
          <div class="title">🔁 Session Replay</div>
          <div class="subtitle">Upload a session JSON log to reconstruct the full conversation and performance metrics.</div>
        </div>
        <div>
          <a href="/" class="badge" style="text-decoration:none; cursor:pointer;">← Back to Agent</a>
        </div>
      </div>

      <!-- ── File upload ── -->
      <div class="upload-section">
        <div class="upload-row">
          <span class="upload-label">📂 Session log (JSON):</span>
          <input type="file" id="logFileInput" class="upload-file-input" accept=".json">
          <button class="button" id="loadBtn" type="button">Load</button>
        </div>
        <div class="upload-row">
          <span class="upload-status" id="loadStatus">Select a session JSON file exported from the agent.</span>
        </div>
      </div>

      <!-- ── Session metadata ── -->
      <div class="session-info" id="sessionInfo" style="display:none;"></div>

      <!-- ── Conversation replay ── -->
      <div class="panel" id="replayPanel" style="display:none;">
        <div class="panel-header">
          <span>Conversation Replay</span>
          <small id="replayMeta"></small>
        </div>
        <div id="replayOutput" class="chat-output"></div>
      </div>

      <!-- ── Metrics panel ── -->
      <div class="metrics-panel" id="metricsPanel" style="display:none;">
        <div class="metrics-header">
          <span class="metrics-title">📊 Performance Metrics</span>
        </div>
        <div class="metrics-grid" id="metricsGrid"></div>
        <details open>
          <summary>Per-turn breakdown</summary>
          <table class="metrics-table" id="metricsTable">
            <thead>
              <tr>
                <th>Turn</th><th>Started at</th><th>Elapsed (s)</th><th>Prompt tok</th>
                <th>Completion tok</th><th>Total tok</th><th>Tool calls</th><th>Step #(s)</th><th>Tools used</th>
              </tr>
            </thead>
            <tbody id="metricsTableBody"></tbody>
          </table>
        </details>
      </div>
    </div>

    <div class="tiny">
      Tip: session logs are saved automatically to <code>BUILD_DIR/log/</code> after each agent run.
      You can also download them from the main UI via the "Download JSON" button in the metrics panel.
    </div>
  </div>

  <script>
    const logFileInput = document.getElementById('logFileInput');
    const loadBtn      = document.getElementById('loadBtn');
    const loadStatus   = document.getElementById('loadStatus');
    const sessionInfo  = document.getElementById('sessionInfo');
    const replayPanel  = document.getElementById('replayPanel');
    const replayOutput = document.getElementById('replayOutput');
    const replayMeta   = document.getElementById('replayMeta');
    const metricsPanel = document.getElementById('metricsPanel');
    const metricsGrid  = document.getElementById('metricsGrid');
    const metricsTableBody = document.getElementById('metricsTableBody');

    function setStatus(text, cls) {
      loadStatus.textContent = text;
      loadStatus.className = 'upload-status' + (cls ? ' ' + cls : '');
    }

    function escapeHtml(str) {
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }

    // Render text as markdown HTML (uses marked.js if available, falls back to pre-wrap).
    function renderMarkdown(text) {
      if (!text) return '';
      if (typeof marked !== 'undefined') {
        try {
          return marked.parse(String(text), { breaks: true, gfm: true });
        } catch(e) { /* fall through */ }
      }
      return '<pre style="white-space:pre-wrap; margin:0;">' + escapeHtml(String(text)) + '</pre>';
    }

    // Extract summary text from a value that may be a JSON string, object, or plain text.
    // Handles mixed strings like "Some plain text\n\n{\"status\": \"success\", \"summary\": \"...\"}"
    function extractSummaryText(value) {
      if (!value) return '';
      const s = String(value).trim();
      // Find the first '{' which may indicate an embedded JSON object.
      const jsonStart = s.indexOf('{');
      if (jsonStart !== -1) {
        const prefix = s.substring(0, jsonStart).trim();
        const jsonPart = s.substring(jsonStart);
        try {
          const parsed = JSON.parse(jsonPart);
          if (parsed && typeof parsed.summary === 'string') {
            // Combine any plain-text prefix with the extracted summary.
            return prefix ? prefix + '\n\n' + parsed.summary : parsed.summary;
          }
          // JSON parsed but no summary field — return prefix + stringified JSON.
          if (prefix) return prefix;
          return JSON.stringify(parsed, null, 2);
        } catch(e) { /* not valid JSON from this position */ }
      }
      return s;
    }

    function fmt(v)  { return v != null ? Number(v).toLocaleString() : 'n/a'; }
    function fmtS(v) { return v != null ? Number(v).toFixed(2) + ' s' : 'n/a'; }

    // ── Normalise data: handle both compact (metrics_summary) and full (SessionMetrics) formats ──

    function normalizeData(raw) {
      // Detect compact format: has "per_turn" array and no "turns" array.
      const isCompact = Array.isArray(raw.per_turn) && !Array.isArray(raw.turns);

      if (!isCompact) {
        // Already full format – ensure summary exists and has all expected fields.
        if (!raw.summary) {
          raw.summary = {};
        }
        const s = raw.summary;
        const turns = Array.isArray(raw.turns) ? raw.turns : [];
        // Fill in missing summary fields from top-level or computed values.
        if (s.total_turns == null) s.total_turns = turns.length;
        if (s.total_tool_calls == null) s.total_tool_calls = raw.total_tool_calls;
        if (s.total_prompt_tokens == null) s.total_prompt_tokens = raw.total_prompt_tokens;
        if (s.total_completion_tokens == null) s.total_completion_tokens = raw.total_completion_tokens;
        if (s.total_tokens == null) s.total_tokens = raw.total_tokens;
        if (s.final_status == null) s.final_status = raw.final_status || 'unknown';
        if (s.final_summary == null) s.final_summary = raw.final_summary || (raw.final_result && raw.final_result.summary) || null;
        if (s.final_error == null) s.final_error = raw.final_error || (raw.final_result && (raw.final_result.error_message || raw.final_result.assistant_question)) || null;
        // Compute averages if not already present.
        if (s.avg_elapsed_per_turn_s == null && turns.length > 0) {
          const totalElapsed = turns.reduce((acc, t) => acc + (t.elapsed_s || 0), 0);
          s.avg_elapsed_per_turn_s = Math.round(totalElapsed / turns.length * 1000) / 1000;
        }
        if (s.avg_tokens_per_turn == null && s.total_tokens != null && turns.length > 0) {
          s.avg_tokens_per_turn = Math.round(s.total_tokens / turns.length);
        }
        return raw;
      }

      // Convert compact → full format.
      // Compute avg_elapsed_per_turn_s and avg_tokens_per_turn if not present.
      const perTurnArr = raw.per_turn || [];
      const avgElapsed = raw.avg_elapsed_per_turn_s != null
        ? raw.avg_elapsed_per_turn_s
        : (raw.total_turns > 0 && raw.total_elapsed_s != null
            ? raw.total_elapsed_s / raw.total_turns : null);
      const avgTokens = raw.avg_tokens_per_turn != null
        ? raw.avg_tokens_per_turn
        : (raw.total_turns > 0 && raw.total_tokens != null
            ? Math.round(raw.total_tokens / raw.total_turns) : null);

      const summary = {
        total_turns: raw.total_turns,
        total_tool_calls: raw.total_tool_calls,
        total_prompt_tokens: raw.total_prompt_tokens,
        total_completion_tokens: raw.total_completion_tokens,
        total_tokens: raw.total_tokens,
        avg_elapsed_per_turn_s: avgElapsed,
        avg_tokens_per_turn: avgTokens,
        final_status: raw.final_status || 'unknown',
        final_summary: raw.final_summary || null,
      };

      // Convert per_turn entries to TurnMetrics-like objects.
      const turns = perTurnArr.map(pt => {
        // Build steps array: prefer full steps array, else build from step_numbers/step_names.
        let steps;
        if (Array.isArray(pt.steps) && pt.steps.length > 0) {
          steps = pt.steps;
        } else if (Array.isArray(pt.step_numbers) && pt.step_numbers.length > 0) {
          steps = pt.step_numbers.map((num, i) => ({
            step: num,
            name: (pt.step_names || [])[i] || '',
            elapsed_s: null,
          }));
        } else {
          steps = new Array(pt.step_count || 0).fill({});
        }
        // Build tool_calls array: prefer full tool_calls, else build stubs from names.
        let toolCalls;
        if (Array.isArray(pt.tool_calls) && pt.tool_calls.length > 0) {
          toolCalls = pt.tool_calls;
        } else if (Array.isArray(pt.tool_call_names) && pt.tool_call_names.length > 0) {
          toolCalls = pt.tool_call_names.map(n => ({ name: n }));
        } else {
          toolCalls = new Array(pt.tool_call_count || 0).fill({});
        }
        return {
          turn: pt.turn,
          started_at: pt.started_at || null,
          elapsed_s: pt.elapsed_s,
          prompt_tokens: pt.prompt_tokens,
          completion_tokens: pt.completion_tokens,
          total_tokens: pt.total_tokens,
          tool_calls: toolCalls,
          tool_call_names: pt.tool_call_names || [],
          steps: steps,
          step_numbers: pt.step_numbers || [],
          step_names: pt.step_names || [],
          conversation_events: pt.conversation_events || [],
        };
      });

      return {
        session_id: raw.session_id,
        codebase: raw.codebase,
        started_at: raw.started_at,
        finished_at: raw.finished_at,
        total_elapsed_s: raw.total_elapsed_s,
        llm_model: raw.llm_model || null,
        summary: summary,
        turns: turns,
        conversation: raw.conversation || [],
        final_result: raw.final_result || null,
      };
    }

    // ── Render metrics panel ────────────────────────────────────────────────

    function renderMetrics(data) {
      // data is already normalised (full SessionMetrics format).
      const s = data.summary || {};
      const turns = Array.isArray(data.turns) ? data.turns : [];
      const totalTurns = s.total_turns != null ? s.total_turns : turns.length;

      // Prefer pre-computed averages from summary; fall back to computing from turns.
      const avgTokensPerTurn = s.avg_tokens_per_turn != null
        ? s.avg_tokens_per_turn
        : (totalTurns > 0 && s.total_tokens != null ? Math.round(s.total_tokens / totalTurns) : null);
      const avgElapsedPerTurn = s.avg_elapsed_per_turn_s != null
        ? s.avg_elapsed_per_turn_s
        : (turns.length > 0
            ? (turns.reduce((acc, t) => acc + (t.elapsed_s || 0), 0) / turns.length)
            : null);
      const completionRatio = s.total_prompt_tokens > 0 && s.total_completion_tokens != null
        ? (s.total_completion_tokens / s.total_prompt_tokens * 100).toFixed(1) + '%' : 'n/a';

      // Collect all tool names used across turns
      const toolCounts = {};
      for (const t of turns) {
        const names = Array.isArray(t.tool_calls) && t.tool_calls.some(tc => tc.name)
          ? t.tool_calls.map(tc => tc.name).filter(Boolean)
          : (Array.isArray(t.tool_call_names) ? t.tool_call_names : []);
        for (const n of names) { toolCounts[n] = (toolCounts[n] || 0) + 1; }
      }
      const topTools = Object.entries(toolCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5)
        .map(([n, c]) => n + ' ×' + c)
        .join(', ') || 'n/a';

      const stats = [
        { label: 'Total time',        value: fmtS(data.total_elapsed_s) },
        { label: 'LLM turns',         value: fmt(totalTurns) },
        { label: 'Tool calls',        value: fmt(s.total_tool_calls) },
        { label: 'Total tokens',      value: fmt(s.total_tokens) },
        { label: 'Prompt tokens',     value: fmt(s.total_prompt_tokens) },
        { label: 'Completion tok',    value: fmt(s.total_completion_tokens) },
        { label: 'Avg tok/turn',      value: avgTokensPerTurn != null ? fmt(avgTokensPerTurn) : 'n/a' },
        { label: 'Avg time/turn',     value: avgElapsedPerTurn != null ? avgElapsedPerTurn.toFixed(2) + ' s' : 'n/a' },
        { label: 'Completion ratio',  value: completionRatio },
        { label: 'Final status',      value: escapeHtml(s.final_status || 'unknown') },
        { label: 'Codebase',          value: escapeHtml(data.codebase || 'n/a') },
        { label: 'LLM model',         value: escapeHtml(data.llm_model || 'n/a') },
        { label: 'Top tools',         value: escapeHtml(topTools) },
      ];
      metricsGrid.innerHTML = stats.map(st => `
        <div class="metrics-stat">
          <div class="metrics-stat-label">${escapeHtml(st.label)}</div>
          <div class="metrics-stat-value" style="font-size:${st.label === 'Top tools' ? '10px' : '14px'};">${st.value}</div>
        </div>
      `).join('');

      metricsTableBody.innerHTML = turns.map(t => {
        // Show actual step numbers (e.g. "3", "4, 5") if available, else count or dash.
        let stepDisplay;
        if (Array.isArray(t.steps) && t.steps.length > 0) {
          // Full format: extract step numbers from steps array.
          const nums = t.steps.map(s => s.step).filter(n => n != null);
          stepDisplay = nums.length > 0 ? nums.join(', ') : t.steps.length + ' step(s)';
        } else if (Array.isArray(t.step_numbers) && t.step_numbers.length > 0) {
          // Compact format with step_numbers field.
          stepDisplay = t.step_numbers.join(', ');
        } else if (t.step_count != null && t.step_count > 0) {
          stepDisplay = t.step_count + ' step(s)';
        } else {
          stepDisplay = '—';
        }

        // Collect tool names for this turn
        const toolNames = Array.isArray(t.tool_calls)
          ? t.tool_calls.map(tc => tc.name).filter(Boolean)
          : (Array.isArray(t.tool_call_names) ? t.tool_call_names : []);
        const toolNamesDisplay = toolNames.length > 0
          ? toolNames.map(n => `<span class="tool-badge" style="font-size:9px;">${escapeHtml(n)}</span>`).join('')
          : '—';

        // Format started_at as time only (HH:MM:SS)
        const startedAt = t.started_at
          ? t.started_at.replace(/^\d{4}-\d{2}-\d{2}T/, '').replace('Z', '')
          : '—';

        const toolCallCount = Array.isArray(t.tool_calls) ? t.tool_calls.length : (t.tool_call_count != null ? t.tool_call_count : 0);
        return `
          <tr>
            <td>${t.turn != null ? t.turn : '?'}</td>
            <td style="font-size:10px; color:var(--muted);">${escapeHtml(startedAt)}</td>
            <td>${fmtS(t.elapsed_s)}</td>
            <td>${fmt(t.prompt_tokens)}</td>
            <td>${fmt(t.completion_tokens)}</td>
            <td>${fmt(t.total_tokens)}</td>
            <td>${toolCallCount}</td>
            <td>${stepDisplay}</td>
            <td style="max-width:200px; overflow:hidden;">${toolNamesDisplay}</td>
          </tr>
        `;
      }).join('');

      metricsPanel.style.display = 'block';
    }

    // ── Render session info bar ─────────────────────────────────────────────

    function renderSessionInfo(data) {
      const s = data.summary || {};
      const finalStatus = s.final_status || 'unknown';
      const statusColor = finalStatus === 'success' ? 'var(--success)'
        : finalStatus === 'error' ? 'var(--danger)'
        : finalStatus === 'ask' ? 'var(--warn)'
        : 'var(--muted)';
      const items = [
        `<span><strong>Session ID:</strong> ${escapeHtml(data.session_id || 'n/a')}</span>`,
        `<span><strong>Codebase:</strong> ${escapeHtml(data.codebase || 'n/a')}</span>`,
        `<span><strong>Started:</strong> ${escapeHtml(data.started_at || 'n/a')}</span>`,
        `<span><strong>Finished:</strong> ${escapeHtml(data.finished_at || 'n/a')}</span>`,
        `<span><strong>Duration:</strong> ${fmtS(data.total_elapsed_s)}</span>`,
        `<span><strong>Status:</strong> <span style="color:${statusColor};">${escapeHtml(finalStatus)}</span></span>`,
      ];
      if (data.llm_model) {
        items.push(`<span><strong>Model:</strong> ${escapeHtml(data.llm_model)}</span>`);
      }
      sessionInfo.innerHTML = items.join('');
      sessionInfo.style.display = 'flex';
    }

    // ── Replay conversation from turns[].conversation_events ────────────────

    function renderConversation(data) {
      replayOutput.innerHTML = '';
      const turns = Array.isArray(data.turns) ? data.turns : [];
      const flatConv = Array.isArray(data.conversation) ? data.conversation : [];

      // Check if any turn has conversation_events populated.
      const hasConvEvents = turns.some(t =>
        Array.isArray(t.conversation_events) && t.conversation_events.length > 0
      );

      if (turns.length === 0 && flatConv.length === 0) {
        replayOutput.insertAdjacentHTML('beforeend', `
          <div style="color:var(--muted); font-size:12px; padding:8px;">
            No conversation data available in this log file.
            This session was saved with an older version of the agent that did not record conversation history.
          </div>
        `);
        return;
      }

      if (!hasConvEvents && flatConv.length > 0) {
        // No per-turn conversation events – fall back to flat conversation array.
        renderFlatConversation(flatConv);
        renderFinalStatus(data);
        return;
      }

      if (!hasConvEvents && turns.length > 0) {
        // Turns exist but no conversation_events – show a notice and per-turn summary.
        replayOutput.insertAdjacentHTML('beforeend', `
          <div style="color:var(--muted); font-size:12px; padding:8px; margin-bottom:8px; border:1px dashed rgba(148,163,184,0.3); border-radius:8px;">
            ℹ Conversation text was not recorded in this log (compact format).
            Per-turn metrics are shown below.
          </div>
        `);
        renderTurnSummaries(turns);
        renderFinalStatus(data);
        return;
      }

      // Full format: render from turns[].conversation_events.
      renderTurnsWithEvents(turns, data);
    }

    // Render turns that have conversation_events.
    function renderTurnsWithEvents(turns, data) {
      // Track step cards across turns.
      const stepCards = {};
      let firstUserRendered = false;

      for (const turn of turns) {
        const events = Array.isArray(turn.conversation_events) ? turn.conversation_events : [];

        // Render user context messages (only from the first turn to avoid
        // repeating the full history for every turn).
        if (!firstUserRendered) {
          for (const ev of events) {
            if (ev.kind === 'context_user') {
              replayOutput.insertAdjacentHTML('beforeend', `
                <div class="msg-user">
                  <div class="msg-user-bubble">${escapeHtml(ev.content || '')}</div>
                </div>
              `);
              firstUserRendered = true;
            }
          }
        }

        // Create an agent bubble for this turn's model response + tool calls.
        const modelEvents = events.filter(e =>
          e.kind === 'model_response' || e.kind === 'tool_call' || e.kind === 'tool_result'
        );
        if (modelEvents.length === 0) continue;

        const bubble = document.createElement('div');
        bubble.className = 'msg-agent';
        const inner = document.createElement('div');
        inner.className = 'msg-agent-bubble';
        bubble.appendChild(inner);
        replayOutput.appendChild(bubble);

        // Render step cards from turn.steps.
        const steps = Array.isArray(turn.steps) ? turn.steps : [];
        for (const step of steps) {
          if (!step.step && !step.name) continue; // skip placeholder steps from compact format
          const card = document.createElement('div');
          card.className = 'step-card';
          card.innerHTML = `
            <div class="step-card-header">
              <span class="step-num">Step ${escapeHtml(String(step.step || '?'))}</span>
              <span class="step-name">${escapeHtml(step.name || '')}</span>
              <span class="step-status-badge">done</span>
            </div>
            ${step.elapsed_s != null ? `<div class="step-row"><span class="step-label">Time</span><span class="step-value">${fmtS(step.elapsed_s)}</span></div>` : ''}
            <div id="replay-step-calls-${turn.turn}-${step.step}"></div>
          `;
          inner.appendChild(card);
          stepCards[`${turn.turn}-${step.step}`] = card;
        }

        // Render model response text (if any).
        const modelResponseEvents = modelEvents.filter(e => e.kind === 'model_response');
        if (modelResponseEvents.length > 0 && steps.length === 0) {
          // Only show raw model response when there are no step cards to avoid duplication.
          for (const ev of modelResponseEvents) {
            if (ev.content && ev.content.trim()) {
              inner.insertAdjacentHTML('beforeend', `
                <div style="white-space:pre-wrap; font-size:12px; color:var(--text); padding:4px 2px;">${escapeHtml(ev.content)}</div>
              `);
            }
          }
        }

        // Render tool calls and results.
        let lastStepKey = null;
        if (steps.length > 0) {
          lastStepKey = `${turn.turn}-${steps[steps.length - 1].step}`;
        }

        for (const ev of modelEvents) {
          if (ev.kind === 'model_response') continue;
          if (ev.kind === 'tool_call') {
            const argsStr = ev.args ? JSON.stringify(ev.args, null, 2) : '';
            const callHtml = `
              <div class="tool-call-inline">
                ▶ <strong>${escapeHtml(ev.name || '')}</strong>
                ${argsStr ? `<details style="margin-top:2px;"><summary>args</summary><pre class="code-block">${escapeHtml(argsStr)}</pre></details>` : ''}
              </div>
            `;
            const targetEl = lastStepKey
              ? document.getElementById(`replay-step-calls-${lastStepKey}`)
              : null;
            if (targetEl) {
              targetEl.insertAdjacentHTML('beforeend', callHtml);
            } else {
              inner.insertAdjacentHTML('beforeend', callHtml);
            }
          } else if (ev.kind === 'tool_result') {
            const resultHtml = `
              <div class="tool-result-inline">${escapeHtml(ev.content || '')}</div>
            `;
            const targetEl = lastStepKey
              ? document.getElementById(`replay-step-calls-${lastStepKey}`)
              : null;
            if (targetEl) {
              targetEl.insertAdjacentHTML('beforeend', resultHtml);
            } else {
              inner.insertAdjacentHTML('beforeend', resultHtml);
            }
          }
        }
      }

      renderFinalStatus(data);
    }

    // Render a compact per-turn summary when no conversation_events are available.
    function renderTurnSummaries(turns) {
      for (const t of turns) {
        const toolCount = Array.isArray(t.tool_calls) ? t.tool_calls.length : (t.tool_call_count || 0);
        const stepCount = Array.isArray(t.steps) ? t.steps.length : (t.step_count || 0);
        replayOutput.insertAdjacentHTML('beforeend', `
          <div class="msg-agent">
            <div class="msg-agent-bubble">
              <div style="font-size:11px; color:var(--muted);">
                <strong style="color:var(--accent);">Turn ${t.turn}</strong>
                &nbsp;·&nbsp; ${fmtS(t.elapsed_s)}
                &nbsp;·&nbsp; ${fmt(t.total_tokens)} tokens
                &nbsp;·&nbsp; ${toolCount} tool call${toolCount !== 1 ? 's' : ''}
                &nbsp;·&nbsp; ${stepCount} step${stepCount !== 1 ? 's' : ''}
              </div>
            </div>
          </div>
        `);
      }
    }

    // Render the final status badge.
    function renderFinalStatus(data) {
      const s = data.summary || {};
      const status = s.final_status || 'unknown';
      // Extract and clean the summary text (may be a raw JSON string from the LLM).
      const rawSummary = s.final_summary || (data.final_result && data.final_result.summary) || '';
      const finalSummary = extractSummaryText(rawSummary);
      const rawError = s.final_error || (data.final_result && (data.final_result.error_message || data.final_result.assistant_question)) || '';
      const finalError = extractSummaryText(rawError);

      if (status === 'success') {
        replayOutput.insertAdjacentHTML('beforeend', `
          <div class="msg-agent">
            <div class="msg-agent-bubble">
              <div class="summary-box success">
                <strong style="color:var(--success);">✓ Task completed successfully</strong>
                ${finalSummary ? `<div class="md-content" style="margin-top:8px;">${renderMarkdown(finalSummary)}</div>` : ''}
              </div>
            </div>
          </div>
        `);
      } else if (status === 'error') {
        replayOutput.insertAdjacentHTML('beforeend', `
          <div class="msg-agent">
            <div class="msg-agent-bubble">
              <div class="summary-box error">
                <strong style="color:var(--danger);">✗ Error</strong>
                ${finalError ? `<div class="md-content" style="margin-top:8px; color:var(--danger);">${renderMarkdown(finalError)}</div>` : ''}
              </div>
            </div>
          </div>
        `);
      } else if (status === 'ask') {
        replayOutput.insertAdjacentHTML('beforeend', `
          <div class="msg-agent">
            <div class="msg-agent-bubble">
              <div class="summary-box ask">
                <strong style="color:var(--warn);">⚠ Agent asked for more information</strong>
                ${finalError ? `<div class="md-content" style="margin-top:8px; color:var(--warn);">${renderMarkdown(finalError)}</div>` : ''}
              </div>
            </div>
          </div>
        `);
      } else if (status !== 'unknown') {
        replayOutput.insertAdjacentHTML('beforeend', `
          <div class="msg-agent">
            <div class="msg-agent-bubble">
              <div class="summary-box">
                <strong>Status: ${escapeHtml(status)}</strong>
                ${finalSummary ? `<div class="md-content" style="margin-top:8px;">${renderMarkdown(finalSummary)}</div>` : ''}
              </div>
            </div>
          </div>
        `);
      }
    }

    // Fallback: render the flat conversation array (role + content).
    function renderFlatConversation(conv) {
      for (const msg of conv) {
        if (msg.role === 'system') continue;
        if (msg.role === 'user') {
          // Extract text content (may be string or array of parts).
          let content = msg.content || '';
          if (Array.isArray(content)) {
            content = content.map(p => (typeof p === 'object' ? (p.text || '') : String(p))).join('\n');
          }
          replayOutput.insertAdjacentHTML('beforeend', `
            <div class="msg-user">
              <div class="msg-user-bubble">${escapeHtml(String(content))}</div>
            </div>
          `);
        } else if (msg.role === 'assistant') {
          let content = msg.content || '';
          if (Array.isArray(content)) {
            content = content.map(p => (typeof p === 'object' ? (p.text || '') : String(p))).join('\n');
          }
          // Render tool_calls if present.
          const toolCallsHtml = (msg.tool_calls || []).map(tc => {
            const fn = tc.function || {};
            let argsStr = '';
            try { argsStr = JSON.stringify(JSON.parse(fn.arguments || '{}'), null, 2); } catch(e) { argsStr = fn.arguments || ''; }
            return `<div class="tool-call-inline">▶ <strong>${escapeHtml(fn.name || '')}</strong>${argsStr ? `<details style="margin-top:2px;"><summary>args</summary><pre class="code-block">${escapeHtml(argsStr)}</pre></details>` : ''}</div>`;
          }).join('');
          replayOutput.insertAdjacentHTML('beforeend', `
            <div class="msg-agent">
              <div class="msg-agent-bubble">
                ${content ? `<div style="white-space:pre-wrap; font-size:12px; color:var(--text); padding:4px 2px;">${escapeHtml(String(content))}</div>` : ''}
                ${toolCallsHtml}
              </div>
            </div>
          `);
        } else if (msg.role === 'tool') {
          replayOutput.insertAdjacentHTML('beforeend', `
            <div class="msg-agent">
              <div class="msg-agent-bubble">
                <div class="tool-result-inline">${escapeHtml(msg.content || '')}</div>
              </div>
            </div>
          `);
        }
      }
    }

    // ── Load button handler ─────────────────────────────────────────────────

    loadBtn.addEventListener('click', () => {
      const file = logFileInput.files[0];
      if (!file) { setStatus('Please select a JSON file first.', 'err'); return; }
      setStatus('Loading…', '');
      const reader = new FileReader();
      reader.onload = (e) => {
        let raw;
        try {
          raw = JSON.parse(e.target.result);
        } catch (err) {
          setStatus('Invalid JSON: ' + err, 'err');
          return;
        }
        // Normalise to full SessionMetrics format regardless of which format was saved.
        const data = normalizeData(raw);
        setStatus('✓ Loaded: ' + file.name, 'ok');

        renderSessionInfo(data);
        renderConversation(data);
        renderMetrics(data);

        replayPanel.style.display = 'block';
        const turnCount = (data.turns || []).length || (data.summary && data.summary.total_turns) || 0;
        replayMeta.textContent = turnCount + ' turns · ' + fmtS(data.total_elapsed_s);
      };
      reader.onerror = () => setStatus('Failed to read file.', 'err');
      reader.readAsText(file);
    });
  </script>
</body>
</html>
    """


# ---------------------------------------------------------------------------
# Code upload / download endpoints
# ---------------------------------------------------------------------------

@app.post("/api/upload")
async def api_upload(file: UploadFile = File(...)) -> JSONResponse:
    """
    Accept a ZIP file containing the user's code directory.

    The archive is extracted to ``BUILD_DIR/upload_code/<upload_id>/`` where
    ``upload_id`` is a freshly generated UUID4.  The response contains:

    - ``upload_id``   – the unique identifier for this upload.
    - ``upload_path`` – the absolute path where the code was extracted.
    - ``generated_code_path`` – the path where the LLM should write output.

    The frontend should pass ``upload_path`` to the LLM as the source
    directory and ``generated_code_path`` as the target directory.
    """
    if not file.filename:
        return JSONResponse({"error": "No file provided."}, status_code=400)

    build_dir = Path(get_project_root())
    upload_id = str(uuid.uuid4())

    upload_dest = build_dir / "upload_code" / upload_id
    generated_dest = build_dir / "generated_code" / upload_id

    upload_dest.mkdir(parents=True, exist_ok=True)
    generated_dest.mkdir(parents=True, exist_ok=True)

    # Read the uploaded bytes
    content = await file.read()

    # Validate it is a ZIP archive
    if not zipfile.is_zipfile(io.BytesIO(content)):
        shutil.rmtree(upload_dest, ignore_errors=True)
        shutil.rmtree(generated_dest, ignore_errors=True)
        return JSONResponse(
            {"error": "Uploaded file is not a valid ZIP archive."},
            status_code=400,
        )

    # Extract, stripping a single top-level directory if the zip was created
    # with one (e.g. ``zip -r mycode.zip mycode/``).
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        members = zf.namelist()
        # Detect common prefix (top-level folder inside the zip)
        top_dirs = {m.split("/")[0] for m in members if m}
        strip_prefix: str | None = None
        if len(top_dirs) == 1:
            prefix = next(iter(top_dirs)) + "/"
            if all(m.startswith(prefix) or m == prefix.rstrip("/") for m in members):
                strip_prefix = prefix

        for member in zf.infolist():
            target_name = member.filename
            if strip_prefix and target_name.startswith(strip_prefix):
                target_name = target_name[len(strip_prefix):]
            if not target_name:
                continue  # skip the top-level directory entry itself
            target_path = upload_dest / target_name
            if member.is_dir():
                target_path.mkdir(parents=True, exist_ok=True)
            else:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, open(target_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)

    return JSONResponse(
        {
            "upload_id": upload_id,
            "upload_path": str(upload_dest),
            "generated_code_path": str(generated_dest),
        }
    )


@app.get("/api/download/{upload_id}")
async def api_download(upload_id: str) -> Response:
    """
    Zip the generated code for ``upload_id`` and return it as a download.

    The generated code is expected at ``BUILD_DIR/generated_code/<upload_id>/``.
    Returns 404 if the directory does not exist or is empty.
    """
    build_dir = Path(get_project_root())
    generated_dir = build_dir / "generated_code" / upload_id

    if not generated_dir.exists() or not any(generated_dir.iterdir()):
        return JSONResponse(
            {"error": "Generated code not found. The agent may not have produced output yet."},
            status_code=404,
        )

    # Build the zip in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(generated_dir.rglob("*")):
            if path.is_file():
                arcname = path.relative_to(generated_dir)
                zf.write(path, arcname)
    buf.seek(0)

    filename = f"generated_code_{upload_id[:8]}.zip"
    return Response(
        content=buf.read(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@app.post("/api/download-written-files")
async def api_download_written_files(request: Request) -> Response:
    """
    Zip a list of files written by the LLM during a session and return as download.

    Accepts JSON body: ``{"file_paths": ["path/to/file1", "path/to/file2", ...]}``

    Each path must resolve to a file inside BUILD_DIR (the project root).
    Returns a ZIP archive containing all found files, preserving their relative
    paths from BUILD_DIR.  Returns 404 if no valid files are found.
    """
    payload: Dict[str, Any] = await request.json()
    file_paths: List[str] = payload.get("file_paths") or []

    if not file_paths:
        return JSONResponse({"error": "No file paths provided."}, status_code=400)

    build_dir = Path(get_project_root()).resolve()

    # Collect valid, existing files that are inside BUILD_DIR
    valid_files: List[Path] = []
    for fp in file_paths:
        p = Path(fp)
        if not p.is_absolute():
            p = build_dir / p
        p = p.resolve()
        # Security: only allow files inside BUILD_DIR
        try:
            p.relative_to(build_dir)
        except ValueError:
            continue  # skip paths outside BUILD_DIR
        if p.is_file():
            valid_files.append(p)

    if not valid_files:
        return JSONResponse(
            {"error": "No generated files found. The agent may not have written any files yet."},
            status_code=404,
        )

    # Build the zip in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(valid_files):
            try:
                arcname = path.relative_to(build_dir)
            except ValueError:
                arcname = path.name
            zf.write(path, arcname)
    buf.seek(0)

    return Response(
        content=buf.read(),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="generated_code.zip"',
        },
    )


# ---------------------------------------------------------------------------
# Legacy batch endpoint (kept for backward compatibility)
# ---------------------------------------------------------------------------

@app.post("/api/chat", response_class=JSONResponse)
async def api_chat(request: Request) -> JSONResponse:
    """Single-step interaction with the deployment agent (OpenAI Agents SDK)."""
    payload: Dict[str, Any] = await request.json()
    message: str = (payload.get("message") or "").strip()
    state: Dict[str, Any] = payload.get("state") or {}
    if "messages" not in state or not isinstance(state["messages"], list):
        state["messages"] = []

    if not message:
        return JSONResponse(
            {
                "status": "error",
                "assistant_question": "Empty message; please provide a description of your code and resilience goals.",
                "state": state,
            },
            status_code=400,
        )

    state["messages"].append({"role": "user", "content": message})

    result = await GRAPH.ainvoke(state)
    combined_state: Dict[str, Any] = dict(state)
    combined_state.update(result)

    status = result.get("status", "error")
    assistant_question = result.get("assistant_question")
    plan = result.get("plan")
    summary = result.get("summary")
    raw_llm = result.get("raw_llm_response")
    llm_trace = result.get("llm_trace")

    return JSONResponse(
        {
            "status": status,
            "assistant_question": assistant_question,
            "plan": plan,
            "summary": summary,
            "raw_llm_response": raw_llm,
            "llm_trace": llm_trace,
            "state": combined_state,
        }
    )
