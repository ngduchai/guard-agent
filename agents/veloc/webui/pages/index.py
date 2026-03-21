"""
Main chat UI page HTML for the Guard Agent Web UI.

Returns the full single-page application HTML for the ``/`` route.
"""

from __future__ import annotations


def index_html() -> str:
    """Return the HTML for the main chat UI page."""
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

    /* ── Thinking blocks ── */
    .thinking-block {
      margin-top: 6px;
      border-radius: 8px;
      border: 1px solid rgba(251,191,36,0.4);
      background: rgba(251,191,36,0.05);
      padding: 0;
      font-size: 11px;
    }
    .thinking-block summary {
      cursor: pointer;
      padding: 4px 8px;
      color: var(--warn);
      font-size: 11px;
      outline: none;
      list-style: none;
      display: flex;
      align-items: center;
      gap: 5px;
    }
    .thinking-block summary::-webkit-details-marker { display: none; }
    .thinking-block-body {
      padding: 4px 8px 6px;
      font-size: 11px;
      opacity: 0.85;
      border-top: 1px solid rgba(251,191,36,0.2);
    }
    /* Override md-content colours inside thinking blocks to use amber palette */
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

    /* ── RAG / Knowledge Base collapsible blocks ── */
    .kb-block {
      margin-top: 6px;
      border-radius: 8px;
      border: 1px solid rgba(168,85,247,0.4);
      background: rgba(168,85,247,0.05);
      padding: 0;
      font-size: 11px;
    }
    .kb-block summary {
      cursor: pointer;
      padding: 4px 8px;
      color: rgba(192,132,252,0.95);
      font-size: 11px;
      outline: none;
      list-style: none;
      display: flex;
      align-items: center;
      gap: 5px;
    }
    .kb-block summary::-webkit-details-marker { display: none; }
    .kb-block-body {
      padding: 4px 8px 6px;
      font-size: 11px;
      opacity: 0.9;
      border-top: 1px solid rgba(168,85,247,0.2);
    }
    .kb-block-row {
      display: flex; gap: 6px; font-size: 11px; color: var(--muted);
      margin-top: 2px;
    }
    .kb-block-row strong { color: rgba(192,132,252,0.8); }
    .kb-result-item {
      margin-top: 4px; padding: 4px 6px; border-radius: 6px;
      background: rgba(168,85,247,0.06); border: 1px solid rgba(168,85,247,0.2);
      font-size: 11px;
    }
    .kb-result-title { font-weight: 600; color: rgba(216,180,254,0.9); }
    .kb-result-meta { font-size: 10px; color: var(--muted); margin-top: 1px; }
    .kb-result-snippet { font-size: 11px; color: rgba(216,180,254,0.75); margin-top: 2px; white-space: pre-wrap; }
    .kb-disabled { opacity: 0.5; font-style: italic; }
    /* Legacy insight-box kept for any remaining references */
    .insight-box {
      font-size: 12px;
      color: var(--text);
      padding: 6px 10px;
      border-radius: 10px;
      border: 1px solid rgba(168,85,247,0.45);
      background: radial-gradient(circle at top left, rgba(168,85,247,0.08), transparent 60%), rgba(15,23,42,0.97);
      margin-top: 6px;
    }
    .insight-box-header {
      display: flex; align-items: center; gap: 6px;
      font-weight: 600; font-size: 12px; color: rgba(192,132,252,0.95);
      margin-bottom: 4px;
    }
    .insight-box-label {
      font-size: 10px; font-weight: 700; letter-spacing: 0.05em;
      padding: 1px 5px; border-radius: 4px;
      background: rgba(168,85,247,0.2); color: rgba(216,180,254,0.9);
    }
    .insight-box-row {
      display: flex; gap: 6px; font-size: 11px; color: var(--muted);
      margin-top: 2px;
    }
    .insight-box-row strong { color: rgba(192,132,252,0.8); }
    .insight-result-item {
      margin-top: 4px; padding: 4px 6px; border-radius: 6px;
      background: rgba(168,85,247,0.06); border: 1px solid rgba(168,85,247,0.2);
      font-size: 11px;
    }
    .insight-result-title { font-weight: 600; color: rgba(216,180,254,0.9); }
    .insight-result-meta { font-size: 10px; color: var(--muted); margin-top: 1px; }
    .insight-result-snippet { font-size: 11px; color: var(--text); margin-top: 2px; white-space: pre-wrap; }
    .insight-disabled { opacity: 0.5; font-style: italic; }

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
        <div style="display:flex; flex-direction:row; align-items:center; gap:8px;">
          <a href="/knowledge" target="_blank" class="button button-secondary" style="text-decoration:none; font-size:12px; padding:5px 14px;">📚 Knowledge Base</a>
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
    // The step number of the currently active (not yet completed) step.
    // Set when step_summary arrives, cleared when step_result arrives.
    // Used by renderThinking to decide whether to place thinking blocks
    // inside the active step card or in the agent bubble.
    let activeStepNum = null;

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
      activeStepNum = stepNum;  // mark this step as active
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
      // Clear the active step so thinking blocks between steps go to the bubble.
      if (activeStepNum === stepNum) activeStepNum = null;
      scrollBottom();
    }

    // Mark every step that is still showing "running…" as done.
    // Called when the agent finishes (done/error events) so that steps whose
    // STEP_RESULT the LLM skipped or emitted in a later turn don't stay stuck.
    function finishAllRunningSteps() {
      Object.keys(stepCards).forEach(k => {
        const badge = document.getElementById('step-badge-' + k);
        if (badge && badge.classList.contains('running')) {
          badge.textContent = 'done';
          badge.className = 'step-status-badge done';
        }
      });
      activeStepNum = null; // no step is active after the agent finishes
    }

    function renderThinking(ev) {
      // The agent emits thinking chunks interleaved with step_summary / step_result
      // events, reflecting the LLM's actual reasoning flow:
      //   thinking(pre-step) → step_summary → thinking(in-step) → step_result → thinking(between-steps) → …
      //
      // Placement rules:
      // • activeStepNum is set when step_summary arrives and cleared when step_result
      //   arrives.  While it is set, thinking belongs inside the active step card.
      // • When activeStepNum is null (before any step or between steps), thinking
      //   goes into the agent bubble.
      const raw = (ev.text || '').trim();
      // Strip any residual STEP_SUMMARY / STEP_RESULT marker lines (safety net).
      const text = raw
        .split('\n')
        .filter(line => !/^\s*STEP_SUMMARY:/.test(line) && !/^\s*STEP_RESULT:/.test(line))
        .join('\n')
        .trim();
      if (!text) return;

      const details = document.createElement('details');
      details.className = 'thinking-block';
      // Use a plain-text snippet for the summary header (no markdown)
      const snippet = text.length > 80 ? text.slice(0, 80).replace(/\n/g, ' ') + '…' : text.replace(/\n/g, ' ');
      details.innerHTML = `
        <summary>💭 <span style="font-style:italic;">thinking</span> <span style="opacity:0.6;font-size:10px;">${escapeHtml(snippet)}</span></summary>
        <div class="thinking-block-body md-content">${renderMarkdown(text)}</div>
      `;

      // Use activeStepNum to determine placement: inside the active step card
      // (if a step is currently running) or in the agent bubble (pre/between steps).
      const callsEl = activeStepNum !== null
        ? document.getElementById('step-calls-' + activeStepNum)
        : null;

      if (callsEl) {
        // Place thinking block inside the active step card (interleaved reasoning).
        callsEl.appendChild(details);
      } else {
        // No active step — place in the agent bubble (pre-step or between-step reasoning).
        ensureAgentBubble().appendChild(details);
      }
      scrollBottom();
    }

    // ── Tool call / result rendering ──────────────────────────────────────────
    // The agent now emits tool_call events with an optional ``step`` field that
    // identifies which step card the tool call belongs to.  When present, the
    // tool call is placed inside that step card's calls area.  When absent (or
    // the step card doesn't exist yet), we fall back to the most recently opened
    // step card, then to the agent bubble.

    function _toolCallsEl(stepHint) {
      // Prefer the step card identified by stepHint (if provided and exists).
      if (stepHint != null) {
        const el = document.getElementById('step-calls-' + stepHint);
        if (el) return el;
      }
      // Fall back to the most recently opened step card.
      const stepNums = Object.keys(stepCards).map(Number).sort((a,b)=>b-a);
      const targetStep = stepNums.length ? stepNums[0] : null;
      return targetStep !== null ? document.getElementById('step-calls-' + targetStep) : null;
    }

    function renderToolCall(ev) {
      const callsEl = _toolCallsEl(ev.step != null ? ev.step : null);
      const argsStr = ev.args ? JSON.stringify(ev.args, null, 2) : '';
      const callHtml = `
        <div class="tool-call-inline">
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
      // Use the same step-hint logic as renderToolCall so the result lands in
      // the same step card as its corresponding tool call.
      const callsEl = _toolCallsEl(ev.step != null ? ev.step : null);
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

    // ── RAG / Knowledge Base collapsible block renderers ──────────────────

    // Helper: find the step-calls container for the current (most recent) step,
    // falling back to the agent bubble if no step card exists yet.
    // Prefers the activeStepNum (currently running step) when set; otherwise
    // falls back to the most recently opened step card (highest step num).
    function _ragInsertTarget() {
      if (activeStepNum !== null) {
        const el = document.getElementById('step-calls-' + activeStepNum);
        if (el) return el;
      }
      const stepNums = Object.keys(stepCards).map(Number).sort((a,b)=>b-a);
      const targetStep = stepNums.length ? stepNums[0] : null;
      return targetStep !== null
        ? document.getElementById('step-calls-' + targetStep)
        : null;
    }

    function _ragAppend(html) {
      const target = _ragInsertTarget();
      if (target) {
        target.insertAdjacentHTML('beforeend', html);
      } else {
        ensureAgentBubble().insertAdjacentHTML('beforeend', html);
      }
      scrollBottom();
    }

    function renderRAGQuery(ev) {
      const query = ev.query || '';
      const results = Array.isArray(ev.results) ? ev.results : [];
      const count = ev.results_count != null ? ev.results_count : results.length;
      const enabled = ev.rag_enabled !== false;

      const resultsHtml = enabled && results.length > 0
        ? results.slice(0, 3).map(r => `
            <div class="kb-result-item">
              <div class="kb-result-title">${escapeHtml(r.title || '')}</div>
              <div class="kb-result-meta">
                cat: ${escapeHtml(r.category || '')} &nbsp;|&nbsp;
                score: ${(r.score || 0).toFixed(2)} &nbsp;|&nbsp;
                conf: ${(r.confidence || 0).toFixed(2)}
              </div>
              ${r.content ? `<div class="kb-result-snippet">${escapeHtml((r.content || '').slice(0, 200))}${(r.content || '').length > 200 ? '…' : ''}</div>` : ''}
            </div>`).join('')
        : (enabled ? '<div class="kb-result-meta" style="margin-top:4px;">No matching insights found.</div>' : '');

      const snippet = query.length > 60 ? query.slice(0, 60) + '…' : query;
      const html = `
        <details class="kb-block">
          <summary>🔍 <span style="font-weight:600;">knowledge base</span> <span style="opacity:0.6;font-size:10px;">${escapeHtml(snippet)}${!enabled ? ' (RAG disabled)' : ''}</span></summary>
          <div class="kb-block-body">
            <div class="kb-block-row"><strong>Query:</strong> ${escapeHtml(query)}</div>
            <div class="kb-block-row"><strong>Hits:</strong> ${count}</div>
            ${resultsHtml}
          </div>
        </details>`;
      _ragAppend(html);
    }

    function renderRAGStore(ev) {
      const title = ev.title || '';
      const category = ev.category || '';
      const confidence = ev.confidence != null ? ev.confidence : 0.8;
      const insightId = ev.insight_id || '';
      const enabled = ev.rag_enabled !== false;

      const snippet = title.length > 60 ? title.slice(0, 60) + '…' : title;
      const html = `
        <details class="kb-block">
          <summary>💾 <span style="font-weight:600;">knowledge base</span> <span style="opacity:0.6;font-size:10px;">${escapeHtml(snippet)}${!enabled ? ' (RAG disabled)' : ''}</span></summary>
          <div class="kb-block-body">
            <div class="kb-block-row"><strong>Title:</strong> ${escapeHtml(title)}</div>
            <div class="kb-block-row"><strong>Category:</strong> ${escapeHtml(category)} &nbsp;|&nbsp; <strong>Confidence:</strong> ${Number(confidence).toFixed(2)}</div>
            ${insightId ? `<div class="kb-block-row" style="font-size:10px;"><strong>ID:</strong> ${escapeHtml(insightId.slice(0, 16))}…</div>` : ''}
          </div>
        </details>`;
      _ragAppend(html);
    }

    function renderRAGUpdate(ev) {
      const title = ev.title || '';
      const insightId = ev.insight_id || '';
      const confidence = ev.confidence;
      const enabled = ev.rag_enabled !== false;

      const snippet = title.length > 60 ? title.slice(0, 60) + '…' : (insightId ? insightId.slice(0, 16) + '…' : '');
      const html = `
        <details class="kb-block">
          <summary>✏️ <span style="font-weight:600;">knowledge base</span> <span style="opacity:0.6;font-size:10px;">${escapeHtml(snippet)}${!enabled ? ' (RAG disabled)' : ''}</span></summary>
          <div class="kb-block-body">
            ${title ? `<div class="kb-block-row"><strong>Title:</strong> ${escapeHtml(title)}</div>` : ''}
            ${insightId ? `<div class="kb-block-row" style="font-size:10px;"><strong>ID:</strong> ${escapeHtml(insightId.slice(0, 16))}…</div>` : ''}
            ${confidence != null ? `<div class="kb-block-row"><strong>New confidence:</strong> ${Number(confidence).toFixed(2)}</div>` : ''}
          </div>
        </details>`;
      _ragAppend(html);
    }

    function renderFinalDone(result) {
      const status = result.status || 'error';
      outputMode.textContent = status === 'success' ? 'Success' :
                               status === 'ask'     ? 'Agent needs more information' :
                               status === 'plan'    ? 'Deployment Plan' :
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
      } else if (status === 'plan') {
        const plan = result.plan || {};
        const planSummary = plan.summary || result.summary || '';
        const steps = Array.isArray(plan.steps) ? plan.steps : [];
        const stepsHtml = steps.length
          ? '<ul style="margin:6px 0 0 0; padding-left:18px; font-size:11px;">' +
            steps.sort((a,b) => (a.order||0)-(b.order||0)).map(s =>
              `<li><strong>[${escapeHtml(String(s.id||'?'))}]</strong> ${escapeHtml(s.name||'')}` +
              (s.description ? `<br><span style="color:var(--muted);">${escapeHtml(s.description)}</span>` : '') +
              '</li>'
            ).join('') + '</ul>'
          : '';
        appendAgentBubble(`
          <div class="summary-box" style="border-color:rgba(56,189,248,0.5); background:rgba(56,189,248,0.05);">
            <strong style="color:var(--accent);">📋 Deployment Plan</strong>
            ${planSummary ? `<div class="md-content" style="margin-top:8px;">${renderMarkdown(planSummary)}</div>` : ''}
            ${stepsHtml}
          </div>
        `);
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
      activeStepNum = null; // reset active step tracking
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
        // Also clean up any steps still showing "running…".
        finishAllRunningSteps();
        streamEnded = true;
        if (busy) enableInput();
      } catch (err) {
        console.error('[send] error:', err);
        streamEnded = true;
        const isAbort = err && err.name === 'AbortError';
        if (!isAbort) {
          // Clean up any steps still showing "running…" on network/server error.
          finishAllRunningSteps();
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
          renderThinking(ev);
          break;

        case 'final':
          // The LLM's final text before done — skip; done event handles rendering.
          break;

        case 'rag_query':
          renderRAGQuery(ev);
          break;

        case 'rag_store':
          renderRAGStore(ev);
          break;

        case 'rag_update':
          renderRAGUpdate(ev);
          break;

        case 'done':
          // Mark any steps that never received a step_result as done.
          // The LLM sometimes skips STEP_RESULT markers, leaving steps stuck
          // in "running…" state even after the agent has finished.
          finishAllRunningSteps();
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
          // Mark any steps that never received a step_result as done.
          finishAllRunningSteps();
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
        // Mark any steps still showing "running…" as done when user stops.
        finishAllRunningSteps();
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
      activeStepNum = null; // reset active step tracking
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
