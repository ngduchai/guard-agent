"""
Knowledge base browser page HTML for the Guard Agent Web UI.

Returns the full HTML for the ``/knowledge`` route.
Supports Add, Edit, and Delete operations on knowledge base entries.
"""

from __future__ import annotations


def knowledge_browser_html() -> str:
    """Return the HTML for the knowledge base browser page."""
    return r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Guard Agent – Knowledge Base</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #050812; --panel: #0f172a; --accent: #38bdf8;
      --border: #1e293b; --text: #e5e7eb; --muted: #9ca3af;
      --danger: #f97373; --success: #86efac; --warn: #fbbf24;
      --mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      --sans: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0; padding: 0; font-family: var(--sans);
      background: radial-gradient(circle at top, #0f172a 0, #020617 55%);
      color: var(--text); min-height: 100vh;
      display: flex; align-items: stretch; justify-content: center;
    }
    .shell {
      max-width: 1120px; width: 100%; padding: 24px 16px 32px;
      display: flex; flex-direction: column; gap: 16px; flex: 1; min-height: 100vh;
    }
    .card {
      background: radial-gradient(circle at top left, rgba(168,85,247,0.08), transparent 55%), var(--panel);
      border-radius: 16px; border: 1px solid rgba(168,85,247,0.3);
      box-shadow: 0 32px 80px rgba(15,23,42,0.9); padding: 18px 18px 12px;
    }
    .header { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 12px; }
    .title { font-size: 20px; font-weight: 700; letter-spacing: 0.02em; color: rgba(216,180,254,0.95); }
    .subtitle { font-size: 13px; color: var(--muted); }
    .nav-link {
      font-size: 12px; color: var(--accent); text-decoration: none;
      border: 1px solid rgba(56,189,248,0.4); border-radius: 999px; padding: 4px 12px;
    }
    .nav-link:hover { background: rgba(56,189,248,0.1); }
    .stats-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
      gap: 8px; margin-bottom: 16px;
    }
    .stat-card {
      background: rgba(168,85,247,0.06); border: 1px solid rgba(168,85,247,0.25);
      border-radius: 10px; padding: 8px 10px;
    }
    .stat-label { font-size: 10px; color: var(--muted); margin-bottom: 2px; }
    .stat-value { font-size: 18px; font-weight: 700; color: rgba(216,180,254,0.95); font-family: var(--mono); }
    .controls { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 12px; }
    .search-input {
      flex: 1; min-width: 200px; padding: 6px 10px; border-radius: 8px;
      background: rgba(15,23,42,0.9); border: 1px solid rgba(168,85,247,0.35);
      color: var(--text); font-size: 12px; outline: none;
    }
    .search-input:focus { border-color: rgba(168,85,247,0.7); }
    .filter-select {
      padding: 6px 10px; border-radius: 8px;
      background: rgba(15,23,42,0.9); border: 1px solid rgba(168,85,247,0.35);
      color: var(--text); font-size: 12px; outline: none; cursor: pointer;
    }
    .entry-count { font-size: 11px; color: var(--muted); white-space: nowrap; }
    .entries-list { display: flex; flex-direction: column; gap: 10px; }
    .entry-card {
      background: rgba(15,23,42,0.95); border: 1px solid rgba(168,85,247,0.25);
      border-radius: 12px; padding: 12px 14px; transition: border-color 0.15s;
    }
    .entry-card:hover { border-color: rgba(168,85,247,0.55); }
    .entry-header { display: flex; align-items: flex-start; gap: 8px; margin-bottom: 6px; }
    .entry-title { font-size: 14px; font-weight: 600; color: rgba(216,180,254,0.95); flex: 1; }
    .entry-cat {
      font-size: 10px; font-weight: 700; letter-spacing: 0.05em;
      padding: 2px 7px; border-radius: 999px;
      background: rgba(168,85,247,0.2); color: rgba(216,180,254,0.9); white-space: nowrap;
    }
    .entry-meta { display: flex; gap: 12px; font-size: 11px; color: var(--muted); margin-bottom: 8px; flex-wrap: wrap; }
    .entry-meta strong { color: rgba(192,132,252,0.8); }
    .entry-content {
      font-size: 12px; color: var(--text);
      background: rgba(168,85,247,0.04); border: 1px solid rgba(168,85,247,0.12);
      border-radius: 8px; padding: 8px 10px; max-height: 300px; overflow-y: auto;
    }
    /* Markdown rendered content inside knowledge entries */
    .entry-content.md-content { line-height: 1.6; }
    .entry-content.md-content p { margin: 0.4em 0; }
    .entry-content.md-content p:first-child { margin-top: 0; }
    .entry-content.md-content p:last-child { margin-bottom: 0; }
    .entry-content.md-content h1, .entry-content.md-content h2,
    .entry-content.md-content h3, .entry-content.md-content h4 {
      margin: 0.6em 0 0.3em; color: rgba(216,180,254,0.95); font-weight: 600;
    }
    .entry-content.md-content ul, .entry-content.md-content ol {
      margin: 0.3em 0; padding-left: 1.4em;
    }
    .entry-content.md-content li { margin: 0.15em 0; }
    .entry-content.md-content code {
      font-family: var(--mono); font-size: 11px;
      background: rgba(168,85,247,0.15); border-radius: 4px;
      padding: 1px 4px; color: rgba(216,180,254,0.9);
    }
    .entry-content.md-content pre {
      background: rgba(15,23,42,0.95); border: 1px solid rgba(168,85,247,0.2);
      border-radius: 8px; padding: 8px 10px; overflow-x: auto; margin: 0.4em 0;
    }
    .entry-content.md-content pre code {
      background: none; padding: 0; color: var(--text); font-size: 11px;
    }
    .entry-content.md-content strong { color: rgba(216,180,254,0.95); }
    .entry-content.md-content em { color: var(--muted); }
    .entry-content.md-content blockquote {
      border-left: 3px solid rgba(168,85,247,0.6); margin: 0.4em 0;
      padding: 2px 10px; color: var(--muted);
    }
    .entry-content.md-content a { color: var(--accent); }
    .entry-content.md-content hr {
      border: none; border-top: 1px solid rgba(168,85,247,0.2); margin: 0.5em 0;
    }
    .entry-tags { display: flex; gap: 4px; flex-wrap: wrap; margin-top: 6px; }
    .tag {
      font-size: 10px; padding: 1px 6px; border-radius: 999px;
      background: rgba(56,189,248,0.1); border: 1px solid rgba(56,189,248,0.25); color: var(--accent);
    }
    .conf-bar-wrap { display: flex; align-items: center; gap: 6px; margin-top: 4px; }
    .conf-bar-bg { flex: 1; height: 4px; border-radius: 2px; background: rgba(168,85,247,0.15); }
    .conf-bar-fill { height: 4px; border-radius: 2px; background: rgba(168,85,247,0.7); }
    .conf-label { font-size: 10px; color: var(--muted); white-space: nowrap; }
    .verified-badge {
      font-size: 10px; padding: 1px 6px; border-radius: 999px;
      background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.3); color: var(--success);
    }
    .empty-state { text-align: center; padding: 40px 20px; color: var(--muted); font-size: 14px; }
    .empty-state .icon { font-size: 40px; margin-bottom: 12px; }
    .loading { text-align: center; padding: 40px; color: var(--muted); }
    .error-msg { color: var(--danger); font-size: 13px; padding: 12px; }

    /* ── Buttons ── */
    .btn {
      padding: 6px 12px; border-radius: 8px; font-size: 11px; cursor: pointer;
      border: 1px solid transparent; transition: background 0.15s, border-color 0.15s;
    }
    .btn-primary {
      background: rgba(168,85,247,0.25); border-color: rgba(168,85,247,0.5);
      color: rgba(216,180,254,0.95);
    }
    .btn-primary:hover { background: rgba(168,85,247,0.4); }
    .btn-secondary {
      background: rgba(56,189,248,0.1); border-color: rgba(56,189,248,0.35);
      color: var(--accent);
    }
    .btn-secondary:hover { background: rgba(56,189,248,0.2); }
    .btn-danger {
      background: rgba(249,115,115,0.1); border-color: rgba(249,115,115,0.35);
      color: var(--danger);
    }
    .btn-danger:hover { background: rgba(249,115,115,0.25); }
    .btn-success {
      background: rgba(134,239,172,0.1); border-color: rgba(134,239,172,0.35);
      color: var(--success);
    }
    .btn-success:hover { background: rgba(134,239,172,0.25); }

    /* ── Entry action row ── */
    .entry-actions { display: flex; gap: 6px; margin-top: 8px; justify-content: flex-end; }

    /* ── Modal overlay ── */
    .modal-overlay {
      display: none; position: fixed; inset: 0;
      background: rgba(2,6,23,0.85); backdrop-filter: blur(4px);
      z-index: 1000; align-items: center; justify-content: center;
    }
    .modal-overlay.open { display: flex; }
    .modal {
      background: var(--panel); border: 1px solid rgba(168,85,247,0.4);
      border-radius: 16px; padding: 24px; width: 100%; max-width: 640px;
      max-height: 90vh; overflow-y: auto;
      box-shadow: 0 32px 80px rgba(0,0,0,0.8);
    }
    .modal-title { font-size: 16px; font-weight: 700; color: rgba(216,180,254,0.95); margin-bottom: 16px; }
    .form-group { margin-bottom: 12px; }
    .form-label { font-size: 11px; color: var(--muted); margin-bottom: 4px; display: block; }
    .form-input, .form-select, .form-textarea {
      width: 100%; padding: 7px 10px; border-radius: 8px;
      background: rgba(15,23,42,0.9); border: 1px solid rgba(168,85,247,0.35);
      color: var(--text); font-size: 12px; outline: none; font-family: var(--sans);
    }
    .form-input:focus, .form-select:focus, .form-textarea:focus {
      border-color: rgba(168,85,247,0.7);
    }
    .form-textarea { resize: vertical; min-height: 120px; font-family: var(--mono); }
    .form-row { display: flex; gap: 10px; }
    .form-row .form-group { flex: 1; }
    .modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px; }

    /* ── Toast ── */
    #toast {
      position: fixed; bottom: 24px; right: 24px; z-index: 2000;
      padding: 10px 16px; border-radius: 10px; font-size: 13px;
      background: rgba(15,23,42,0.97); border: 1px solid rgba(168,85,247,0.4);
      color: var(--text); opacity: 0; transition: opacity 0.25s;
      pointer-events: none; max-width: 360px;
    }
    #toast.show { opacity: 1; }
    #toast.ok { border-color: rgba(134,239,172,0.5); color: var(--success); }
    #toast.err { border-color: rgba(249,115,115,0.5); color: var(--danger); }

    /* ── Confirm dialog ── */
    .confirm-overlay {
      display: none; position: fixed; inset: 0;
      background: rgba(2,6,23,0.85); backdrop-filter: blur(4px);
      z-index: 1100; align-items: center; justify-content: center;
    }
    .confirm-overlay.open { display: flex; }
    .confirm-box {
      background: var(--panel); border: 1px solid rgba(249,115,115,0.4);
      border-radius: 14px; padding: 24px; width: 100%; max-width: 400px;
      box-shadow: 0 32px 80px rgba(0,0,0,0.8);
    }
    .confirm-title { font-size: 15px; font-weight: 700; color: var(--danger); margin-bottom: 10px; }
    .confirm-msg { font-size: 13px; color: var(--muted); margin-bottom: 20px; }
    .confirm-actions { display: flex; gap: 8px; justify-content: flex-end; }
  </style>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
