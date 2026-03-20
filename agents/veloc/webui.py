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
import json
from typing import Any, AsyncIterator, Dict, List

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from agents.veloc.agent import stream_veloc_agent
from agents.veloc.agent_graph import build_agent_graph

app = FastAPI(title="Guard Agent Deployment Web UI")

GRAPH = build_agent_graph()

# Interval (seconds) between SSE keep-alive comments sent while waiting for
# the LLM to respond.  Browsers and proxies typically time out idle SSE
# connections after 30–60 s; 15 s is a safe default.
_SSE_HEARTBEAT_INTERVAL = 15


# ---------------------------------------------------------------------------
# SSE helper
# ---------------------------------------------------------------------------

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
  </style>
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
          <div class="badge">
            <span class="badge-dot"></span>
            <span>OpenAI Agents SDK · VeloC</span>
          </div>
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
            <strong style="color:var(--success);">✓ Task completed successfully</strong><br>
            <div style="margin-top:6px;">${escapeHtml(result.summary || 'No summary provided.')}</div>
          </div>
        `);
      } else if (status === 'ask') {
        appendAgentBubble(`
          <div class="summary-box ask">
            <strong style="color:var(--warn);">⚠ Agent needs more information</strong><br>
            <div style="margin-top:6px;">${escapeHtml(result.assistant_question || 'Please provide more details.')}</div>
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
            <strong style="color:var(--danger);">✗ Error from agent</strong><br>
            <div style="margin-top:6px;">${escapeHtml(result.assistant_question || result.error_message || 'Unknown error.')}</div>
          </div>
        `);
      }
    }

    // ── Input enable/disable ───────────────────────────────────────────────

    function disableInput() {
      promptEl.disabled = true;
      sendBtn.disabled  = true;
      if (stopBtn) stopBtn.style.display = 'inline-block';
    }

    function enableInput() {
      promptEl.disabled = false;
      sendBtn.disabled  = false;
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

      appendUserMessage(message);
      promptEl.value = '';
      state.messages.push({ role: 'user', content: message });

      busy = true;
      agentBubble = null;   // reset for new agent turn
      Object.keys(stepCards).forEach(k => delete stepCards[k]);

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
    });
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
