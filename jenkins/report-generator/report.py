#!/usr/bin/env python3
"""
Author      : Sagar Malla
Email       : sagarmalla08@gmail.com
Last Updated  : 21st May, 2026
Description : Unified security report generator — auto-detects SBOM JSON or
              OWASP Dependency-Check XML input and produces an enhanced HTML
              report with severity sorting, dark mode, live search, and
              sortable columns.
              Usage:
                python3 report.py
                python3 report.py sbom.json vuln-report.json
                python3 report.py dependency-check.xml
                python3 report.py dependency-check.xml output.html
"""

import sys
import json
import xml.etree.ElementTree as ET
from html import escape
from pathlib import Path
from datetime import datetime

# ── Shared Constants ──────────────────────────────────────────────────────────

SVG_SHIELD = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>'
SVG_FLAME = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/></svg>'
SVG_TRI = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>'
SVG_ALERT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>'
SVG_INFO = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
SVG_CHART = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20h16"/><path d="M4 20V4"/><path d="M9 20V10"/><path d="M14 20V7"/><path d="M19 20V13"/></svg>'
SVG_CALENDAR = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>'
SVG_PACKAGE = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16.5 9.4 7.55 4.24"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><path d="M3.27 6.96 12 12.01l8.73-5.05"/><path d="M12 22.08V12"/></svg>'

SVG_MAP = {"CRITICAL": SVG_FLAME, "HIGH": SVG_TRI, "MEDIUM": SVG_ALERT, "LOW": SVG_INFO}
SEV_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
SEV_COLORS = {"CRITICAL": "#ef4444", "HIGH": "#f97316", "MEDIUM": "#eab308", "LOW": "#22c55e"}


# ── HTML Template Engine ─────────────────────────────────────────────────────

def build_html(title, subtitle, project_label, header_meta_rows,
               stat_cards, bar_segments, bar_legend,
               table_headers, rows_json, no_data_msg,
               search_placeholder, sort_keys, severity_col_idx):
    now = datetime.now()
    svg_pattern = (
        'url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' '
        'viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg '
        'fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%23ffffff\' '
        'fill-opacity=\'0.05\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4'
        'zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 '
        '4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")'
    )
    svg_search = (
        'url("data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' '
        'width=\'16\' height=\'16\' viewBox=\'0 0 24 24\' fill=\'none\' '
        'stroke=\'%2394a3b8\' stroke-width=\'2\' stroke-linecap=\'round\' '
        'stroke-linejoin=\'round\'%3E%3Ccircle cx=\'11\' cy=\'11\' r=\'8\'/%3E'
        '%3Cline x1=\'21\' y1=\'21\' x2=\'16.65\' y2=\'16.65\'/%3E%3C/svg%3E")'
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(title)}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Inter','Segoe UI',system-ui,sans-serif; background:#f8fafc; color:#1e293b; line-height:1.6; transition:background .3s,color .3s; }}
.container {{ max-width:1400px; margin:0 auto; padding:0 24px; }}