</head>
<body>
  <div class="shell">
    <div class="card">
      <div class="header">
        <div>
          <div class="title">🧠 Knowledge Base</div>
          <div class="subtitle">VeloC agent accumulated insights — add, edit or remove entries</div>
        </div>
        <a href="/" class="nav-link">← Back to Agent</a>
      </div>

      <div id="stats-grid" class="stats-grid" style="display:none;"></div>

      <div class="controls">
        <input id="search" class="search-input" type="text" placeholder="Search insights…" oninput="filterEntries()">
        <select id="cat-filter" class="filter-select" onchange="filterEntries()">
          <option value="">All categories</option>
          <option value="best_practice">Best Practice</option>
          <option value="api_usage">API Usage</option>
          <option value="error_solution">Error Solution</option>
          <option value="state_identification">State Identification</option>
          <option value="checkpoint_timing">Checkpoint Timing</option>
          <option value="code_pattern">Code Pattern</option>
        </select>
        <span id="entry-count" class="entry-count"></span>
        <button class="btn btn-primary" onclick="openAddModal()">＋ Add Entry</button>
        <button class="btn btn-secondary" onclick="loadData()">↻ Refresh</button>
      </div>

      <div id="entries-list" class="entries-list">
        <div class="loading">Loading knowledge base…</div>
      </div>
    </div>
  </div>

  <!-- ── Add / Edit Modal ── -->
  <div id="entry-modal" class="modal-overlay" onclick="handleOverlayClick(event)">
    <div class="modal" onclick="event.stopPropagation()">
      <div class="modal-title" id="modal-title">Add Entry</div>
      <input type="hidden" id="modal-entry-id">

      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Title *</label>
          <input id="f-title" class="form-input" type="text" placeholder="Short descriptive title">
        </div>
        <div class="form-group" style="max-width:200px;">
          <label class="form-label">Category *</label>
          <select id="f-category" class="form-select">
            <option value="best_practice">Best Practice</option>
            <option value="api_usage">API Usage</option>
            <option value="error_solution">Error Solution</option>
            <option value="state_identification">State Identification</option>
            <option value="checkpoint_timing">Checkpoint Timing</option>
            <option value="code_pattern">Code Pattern</option>
          </select>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">Content * (Markdown supported)</label>
        <textarea id="f-content" class="form-textarea" rows="8" placeholder="Full text of the insight…"></textarea>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label class="form-label">Tags (comma-separated)</label>
          <input id="f-tags" class="form-input" type="text" placeholder="veloc, mpi, checkpoint">
        </div>
        <div class="form-group" style="max-width:160px;">
          <label class="form-label">Confidence (0–1)</label>
          <input id="f-confidence" class="form-input" type="number" min="0" max="1" step="0.05" value="0.5">
        </div>
        <div class="form-group" style="max-width:120px; display:flex; flex-direction:column; justify-content:flex-end;">
          <label class="form-label" style="display:flex; align-items:center; gap:6px; cursor:pointer;">
            <input id="f-verified" type="checkbox" style="accent-color: rgba(134,239,172,0.9);">
            Verified
          </label>
        </div>
      </div>

      <div class="modal-actions">
        <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
        <button class="btn btn-success" onclick="submitEntry()">Save</button>
      </div>
    </div>
  </div>

  <!-- ── Confirm Delete Dialog ── -->
  <div id="confirm-overlay" class="confirm-overlay" onclick="closeConfirm()">
    <div class="confirm-box" onclick="event.stopPropagation()">
      <div class="confirm-title">⚠ Delete Entry</div>
      <div class="confirm-msg" id="confirm-msg">Are you sure you want to delete this entry? This action cannot be undone.</div>
      <div class="confirm-actions">
        <button class="btn btn-secondary" onclick="closeConfirm()">Cancel</button>
        <button class="btn btn-danger" onclick="confirmDelete()">Delete</button>
      </div>
    </div>
  </div>

  <!-- ── Toast ── -->
  <div id="toast"></div>

  <script>
    let allEntries = [];
    let pendingDeleteId = null;
    let toastTimer = null;

    // ── Utilities ──────────────────────────────────────────────────────────

    function escapeHtml(s) {
      return String(s)
        .replace(/&/g, '&').replace(/</g, '<')
        .replace(/>/g, '>').replace(/"/g, '"');
    }

    function renderMarkdown(text) {
      if (!text) return '';
      if (typeof marked !== 'undefined') {
        try { return marked.parse(String(text), { breaks: true, gfm: true }); }
        catch(e) { /* fall through */ }
      }
      return '<pre style="white-space:pre-wrap; margin:0;">' + escapeHtml(String(text)) + '</pre>';
    }

    function fmtDate(iso) {
      if (!iso) return '';
      try { return new Date(iso).toLocaleString(); } catch(e) { return iso; }
    }

    function catLabel(cat) {
      const map = {
        best_practice: 'Best Practice', api_usage: 'API Usage',
        error_solution: 'Error Solution', state_identification: 'State ID',
        checkpoint_timing: 'Checkpoint Timing', code_pattern: 'Code Pattern',
      };
      return map[cat] || cat;
    }

    function showToast(msg, type = '') {
      const t = document.getElementById('toast');
      t.textContent = msg;
      t.className = 'show' + (type ? ' ' + type : '');
      if (toastTimer) clearTimeout(toastTimer);
      toastTimer = setTimeout(() => { t.className = ''; }, 3500);
    }

    // ── Stats ──────────────────────────────────────────────────────────────

    function renderStats(stats) {
      const grid = document.getElementById('stats-grid');
      if (!stats) { grid.style.display = 'none'; return; }
      const items = [
        { label: 'Total Entries', value: stats.total_entries ?? 0 },
        { label: 'DB Version', value: stats.version ?? 1 },
      ];
      const byCat = stats.by_category || {};
      for (const [cat, count] of Object.entries(byCat)) {
        items.push({ label: catLabel(cat), value: count });
      }
      grid.innerHTML = items.map(i =>
        `<div class="stat-card"><div class="stat-label">${escapeHtml(i.label)}</div><div class="stat-value">${escapeHtml(String(i.value))}</div></div>`
      ).join('');
      grid.style.display = 'grid';
    }

    // ── Render entries ─────────────────────────────────────────────────────

    // Keep a reference to the currently-rendered entries so edit/delete
    // buttons can look them up by index instead of inlining JSON into
    // onclick attributes (which breaks when content contains quotes / angle brackets).
    let renderedEntries = [];

    function renderEntries(entries) {
      const list = document.getElementById('entries-list');
      const count = document.getElementById('entry-count');
      if (!entries || entries.length === 0) {
        renderedEntries = [];
        list.innerHTML = `<div class="empty-state"><div class="icon">🧠</div>No insights yet. Run the agent on a VeloC task to start building the knowledge base, or add one manually.</div>`;
        count.textContent = '0 entries';
        return;
      }
      renderedEntries = entries;
      count.textContent = entries.length + ' entr' + (entries.length === 1 ? 'y' : 'ies');
      list.innerHTML = entries.map((e, idx) => {
        const conf = typeof e.confidence === 'number' ? e.confidence : 0.8;
        const confPct = Math.round(conf * 100);
        const tags = Array.isArray(e.tags) ? e.tags : [];
        const tagsHtml = tags.map(t => `<span class="tag">${escapeHtml(t)}</span>`).join('');
        const verifiedHtml = e.verified ? `<span class="verified-badge">✓ verified</span>` : '';
        return `
          <div class="entry-card" data-cat="${escapeHtml(e.category||'')}">
            <div class="entry-header">
              <div class="entry-title">${escapeHtml(e.title || '(untitled)')}</div>
              <span class="entry-cat">${escapeHtml(catLabel(e.category||''))}</span>
              ${verifiedHtml}
            </div>
            <div class="entry-meta">
              <span><strong>ID:</strong> ${escapeHtml((e.id||'').slice(0,16))}…</span>
              <span><strong>Created:</strong> ${escapeHtml(fmtDate(e.created_at))}</span>
              ${e.updated_at && e.updated_at !== e.created_at ? `<span><strong>Updated:</strong> ${escapeHtml(fmtDate(e.updated_at))}</span>` : ''}
              ${e.source ? `<span><strong>Source:</strong> ${escapeHtml(e.source)}</span>` : ''}
            </div>
            <div class="conf-bar-wrap">
              <div class="conf-bar-bg"><div class="conf-bar-fill" style="width:${confPct}%"></div></div>
              <span class="conf-label">Confidence: ${confPct}%</span>
            </div>
            <div class="entry-content md-content">${renderMarkdown(e.content||'')}</div>
            ${tagsHtml ? `<div class="entry-tags">${tagsHtml}</div>` : ''}
            <div class="entry-actions">
              <button class="btn btn-secondary" onclick="openEditModal(renderedEntries[${idx}])">✏ Edit</button>
              <button class="btn btn-danger" onclick="askDeleteByIndex(${idx})">🗑 Delete</button>
            </div>
          </div>`;
      }).join('');
    }

    // ── Filter ─────────────────────────────────────────────────────────────

    function filterEntries() {
      const q = (document.getElementById('search').value || '').toLowerCase();
      const cat = document.getElementById('cat-filter').value;
      const filtered = allEntries.filter(e => {
        const matchCat = !cat || e.category === cat;
        const matchQ = !q
          || (e.title||'').toLowerCase().includes(q)
          || (e.content||'').toLowerCase().includes(q)
          || (e.tags||[]).some(t => t.toLowerCase().includes(q));
        return matchCat && matchQ;
      });
      renderEntries(filtered);
    }

    // ── Load data ──────────────────────────────────────────────────────────

    async function loadData() {
      const list = document.getElementById('entries-list');
      list.innerHTML = '<div class="loading">Loading…</div>';
      try {
        const resp = await fetch('/api/knowledge');
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        const data = await resp.json();
        if (data.error) throw new Error(data.error);
        renderStats(data.stats);
        allEntries = Array.isArray(data.entries) ? data.entries : [];
        filterEntries();
      } catch (err) {
        list.innerHTML = `<div class="error-msg">Failed to load knowledge base: ${escapeHtml(String(err))}</div>`;
      }
    }

    // ── Modal helpers ──────────────────────────────────────────────────────

    function openAddModal() {
      document.getElementById('modal-title').textContent = 'Add Entry';
      document.getElementById('modal-entry-id').value = '';
      document.getElementById('f-title').value = '';
      document.getElementById('f-category').value = 'best_practice';
      document.getElementById('f-content').value = '';
      document.getElementById('f-tags').value = '';
      document.getElementById('f-confidence').value = '0.5';
      document.getElementById('f-verified').checked = false;
      document.getElementById('entry-modal').classList.add('open');
      document.getElementById('f-title').focus();
    }

    function openEditModal(entry) {
      document.getElementById('modal-title').textContent = 'Edit Entry';
      document.getElementById('modal-entry-id').value = entry.id || '';
      document.getElementById('f-title').value = entry.title || '';
      document.getElementById('f-category').value = entry.category || 'best_practice';
      document.getElementById('f-content').value = entry.content || '';
      document.getElementById('f-tags').value = (entry.tags || []).join(', ');
      document.getElementById('f-confidence').value = typeof entry.confidence === 'number' ? entry.confidence : 0.5;
      document.getElementById('f-verified').checked = !!entry.verified;
      document.getElementById('entry-modal').classList.add('open');
      document.getElementById('f-title').focus();
    }

    function closeModal() {
      document.getElementById('entry-modal').classList.remove('open');
    }

    function handleOverlayClick(e) {
      if (e.target === document.getElementById('entry-modal')) closeModal();
    }

    // ── Submit (add or edit) ───────────────────────────────────────────────

    async function submitEntry() {
      const id = document.getElementById('modal-entry-id').value.trim();
      const title = document.getElementById('f-title').value.trim();
      const category = document.getElementById('f-category').value;
      const content = document.getElementById('f-content').value.trim();
      const tagsRaw = document.getElementById('f-tags').value;
      const tags = tagsRaw.split(',').map(t => t.trim()).filter(Boolean);
      const confidence = parseFloat(document.getElementById('f-confidence').value) || 0.5;
      const verified = document.getElementById('f-verified').checked;

      if (!title) { showToast('Title is required.', 'err'); return; }
      if (!content) { showToast('Content is required.', 'err'); return; }

      const isEdit = !!id;
      const url = isEdit ? `/api/knowledge/${encodeURIComponent(id)}` : '/api/knowledge';
      const method = isEdit ? 'PUT' : 'POST';
      const body = isEdit
        ? { title, category, content, tags, confidence, verified }
        : { title, category, content, tags, confidence, source: 'webui' };

      try {
        const resp = await fetch(url, {
          method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        const data = await resp.json();
        if (!data.ok) throw new Error(data.error || 'Unknown error');
        closeModal();
        showToast(isEdit ? '✓ Entry updated.' : '✓ Entry added.', 'ok');
        await loadData();
      } catch (err) {
        showToast('Error: ' + String(err), 'err');
      }
    }

    // ── Delete ─────────────────────────────────────────────────────────────

    function askDeleteByIndex(idx) {
      const e = renderedEntries[idx];
      if (!e) return;
      askDelete(e.id || '', e.title || '(untitled)');
    }

    function askDelete(id, title) {
      pendingDeleteId = id;
      document.getElementById('confirm-msg').textContent =
        `Delete "${title}"? This action cannot be undone.`;
      document.getElementById('confirm-overlay').classList.add('open');
    }

    function closeConfirm() {
      pendingDeleteId = null;
      document.getElementById('confirm-overlay').classList.remove('open');
    }

    async function confirmDelete() {
      if (!pendingDeleteId) return;
      const id = pendingDeleteId;
      closeConfirm();
      try {
        const resp = await fetch(`/api/knowledge/${encodeURIComponent(id)}`, { method: 'DELETE' });
        const data = await resp.json();
        if (!data.ok) throw new Error(data.error || 'Unknown error');
        showToast('✓ Entry deleted.', 'ok');
        await loadData();
      } catch (err) {
        showToast('Error: ' + String(err), 'err');
      }
    }

    // ── Keyboard shortcuts ─────────────────────────────────────────────────

    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') {
        closeModal();
        closeConfirm();
      }
    });

    // ── Init ───────────────────────────────────────────────────────────────

    loadData();
  </script>
</body>
</html>
"""
