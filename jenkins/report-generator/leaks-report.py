#!/usr/bin/env python3
import sys
import json
import argparse
from datetime import datetime
from html import escape

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

def auto_parse(path):
    with open(path) as f:
        first = f.read(1024)
    fname = path.lower()
    if 'gitleaks' in fname:
        return parse_gitleaks(path)
    if 'trufflehog' in fname:
        return parse_trufflehog(path)
    first = first.strip()
    if first.startswith('['):
        return parse_gitleaks(path)
    if first.startswith('{'):
        return parse_trufflehog(path)
    sys.exit(f"Error: cannot auto-detect report format for {path}")

def severity(secret, verified, tags):
    if verified:
        return 'CRITICAL'
    if secret and len(secret) > 10:
        return 'HIGH'
    return 'MEDIUM'

SEV_ORDER = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2}
SEV_COLORS = {'CRITICAL': '#ef4444', 'HIGH': '#f97316', 'MEDIUM': '#eab308'}

def generate_html(findings, title, subtitle):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    rows = []
    counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0}
    sources = set()
    for f in findings:
        sev = severity(f.get('secret', ''), f.get('verified', False), f.get('tags', []))
        counts[sev] = counts.get(sev, 0) + 1
        sources.add(f.get('source', 'unknown'))
        sc = SEV_COLORS.get(sev, '#94a3b8')
        rows.append(f"""
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

    table_rows = '\n'.join(rows)
    source_label = ' + '.join(sorted(sources)).title()
    total = len(findings)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(title)}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Inter','Segoe UI',system-ui,sans-serif; background:#f8fafc; color:#1e293b; line-height:1.6; transition:background .3s,color .3s; }}
body.dark {{ background:#0f172a; color:#e2e8f0; }}
header {{ background:linear-gradient(135deg,#ef4444 0%,#dc2626 50%,#b91c1c 100%); color:white; padding:2rem 0; position:relative; overflow:hidden; }}
.header-content {{ max-width:1200px; margin:0 auto; padding:0 24px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; }}
.logo h1 {{ font-size:1.5rem; font-weight:700; letter-spacing:-0.02em; }}
.logo p {{ font-size:0.85rem; opacity:0.85; margin-top:2px; }}
.header-meta {{ text-align:right; font-size:0.82rem; opacity:0.9; line-height:1.8; }}
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
.summary-card {{ flex:1; min-width:120px; background:#fff; border-radius:10px; padding:20px 16px; text-align:center; border:1px solid #e2e8f0; }}
body.dark .summary-card {{ background:#1e293b; border-color:#334155; }}
.summary-card .num {{ font-size:1.75rem; font-weight:700; line-height:1.2; }}
.summary-card .lbl {{ font-size:0.72rem; color:#64748b; margin-top:6px; text-transform:uppercase; letter-spacing:0.04em; }}
body.dark .summary-card .lbl {{ color:#94a3b8; }}
.section {{ background:#fff; border-radius:10px; padding:20px 24px; margin-bottom:20px; border:1px solid #e2e8f0; }}
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
.footer {{ text-align:center; padding:20px; font-size:0.72rem; color:#94a3b8; }}
body.dark .footer {{ color:#475569; }}
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
        <h1>&#128274; {escape(title)}</h1>
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
        <tbody>{table_rows if table_rows else '<tr><td colspan="9" class="empty" style="text-align:center;padding:40px;">No secrets found.</td></tr>'}</tbody>
    </table>
    </div>
</div>
</main>
<div class="footer">
    Generated by Security Pipelines CI/CD &mdash; This is an automated report.
</div>
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

def main():
    parser = argparse.ArgumentParser(description='Convert gitleaks/trufflehog JSON reports to HTML')
    parser.add_argument('input', nargs='+', help='Path(s) to gitleaks JSON or trufflehog JSONL report')
    parser.add_argument('--output', '-o', default='leaks-report.html', help='Output HTML file (default: leaks-report.html)')
    parser.add_argument('--title', default='Secret Leaks Report', help='Report title')
    args = parser.parse_args()

    all_findings = []
    for path in args.input:
        print(f"Parsing {path}...")
        findings = auto_parse(path)
        print(f"  Found {len(findings)} finding(s)")
        all_findings.extend(findings)

    if not all_findings:
        print("No findings found. Generating empty report.")

    subtitle = f"Generated from {len(args.input)} file(s) — {len(all_findings)} total finding(s)"
    html = generate_html(all_findings, args.title, subtitle)

    with open(args.output, 'w') as f:
        f.write(html)
    print(f"Report written to {args.output}")

if __name__ == '__main__':
    main()