body.dark {{ background:#0f172a; color:#e2e8f0; }}
body.dark .card {{ background:#1e293b; border-color:#334155; }}
body.dark th {{ background:#1e293b; color:#94a3b8; border-bottom-color:#334155; }}
body.dark td {{ border-bottom-color:#334155; }}
body.dark tr:hover td {{ background:#1a2332; }}
body.dark tr:nth-child(even) td {{ background:#172033; }}
body.dark tr:nth-child(even):hover td {{ background:#1a2332; }}
body.dark .stat-card {{ background:#0f172a; border-color:#334155; }}
body.dark header {{ background:linear-gradient(135deg,#1e3a5f 0%,#2d1b69 100%); }}
body.dark footer {{ background:#1e293b; border-color:#334155; }}
body.dark .search-box {{ background:#0f172a; border-color:#334155; color:#e2e8f0; }}
body.dark .ref-cell a {{ color:#93c5fd; }}
body.dark .stat-value {{ color:#f1f5f9; }}
body.dark .chip {{ background:#334155; color:#94a3b8; }}
body.dark .desc-text {{ color:#cbd5e1; }}
body.dark .severity-critical {{ background:rgba(239,68,68,0.15); color:#fca5a5; }}
body.dark .severity-high {{ background:rgba(249,115,22,0.15); color:#fdba74; }}
body.dark .severity-medium {{ background:rgba(234,179,8,0.15); color:#fde047; }}
body.dark .severity-low {{ background:rgba(34,197,94,0.15); color:#86efac; }}
body.dark .fix-available {{ background:rgba(59,130,246,0.15); color:#93c5fd; }}
body.dark .fix-none {{ background:#334155; color:#94a3b8; }}
body.dark .vuln-id {{ color:#a5b4fc; }}
body.dark .count-badge {{ background:#334155; color:#94a3b8; }}

header {{ background:linear-gradient(135deg,#6366f1 0%,#8b5cf6 50%,#a855f7 100%); color:white; padding:2rem 0; position:relative; overflow:hidden; }}
header::before {{ content:''; position:absolute; inset:0; background:{svg_pattern}; opacity:0.4; }}
.header-content {{ display:flex; justify-content:space-between; align-items:center; position:relative; z-index:1; flex-wrap:wrap; gap:16px; }}
.logo {{ display:flex; align-items:center; gap:16px; }}
.logo-icon {{ font-size:2.5rem; }}
.logo h1 {{ font-size:1.6rem; font-weight:700; letter-spacing:-0.02em; }}
.logo p {{ font-size:0.9rem; opacity:0.85; margin-top:2px; }}
.header-meta {{ text-align:right; font-size:0.85rem; opacity:0.9; line-height:1.8; }}
.header-meta span {{ display:block; }}

.theme-toggle {{ position:fixed; top:20px; right:20px; z-index:100; background:rgba(255,255,255,0.2); backdrop-filter:blur(8px); border:none; color:white; width:44px; height:44px; border-radius:12px; cursor:pointer; font-size:1.3rem; display:flex; align-items:center; justify-content:center; transition:background .2s; }}
.theme-toggle:hover {{ background:rgba(255,255,255,0.35); }}
.gototop {{ position:fixed; bottom:20px; right:20px; z-index:100; background:rgba(0,0,0,0.12); backdrop-filter:blur(8px); border:none; color:#334155; width:44px; height:44px; border-radius:12px; cursor:pointer; font-size:1.3rem; display:none; align-items:center; justify-content:center; transition:background .2s,color .2s,opacity .3s; opacity:0.7; }}
.gototop:hover {{ background:rgba(0,0,0,0.22); opacity:1; }}
body.dark .gototop {{ background:rgba(255,255,255,0.2); color:#fff; }}
body.dark .gototop:hover {{ background:rgba(255,255,255,0.35); }}

.card {{ background:white; border-radius:16px; padding:28px; margin:28px 0; box-shadow:0 1px 3px rgba(0,0,0,0.06),0 1px 2px rgba(0,0,0,0.04); border:1px solid #e2e8f0; transition:background .3s,border-color .3s; }}
.section-title {{ font-size:1.15rem; font-weight:600; margin-bottom:20px; color:#334155; display:flex; align-items:center; gap:10px; }}
body.dark .section-title {{ color:#cbd5e1; }}

.stats-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:16px; }}
.stat-card {{ background:#f8fafc; border-radius:12px; padding:20px 12px; text-align:center; border:1px solid #e2e8f0; transition:transform .2s,box-shadow .2s; }}
.stat-card:hover {{ transform:translateY(-2px); box-shadow:0 4px 12px rgba(0,0,0,0.06); }}
.stat-icon {{ margin-bottom:8px; color:#6366f1; }}
.stat-icon svg {{ width:28px; height:28px; display:block; margin:0 auto; }}
.stat-value {{ font-size:2rem; font-weight:700; margin-bottom:2px; color:#0f172a; transition:color .3s; }}
.stat-label {{ font-size:0.78rem; color:#64748b; font-weight:500; text-transform:uppercase; letter-spacing:0.04em; }}
body.dark .stat-label {{ color:#94a3b8; }}
.stat-sev-critical .stat-icon {{ color:#dc2626; }}
.stat-sev-critical .stat-value {{ color:#dc2626; }}
.stat-sev-high .stat-icon {{ color:#ea580c; }}
.stat-sev-high .stat-value {{ color:#ea580c; }}
.stat-sev-medium .stat-icon {{ color:#ca8a04; }}
.stat-sev-medium .stat-value {{ color:#ca8a04; }}
.stat-sev-low .stat-icon {{ color:#16a34a; }}
.stat-sev-low .stat-value {{ color:#16a34a; }}

.severity-bar {{ display:flex; height:10px; border-radius:99px; overflow:hidden; margin-top:20px; background:#e2e8f0; }}
.bar-seg {{ transition:width .6s ease; }}
.sev-critical {{ background:#ef4444; }}
.sev-high {{ background:#f97316; }}
.sev-medium {{ background:#eab308; }}
.sev-low {{ background:#22c55e; }}
.bar-legend {{ display:flex; gap:20px; margin-top:10px; flex-wrap:wrap; font-size:0.8rem; color:#64748b; }}
.bar-legend-item {{ display:flex; align-items:center; gap:6px; }}
.bar-legend-dot {{ width:10px; height:10px; border-radius:50%; }}

.table-controls {{ display:flex; gap:12px; align-items:center; margin-bottom:16px; flex-wrap:wrap; }}
.search-box {{ flex:1; min-width:200px; padding:10px 16px 10px 40px; border:1px solid #e2e8f0; border-radius:10px; font-size:0.9rem; background:#fff {svg_search} 12px center no-repeat; outline:none; transition:border-color .2s; }}
.search-box:focus {{ border-color:#6366f1; box-shadow:0 0 0 3px rgba(99,102,241,0.1); }}

.table-wrap {{ overflow-x:auto; border-radius:12px; border:1px solid #e2e8f0; }}
body.dark .table-wrap {{ border-color:#334155; }}
table {{ width:100%; border-collapse:collapse; font-size:0.85rem; }}
th {{ position:sticky; top:0; z-index:10; background:#f1f5f9; padding:14px 12px; text-align:left; font-weight:600; font-size:0.75rem; text-transform:uppercase; letter-spacing:0.05em; color:#64748b; border-bottom:2px solid #e2e8f0; cursor:pointer; user-select:none; white-space:nowrap; transition:background .2s; }}
th:hover {{ background:#e9edf3; }}
th .sort-icon {{ display:inline-block; margin-left:6px; }}
th .sort-icon::after {{ content:'\\25B2\\25BC'; font-size:0.6rem; letter-spacing:-2px; opacity:0.3; }}
th.sort-asc .sort-icon::after {{ content:'\\25B2'; opacity:1; }}
th.sort-desc .sort-icon::after {{ content:'\\25BC'; opacity:1; }}
td {{ padding:12px; border-bottom:1px solid #e2e8f0; vertical-align:top; transition:background .15s; }}
tr:last-child td {{ border-bottom:none; }}
tr:nth-child(even) td {{ background:#f8fafc; }}
tr:hover td {{ background:#eef2ff; }}

.severity-badge {{ display:inline-flex; align-items:center; gap:6px; padding:4px 12px; border-radius:20px; font-size:0.75rem; font-weight:600; text-transform:uppercase; letter-spacing:0.03em; }}
.severity-critical {{ background:#fef2f2; color:#991b1b; }}
.severity-high {{ background:#fff7ed; color:#9a3412; }}
.severity-medium {{ background:#fefce8; color:#854d0e; }}
.severity-low {{ background:#f0fdf4; color:#166534; }}

.sev-badge {{ display:inline-flex; align-items:center; gap:6px; padding:3px 10px; border-radius:20px; font-size:0.7rem; font-weight:600; text-transform:uppercase; letter-spacing:0.03em; color:#fff; }}
.sev-badge.sev-critical {{ background:#ef4444; }}
.sev-badge.sev-high {{ background:#f97316; }}
.sev-badge.sev-medium {{ background:#eab308; color:#422006; }}
.sev-badge.sev-low {{ background:#22c55e; color:#052e16; }}

.severity-dot {{ width:8px; height:8px; border-radius:50%; background:currentColor; }}
.sev-dot-critical {{ background:#ef4444; }}
.sev-dot-high {{ background:#f97316; }}
.sev-dot-medium {{ background:#eab308; }}
.sev-dot-low {{ background:#22c55e; }}

.cvss-cell {{ font-family:'JetBrains Mono','Fira Code',monospace; font-weight:600; font-size:0.85rem; }}
.cvss-critical {{ color:#dc2626; }}
.cvss-high {{ color:#ea580c; }}
.cvss-medium {{ color:#ca8a04; }}
.cvss-low {{ color:#16a34a; }}

.ref-cell {{ max-width:300px; }}
.ref-cell a {{ color:#6366f1; text-decoration:none; font-size:0.78rem; display:inline-block; margin-bottom:2px; transition:color .15s; }}
.ref-cell a:hover {{ color:#4f46e5; text-decoration:underline; }}

.desc-text {{ color:#475569; max-width:320px; }}
.desc-truncated {{ display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; cursor:pointer; }}

.vuln-id {{ font-family:'JetBrains Mono','Fira Code',monospace; font-size:0.85rem; color:#6366f1; font-weight:500; }}
.fix-badge {{ display:inline-block; padding:2px 10px; border-radius:20px; font-size:0.75rem; font-weight:500; }}
.fix-available {{ background:#dbeafe; color:#1e40af; }}
.fix-none {{ background:#f1f5f9; color:#64748b; }}

.chips {{ display:flex; flex-wrap:wrap; gap:4px; }}
.chip {{ background:#f1f5f9; padding:2px 8px; border-radius:4px; font-size:0.75rem; color:#475569; }}

.empty-state {{ text-align:center; padding:60px 20px; }}
.empty-state-icon {{ font-size:4rem; margin-bottom:12px; }}
.empty-state h2 {{ font-size:1.4rem; margin-bottom:8px; color:#334155; }}
body.dark .empty-state h2 {{ color:#cbd5e1; }}
.empty-state p {{ color:#64748b; }}

footer {{ background:#f1f5f9; padding:24px 0; border-top:1px solid #e2e8f0; margin-top:40px; transition:background .3s,border-color .3s; }}
.footer-content {{ display:flex; flex-direction:column; align-items:center; gap:4px; font-size:0.82rem; color:#64748b; }}


.count-badge {{ display:inline-flex; align-items:center; justify-content:center; background:#e2e8f0; color:#475569; border-radius:99px; padding:2px 10px; font-size:0.75rem; font-weight:600; margin-left:8px; }}

@media (max-width:768px) {{
    .container {{ padding:0 16px; }}
    .header-content {{ flex-direction:column; text-align:center; }}
    .header-meta {{ text-align:center; }}
    .stats-grid {{ grid-template-columns:repeat(2,1fr); }}
    .stat-value {{ font-size:1.6rem; }}
    .table-controls {{ flex-direction:column; }}
    .search-box {{ width:100%; }}
    .card {{ padding:20px; }}
    .logo h1 {{ font-size:1.25rem; }}
    th, td {{ padding:10px 8px; font-size:0.78rem; }}
    .theme-toggle {{ top:12px; right:12px; width:38px; height:38px; font-size:1.1rem; }}
}}
</style>
</head>
<body>

<button class="theme-toggle" onclick="toggleTheme()" title="Toggle dark mode" aria-label="Toggle dark mode">🌙</button>
<button class="gototop" onclick="goToTop()" title="Go to top" id="goToTopBtn"><svg width="22" height="22" viewBox="0 0 512 512"><path d="M256 8C119 8 8 119 8 256s111 248 248 248 248-111 248-248S393 8 256 8z" fill="none" stroke="#60bb47" stroke-width="24"/><polygon points="132.9 277.9 173.6 318.6 256 236.1 338.4 318.6 379.1 277.9 256 154.8" fill="#60bb47"/></svg></button>

<header>
<div class="container">
    <div class="header-content">
        <div class="logo">
            <span class="logo-icon">{project_label}</span>
            <div>
                <h1>{escape(title)}</h1>
                <p>{escape(subtitle)}</p>
            </div>
        </div>
        <div class="header-meta">
            {header_meta_rows}
        </div>
    </div>
</div>
</header>

<main class="container">

<div class="card">
    <div class="section-title">{SVG_CHART} Vulnerability Overview</div>
    <div class="stats-grid">{stat_cards}</div>
    <div class="severity-bar">{bar_segments}</div>
    <div class="bar-legend">{bar_legend}</div>
</div>

<div class="card">
    <div class="section-title">
        📋 Detailed Findings
        <span class="count-badge" id="visible-count">0</span>
    </div>
    <div class="table-controls">
        <input type="text" class="search-box" id="search-input" placeholder="{escape(search_placeholder)}" oninput="applyFilter()">
    </div>
    <div class="table-wrap">
    <table>
        <thead>
            <tr>{table_headers}</tr>
        </thead>
        <tbody id="vuln-tbody"></tbody>
    </table>
    </div>
</div>

</main>

<footer>
<div class="container">
    <div class="footer-content">
        <div>Maintainer : <b style="color:#3db409;">Aditya Tuladhar | Sagar Malla</b></div>
        <div>Generated on {now.strftime('%B %d, %Y at %H:%M')}</div>
    </div>
</div>
</footer>

<script>
const ROWS = {rows_json};
const SEV_IDX = {json.dumps({s: i for i, s in enumerate(SEV_ORDER)})};
const SORT_KEYS = {json.dumps(sort_keys)};
const SEV_COL = {severity_col_idx};

let sortCol = -1;
let sortDir = 1;
let filterText = '';

function esc(s) {{
    if (!s) return '';
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

function sevClass(sev) {{ return 'severity-' + sev.toLowerCase(); }}

function sevBadgeClass(sev) {{ return 'sev-' + sev.toLowerCase(); }}

function sevDot(sev) {{ return '<span class="severity-dot sev-dot-' + sev.toLowerCase() + '"></span>'; }}

function cvssCls(score) {{
    if (score >= 9.0) return 'cvss-critical';
    if (score >= 7.0) return 'cvss-high';
    if (score >= 4.0) return 'cvss-medium';
    return 'cvss-low';
}}

function renderRows(rows) {{
    const tbody = document.getElementById('vuln-tbody');
    if (!tbody) return;
    if (rows.length === 0) {{
        tbody.innerHTML = '<tr><td colspan="' + document.querySelector('thead th').parentNode.children.length + '" style="text-align:center;padding:40px;color:#64748b;">' + {json.dumps(no_data_msg)} + '</td></tr>';
        const badge = document.getElementById('visible-count');
        if (badge) badge.textContent = '0';
        return;
    }}
    tbody.innerHTML = rows.map(r => r._html).join('');
    const badge = document.getElementById('visible-count');
    if (badge) badge.textContent = rows.length;
}}

function buildRows(data) {{
    // _html is already generated server-side
}}

function applyFilter() {{
    filterText = (document.getElementById('search-input')?.value || '').toLowerCase().trim();
    const filtered = ROWS.filter(r => {{
        if (!filterText) return true;
        return (r._search || '').toLowerCase().includes(filterText);
    }});
    if (sortCol >= 0) {{
        filtered.sort((a, b) => {{
            let va, vb;
            if (sortCol === SEV_COL) {{
                va = SEV_IDX[a.severity] ?? 99;
                vb = SEV_IDX[b.severity] ?? 99;
            }} else {{
                const key = SORT_KEYS[sortCol] || '';
                va = (key.startsWith('__num_') ? parseFloat(a[key.slice(6)]) || -1 : (a[key] || '').toString().toLowerCase());
                vb = (key.startsWith('__num_') ? parseFloat(b[key.slice(6)]) || -1 : (b[key] || '').toString().toLowerCase());
            }}
            if (va < vb) return -1 * sortDir;
            if (va > vb) return 1 * sortDir;
            return 0;
        }});
    }}
    renderRows(filtered);
}}

function sortTable(col) {{
    const ths = document.querySelectorAll('th[data-col]');
    ths.forEach(th => th.classList.remove('sort-asc', 'sort-desc'));
    if (sortCol === col) {{ sortDir *= -1; }} else {{ sortCol = col; sortDir = 1; }}
    const activeTh = document.querySelector('th[data-col="' + col + '"]');
    if (activeTh) activeTh.classList.add(sortDir === 1 ? 'sort-asc' : 'sort-desc');
    applyFilter();
}}

function toggleDesc(el) {{ el.classList.toggle('desc-truncated'); }}

function toggleTheme() {{
    const body = document.body;
    const btn = document.querySelector('.theme-toggle');
    body.classList.toggle('dark');
    const isDark = body.classList.contains('dark');
    btn.textContent = isDark ? '☀️' : '🌙';
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
}}

(function() {{
    const saved = localStorage.getItem('theme');
    if (saved !== 'light') {{
        document.body.classList.add('dark');
        const btn = document.querySelector('.theme-toggle');
        if (btn) btn.textContent = '☀️';
    }}
}})();

buildRows(ROWS);
renderRows(ROWS);
function goToTop() {{ window.scrollTo({{top:0,behavior:'smooth'}}); }}
window.addEventListener('scroll',function(){{
    var btn=document.getElementById('goToTopBtn');
    if(btn) btn.style.display=window.scrollY>100?'flex':'none';
}});
</script>
</body>
</html>"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def severity_stats(items):
    counts = {s: 0 for s in SEV_ORDER}
    for item in items:
        sev = item.get("severity", "").upper()
        if sev in counts:
            counts[sev] += 1
    return counts


def build_stat_cards(items, total, extra_cards=None):
    counts = severity_stats(items)
    total_vulns = sum(counts.values())
    cards = ""

    if extra_cards:
        for label, value, icon in extra_cards:
            cards += f"""
        <div class="stat-card">
            <div class="stat-icon">{icon}</div>
            <div class="stat-value">{value}</div>
            <div class="stat-label">{label}</div>
        </div>"""

    cards += f"""
        <div class="stat-card">
            <div class="stat-icon">{SVG_SHIELD}</div>
            <div class="stat-value">{total_vulns}</div>
            <div class="stat-label">Vulnerabilities</div>
        </div>"""
    for sev in SEV_ORDER:
        cnt = counts[sev]
        svg = SVG_MAP[sev]
        cards += f"""
        <div class="stat-card stat-sev-{sev.lower()}">
            <div class="stat-icon">{svg}</div>
            <div class="stat-value">{cnt}</div>
            <div class="stat-label">{sev}</div>
        </div>"""
    return cards, counts


def build_bar(items):
    counts = severity_stats(items)
    total = sum(counts.values())
    segments = ""
    for sev in SEV_ORDER:
        cnt = counts[sev]
        pct = round(cnt / total * 100, 1) if total else 0
        segments += f'<div class="bar-seg sev-{sev.lower()}" style="width:{pct}%"></div>'
    legend = ""
    for sev in SEV_ORDER:
        cnt = counts[sev]
        legend += f'<span class="bar-legend-item"><span class="bar-legend-dot" style="background:{SEV_COLORS[sev]}"></span>{sev.title()} ({cnt})</span>'
    return segments, legend


# ── SBOM / Vulnerability-Report handler ──────────────────────────────────────

def handle_sbom(sbom_path, vuln_path):
    with open(sbom_path) as f: sbom = json.load(f)
    with open(vuln_path) as f: vuln_report = json.load(f)

    components = {f"{c.get('name')}:{c.get('version')}": c
                  for c in sbom.get("components", []) if c.get('name') and c.get('version')}

    vuln_mapping = []
    for match in vuln_report.get("matches", []):
        artifact = match.get("artifact", {})
        vuln = match.get("vulnerability", {})
        name, version = artifact.get("name"), artifact.get("version")
        if f"{name}:{version}" in components:
            vuln_mapping.append({
                "name": name,
                "version": version,
                "vulnerability": vuln.get("id"),
                "severity": vuln.get("severity"),
                "description": vuln.get("description"),
                "fix_version": match.get("matchDetails", [{}])[0].get("fix", {}).get("suggestedVersion", "N/A"),
                "locations": [loc.get("path") for loc in artifact.get("locations", [])]
            })

    counts = severity_stats(vuln_mapping)
    total_vulns = sum(counts.values())

    sev_class_map = {s: f"severity-{s.lower()}" for s in SEV_ORDER}
    sev_dot_map = {s: f'<span class="severity-dot sev-dot-{s.lower()}"></span>' for s in SEV_ORDER}

    rows = []
    for v in vuln_mapping:
        sev = v["severity"].upper() if v["severity"] and v["severity"].upper() in SEV_ORDER else "LOW"
        desc = v["description"] or "No description"
        esc_desc = escape(desc)
        fix = v["fix_version"] if v["fix_version"] and v["fix_version"] != "N/A" else "N/A"
        fix_class = "fix-available" if fix != "N/A" else "fix-none"
        locs = v["locations"] or []
        loc_html = '<div class="chips">' + ''.join(f'<span class="chip">{escape(l)}</span>' for l in locs) + '</div>' if locs else '<span style="color:#94a3b8;">—</span>'
        search_str = f"{v['name']} {v['version']} {v['vulnerability']} {sev} {desc} {fix} {' '.join(locs)}"

        row_html = (
            '<tr>'
            f'<td><strong>{escape(v["name"])}</strong></td>'
            f'<td>{escape(v["version"])}</td>'
            f'<td><span class="vuln-id">{escape(v["vulnerability"])}</span></td>'
            f'<td><span class="severity-badge {sev_class_map[sev]}">{sev_dot_map[sev]}{sev}</span></td>'
            f'<td><div class="desc-text desc-truncated" onclick="toggleDesc(this)">{esc_desc}</div></td>'
            f'<td><span class="fix-badge {fix_class}">{escape(fix)}</span></td>'
            f'<td>{loc_html}</td>'
            '</tr>'
        )

        rows.append({
            "name": v["name"], "version": v["version"], "vuln": v["vulnerability"],
            "severity": sev, "desc": esc_desc, "fix": fix,
            "_html": row_html,
            "_search": search_str,
        })

    rows.sort(key=lambda r: SEV_ORDER.index(r["severity"]) if r["severity"] in SEV_ORDER else 99)

    stat_cards, _ = build_stat_cards(vuln_mapping, 0,
                                      extra_cards=[("Components", len(components), SVG_SHIELD)])
    bar_segments, bar_legend = build_bar(vuln_mapping)
    header_meta = f'<span>{SVG_CALENDAR} {datetime.now().strftime("%Y-%m-%d %H:%M")}</span><span>{SVG_PACKAGE} {len(components)} components scanned</span>'

    th = '<th onclick="sortTable(0)" data-col="0">Package <span class="sort-icon"></span></th><th onclick="sortTable(1)" data-col="1">Version <span class="sort-icon"></span></th><th onclick="sortTable(2)" data-col="2">Vulnerability <span class="sort-icon"></span></th><th onclick="sortTable(3)" data-col="3">Severity <span class="sort-icon"></span></th><th onclick="sortTable(4)" data-col="4">Description <span class="sort-icon"></span></th><th onclick="sortTable(5)" data-col="5">Fix Version <span class="sort-icon"></span></th><th>Locations</th>'

    html = build_html(
        title="SBOM Vulnerability Report",
        subtitle="Software Bill of Materials Security Analysis",
        project_label="🛡️",
        header_meta_rows=header_meta,
        stat_cards=stat_cards,
        bar_segments=bar_segments,
        bar_legend=bar_legend,
        table_headers=th,
        rows_json=json.dumps(rows),
        no_data_msg="No matching vulnerabilities found",
        search_placeholder="Search by package, CVE, description...",
        sort_keys=["name", "version", "vuln", "severity", "desc", "fix"],
        severity_col_idx=3,
    )
    return html


# ── Dependency-Check XML handler ─────────────────────────────────────────────

def handle_depcheck(xml_path):
    NS = "https://jeremylong.github.io/DependencyCheck/dependency-check.4.1.xsd"
    tree = ET.parse(xml_path)
    root = tree.getroot()

    def tag(name):
        return f"{{{NS}}}{name}"

    project = root.find(tag("projectInfo"))
    project_name = project.findtext(tag("name"), "N/A") if project is not None else "N/A"
    report_date = project.findtext(tag("reportDate"), "") if project is not None else ""

    vulnerabilities = []
    for dep_el in root.findall(f".//{tag('dependency')}"):
        fname = dep_el.findtext(tag("fileName"), "unknown")
        for vuln_el in dep_el.findall(f".//{tag('vulnerability')}"):
            name = vuln_el.findtext(tag("name"), "unknown")
            severity = vuln_el.findtext(tag("severity"), "UNKNOWN").upper()
            description = vuln_el.findtext(tag("description"), "")

            cvss_score = None
            for cvss_key in ("cvssV4", "cvssV3", "cvssV2"):
                cvss_el = vuln_el.find(tag(cvss_key))
                if cvss_el is not None:
                    base = cvss_el.findtext(tag("baseScore"))
                    if base:
                        cvss_score = float(base)
                        break

            cwes = [cwe.text for cwe in vuln_el.findall(f".//{tag('cwe')}") if cwe.text]
            refs = []
            for ref_el in vuln_el.findall(f".//{tag('reference')}"):
                url = ref_el.findtext(tag("url"))
                if url:
                    refs.append(url)

            vulnerabilities.append({
                "name": name,
                "severity": severity,
                "cvss_score": cvss_score,
                "fname": fname,
                "description": description,
                "cwes": cwes,
                "refs": refs,
            })

    total_deps = len(root.findall(f".//{tag('dependency')}"))
    counts = severity_stats(vulnerabilities)
    total_vulns = sum(counts.values())

    sev_badge_map = {s: f"sev-{s.lower()}" for s in SEV_ORDER}
    sev_dot_map = {s: f'<span class="severity-dot sev-dot-{s.lower()}"></span>' for s in SEV_ORDER}

    def cvss_class(score):
        if score is not None and score >= 9.0:
            return "cvss-critical"
        if score is not None and score >= 7.0:
            return "cvss-high"
        if score is not None and score >= 4.0:
            return "cvss-medium"
        if score is not None:
            return "cvss-low"
        return ""

    rows = []
    for v in vulnerabilities:
        sev = v["severity"].upper() if v["severity"] and v["severity"].upper() in SEV_ORDER else "LOW"
        cvss = f"{v['cvss_score']:.1f}" if v["cvss_score"] is not None else "—"
        cvss_num = v["cvss_score"] if v["cvss_score"] is not None else -1
        desc = escape(v["description"][:200]) + ("..." if len(v["description"]) > 200 else "")
        cwe_str = ", ".join(escape(c) for c in v["cwes"]) if v["cwes"] else "—"
        refs_str = "".join(
            f'<a href="{escape(r)}" target="_blank" rel="noopener">{escape(r[:60])}...</a><br>' if len(r) > 60
            else f'<a href="{escape(r)}" target="_blank" rel="noopener">{escape(r)}</a><br>'
            for r in v["refs"][:5]
        ) or "—"
        search_str = f"{v['name']} {v['fname']} {sev} {cvss} {cwe_str} {desc} {' '.join(v['refs'])}"
        cvss_cls = cvss_class(v["cvss_score"])

        row_html = (
            '<tr>'
            f'<td><strong>{escape(v["name"])}</strong></td>'
            f'<td>{escape(v["fname"])}</td>'
            f'<td><span class="sev-badge {sev_badge_map[sev]}">{sev_dot_map[sev]}{sev}</span></td>'
            f'<td class="cvss-cell {cvss_cls}">{escape(cvss)}</td>'
            f'<td>{escape(cwe_str)}</td>'
            f'<td><div class="desc-text desc-truncated" onclick="toggleDesc(this)">{desc}</div></td>'
            f'<td class="ref-cell">{refs_str}</td>'
            '</tr>'
        )

        rows.append({
            "name": escape(v["name"]),
            "fname": escape(v["fname"]),
            "severity": sev,
            "cvss": cvss,
            "__num_cvss": cvss_num,
            "cwe": cwe_str,
            "desc": desc,
            "_html": row_html,
            "_search": search_str,
        })

    rows.sort(key=lambda r: SEV_ORDER.index(r["severity"]) if r["severity"] in SEV_ORDER else 99)

    stat_cards, _ = build_stat_cards(vulnerabilities, total_deps,
                                      extra_cards=[("Dependencies", total_deps, SVG_SHIELD)])
    bar_segments, bar_legend = build_bar(vulnerabilities)
    header_meta = f'<span>{SVG_CALENDAR} {escape(report_date)}</span><span>{SVG_PACKAGE} {total_deps} dependencies scanned</span>'

    th = '<th onclick="sortTable(0)" data-col="0">CVE / Name <span class="sort-icon"></span></th><th onclick="sortTable(1)" data-col="1">File Name <span class="sort-icon"></span></th><th onclick="sortTable(2)" data-col="2">Severity <span class="sort-icon"></span></th><th onclick="sortTable(3)" data-col="3">CVSS <span class="sort-icon"></span></th><th onclick="sortTable(4)" data-col="4">CWE <span class="sort-icon"></span></th><th onclick="sortTable(5)" data-col="5">Description <span class="sort-icon"></span></th><th>References</th>'

    html = build_html(
        title=project_name,
        subtitle="OWASP Dependency-Check Report",
        project_label="🔍",
        header_meta_rows=header_meta,
        stat_cards=stat_cards,
        bar_segments=bar_segments,
        bar_legend=bar_legend,
        table_headers=th,
        rows_json=json.dumps(rows),
        no_data_msg="No matching vulnerabilities found",
        search_placeholder="Search by CVE, file, severity, CWE...",
        sort_keys=["name", "fname", "severity", "__num_cvss", "cwe", "desc"],
        severity_col_idx=2,
    )
    return html


# ── Trivy JSON handler ─────────────────────────────────────────────────────────

def handle_trivy(json_path):
    with open(json_path) as f: data = json.load(f)

    results = data.get("Results", [])
    vuln_mapping = []
    target_map = {}

    for result in results:
        target = result.get("Target", "unknown")
        for vuln in result.get("Vulnerabilities", []):
            vuln_mapping.append({
                "name": vuln.get("PkgName", "unknown"),
                "version": vuln.get("InstalledVersion", "unknown"),
                "vulnerability": vuln.get("VulnerabilityID", "unknown"),
                "severity": vuln.get("Severity", "UNKNOWN"),
                "description": vuln.get("Title") or vuln.get("Description") or "No description",
                "fix_version": vuln.get("FixedVersion", "N/A"),
                "locations": [target],
            })
            target_map[vuln.get("PkgName", "unknown")] = target

    counts = severity_stats(vuln_mapping)
    total_vulns = sum(counts.values())
    targets = sorted(set(target_map.values()))

    sev_class_map = {s: f"severity-{s.lower()}" for s in SEV_ORDER}
    sev_dot_map = {s: f'<span class="severity-dot sev-dot-{s.lower()}"></span>' for s in SEV_ORDER}

    rows = []
    for v in vuln_mapping:
        sev = v["severity"].upper() if v["severity"] and v["severity"].upper() in SEV_ORDER else "LOW"
        desc = v["description"] or "No description"
        esc_desc = escape(desc)
        fix = v["fix_version"] if v["fix_version"] and v["fix_version"] != "N/A" else "N/A"
        fix_class = "fix-available" if fix != "N/A" else "fix-none"
        locs = v["locations"] or []
        loc_html = '<div class="chips">' + ''.join(f'<span class="chip">{escape(l)}</span>' for l in locs) + '</div>' if locs else '<span style="color:#94a3b8;">—</span>'
        search_str = f"{v['name']} {v['version']} {v['vulnerability']} {sev} {desc} {fix} {' '.join(locs)}"

        row_html = (
            '<tr>'
            f'<td><strong>{escape(v["name"])}</strong></td>'
            f'<td>{escape(v["version"])}</td>'
            f'<td><span class="vuln-id">{escape(v["vulnerability"])}</span></td>'
            f'<td><span class="severity-badge {sev_class_map[sev]}">{sev_dot_map[sev]}{sev}</span></td>'
            f'<td><div class="desc-text desc-truncated" onclick="toggleDesc(this)">{esc_desc}</div></td>'
            f'<td><span class="fix-badge {fix_class}">{escape(fix)}</span></td>'
            f'<td>{loc_html}</td>'
            '</tr>'
        )

        rows.append({
            "name": v["name"], "version": v["version"], "vuln": v["vulnerability"],
            "severity": sev, "desc": esc_desc, "fix": fix,
            "_html": row_html,
            "_search": search_str,
        })

    rows.sort(key=lambda r: SEV_ORDER.index(r["severity"]) if r["severity"] in SEV_ORDER else 99)

    stat_cards, _ = build_stat_cards(vuln_mapping, 0,
                                      extra_cards=[("Targets", len(targets), SVG_SHIELD)])
    bar_segments, bar_legend = build_bar(vuln_mapping)
    header_meta = f'<span>{SVG_CALENDAR} {datetime.now().strftime("%Y-%m-%d %H:%M")}</span><span>{SVG_PACKAGE} {len(targets)} target(s) scanned</span>'

    th = '<th onclick="sortTable(0)" data-col="0">Package <span class="sort-icon"></span></th><th onclick="sortTable(1)" data-col="1">Version <span class="sort-icon"></span></th><th onclick="sortTable(2)" data-col="2">Vulnerability <span class="sort-icon"></span></th><th onclick="sortTable(3)" data-col="3">Severity <span class="sort-icon"></span></th><th onclick="sortTable(4)" data-col="4">Description <span class="sort-icon"></span></th><th onclick="sortTable(5)" data-col="5">Fix Version <span class="sort-icon"></span></th><th>Target</th>'

    html = build_html(
        title="Trivy Vulnerability Report",
        subtitle="Container Image & Filesystem Security Scan",
        project_label="🔍",
        header_meta_rows=header_meta,
        stat_cards=stat_cards,
        bar_segments=bar_segments,
        bar_legend=bar_legend,
        table_headers=th,
        rows_json=json.dumps(rows),
        no_data_msg="No vulnerabilities found",
        search_placeholder="Search by package, CVE, description...",
        sort_keys=["name", "version", "vuln", "severity", "desc", "fix"],
        severity_col_idx=3,
    )
    return html


# ── Gitleaks / TruffleHog (Secret Leaks) handler ──────────────────────────────

LEAKS_SEV_ORDER = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2}
LEAKS_SEV_COLORS = {'CRITICAL': '#ef4444', 'HIGH': '#f97316', 'MEDIUM': '#eab308'}

def parse_gitleaks(path):
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, ValueError):
        return []
    findings = []
    for item in data:
        findings.append({
            'source': 'gitleaks',
            'file': item.get('File', ''),
            'line': str(item.get('StartLine', item.get('Line', ''))),
            'rule': item.get('RuleID', item.get('rule', '')),
            'description': item.get('Description', ''),
            'secret': item.get('Secret', item.get('secret', '')),
            'match': item.get('Match', item.get('match', '')),
            'commit': item.get('Commit', ''),
            'author': item.get('Author', ''),
            'email': item.get('Email', ''),
            'date': item.get('Date', ''),
            'tags': item.get('Tags', item.get('tags', [])),
            'entropy': item.get('Entropy', item.get('entropy', '')),
            'fingerprint': item.get('Fingerprint', ''),
        })
    return findings

def parse_trufflehog(path):
    findings = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            meta = item.get('SourceMetadata', {}).get('Data', {})
            git = meta.get('Git', {}) or {}
            fs = meta.get('Filesystem', {}) or {}
            findings.append({
                'source': 'trufflehog',
                'file': git.get('file', fs.get('path', '')),
                'line': git.get('line', fs.get('line', '')),
                'rule': item.get('DetectorName', ''),
                'description': item.get('DetectorDescription', ''),
                'secret': item.get('Redacted', item.get('Raw', '')),
                'match': '',
                'commit': git.get('commit', ''),
                'author': git.get('author', ''),
                'email': git.get('email', ''),
                'date': git.get('timestamp', ''),
                'tags': [],
                'entropy': '',
                'verified': item.get('Verified', False),
                'fingerprint': item.get('Fingerprint', ''),
            })
    return findings

def _leaks_severity(secret, verified, tags):
    if verified:
        return 'CRITICAL'
    if secret and len(secret) > 10:
        return 'HIGH'
    return 'MEDIUM'

def handle_leaks(paths):
    all_findings = []
    sources = set()
    for path in paths:
        fname = path.lower()
        if 'gitleaks' in fname:
            findings = parse_gitleaks(path)
        elif 'trufflehog' in fname:
            findings = parse_trufflehog(path)
        else:
            with open(path) as f:
                peek = f.read(1024).strip()
            if peek.startswith('['):
                findings = parse_gitleaks(path)
            elif peek.startswith('{'):
                findings = parse_trufflehog(path)
            else:
                print(f"  Skipping {path}: unrecognized format", file=sys.stderr)
                continue
        all_findings.extend(findings)
        for f in findings:
            sources.add(f['source'])

    source_label = ' + '.join(sorted(sources)).title() if sources else 'None'
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0}
    rows_html = []
    for f in all_findings:
        sev = _leaks_severity(f.get('secret', ''), f.get('verified', False), f.get('tags', []))
        counts[sev] = counts.get(sev, 0) + 1
        sc = LEAKS_SEV_COLORS.get(sev, '#94a3b8')
        rows_html.append(f"""
        <tr>
            <td data-sort="{f['file'].lower()}"><span class="file-cell">{escape(f['file'])}</span></td>
            <td data-sort="{int(f['line'] or 0)}">{escape(str(f['line']))}</td>
            <td data-sort="{sev}"><span class="sev-badge" style="background:{sc}18;color:{sc}">{sev}</span></td>
            <td data-sort="{f['rule'].lower()}">{escape(f['rule'])}</td>
            <td data-sort="{(f.get('verified', False) or '')}">{'<span class="verified">Verified</span>' if f.get('verified') else '<span class="unverified">Unverified</span>' if f.get('source') == 'trufflehog' else '-'}</td>
            <td data-sort="{escape(f['description'].lower())}" class="desc-cell"><span class="desc-text">{escape(f['description'] or '-')}</span></td>
            <td data-sort="{escape(f['secret'].lower())}" class="secret-cell"><code class="secret-text">{escape(f['secret'] or '-')}</code></td>
            <td data-sort="{escape(f.get('commit', '') or '')}"><code class="commit-hash">{escape((f.get('commit', '') or '')[:12])}</code></td>
            <td data-sort="{escape(f.get('date', '') or '')}">{escape((f.get('date', '') or '')[:10])}</td>
        </tr>""")

    total = len(all_findings)
    subtitle = f"Generated from {len(paths)} file(s) — {total} finding(s)"
    svg_pattern = (
        'url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' '
        'viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg '
        'fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%23ffffff\' '
        'fill-opacity=\'0.05\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4'
        'zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 '
        '4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")'
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Secret Leaks Report</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Inter','Segoe UI',system-ui,sans-serif; background:#f8fafc; color:#1e293b; line-height:1.6; transition:background .3s,color .3s; }}
body.dark {{ background:#0f172a; color:#e2e8f0; }}
header {{ background:linear-gradient(135deg,#ef4444 0%,#dc2626 50%,#b91c1c 100%); color:white; padding:2rem 0; position:relative; overflow:hidden; }}
header::before {{ content:''; position:absolute; inset:0; background:{svg_pattern}; opacity:0.4; }}
.header-content {{ max-width:1200px; margin:0 auto; padding:0 24px; display:flex; justify-content:space-between; align-items:center; position:relative; z-index:1; flex-wrap:wrap; gap:16px; }}
.logo h1 {{ font-size:1.5rem; font-weight:700; letter-spacing:-0.02em; }}
.logo p {{ font-size:0.85rem; opacity:0.85; margin-top:2px; }}
.header-meta {{ text-align:right; font-size:0.82rem; opacity:0.9; line-height:1.8; }}
.header-meta span {{ display:block; }}
.theme-toggle {{ position:fixed; top:20px; right:20px; z-index:100; background:rgba(0,0,0,0.12); backdrop-filter:blur(8px); border:none; color:#334155; width:44px; height:44px; border-radius:12px; cursor:pointer; font-size:1.3rem; display:flex; align-items:center; justify-content:center; transition:background .2s,color .2s; }}
.theme-toggle:hover {{ background:rgba(0,0,0,0.22); }}
body.dark .theme-toggle {{ background:rgba(255,255,255,0.2); color:#fff; }}
body.dark .theme-toggle:hover {{ background:rgba(255,255,255,0.35); }}
.gototop {{ position:fixed; bottom:20px; right:20px; z-index:100; background:rgba(0,0,0,0.12); backdrop-filter:blur(8px); border:none; color:#334155; width:44px; height:44px; border-radius:12px; cursor:pointer; font-size:1.3rem; display:none; align-items:center; justify-content:center; transition:background .2s,color .2s,opacity .3s; opacity:0.7; }}
.gototop:hover {{ background:rgba(0,0,0,0.22); opacity:1; }}
body.dark .gototop {{ background:rgba(255,255,255,0.2); color:#fff; }}
body.dark .gototop:hover {{ background:rgba(255,255,255,0.35); }}
.container {{ max-width:1200px; margin:0 auto; padding:24px; }}
.summary {{ display:flex; flex-wrap:wrap; gap:12px; margin-bottom:24px; }}
.summary-card {{ flex:1; min-width:120px; background:#fff; border-radius:10px; padding:20px 16px; text-align:center; border:1px solid #e2e8f0; transition:background .3s,border-color .3s; }}
body.dark .summary-card {{ background:#1e293b; border-color:#334155; }}
.summary-card .num {{ font-size:1.75rem; font-weight:700; line-height:1.2; }}
.summary-card .lbl {{ font-size:0.72rem; color:#64748b; margin-top:6px; text-transform:uppercase; letter-spacing:0.04em; }}
body.dark .summary-card .lbl {{ color:#94a3b8; }}
.section {{ background:#fff; border-radius:10px; padding:20px 24px; margin-bottom:20px; border:1px solid #e2e8f0; transition:background .3s,border-color .3s; }}
body.dark .section {{ background:#1e293b; border-color:#334155; }}
.section h2 {{ margin:0 0 14px; font-size:0.95rem; font-weight:600; color:#334155; padding-bottom:10px; border-bottom:2px solid #ef4444; display:flex; align-items:center; gap:8px; }}
body.dark .section h2 {{ color:#e2e8f0; }}
table {{ width:100%; border-collapse:collapse; font-size:0.78rem; }}
th {{ background:#f1f5f9; padding:10px 10px; text-align:left; font-weight:600; color:#64748b; text-transform:uppercase; letter-spacing:0.03em; font-size:0.68rem; cursor:pointer; user-select:none; white-space:nowrap; }}
th:hover {{ color:#1e293b; background:#e2e8f0; }}
body.dark th {{ background:#0f172a; color:#94a3b8; }}
body.dark th:hover {{ color:#e2e8f0; background:#1e293b; }}
td {{ padding:10px 10px; border-bottom:1px solid #e2e8f0; color:#475569; vertical-align:top; }}
body.dark td {{ border-bottom-color:#334155; color:#cbd5e1; }}
tr:hover td {{ background:#f1f5f9; }}
body.dark tr:hover td {{ background:#0f172a40; }}
.srt {{ font-size:0.6rem; margin-left:3px; color:#ef4444; }}
.file-cell {{ color:#6366f1; font-family:'SF Mono','Fira Code',monospace; font-size:0.72rem; word-break:break-all; }}
body.dark .file-cell {{ color:#818cf8; }}
.sev-badge {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:0.65rem; font-weight:700; text-transform:uppercase; }}
.verified {{ color:#22c55e; font-size:0.65rem; font-weight:600; text-transform:uppercase; }}
.unverified {{ color:#94a3b8; font-size:0.65rem; font-weight:600; text-transform:uppercase; }}
.secret-cell {{ max-width:200px; }}
.secret-text {{ font-family:'SF Mono','Fira Code',monospace; font-size:0.7rem; background:#fef2f2; color:#dc2626; padding:1px 6px; border-radius:3px; word-break:break-all; display:inline-block; max-width:100%; }}
body.dark .secret-text {{ background:#450a0a; color:#fca5a5; }}
.commit-hash {{ font-family:'SF Mono','Fira Code',monospace; font-size:0.7rem; color:#64748b; background:#f1f5f9; padding:1px 5px; border-radius:3px; }}
body.dark .commit-hash {{ color:#94a3b8; background:#1e293b; }}
.desc-cell {{ max-width:250px; }}
.desc-text {{ display:inline-block; max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; cursor:pointer; }}
.desc-text:hover {{ white-space:normal; }}
.empty {{ color:#64748b; font-style:italic; font-size:0.85rem; padding:12px 0; }}
.search-box {{ width:100%; padding:10px 14px; border:1px solid #e2e8f0; border-radius:8px; font-size:0.82rem; background:#fff; color:#1e293b; margin-bottom:16px; outline:none; }}
.search-box:focus {{ border-color:#ef4444; box-shadow:0 0 0 3px rgba(239,68,68,0.1); }}
body.dark .search-box {{ background:#0f172a; border-color:#334155; color:#e2e8f0; }}
footer {{ background:#1e293b; padding:20px 0; text-align:center; margin-top:20px; border-top:1px solid #334155; }}
.footer-content {{ font-size:0.72rem; color:#94a3b8; }}
.tag {{ display:inline-block; padding:1px 6px; border-radius:3px; font-size:0.6rem; font-weight:600; background:#e0e7ff; color:#4338ca; margin:1px; }}
body.dark .tag {{ background:#312e81; color:#a5b4fc; }}
@media(max-width:768px) {{
    th, td {{ padding:8px 6px; font-size:0.72rem; }}
    .secret-cell, .desc-cell {{ max-width:120px; }}
    .header-content {{ flex-direction:column; text-align:center; }}
    .header-meta {{ text-align:center; }}
    .theme-toggle {{ top:12px; right:12px; width:38px; height:38px; font-size:1.1rem; }}
}}
</style>
</head>
<body class="dark">
<button class="theme-toggle" onclick="toggleTheme()" title="Toggle dark/light mode" aria-label="Toggle dark/light mode">☀️</button>
<button class="gototop" onclick="goToTop()" title="Go to top" id="goToTopBtn"><svg width="22" height="22" viewBox="0 0 512 512"><path d="M256 8C119 8 8 119 8 256s111 248 248 248 248-111 248-248S393 8 256 8z" fill="none" stroke="#60bb47" stroke-width="24"/><polygon points="132.9 277.9 173.6 318.6 256 236.1 338.4 318.6 379.1 277.9 256 154.8" fill="#60bb47"/></svg></button>
<header>
<div class="header-content">
    <div class="logo">
        <h1>&#128274; Secret Leaks Report</h1>
        <p>{escape(subtitle)}</p>
    </div>
    <div class="header-meta">
        <span>Source: <strong>{source_label}</strong></span>
        <span>Findings: <strong>{total}</strong></span>
        <span>Generated: {now}</span>
    </div>
</div>
</header>
<main class="container">
<div class="summary">
    <div class="summary-card">
        <div class="num" style="color:#ef4444">{counts.get('CRITICAL', 0)}</div>
        <div class="lbl">Critical</div>
    </div>
    <div class="summary-card">
        <div class="num" style="color:#f97316">{counts.get('HIGH', 0)}</div>
        <div class="lbl">High</div>
    </div>
    <div class="summary-card">
        <div class="num" style="color:#eab308">{counts.get('MEDIUM', 0)}</div>
        <div class="lbl">Medium</div>
    </div>
    <div class="summary-card">
        <div class="num" style="color:#6366f1">{total}</div>
        <div class="lbl">Total</div>
    </div>
</div>
<div class="section">
    <h2>&#128270; Findings</h2>
    <input class="search-box" type="text" id="searchInput" onkeyup="applyFilter()" placeholder="Search by file, rule, description, secret...">
    <div style="overflow-x:auto;">
    <table class="sortable" id="findings-table">
        <thead>
            <tr>
                <th onclick="sortTable(this,0)">File <span class="srt"></span></th>
                <th onclick="sortTable(this,1)">Line <span class="srt"></span></th>
                <th onclick="sortTable(this,2)">Severity <span class="srt"></span></th>
                <th onclick="sortTable(this,3)">Rule <span class="srt"></span></th>
                <th onclick="sortTable(this,4)">Status <span class="srt"></span></th>
                <th onclick="sortTable(this,5)">Description <span class="srt"></span></th>
                <th onclick="sortTable(this,6)">Secret <span class="srt"></span></th>
                <th onclick="sortTable(this,7)">Commit <span class="srt"></span></th>
                <th onclick="sortTable(this,8)">Date <span class="srt"></span></th>
            </tr>
        </thead>
        <tbody>{"".join(rows_html) if rows_html else '<tr><td colspan="9" class="empty" style="text-align:center;padding:40px;">No secrets found.</td></tr>'}</tbody>
    </table>
    </div>
</div>
</main>
<footer>
<div class="container">
    <div class="footer-content">
        Generated by Security Pipelines CI/CD &mdash; This is an automated report.
    </div>
</div>
</footer>
<script>
function sortTable(th, col) {{
    var table = th.closest('table.sortable');
    var tbody = table.querySelector('tbody');
    var rows = Array.from(tbody.querySelectorAll('tr'));
    var asc = th.classList.contains('asc');
    table.querySelectorAll('th').forEach(function(h) {{ h.classList.remove('asc', 'desc'); h.querySelector('.srt').textContent = ''; }});
    th.classList.add(asc ? 'desc' : 'asc');
    var dir = asc ? -1 : 1;
    rows.sort(function(a, b) {{
        var va = (a.cells[col] && (a.cells[col].getAttribute('data-sort') || a.cells[col].textContent.trim())) || '';
        var vb = (b.cells[col] && (b.cells[col].getAttribute('data-sort') || b.cells[col].textContent.trim())) || '';
        var na = parseFloat(va), nb = parseFloat(vb);
        if (!isNaN(na) && !isNaN(nb)) return (na - nb) * dir;
        return va.localeCompare(vb) * dir;
    }});
    rows.forEach(function(r) {{ tbody.appendChild(r); }});
    th.querySelector('.srt').textContent = asc ? ' \\u25B2' : ' \\u25BC';
}}
function toggleTheme() {{
    var body = document.body;
    var btn = document.querySelector('.theme-toggle');
    body.classList.toggle('dark');
    var isDark = body.classList.contains('dark');
    btn.textContent = isDark ? '\\u2600\\uFE0F' : '\\uD83C\\uDF19';
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
}}
(function() {{
    var saved = localStorage.getItem('theme');
    if (saved !== 'light') {{
        document.body.classList.add('dark');
        var btn = document.querySelector('.theme-toggle');
        if (btn) btn.textContent = '\\u2600\\uFE0F';
    }}
}})();
function applyFilter() {{
    var q = document.getElementById('searchInput').value.toLowerCase();
    var rows = document.querySelectorAll('#findings-table tbody tr');
    rows.forEach(function(r) {{
        r.style.display = r.textContent.toLowerCase().includes(q) ? '' : 'none';
    }});
}}
function goToTop() {{ window.scrollTo({{top:0,behavior:'smooth'}}); }}
window.addEventListener('scroll',function(){{
    var btn=document.getElementById('goToTopBtn');
    if(btn) btn.style.display=window.scrollY>100?'flex':'none';
}});
</script>
</body>
</html>"""
    return html


def parse_float(s):
    try:
        return float(s)
    except (ValueError, TypeError):
        return float('nan')


def isNaN(v):
    return v != v


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if len(args) == 0:
        if Path("sbom.json").exists() and Path("vuln-report.json").exists():
            html = handle_sbom("sbom.json", "vuln-report.json")
            Path("vuln-report.html").write_text(html, encoding="utf-8")
            print("Report generated: vuln-report.html")
        elif Path("trivy-image-report.json").exists():
            html = handle_trivy("trivy-image-report.json")
            Path("trivy-report.html").write_text(html, encoding="utf-8")
            print("Report generated: trivy-report.html")
        else:
            print("""Usage:
  python3 report.py                                    # tries sbom.json + vuln-report.json
  python3 report.py trivy-image-report.json
  python3 report.py dependency-check.xml
  python3 report.py dependency-check.xml output.html
  python3 report.py gitleaks-report.json               # gitleaks leaks report
  python3 report.py trufflehog-report.json             # trufflehog leaks report""", file=sys.stderr)
            sys.exit(1)
    elif len(args) == 1:
        path = args[0]
        if path.endswith(".xml"):
            html = handle_depcheck(path)
            out = "dependency-check-report.html"
            Path(out).write_text(html, encoding="utf-8")
            print(f"Report generated: {out}")
        elif path.endswith(".json"):
            p = Path(path)

            # Auto-detect format by peeking at JSON structure
            try:
                with open(p) as f:
                    peek = json.load(f)
                is_trivy = isinstance(peek, dict) and "Results" in peek
                is_grype = isinstance(peek, dict) and "matches" in peek
                is_gitleaks = isinstance(peek, list) and len(peek) > 0 and "RuleID" in peek[0]
                is_trufflehog = isinstance(peek, dict) and "DetectorName" in peek
            except Exception:
                is_trivy = is_grype = is_gitleaks = is_trufflehog = False
                try:
                    with open(p) as f:
                        first = f.readline().strip()
                    if first.startswith('{') and 'DetectorName' in first:
                        is_trufflehog = True
                    elif not first:
                        # Empty file — could be a gitleaks/trufflehog report with zero findings
                        stem = p.stem.lower()
                        if 'gitleaks' in stem:
                            is_gitleaks = True
                        elif 'trufflehog' in stem:
                            is_trufflehog = True
                except Exception:
                    pass
            else:
                pass

            if is_trufflehog:
                html = handle_leaks([path])
                out = "leaks-report.html"
            elif is_trivy:
                html = handle_trivy(path)
                out = "trivy-report.html"
            elif is_grype:
                companion = path.replace("vuln", "sbom").replace("Vuln", "Sbom")
                sbom_candidates = [companion, "sbom.json"]
                found = next((c for c in sbom_candidates if Path(c).exists()), None)
                if not found:
                    print(f"SBOM file not found for grype report. Tried: {sbom_candidates}", file=sys.stderr)
                    sys.exit(1)
                html = handle_sbom(found, path)
                out = "vuln-report.html"
            elif is_gitleaks:
                html = handle_leaks([path])
                out = "leaks-report.html"
            else:
                is_trufflehog = False

            if is_trufflehog:
                html = handle_leaks([path])
                out = "leaks-report.html"
            elif is_trivy:
                html = handle_trivy(path)
                out = "trivy-report.html"
            elif is_grype:
                companion = path.replace("vuln", "sbom").replace("Vuln", "Sbom")
                sbom_candidates = [companion, "sbom.json"]
                found = next((c for c in sbom_candidates if Path(c).exists()), None)
                if not found:
                    print(f"SBOM file not found for grype report. Tried: {sbom_candidates}", file=sys.stderr)
                    sys.exit(1)
                html = handle_sbom(found, path)
                out = "vuln-report.html"
            elif is_gitleaks:
                html = handle_leaks([path])
                out = "leaks-report.html"
            else:
                dir_ = p.parent
                stem = p.stem

                if "vuln" in stem.lower():
                    vuln_path = p
                    sbom_path = dir_ / "sbom.json"
                    if not sbom_path.exists():
                        candidate = stem.replace("vuln", "sbom").replace("Vuln", "Sbom")
                        sbom_path = dir_ / f"{candidate}.json"
                else:
                    sbom_path = p
                    candidate = stem + "-vuln-report"
                    vuln_path = dir_ / "vuln-report.json"
                    if not vuln_path.exists():
                        vuln_path = dir_ / f"{stem}-vuln-report.json"

                if not sbom_path.exists() or not vuln_path.exists():
                    print(f"Could not find SBOM & vuln-report JSON files. Tried:\n  {sbom_path}\n  {vuln_path}", file=sys.stderr)
                    sys.exit(1)
                html = handle_sbom(sbom_path, vuln_path)
                out = "vuln-report.html"
            Path(out).write_text(html, encoding="utf-8")
            print(f"Report generated: {out}")
        else:
            print(f"Unrecognized file type: {path}", file=sys.stderr)
            sys.exit(1)
    elif len(args) >= 2:
        if args[0].endswith(".xml"):
            html = handle_depcheck(args[0])
            out = args[1] if len(args) > 1 else "dependency-check-report.html"
        elif args[0].endswith(".json"):
            # Determine if second arg is output path or another input
            is_output = args[1].endswith(".html") or args[1].endswith(".htm")
            in_path = Path(args[0])

            # Auto-detect format by peeking at JSON structure
            try:
                with open(in_path) as f:
                    peek = json.load(f)
                is_trivy = isinstance(peek, dict) and "Results" in peek
                is_grype = isinstance(peek, dict) and "matches" in peek
                is_gitleaks = isinstance(peek, list) and len(peek) > 0 and "RuleID" in peek[0]
                is_trufflehog = isinstance(peek, dict) and "DetectorName" in peek
            except Exception:
                is_trivy = is_grype = is_gitleaks = is_trufflehog = False
                try:
                    with open(in_path) as f:
                        first = f.readline().strip()
                    if first.startswith('{') and 'DetectorName' in first:
                        is_trufflehog = True
                    elif not first:
                        stem = in_path.stem.lower()
                        if 'gitleaks' in stem:
                            is_gitleaks = True
                        elif 'trufflehog' in stem:
                            is_trufflehog = True
                except Exception:
                    pass
            else:
                pass

            if is_trufflehog:
                out = args[1] if is_output else (args[2] if len(args) > 2 else "leaks-report.html")
                html = handle_leaks(args[:1] if is_output else args[:2])
                Path(out).write_text(html, encoding="utf-8")
                print(f"Report generated: {out}")
                return
            elif is_trivy:
                html = handle_trivy(args[0])
                out = args[1] if is_output else (args[2] if len(args) > 2 else "trivy-report.html")
            elif is_grype:
                if is_output:
                    vuln_path = args[0]
                    companion = Path(vuln_path).stem.replace("vulnerability", "sbom").replace("Vulnerability", "Sbom").replace("vuln", "sbom").replace("Vuln", "Sbom")
                    sbom_path = Path(vuln_path).parent / f"{companion}.json"
                    if not sbom_path.exists():
                        sbom_path = Path(vuln_path).parent / "sbom.json"
                    if not sbom_path.exists():
                        print(f"Could not find SBOM file for grype report. Tried:\n  {sbom_path}", file=sys.stderr)
                        sys.exit(1)
                    html = handle_sbom(str(sbom_path), vuln_path)
                    out = args[1]
                else:
                    html = handle_sbom(args[0], args[1])
                    out = args[2] if len(args) > 2 else "vuln-report.html"
            elif is_gitleaks:
                if is_output:
                    html = handle_leaks([args[0]])
                    out = args[1]
                else:
                    html = handle_leaks(args[:2])
                    out = args[2] if len(args) > 2 else "leaks-report.html"
            else:
                if is_output:
                    sbom_path = args[0]
                    candidate = Path(sbom_path).stem + "-vuln-report"
                    vuln_path = Path(sbom_path).parent / f"{candidate}.json"
                    if not vuln_path.exists():
                        vuln_path = Path(sbom_path).parent / "vuln-report.json"
                    if not vuln_path.exists():
                        print(f"Could not find vuln-report JSON. Tried:\n  {vuln_path}", file=sys.stderr)
                        sys.exit(1)
                    html = handle_sbom(args[0], str(vuln_path))
                    out = args[1]
                else:
                    html = handle_sbom(args[0], args[1])
                    out = args[2] if len(args) > 2 else "vuln-report.html"
        else:
            print(f"Unrecognized file type: {args[0]}", file=sys.stderr)
            sys.exit(1)
        Path(out).write_text(html, encoding="utf-8")
        print(f"Report generated: {out}")


if __name__ == "__main__":
    main()
