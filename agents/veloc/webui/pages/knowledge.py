"""
Knowledge base browser page HTML for the Guard Agent Web UI.

Returns the full HTML for the ``/knowledge`` route.
"""

from __future__ import annotations


def knowledge_browser_html() -> str:
    """Return the HTML for the knowledge base browser page."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Guard Agent \u2013 Knowledge Base</title>
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
    .refresh-btn {
      padding: 6px 12px; border-radius: 8px;
      background: rgba(168,85,247,0.2); border: 1px solid rgba(168,85,247,0.4);
      color: rgba(216,180,254,0.9); font-size: 11px; cursor: pointer;
    }
    .refresh-btn:hover { background: rgba(168,85,247,0.3); }
  </style>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
</head>
<body>
  <div class="shell">
    <div class="card">
      <div class="header">
        <div>
          <div class="title">\U0001f9e0 Knowledge Base</div>
          <div class="subtitle">VeloC agent accumulated insights \u2014 updated automatically during sessions</div>
        </div>
        <a href="/" class="nav-link">\u2190 Back to Agent</a>
      </div>

      <div id="stats-grid" class="stats-grid" style="display:none;"></div>

      <div class="controls">
        <input id="search" class="search-input" type="text" placeholder="Search insights\u2026" oninput="filterEntries()">
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
        <button class="refresh-btn" onclick="loadData()">\u21bb Refresh</button>
      </div>

      <div id="entries-list" class="entries-list">
        <div class="loading">Loading knowledge base\u2026</div>
      </div>
    </div>
  </div>

  <script>
    let allEntries = [];

    function escapeHtml(s) {
      return String(s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function renderMarkdown(text) {
      if (!text) return '';
      if (typeof marked !== 'undefined') {
        try {
          return marked.parse(String(text), { breaks: true, gfm: true });
        } catch(e) { /* fall through */ }
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

    function renderEntries(entries) {
      const list = document.getElementById('entries-list');
      const count = document.getElementById('entry-count');
      if (!entries || entries.length === 0) {
        list.innerHTML = `<div class="empty-state"><div class="icon">\U0001f9e0</div>No insights yet. Run the agent on a VeloC task to start building the knowledge base.</div>`;
        count.textContent = '0 entries';
        return;
      }
      count.textContent = entries.length + ' entr' + (entries.length === 1 ? 'y' : 'ies');
      list.innerHTML = entries.map(e => {
        const conf = typeof e.confidence === 'number' ? e.confidence : 0.8;
        const confPct = Math.round(conf * 100);
        const tags = Array.isArray(e.tags) ? e.tags : [];
        const tagsHtml = tags.map(t => `<span class="tag">${escapeHtml(t)}</span>`).join('');
        const verifiedHtml = e.verified ? `<span class="verified-badge">\u2713 verified</span>` : '';
        return `
          <div class="entry-card" data-title="${escapeHtml((e.title||'').toLowerCase())}" data-content="${escapeHtml((e.content||'').toLowerCase())}" data-cat="${escapeHtml(e.category||'')}">
            <div class="entry-header">
              <div class="entry-title">${escapeHtml(e.title || '(untitled)')}</div>
              <span class="entry-cat">${escapeHtml(catLabel(e.category||''))}</span>
              ${verifiedHtml}
            </div>
            <div class="entry-meta">
              <span><strong>ID:</strong> ${escapeHtml((e.id||'').slice(0,16))}\u2026</span>
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
          </div>`;
      }).join('');
    }

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

    async function loadData() {
      const list = document.getElementById('entries-list');
      list.innerHTML = '<div class="loading">Loading\u2026</div>';
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

    loadData();
  </script>
</body>
</html>
"""
