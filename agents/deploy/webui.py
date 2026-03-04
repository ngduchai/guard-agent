"""
Simple web UI for the deployment agent (LangGraph + MCP + VeloC).

Run from the build directory with:
    ./build/run_deploy_webui.sh
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from agents.deploy.agent_graph import build_agent_graph
from agents.deploy.mcp_client import call_tool, list_tools

app = FastAPI(title="Guard Agent Deployment Web UI")

# The LangGraph deployment agent now executes MCP-backed steps (including file edits)
# inside the workflow steps themselves. The Web UI no longer auto-runs MCP tools
# based on the final plan; it only visualizes what was already executed.
AUTO_EXECUTE_TOOLS = frozenset()

GRAPH = build_agent_graph()


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    """Serve a chat-style single-page web UI."""
    return """
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
    .title {
      font-size: 18px;
      font-weight: 600;
      letter-spacing: 0.02em;
    }
    .subtitle {
      font-size: 13px;
      color: var(--muted);
    }
    .debug-toggle {
      font-size: 11px;
      color: var(--muted);
      display: inline-flex;
      align-items: center;
      gap: 4px;
      cursor: pointer;
    }
    .debug-toggle input {
      accent-color: var(--accent);
    }
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
      width: 8px;
      height: 8px;
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
    .panel-header span {
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .panel-header small {
      font-weight: 400;
      color: var(--muted);
      font-size: 11px;
    }
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
    .button:disabled {
      opacity: 0.55;
      cursor: default;
      box-shadow: none;
    }
    .button-secondary {
      background: transparent;
      border: 1px solid rgba(148,163,184,0.65);
      color: var(--muted);
      box-shadow: none;
      padding-inline: 10px;
    }
    .status {
      font-size: 11px;
      color: var(--muted);
    }
    .status-dot {
      width: 7px;
      height: 7px;
      border-radius: 999px;
      background: var(--accent);
      display: inline-block;
      margin-right: 5px;
    }
    .status-dot.idle { background: #4b5563; }
    .status-dot.error { background: var(--danger); }

    .summary {
      font-size: 13px;
      color: var(--text);
      padding: 6px 8px;
      border-radius: 10px;
      border: 1px solid rgba(51,65,85,0.9);
      background: radial-gradient(circle at top left, rgba(56,189,248,0.12), transparent 55%), #020617;
    }
    .steps {
      display: flex;
      flex-direction: column;
      gap: 6px;
      max-height: 260px;
      overflow: auto;
    }
    .step {
      border-radius: 9px;
      border: 1px solid rgba(30,64,175,0.9);
      background: radial-gradient(circle at top left, rgba(59,130,246,0.13), transparent 60%), rgba(15,23,42,0.96);
      padding: 7px 8px;
      font-size: 12px;
    }
    .step-header {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 6px;
      margin-bottom: 3px;
    }
    .step-title {
      font-weight: 500;
      color: #e5e7eb;
    }
    .step-id {
      font-size: 11px;
      color: var(--muted);
    }
    .step-body {
      font-size: 12px;
      color: var(--muted);
    }
    .step-tools {
      margin-top: 3px;
      font-size: 11px;
      color: #a5b4fc;
    }
    .step-tools code {
      font-family: var(--mono);
      background: rgba(15,23,42,0.9);
      padding: 1px 4px;
      border-radius: 6px;
    }

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
    details {
      margin-top: 6px;
      border-radius: 8px;
      background: rgba(15,23,42,0.9);
      border: 1px dashed rgba(55,65,81,0.9);
      padding: 4px 6px;
    }
    summary {
      cursor: pointer;
      font-size: 11px;
      color: var(--muted);
      outline: none;
    }
    .tiny {
      font-size: 11px;
      color: var(--muted);
    }

    .chat-panel {
      margin-top: 6px;
      margin-bottom: 10px;
      flex: 1;
      min-height: 0;
    }
    .chat-output {
      flex: 1;
      min-height: 0;
      overflow-y: auto;
      padding: 4px 2px 2px 2px;
    }
    .input-panel {
      margin-top: 6px;
      flex-shrink: 0;
    }
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
            <span>LangGraph · MCP · VeloC</span>
          </div>
          <label class="debug-toggle">
            <input type="checkbox" id="debugToggle">
            <span>Show raw LLM output</span>
          </label>
        </div>
      </div>
      <div class="panel chat-panel">
        <div class="panel-header">
          <span>Conversation</span>
          <small id="outputMode">Waiting for first response…</small>
        </div>
        <div id="output" class="chat-output">
          <div class="tiny">Responses from the agent will appear here.</div>
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
      Tip: the agent may ask a single follow-up question if your initial prompt is missing key details
      (e.g. code location, environment, or checkpointing requirements). Answer that question in one message.
    </div>
  </div>

  <script>
    const sendBtn = document.getElementById('sendBtn');
    const resetBtn = document.getElementById('resetBtn');
    const stopBtn = document.getElementById('stopBtn');
    const promptEl = document.getElementById('prompt');
    const statusEl = document.getElementById('status');
    const outputEl = document.getElementById('output');
    const outputModeEl = document.getElementById('outputMode');
    const debugToggle = document.getElementById('debugToggle');

    let state = { messages: [] };
    let busy = false;
    let currentAbortController = null;
    let debugLLM = false;

    if (debugToggle) {
      const params = new URLSearchParams(window.location.search || '');
      if (params.get('debug_llm') === '1' || params.get('debug') === '1') {
        debugLLM = true;
        debugToggle.checked = true;
      }
      debugToggle.addEventListener('change', () => {
        debugLLM = debugToggle.checked;
      });
    }

    function setStatus(text, mode) {
      statusEl.innerHTML = '<span class="status-dot ' + (mode || 'idle') + '"></span>' + text;
    }

    function appendUserMessage(text) {
      const html = `
        <div style="margin-top:6px; display:flex; justify-content:flex-end;">
          <div style="max-width:82%; border-radius:14px; padding:7px 10px; background:linear-gradient(to right,#0ea5e9,#6366f1); color:white; font-size:12px; white-space:pre-wrap;">
            ${escapeHtml(text)}
          </div>
        </div>
      `;
      outputEl.insertAdjacentHTML('beforeend', html);
      outputEl.scrollTop = outputEl.scrollHeight;
    }

    function appendAgentBlock(innerHtml) {
      const html = `
        <div style="margin-top:6px; display:flex; justify-content:flex-start;">
          <div style="max-width:92%; border-radius:14px; padding:7px 9px; background:rgba(15,23,42,0.96); border:1px solid rgba(30,64,175,0.85); font-size:12px;">
            ${innerHtml}
          </div>
        </div>
      `;
      outputEl.insertAdjacentHTML('beforeend', html);
      outputEl.scrollTop = outputEl.scrollHeight;
    }

    function renderAsk(question, trace) {
      outputModeEl.textContent = 'Agent needs more information';
      let rawSection = '';
      if (debugLLM && Array.isArray(trace) && trace.length) {
        let body = '';
        trace.forEach((entry, idx) => {
          if (!entry || typeof entry !== 'object') return;
          const step = entry.step || '?';
          const prompt = entry.prompt || '';
          const resp = entry.response || '';
          body += `LLM call ${idx + 1} (step: ${escapeHtml(step)}):\n\n` +
                  `PROMPT:\n${escapeHtml(prompt)}\n\n` +
                  `RESPONSE:\n${escapeHtml(resp)}\n\n` +
                  `-----------------------------\n\n`;
        });
        rawSection = body
          ? `
        <details style="margin-top:6px;">
          <summary>Show full LLM interaction trace</summary>
          <pre class="code-block">${body}</pre>
        </details>
        `
          : '';
      }
      appendAgentBlock(`
        <div class="summary">
          <strong>Follow-up question from the agent:</strong><br>
          ${escapeHtml(question)}
        </div>
        <div class="tiny" style="margin-top:6px;">
          Answer this question in your next message. Try to include all missing details in a single reply.
        </div>
        ${rawSection}
      `);
    }

    function renderPlan(plan, trace, autoResults) {
      const summary = plan.summary || '';
      const steps = Array.isArray(plan.steps) ? plan.steps : [];
      const transformed = plan.transformed_code || '';
      const executedIds = new Set((state.executed_step_ids || []));

      outputModeEl.textContent = 'Deployment plan';

      let autoSection = '';
      if (Array.isArray(autoResults) && autoResults.length) {
        autoSection = `
          <div class="summary" style="margin-bottom:8px; border-color:rgba(34,197,94,0.6); background:rgba(34,197,94,0.08);">
            <strong>MCP-backed steps executed automatically</strong><br>
            <span class="tiny">Includes file edits; no extra confirmation needed.</span>
            <div class="steps" style="margin-top:6px;">${autoResults.map(r =>
              `<div class="step"><div class="step-header"><div class="step-title">${escapeHtml(r.tool_used || '')}</div></div><div class="step-body">${escapeHtml((r.message || '').toString().slice(0, 200))}${(r.message || '').length > 200 ? '…' : ''}</div></div>`
            ).join('')}</div>
          </div>
        `;
      }

      let stepsHtml = '';
      steps.sort((a, b) => (a.order || 0) - (b.order || 0)).forEach(step => {
        const alreadyRun = executedIds.has(step.id);
        if (alreadyRun) return;
        const id = step.id || '?';
        const name = step.name || '';
        const desc = step.description || '';
        const tool = step.tool_used || null;
        const args = step.tool_args || {};
        const argsJson = JSON.stringify(args, null, 2);
        stepsHtml += `
          <div class="step">
            <div class="step-header">
              <div class="step-title">${escapeHtml(name || 'Untitled step')}</div>
              <div class="step-id">#${escapeHtml(id.toString())}</div>
            </div>
            <div class="step-body">${escapeHtml(desc)}</div>
            ${tool ? `
              <div class="step-tools">
                MCP tool: <code>${escapeHtml(tool)}</code>
                ${args && Object.keys(args).length ? `<br><span>Args:</span>
                  <pre class="code-block" style="margin-top:2px; font-size:10px;">${escapeHtml(argsJson)}</pre>` : ''}
              </div>
            ` : ''}
          </div>
        `;
      });

      if (!stepsHtml) {
        stepsHtml = '<div class="tiny">All MCP-backed steps in this plan have already been executed.</div>';
      }

      let codeHtml = '';
      let rawSection = '';
      if (debugLLM && Array.isArray(trace) && trace.length) {
        let body = '';
        trace.forEach((entry, idx) => {
          if (!entry || typeof entry !== 'object') return;
          const step = entry.step || '?';
          const prompt = entry.prompt || '';
          const resp = entry.response || '';
          body += `LLM call ${idx + 1} (step: ${escapeHtml(step)}):\n\n` +
                  `PROMPT:\n${escapeHtml(prompt)}\n\n` +
                  `RESPONSE:\n${escapeHtml(resp)}\n\n` +
                  `-----------------------------\n\n`;
        });
        rawSection = body
          ? `
        <details style="margin-top:6px;">
          <summary>Show full LLM interaction trace</summary>
          <pre class="code-block">${body}</pre>
        </details>
        `
          : '';
      }
      if (transformed) {
        codeHtml = `
          <details>
            <summary>Show example transformed code snippet</summary>
            <pre class="code-block">${escapeHtml(transformed)}</pre>
          </details>
        `;
      }

      const confirmLabel = 'All MCP-backed steps have been executed automatically. Describe any follow-up changes or adjustments you want.';
      appendAgentBlock(`
        <div class="summary">
          <strong>Summary</strong><br>
          ${escapeHtml(summary || 'No summary provided.')}
        </div>
        ${autoSection}
        <div style="margin-top:8px;">
          <strong style="font-size:12px;">Planned MCP-backed steps</strong>
          <div class="steps">${stepsHtml}</div>
        </div>
        ${codeHtml}
        <div class="tiny" style="margin-top:6px;">
          ${confirmLabel}
        </div>
        ${rawSection}
      `);
    }

    function renderError(message, raw) {
      outputModeEl.textContent = 'Error';
      const rawSection = raw ? `
        <details style="margin-top:6px;">
          <summary>Show raw LLM response</summary>
          <pre class="code-block">${escapeHtml(raw)}</pre>
        </details>
      ` : '';
      appendAgentBlock(`
        <div class="summary" style="border-color:#7f1d1d; background:rgba(127,29,29,0.1);">
          <strong style="color:#fecaca;">Error from agent</strong><br>
          ${escapeHtml(message)}
        </div>
        ${rawSection}
      `);
    }

    function escapeHtml(str) {
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }

    async function send() {
      if (busy) return;
      const message = promptEl.value.trim();
      if (!message) {
        promptEl.focus();
        return;
      }

      if (message.toLowerCase() === 'quit' || message.toLowerCase() === 'exit') {
        setStatus('Session ended by user.', 'idle');
        outputModeEl.textContent = 'Session ended';
        return;
      }

      appendUserMessage(message);
      promptEl.value = '';

      busy = true;
      sendBtn.disabled = true;
      if (stopBtn) stopBtn.style.display = 'inline-block';
      setStatus('Thinking with deployment agent…', 'busy');
      // Show an inline "thinking" indicator in the conversation.
      const existingThinking = document.getElementById('agent-thinking');
      if (existingThinking) existingThinking.remove();
      appendAgentBlock(`
        <div id="agent-thinking" class="tiny">
          Agent is thinking about your request…
        </div>
      `);

      try {
        const controller = new AbortController();
        currentAbortController = controller;
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message, state }),
          signal: controller.signal,
        });
        if (!res.ok) {
          throw new Error('HTTP ' + res.status);
        }
        const data = await res.json();
        state = data.state || state;

        const status = data.status || 'error';
        // Remove inline thinking indicator now that we have a response.
        const thinking = document.getElementById('agent-thinking');
        if (thinking) thinking.remove();

        if (status === 'ask') {
          setStatus('Agent requested more information.', 'idle');
          renderAsk(
            data.assistant_question || 'Please provide more details.',
            data.llm_trace || null
          );
        } else if (status === 'plan') {
          setStatus('Deployment plan generated.', 'idle');
          renderPlan(
            data.plan || {},
            data.llm_trace || null,
            (data.state || {}).auto_execute_results || null
          );
        } else if (status === 'applied') {
          setStatus('Applied MCP-backed steps.', 'idle');
          const results = data.apply_results || [];
          let html = '<div class="summary"><strong>Execution results</strong></div><div class="steps">';
          if (!results.length) {
            html += '<div class="tiny" style="margin-top:6px;">No MCP-backed steps were executed.</div>';
          } else {
            for (const r of results) {
              html += `
                <div class="step">
                  <div class="step-header">
                    <div class="step-title">Step ${escapeHtml((r.step_id || '?').toString())}</div>
                    <div class="step-id"><code>${escapeHtml(r.tool_used || 'n/a')}</code></div>
                  </div>
                  <div class="step-body">${escapeHtml(r.message || '')}</div>
                </div>
              `;
            }
          }
          html += '</div>';
          appendAgentBlock(html);
        } else {
          setStatus('Agent returned an error.', 'error');
          renderError(
            data.assistant_question || 'The agent returned an unexpected structure.',
            data.raw_llm_response || null
          );
        }
      } catch (err) {
        console.error(err);
        const isAbort = err && err.name === 'AbortError';
        if (isAbort) {
          setStatus('Request cancelled by user.', 'idle');
          appendAgentBlock(`
            <div class="tiny">
              <strong>Request cancelled.</strong> Showing conversation up to the last completed step.
              You can adjust your prompt and try again.
            </div>
          `);
        } else {
          setStatus('Network or server error.', 'error');
          renderError('Network or server error while talking to the agent.', '');
        }
      } finally {
        busy = false;
        sendBtn.disabled = false;
        if (stopBtn) stopBtn.style.display = 'none';
        currentAbortController = null;
      }
    }

    sendBtn.addEventListener('click', send);
    if (stopBtn) {
      stopBtn.addEventListener('click', () => {
        if (currentAbortController) {
          currentAbortController.abort();
        }
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
      outputEl.innerHTML = '<div class="tiny">Responses from the agent will appear here.</div>';
      outputModeEl.textContent = 'Waiting for first response…';
      setStatus('Idle', 'idle');
      promptEl.focus();
    });
  </script>
</body>
</html>
    """


@app.post("/api/chat", response_class=JSONResponse)
async def api_chat(request: Request) -> JSONResponse:
    """Single-step interaction with the LangGraph deployment agent."""
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

    # If the user is explicitly approving a plan, execute only the steps that modify files (edit steps).
    # Non-edit steps (copy, list, read, etc.) are already run when the plan is first returned.
    lowered = message.lower()
    if lowered in {"apply", "yes", "y", "approve", "ok", "okay"} and "plan" in state:
        plan = state.get("plan") or {}
        steps = plan.get("steps") or []
        executed_ids = set(state.get("executed_step_ids") or [])
        available = {t.get("name"): t for t in list_tools()}
        results: List[Dict[str, Any]] = []

        for step in sorted(steps, key=lambda s: s.get("order", 0)):
            step_id = step.get("id")
            if step_id in executed_ids:
                continue  # already run as auto-step
            tool_name = step.get("tool_used")
            if not tool_name:
                continue
            args = step.get("tool_args") or {}
            if tool_name not in available:
                results.append(
                    {
                        "step_id": step_id,
                        "tool_used": tool_name,
                        "message": f"Tool '{tool_name}' not exposed by MCP server; skipping.",
                    }
                )
                continue
            try:
                result_obj = call_tool(tool_name, args)
            except Exception as exc:  # noqa: BLE001
                results.append(
                    {
                        "step_id": step_id,
                        "tool_used": tool_name,
                        "message": f"Error calling tool: {exc}",
                    }
                )
                continue

            results.append(
                {
                    "step_id": step_id,
                    "tool_used": tool_name,
                    "message": str(result_obj),
                }
            )

        state["plan_applied"] = True
        return JSONResponse(
            {
                "status": "applied",
                "apply_results": results,
                "state": state,
            }
        )

    state["messages"].append({"role": "user", "content": message})

    result = await GRAPH.ainvoke(state)
    combined_state: Dict[str, Any] = dict(state)
    combined_state.update(result)

    status = result.get("status", "error")
    assistant_question = result.get("assistant_question")
    plan = result.get("plan")
    raw_llm = result.get("raw_llm_response")
    llm_trace = result.get("llm_trace")

    # When we have a plan, run non-edit steps (copy, list, read, etc.) immediately without confirmation.
    # If any fail, return error to the user. Store executed step ids so "apply" only runs edit steps.
    if status == "plan" and plan:
        steps = plan.get("steps") or []
        available = {t.get("name"): t for t in list_tools()}
        executed_ids: List[str] = []
        auto_results: List[Dict[str, Any]] = []
        for step in sorted(steps, key=lambda s: s.get("order", 0)):
            tool_name = step.get("tool_used")
            if not tool_name or tool_name not in AUTO_EXECUTE_TOOLS:
                continue
            if tool_name not in available:
                return JSONResponse(
                    {
                        "status": "error",
                        "assistant_question": f"Auto step failed: tool '{tool_name}' not exposed by MCP server.",
                        "state": combined_state,
                    },
                    status_code=200,
                )
            args = step.get("tool_args") or {}
            try:
                result_obj = call_tool(tool_name, args)
            except Exception as exc:  # noqa: BLE001
                return JSONResponse(
                    {
                        "status": "error",
                        "assistant_question": f"Copy/setup step failed: {exc}. Fix the issue and try again.",
                        "state": combined_state,
                    },
                    status_code=200,
                )
            res_text = str(result_obj)
            if isinstance(result_obj, dict) and result_obj.get("isError"):
                return JSONResponse(
                    {
                        "status": "error",
                        "assistant_question": f"Copy/setup step failed: {res_text}. Fix the issue and try again.",
                        "state": combined_state,
                    },
                    status_code=200,
                )
            # MCP may return isError: false but content like "No such directory"
            if isinstance(result_obj, dict):
                for part in result_obj.get("content") or []:
                    if isinstance(part, dict) and part.get("type") == "text":
                        t = (part.get("text") or "").lower()
                        if "no such directory" in t or "not found" in t or "refusing to overwrite" in t:
                            return JSONResponse(
                                {
                                    "status": "error",
                                    "assistant_question": f"Copy/setup step failed: {part.get('text', t)}. Fix the issue and try again.",
                                    "state": combined_state,
                                },
                                status_code=200,
                            )
                        break
            executed_ids.append(step.get("id") or "")
            auto_results.append(
                {"step_id": step.get("id"), "tool_used": tool_name, "message": res_text}
            )
        combined_state["executed_step_ids"] = executed_ids
        combined_state["auto_execute_results"] = auto_results

    return JSONResponse(
        {
            "status": status,
            "assistant_question": assistant_question,
            "plan": plan,
            "raw_llm_response": raw_llm,
            "llm_trace": llm_trace,
            "state": combined_state,
        }
    )

