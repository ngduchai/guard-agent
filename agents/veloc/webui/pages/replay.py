"""
Session replay page HTML for the Guard Agent Web UI.

Returns the full HTML for the ``/replay`` route, which lets users upload
a session JSON log and reconstruct the full conversation and metrics.
"""

from __future__ import annotations


def replay_html() -> str:
    """Return the HTML for the session replay page."""
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
      width: 96%; max-width: 96%; border-radius: 14px; padding: 7px 9px;
      background: rgba(15,23,42,0.96); border: 1px solid rgba(30,64,175,0.85);
      font-size: 12px; box-sizing: border-box;
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
    .thinking-block {
      margin-top: 6px; border-radius: 8px;
      border: 1px solid rgba(251,191,36,0.4); background: rgba(251,191,36,0.05);
      padding: 0; font-size: 11px;
    }
    .thinking-block summary {
      cursor: pointer; padding: 4px 8px; color: var(--warn);
      font-size: 11px; outline: none; list-style: none;
      display: flex; align-items: center; gap: 5px;
    }
    .thinking-block summary::-webkit-details-marker { display: none; }
    .thinking-block-body {
      padding: 4px 8px 6px; font-size: 11px; opacity: 0.85;
      border-top: 1px solid rgba(251,191,36,0.2);
    }
    .thinking-block-body.md-content { color: var(--warn); }
    .thinking-block-body.md-content p,
    .thinking-block-body.md-content li { color: var(--warn); }
    .thinking-block-body.md-content strong { color: #fde68a; }
    .thinking-block-body.md-content em { color: rgba(251,191,36,0.7); }
    .thinking-block-body.md-content h1,
    .thinking-block-body.md-content h2,
    .thinking-block-body.md-content h3,
    .thinking-block-body.md-content h4 { color: #fde68a; }
    .thinking-block-body.md-content code { color: #fde68a; background: rgba(251,191,36,0.1); }
    .thinking-block-body.md-content blockquote { border-left-color: rgba(251,191,36,0.5); color: rgba(251,191,36,0.7); }
    .summary-box {
      font-size: 13px; color: var(--text); padding: 6px 8px; border-radius: 10px;
      border: 1px solid rgba(51,65,85,0.9);
      background: radial-gradient(circle at top left, rgba(56,189,248,0.12), transparent 55%), #020617;
      white-space: pre-wrap;
    }
    .summary-box.success { border-color: #166534; background: rgba(22,101,52,0.1); }
    .summary-box.error   { border-color: #7f1d1d; background: rgba(127,29,29,0.1); }
    .summary-box.ask     { border-color: rgba(251,191,36,0.5); background: rgba(251,191,36,0.05); }
    /* ── RAG / Knowledge Base collapsible blocks (replay page) ── */
    .kb-block {
      margin-top: 6px; border-radius: 8px;
      border: 1px solid rgba(168,85,247,0.4);
      background: rgba(168,85,247,0.05);
      padding: 0; font-size: 11px;
    }
    .kb-block summary {
      cursor: pointer; padding: 4px 8px; color: rgba(192,132,252,0.95);
      font-size: 11px; outline: none; list-style: none;
      display: flex; align-items: center; gap: 5px;
    }
    .kb-block summary::-webkit-details-marker { display: none; }
    .kb-block-body {
      padding: 4px 8px 6px; font-size: 11px; opacity: 0.9;
      border-top: 1px solid rgba(168,85,247,0.2);
    }
    .kb-block-row { display: flex; gap: 6px; font-size: 11px; color: var(--muted); margin-top: 2px; }
    .kb-block-row strong { color: rgba(192,132,252,0.8); }
    .kb-result-item {
      margin-top: 4px; padding: 4px 6px; border-radius: 6px;
      background: rgba(168,85,247,0.06); border: 1px solid rgba(168,85,247,0.2); font-size: 11px;
    }
    .kb-result-title { font-weight: 600; color: rgba(216,180,254,0.9); }
    .kb-result-meta { font-size: 10px; color: var(--muted); margin-top: 1px; }
    .kb-result-snippet { font-size: 11px; color: rgba(216,180,254,0.75); margin-top: 2px; white-space: pre-wrap; }
    .kb-disabled { opacity: 0.5; font-style: italic; }
    /* Legacy insight-box kept for compatibility */
    .insight-box {
      font-size: 12px; color: var(--text); padding: 6px 10px; border-radius: 10px;
      border: 1px solid rgba(168,85,247,0.45);
      background: radial-gradient(circle at top left, rgba(168,85,247,0.08), transparent 60%), rgba(15,23,42,0.97);
      margin-top: 6px;
    }
    .insight-box-header {
      display: flex; align-items: center; gap: 6px;
      font-weight: 600; font-size: 12px; color: rgba(192,132,252,0.95); margin-bottom: 4px;
    }
    .insight-box-label {
      font-size: 10px; font-weight: 700; letter-spacing: 0.05em;
      padding: 1px 5px; border-radius: 4px;
      background: rgba(168,85,247,0.2); color: rgba(216,180,254,0.9);
    }
    .insight-box-row { display: flex; gap: 6px; font-size: 11px; color: var(--muted); margin-top: 2px; }
    .insight-box-row strong { color: rgba(192,132,252,0.8); }
    .insight-result-item {
      margin-top: 4px; padding: 4px 6px; border-radius: 6px;
      background: rgba(168,85,247,0.06); border: 1px solid rgba(168,85,247,0.2); font-size: 11px;
    }
    .insight-result-title { font-weight: 600; color: rgba(216,180,254,0.9); }
    .insight-result-meta { font-size: 10px; color: var(--muted); margin-top: 1px; }
    .insight-result-snippet { font-size: 11px; color: var(--text); margin-top: 2px; white-space: pre-wrap; }
    .insight-disabled { opacity: 0.5; font-style: italic; }
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
      // Ensure summary exists and has all expected fields.
      if (!raw.summary) {
        raw.summary = {};
      }
      const s = raw.summary;
      const turns = Array.isArray(raw.turns) ? raw.turns : [];
      if (s.total_turns == null) s.total_turns = turns.length;
      if (s.final_status == null) s.final_status = (raw.final_result && raw.final_result.status) || 'unknown';
      if (s.final_summary == null) s.final_summary = (raw.final_result && raw.final_result.summary) || null;
      if (s.final_error == null) s.final_error = (raw.final_result && (raw.final_result.error_message || raw.final_result.assistant_question)) || null;
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

      if (turns.length === 0) {
        replayOutput.insertAdjacentHTML('beforeend', `
          <div style="color:var(--muted); font-size:12px; padding:8px;">
            No conversation data available in this log file.
          </div>
        `);
        return;
      }

      renderTurnsWithEvents(turns, data);
    }

    // ── Helper: parse STEP_SUMMARY / STEP_RESULT JSON from a text line ───────
    function parseStepMarker(line, prefix) {
      const idx = line.indexOf(prefix);
      if (idx === -1) return null;
      try { return JSON.parse(line.slice(idx + prefix.length).trim()); } catch { return null; }
    }

    // ── Helper: build a thinking block <details> element ─────────────────────
    function makeThinkingBlock(text) {
      const snippet = text.length > 80
        ? text.slice(0, 80).replace(/\n/g, ' ') + '…'
        : text.replace(/\n/g, ' ');
      const details = document.createElement('details');
      details.className = 'thinking-block';
      details.innerHTML = `
        <summary>💭 <span style="font-style:italic;">thinking</span> <span style="opacity:0.6;font-size:10px;">${escapeHtml(snippet)}</span></summary>
        <div class="thinking-block-body md-content">${renderMarkdown(text)}</div>
      `;
      return details;
    }

    // ── Helper: detect whether a turn uses the new interleaved event format ───
    // New logs have explicit "thinking" / "step_summary" / "step_result" events.
    // Old logs only have "model_response" / "tool_call" / "tool_result".
    function hasInterleavedEvents(events) {
      return events.some(e => e.kind === 'thinking' || e.kind === 'step_summary' || e.kind === 'step_result');
    }

    // Render turns that have conversation_events.
    function renderTurnsWithEvents(turns, data) {
      // ── Rendering pass ────────────────────────────────────────────────────
      let firstUserRendered = false;

      // Build a map of step timing from turn.steps (all turns) for elapsed time display.
      const stepTimings = {}; // stepNum → elapsed_s
      for (const turn of turns) {
        for (const step of (Array.isArray(turn.steps) ? turn.steps : [])) {
          if (step.step != null && step.elapsed_s != null) {
            stepTimings[step.step] = step.elapsed_s;
          }
        }
      }

      // Build a queue of RAG interactions per turn for interleaving.
      const ragByTurn = {}; // turnNum → [RAGInteractionMetrics, ...]
      for (const ri of (Array.isArray(data.rag_interactions) ? data.rag_interactions : [])) {
        if (!ragByTurn[ri.turn]) ragByTurn[ri.turn] = [];
        ragByTurn[ri.turn].push(ri);
      }
      const toolToRagKind = {
        'query_knowledge_base': 'query',
        'store_insight': 'store',
        'update_insight': 'update',
      };

      // Cross-turn state for the interleaved rendering path.
      // These must persist across turns because step_result events for step N
      // appear in turn N+1's conversation_events (before the next step_summary).
      let activeStepCallsEl = null;
      let activeStepResultEl = null;
      // Registry: stepNum → { callsEl, resultEl } — allows step_result to find
      // its card by step number even when it arrives in a later turn.
      const stepCardsMap = {};

      // Helper: get the calls container for the most recently created step card.
      // Used as a fallback when tool_call/tool_result arrive before any step_summary
      // in the current turn (they belong to the previous turn's step card).
      function getMostRecentStepCallsEl() {
        const nums = Object.keys(stepCardsMap).map(Number).sort((a, b) => b - a);
        return nums.length ? stepCardsMap[nums[0]].callsEl : null;
      }

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

        // Determine which rendering path to use.
        const useInterleaved = hasInterleavedEvents(events);

        if (useInterleaved) {
          // ── New format: events are already in the correct interleaved order ──
          // Iterate through events in order, building the bubble and step cards
          // dynamically so thinking blocks appear in the exact position they were
          // emitted (before, inside, or between step cards).

          const hasContent = events.some(e =>
            e.kind === 'thinking' || e.kind === 'step_summary' || e.kind === 'step_result' ||
            e.kind === 'tool_call' || e.kind === 'tool_result'
          );
          if (!hasContent) continue;

          const bubble = document.createElement('div');
          bubble.className = 'msg-agent';
          const inner = document.createElement('div');
          inner.className = 'msg-agent-bubble';
          bubble.appendChild(inner);

          // RAG queue for this turn (consumed as tool_result events are processed).
          const ragQueue = (ragByTurn[turn.turn] || []).slice();
          const ragUsed = new Array(ragQueue.length).fill(false);

          for (const ev of events) {
            if (ev.kind === 'thinking') {
              // Place thinking block inside the active step card (if any),
              // otherwise in the agent bubble (pre-step reasoning).
              const thinkingEl = makeThinkingBlock((ev.content || '').trim());
              if (activeStepCallsEl) {
                activeStepCallsEl.appendChild(thinkingEl);
              } else {
                inner.appendChild(thinkingEl);
              }

            } else if (ev.kind === 'step_summary') {
              // Create a new step card.
              const stepNum = ev.step || '?';
              const tools = Array.isArray(ev.step_tools) && ev.step_tools.length
                ? ev.step_tools.map(t => `<span class="tool-badge">⚙ ${escapeHtml(t)}</span>`).join('')
                : '<span style="color:var(--muted);font-size:10px;">none</span>';
              const elapsed = stepTimings[ev.step];
              const card = document.createElement('div');
              card.className = 'step-card';
              card.innerHTML = `
                <div class="step-card-header">
                  <span class="step-num">Step ${escapeHtml(String(stepNum))}</span>
                  <span class="step-name">${escapeHtml(ev.step_name || '')}</span>
                  <span class="step-status-badge">done</span>
                </div>
                ${ev.step_why ? `<div class="step-row"><span class="step-label">Why</span><span class="step-value">${escapeHtml(ev.step_why)}</span></div>` : ''}
                ${ev.step_how ? `<div class="step-row"><span class="step-label">How</span><span class="step-value">${escapeHtml(ev.step_how)}</span></div>` : ''}
                <div class="step-row"><span class="step-label">Tools</span><span class="step-value">${tools}</span></div>
                ${elapsed != null ? `<div class="step-row"><span class="step-label">Time</span><span class="step-value">${fmtS(elapsed)}</span></div>` : ''}
              `;
              // Add a calls container and result container.
              const callsEl = document.createElement('div');
              callsEl.className = 'step-calls-area';
              card.appendChild(callsEl);
              const resultEl = document.createElement('div');
              resultEl.className = 'step-result-area';
              card.appendChild(resultEl);
              inner.appendChild(card);
              activeStepCallsEl = callsEl;
              activeStepResultEl = resultEl;
              // Register in cross-turn map so step_result can find it by step number.
              if (ev.step != null) stepCardsMap[ev.step] = { callsEl, resultEl };

            } else if (ev.kind === 'step_result') {
              // Attach result to the step card identified by step number.
              // The step_result event for step N arrives in turn N+1 (before the
              // next step_summary), so activeStepResultEl may be null here.
              // We look up the card by step number from the cross-turn registry.
              const resultText = (ev.content || '').trim();
              if (resultText) {
                // Prefer lookup by step number (handles cross-turn case).
                const card = (ev.step != null) ? stepCardsMap[ev.step] : null;
                const targetEl = (card && card.resultEl) ? card.resultEl : activeStepResultEl;
                if (targetEl) {
                  targetEl.innerHTML = `<div class="step-result-box">✓ ${escapeHtml(resultText)}</div>`;
                }
              }
              // Close the active step card (next events go to the bubble or next card).
              activeStepCallsEl = null;
              activeStepResultEl = null;

            } else if (ev.kind === 'tool_call') {
              const argsStr = ev.args ? JSON.stringify(ev.args, null, 2) : '';
              const callHtml = `
                <div class="tool-call-inline">
                  ▶ <strong>${escapeHtml(ev.name || '')}</strong>
                  ${argsStr ? `<details style="margin-top:2px;"><summary>args</summary><pre class="code-block">${escapeHtml(argsStr)}</pre></details>` : ''}
                </div>
              `;
              // Use active step card, or fall back to the most recently created
              // step card (for tool_calls that arrive before step_summary in this turn).
              const callsTarget = activeStepCallsEl || getMostRecentStepCallsEl();
              if (callsTarget) {
                callsTarget.insertAdjacentHTML('beforeend', callHtml);
              } else {
                inner.insertAdjacentHTML('beforeend', callHtml);
              }

            } else if (ev.kind === 'tool_result') {
              const resultHtml = `<div class="tool-result-inline">${escapeHtml(ev.content || '')}</div>`;
              const callsTarget = activeStepCallsEl || getMostRecentStepCallsEl();
              if (callsTarget) {
                callsTarget.insertAdjacentHTML('beforeend', resultHtml);
              } else {
                inner.insertAdjacentHTML('beforeend', resultHtml);
              }
              // Interleave RAG insight after matching tool_result.
              const expectedKind = toolToRagKind[ev.name];
              if (expectedKind) {
                const idx = ragQueue.findIndex((r, i) => !ragUsed[i] && r.kind === expectedKind);
                if (idx !== -1) {
                  ragUsed[idx] = true;
                  const ragHtml = replayRagInsightHtml(ragQueue[idx]);
                  const ragTarget = activeStepCallsEl || getMostRecentStepCallsEl();
                  if (ragTarget) {
                    ragTarget.insertAdjacentHTML('beforeend', ragHtml);
                  } else {
                    inner.insertAdjacentHTML('beforeend', ragHtml);
                  }
                }
              }
            }
          }

          if (inner.children.length > 0) {
            replayOutput.appendChild(bubble);
          }

        } else {
          // ── Legacy format: only model_response / tool_call / tool_result ──────
          // Fall back to the old rendering approach: extract thinking from
          // model_response text, then render step cards from turn.steps.

          // ── Pre-pass: collect STEP_RESULT text and tool calls per step ────────
          const stepResults = {};   // stepNum → result string
          const stepToolCalls = {}; // stepNum → [{kind, name, args, content}, ...]

          // Find which step number is being STARTED in this turn (from STEP_SUMMARY).
          let activeSummaryStep = null;
          for (const ev of events) {
            if (ev.kind !== 'model_response') continue;
            for (const line of (ev.content || '').split('\n')) {
              const parsed = parseStepMarker(line, 'STEP_SUMMARY:');
              if (parsed && parsed.step) { activeSummaryStep = parsed.step; break; }
            }
            if (activeSummaryStep) break;
          }

          // Collect STEP_RESULT text from model_response events in this turn.
          for (const ev of events) {
            if (ev.kind !== 'model_response') continue;
            for (const line of (ev.content || '').split('\n')) {
              const parsed = parseStepMarker(line, 'STEP_RESULT:');
              if (parsed && parsed.step && parsed.result) {
                stepResults[parsed.step] = parsed.result;
              }
            }
          }

          // Collect tool calls/results for the active step in this turn.
          if (activeSummaryStep != null) {
            if (!stepToolCalls[activeSummaryStep]) stepToolCalls[activeSummaryStep] = [];
            const ragQueue = (ragByTurn[turn.turn] || []).slice();
            const ragUsed = new Array(ragQueue.length).fill(false);
            for (const ev of events) {
              if (ev.kind === 'tool_call' || ev.kind === 'tool_result') {
                stepToolCalls[activeSummaryStep].push(ev);
                if (ev.kind === 'tool_result') {
                  const expectedKind = toolToRagKind[ev.name];
                  if (expectedKind) {
                    const idx = ragQueue.findIndex((r, i) => !ragUsed[i] && r.kind === expectedKind);
                    if (idx !== -1) {
                      ragUsed[idx] = true;
                      stepToolCalls[activeSummaryStep].push({ kind: 'rag_insight', ri: ragQueue[idx] });
                    }
                  }
                }
              }
            }
          }

          // ── Rendering ─────────────────────────────────────────────────────────
          const modelEvents = events.filter(e =>
            e.kind === 'model_response' || e.kind === 'tool_call' || e.kind === 'tool_result'
          );
          if (modelEvents.length === 0) continue;

          const bubble = document.createElement('div');
          bubble.className = 'msg-agent';
          const inner = document.createElement('div');
          inner.className = 'msg-agent-bubble';
          bubble.appendChild(inner);

          // Thinking block: extract from model_response, strip marker lines.
          // Always render the thinking block first (before step cards), matching
          // the old live-stream order: thinking → step card → tool calls → result.
          const modelResponseEvents = events.filter(e => e.kind === 'model_response');
          for (const ev of modelResponseEvents) {
            const raw = (ev.content || '').trim();
            const thinkingText = raw
              .split('\n')
              .filter(line => !/^\s*STEP_SUMMARY:/.test(line) && !/^\s*STEP_RESULT:/.test(line))
              .join('\n')
              .trim();
            if (thinkingText) {
              inner.appendChild(makeThinkingBlock(thinkingText));
            }
          }

          // Step cards from turn.steps.
          const steps = Array.isArray(turn.steps) ? turn.steps : [];
          for (const step of steps) {
            if (!step.step && !step.name) continue;
            const card = document.createElement('div');
            card.className = 'step-card';

            const toolEventsForStep = stepToolCalls[step.step] || [];
            let toolCallsHtml = '';
            for (const ev of toolEventsForStep) {
              if (ev.kind === 'tool_call') {
                const argsStr = ev.args ? JSON.stringify(ev.args, null, 2) : '';
                toolCallsHtml += `
                  <div class="tool-call-inline">
                    ▶ <strong>${escapeHtml(ev.name || '')}</strong>
                    ${argsStr ? `<details style="margin-top:2px;"><summary>args</summary><pre class="code-block">${escapeHtml(argsStr)}</pre></details>` : ''}
                  </div>
                `;
              } else if (ev.kind === 'tool_result') {
                toolCallsHtml += `<div class="tool-result-inline">${escapeHtml(ev.content || '')}</div>`;
              } else if (ev.kind === 'rag_insight') {
                toolCallsHtml += replayRagInsightHtml(ev.ri);
              }
            }

            const resultText = stepResults[step.step];
            const resultBoxHtml = resultText
              ? `<div class="step-result-box">✓ ${escapeHtml(resultText)}</div>`
              : '';

            card.innerHTML = `
              <div class="step-card-header">
                <span class="step-num">Step ${escapeHtml(String(step.step || '?'))}</span>
                <span class="step-name">${escapeHtml(step.name || '')}</span>
                <span class="step-status-badge">done</span>
              </div>
              ${step.elapsed_s != null ? `<div class="step-row"><span class="step-label">Time</span><span class="step-value">${fmtS(step.elapsed_s)}</span></div>` : ''}
              ${toolCallsHtml}
              ${resultBoxHtml}
            `;
            inner.appendChild(card);
          }

          if (inner.children.length > 0) {
            replayOutput.appendChild(bubble);
          }
        }
      }

      renderFinalStatus(data);
    }

    // Build collapsible HTML for a single RAG interaction entry.
    function replayRagInsightHtml(ri) {
      const kind = ri.kind || '';
      const ragEnabled = ri.rag_enabled !== false;
      if (!ragEnabled) {
        return `<details class="kb-block">
          <summary>🔍 <span style="font-weight:600;">knowledge base</span> <span style="opacity:0.6;font-size:10px;">(RAG disabled)</span></summary>
          <div class="kb-block-body"><span class="kb-disabled">RAG is disabled for this session.</span></div>
        </details>`;
      }
      if (kind === 'query') {
        const query = escapeHtml(ri.query || '');
        const count = ri.results_count != null ? ri.results_count : '?';
        const snippet = (ri.query || '').length > 60 ? escapeHtml((ri.query || '').slice(0, 60)) + '…' : query;
        return `<details class="kb-block">
          <summary>🔍 <span style="font-weight:600;">knowledge base</span> <span style="opacity:0.6;font-size:10px;">${snippet}</span></summary>
          <div class="kb-block-body">
            <div class="kb-block-row"><strong>Query:</strong> ${query}</div>
            <div class="kb-block-row"><strong>Hits:</strong> ${count}</div>
          </div>
        </details>`;
      }
      if (kind === 'store') {
        const title = escapeHtml(ri.title || '');
        const cat = escapeHtml(ri.category || '');
        const conf = ri.confidence != null ? Number(ri.confidence).toFixed(2) : '?';
        const id = ri.insight_id ? escapeHtml(ri.insight_id.slice(0, 16)) + '…' : '';
        const snippet = title.length > 60 ? title.slice(0, 60) + '…' : title;
        return `<details class="kb-block">
          <summary>💾 <span style="font-weight:600;">knowledge base</span> <span style="opacity:0.6;font-size:10px;">${snippet}</span></summary>
          <div class="kb-block-body">
            <div class="kb-block-row"><strong>Title:</strong> ${title}</div>
            <div class="kb-block-row"><strong>Category:</strong> ${cat} &nbsp;·&nbsp; <strong>Confidence:</strong> ${conf}</div>
            ${id ? `<div class="kb-block-row"><strong>ID:</strong> ${id}</div>` : ''}
          </div>
        </details>`;
      }
      if (kind === 'update') {
        const title = escapeHtml(ri.title || '');
        const id = ri.insight_id ? escapeHtml(ri.insight_id.slice(0, 16)) + '…' : '';
        const conf = ri.confidence != null ? Number(ri.confidence).toFixed(2) : null;
        const snippet = title.length > 60 ? title.slice(0, 60) + '…' : (id || '');
        return `<details class="kb-block">
          <summary>✏️ <span style="font-weight:600;">knowledge base</span> <span style="opacity:0.6;font-size:10px;">${snippet}</span></summary>
          <div class="kb-block-body">
            ${title ? `<div class="kb-block-row"><strong>Title:</strong> ${title}</div>` : ''}
            ${id ? `<div class="kb-block-row"><strong>ID:</strong> ${id}</div>` : ''}
            ${conf !== null ? `<div class="kb-block-row"><strong>Confidence:</strong> ${conf}</div>` : ''}
          </div>
        </details>`;
      }
      return '';
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
