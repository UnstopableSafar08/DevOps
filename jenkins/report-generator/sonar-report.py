#!/usr/bin/env python3
import sys
import json
import argparse
import urllib.request
import urllib.parse
from datetime import datetime
from html import escape

def fetch(url, token):
    req = urllib.request.Request(url)
    if token:
        import base64
        creds = base64.b64encode(f"{token}:".encode()).decode()
        req.add_header('Authorization', f'Basic {creds}')
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def get_metrics(base_url, project, token):
    metrics = 'bugs,vulnerabilities,code_smells,coverage,duplicated_lines_density,ncloc,security_hotspots,reliability_rating,security_rating,sqale_rating'
    url = f"{base_url}/api/measures/component?component={project}&metricKeys={metrics}"
    data = fetch(url, token)
    result = {}
    for m in data['component']['measures']:
        result[m['metric']] = m.get('value', 'N/A')
    return result

def get_issues(base_url, project, token, issue_type, severity=None):
    params = f"componentKeys={project}&types={issue_type}&ps=50&resolved=false"
    if severity:
        params += f"&severities={severity}"
    url = f"{base_url}/api/issues/search?{params}"
    data = fetch(url, token)
    return data.get('issues', [])

def get_hotspots(base_url, project, token):
    url = f"{base_url}/api/hotspots/search?projectKey={project}&ps=50"
    try:
        data = fetch(url, token)
        return data.get('hotspots', [])
    except:
        return []

def rating_label(val):
    return {'1': 'A', '2': 'B', '3': 'C', '4': 'D', '5': 'E'}.get(str(int(float(val))) if val != 'N/A' else 'N/A', 'N/A')

def rating_color(val):
    return {'A': '#00aa00', 'B': '#b0d400', 'C': '#f4a000', 'D': '#e00', 'E': '#900'}.get(rating_label(val), '#aaa')

def issues_table(issues):
    sev_colors = {
        'BLOCKER': '#dc2626', 'CRITICAL': '#ef4444',
        'MAJOR': '#f59e0b', 'MINOR': '#64748b', 'INFO': '#94a3b8',
    }
    sev_order = {'BLOCKER': 0, 'CRITICAL': 1, 'MAJOR': 2, 'MINOR': 3, 'INFO': 4}
    rows = ''
    for i in sorted(issues, key=lambda x: sev_order.get(x.get('severity', 'MAJOR'), 5)):
        sev = i.get('severity', 'MAJOR')
        sc = sev_colors.get(sev, '#94a3b8')
        comp = escape(str(i.get('component', '')).split(':')[-1])
        msg = escape(str(i.get('message', '')))
        line = str(i.get('line', ''))
        rows += f"""
        <tr>
            <td class="file-col" data-sort="{comp.lower()}">{comp}</td>
            <td data-sort="{sev_order.get(sev, 5)}"><span class="sev-label" style="background:{sc}20;color:{sc}">{sev}</span></td>
            <td data-sort="{msg.lower()}" class="msg-cell"><span class="msg-text">{msg}</span></td>
            <td data-sort="{line}" class="line-cell">{line}</td>
        </tr>"""
    return f"""
    <table class="sortable">
        <thead><tr><th onclick="sortTable(this,0)">File <span class="srt"></span></th><th onclick="sortTable(this,1)">Severity <span class="srt"></span></th><th onclick="sortTable(this,2)">Message <span class="srt"></span></th><th onclick="sortTable(this,3)">Line <span class="srt"></span></th></tr></thead>
        <tbody>{rows}</tbody>
    </table>"""

def generate_html(project, base_url, metrics, bugs, vulns, smells, hotspots):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    dashboard_url = f"{base_url}/dashboard?id={project}"

    r_rel   = rating_label(metrics.get('reliability_rating', 'N/A'))
    r_sec   = rating_label(metrics.get('security_rating', 'N/A'))
    r_maint = rating_label(metrics.get('sqale_rating', 'N/A'))

    bugs_count = len(bugs)
    vulns_count = len(vulns)
    smells_count = len(smells)
    hotspots_count = len(hotspots)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SonarQube Report - {project}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Inter', system-ui, -apple-system, sans-serif; background: #f8fafc; color: #1e293b; transition: background .3s, color .3s; }}
  body.dark {{ background: #0f172a; color: #e2e8f0; }}
  .header {{ background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%); padding: 32px 32px 28px; }}
  body.dark .header {{ background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #3730a3 100%); }}
  .header-inner {{ max-width: 1100px; margin: 0 auto; }}
  .header h1 {{ font-size: 1.5rem; font-weight: 700; color: #e0e7ff; letter-spacing: -0.02em; }}
  .header .sub {{ margin-top: 4px; font-size: 0.85rem; color: #c7d2fe; }}
  .header .sub strong {{ color: #e0e7ff; }}
  .btn {{ display: inline-block; margin-top: 14px; padding: 10px 24px;
          background: #4f46e5; color: #fff; border-radius: 6px;
          text-decoration: none; font-size: 0.85rem; font-weight: 600; }}
  .btn:hover {{ background: #4338ca; }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 24px 16px; }}
  .cards {{ display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 24px; }}
  .card {{ background: #ffffff; border-radius: 10px; padding: 20px 16px;
           flex: 1; min-width: 130px; text-align: center;
           border: 1px solid #e2e8f0; }}
  body.dark .card {{ background: #1e293b; border-color: #334155; }}
  .card .val {{ font-size: 1.75rem; font-weight: 700; line-height: 1.2; }}
  .card .lbl {{ font-size: 0.72rem; color: #64748b; margin-top: 6px; text-transform: uppercase; letter-spacing: 0.04em; }}
  body.dark .card .lbl {{ color: #94a3b8; }}
  .rating {{ display: inline-flex; align-items: center; justify-content: center;
             width: 38px; height: 38px; border-radius: 50%;
             font-size: 1rem; font-weight: 700; color: #fff; }}
  .section {{ background: #ffffff; border-radius: 10px; padding: 20px 24px;
              margin-bottom: 20px; border: 1px solid #e2e8f0; }}
  body.dark .section {{ background: #1e293b; border-color: #334155; }}
  .section h2 {{ margin: 0 0 14px; font-size: 0.95rem; font-weight: 600; color: #334155;
                 padding-bottom: 10px; border-bottom: 2px solid #4f46e5;
                 display: flex; align-items: center; gap: 8px; }}
  body.dark .section h2 {{ color: #e2e8f0; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.8rem; }}
  th {{ background: #f1f5f9; padding: 10px 12px; text-align: left; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.03em; font-size: 0.72rem; cursor: pointer; user-select: none; }}
  th:hover {{ color: #1e293b; background: #e2e8f0; }}
  body.dark th {{ background: #0f172a; color: #94a3b8; }}
  body.dark th:hover {{ color: #e2e8f0; background: #1e293b; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #e2e8f0; color: #475569; word-break: break-word; }}
  body.dark td {{ border-bottom-color: #334155; color: #cbd5e1; }}
  tr:hover td {{ background: #f1f5f9; }}
  body.dark tr:hover td {{ background: #0f172a40; }}
  .srt {{ font-size: 0.6rem; margin-left: 3px; color: #6366f1; }}
  .file-col {{ color: #6366f1; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.75rem; }}
  body.dark .file-col {{ color: #818cf8; }}
  .msg-cell {{ max-width: 400px; }}
  .msg-text {{ display: inline-block; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: pointer; }}
  .msg-text:hover {{ white-space: normal; overflow: visible; }}
  .line-cell {{ white-space: nowrap; width: 60px; }}
  .sev-label {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; }}
  .empty {{ color: #64748b; font-style: italic; font-size: 0.85rem; padding: 12px 0; }}
  .badge {{ display: inline-block; padding: 2px 10px; border-radius: 99px; font-size: 0.7rem; font-weight: 700; color: #6366f1; background: #eef2ff; border: 1px solid #c7d2fe; }}
  body.dark .badge {{ color: #a5b4fc; background: #312e8140; border-color: #312e81; }}
.theme-toggle {{ position: fixed; top: 20px; right: 20px; z-index: 100; background: rgba(0,0,0,0.12); backdrop-filter: blur(8px); border: none; color: #334155; width: 44px; height: 44px; border-radius: 12px; cursor: pointer; font-size: 1.3rem; display: flex; align-items: center; justify-content: center; transition: background .2s, color .2s; }}
.theme-toggle:hover {{ background: rgba(0,0,0,0.22); }}
body.dark .theme-toggle {{ background: rgba(255,255,255,0.2); color: #fff; }}
body.dark .theme-toggle:hover {{ background: rgba(255,255,255,0.35); }}
.gototop {{ position:fixed; bottom:20px; right:20px; z-index:100; background:rgba(0,0,0,0.12); backdrop-filter:blur(8px); border:none; color:#334155; width:44px; height:44px; border-radius:12px; cursor:pointer; font-size:1.3rem; display:none; align-items:center; justify-content:center; transition:background .2s,color .2s,opacity .3s; opacity:0.7; }}
.gototop:hover {{ background:rgba(0,0,0,0.22); opacity:1; }}
body.dark .gototop {{ background:rgba(255,255,255,0.2); color:#fff; }}
body.dark .gototop:hover {{ background:rgba(255,255,255,0.35); }}
  .footer {{ text-align: center; padding: 20px; font-size: 0.72rem; color: #94a3b8; }}
  body.dark .footer {{ color: #475569; }}
</style>
<script>
function sortTable(th, col) {{
    var table = th.closest('table.sortable');
    if (!table) return;
    var tbody = table.querySelector('tbody');
    if (!tbody) return;
    var rows = Array.from(tbody.querySelectorAll('tr'));
    if (rows.length < 2) return;
    var asc = th.classList.contains('asc');
    table.querySelectorAll('th').forEach(function(h) {{
        h.classList.remove('asc', 'desc');
        var s = h.querySelector('.srt');
        if (s) s.textContent = '';
    }});
    th.classList.add(asc ? 'desc' : 'asc');
    var dir = asc ? -1 : 1;
    rows.sort(function(a, b) {{
        var cellA = a.cells[col], cellB = b.cells[col];
        if (!cellA || !cellB) return 0;
        var va = cellA.getAttribute('data-sort');
        if (va === null || va === undefined) va = (cellA.textContent || '').trim();
        var vb = cellB.getAttribute('data-sort');
        if (vb === null || vb === undefined) vb = (cellB.textContent || '').trim();
        var na = parseFloat(va), nb = parseFloat(vb);
        if (!isNaN(na) && !isNaN(nb)) return (na - nb) * dir;
        return (va || '').localeCompare(vb || '') * dir;
    }});
    rows.forEach(function(r) {{ tbody.appendChild(r); }});
    var srt = th.querySelector('.srt');
    if (srt) srt.textContent = asc ? ' \u25B2' : ' \u25BC';
}}
function toggleTheme() {{
    var body = document.body;
    var btn = document.querySelector('.theme-toggle');
    body.classList.toggle('dark');
    var isDark = body.classList.contains('dark');
    btn.textContent = isDark ? '☀️' : '🌙';
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
}}
(function() {{
    var saved = localStorage.getItem('theme');
    if (saved !== 'light') {{
        document.body.classList.add('dark');
        var btn = document.querySelector('.theme-toggle');
        if (btn) btn.textContent = '☀️';
    }}
}})();
function goToTop() {{ window.scrollTo({{top:0,behavior:'smooth'}}); }}
window.addEventListener('scroll',function(){{
    var btn=document.getElementById('goToTopBtn');
    if(btn) btn.style.display=window.scrollY>100?'flex':'none';
}});
</script>
</head>
<body class="dark">
<button class="theme-toggle" onclick="toggleTheme()" title="Toggle dark/light mode" aria-label="Toggle dark/light mode">☀️</button>
<button class="gototop" onclick="goToTop()" title="Go to top" id="goToTopBtn"><svg width="22" height="22" viewBox="0 0 512 512"><path d="M256 8C119 8 8 119 8 256s111 248 248 248 248-111 248-248S393 8 256 8z" fill="none" stroke="#60bb47" stroke-width="24"/><polygon points="132.9 277.9 173.6 318.6 256 236.1 338.4 318.6 379.1 277.9 256 154.8" fill="#60bb47"/></svg></button>
<div class="header">
  <div class="header-inner">
    <h1>&#128269; SonarQube Analysis Report</h1>
    <p class="sub">Project: <strong>{project}</strong> &nbsp;&#183;&nbsp; Generated: {now}</p>
    <a class="btn" href="{dashboard_url}" target="_blank">&#128279; Open SonarQube Dashboard</a>
  </div>
</div>
<div class="container">

  <div class="cards">
    <div class="card">
      <div class="val" style="color:#f87171">{metrics.get('bugs', 'N/A')}</div>
      <div class="lbl">Bugs</div>
    </div>
    <div class="card">
      <div class="val" style="color:#ef4444">{metrics.get('vulnerabilities', 'N/A')}</div>
      <div class="lbl">Vulnerabilities</div>
    </div>
    <div class="card">
      <div class="val" style="color:#fbbf24">{metrics.get('code_smells', 'N/A')}</div>
      <div class="lbl">Code Smells</div>
    </div>
    <div class="card">
      <div class="val" style="color:#34d399">{metrics.get('coverage', 'N/A')}%</div>
      <div class="lbl">Coverage</div>
    </div>
    <div class="card">
      <div class="val" style="color:#60a5fa">{metrics.get('duplicated_lines_density', 'N/A')}%</div>
      <div class="lbl">Duplication</div>
    </div>
    <div class="card">
      <div class="val" style="color:#a78bfa">{metrics.get('ncloc', 'N/A')}</div>
      <div class="lbl">Lines of Code</div>
    </div>
    <div class="card">
      <div class="val">
        <span class="rating" style="background:{rating_color(metrics.get('reliability_rating', 'N/A'))}">{r_rel}</span>
      </div>
      <div class="lbl">Reliability</div>
    </div>
    <div class="card">
      <div class="val">
        <span class="rating" style="background:{rating_color(metrics.get('security_rating', 'N/A'))}">{r_sec}</span>
      </div>
      <div class="lbl">Security</div>
    </div>
    <div class="card">
      <div class="val">
        <span class="rating" style="background:{rating_color(metrics.get('sqale_rating', 'N/A'))}">{r_maint}</span>
      </div>
      <div class="lbl">Maintainability</div>
    </div>
  </div>

  <div class="section">
    <h2>&#128030; Bugs <span class="badge">{bugs_count}</span></h2>
    {issues_table(bugs) if bugs else '<p class="empty">No bugs found.</p>'}
  </div>

  <div class="section">
    <h2>&#128737; Vulnerabilities <span class="badge">{vulns_count}</span></h2>
    {issues_table(vulns) if vulns else '<p class="empty">No vulnerabilities found.</p>'}
  </div>

  <div class="section">
    <h2>&#128293; Security Hotspots <span class="badge">{hotspots_count}</span></h2>
    {issues_table(hotspots) if hotspots else '<p class="empty">No security hotspots found.</p>'}
  </div>

  <div class="section">
    <h2>&#128200; Code Smells <span class="badge">{smells_count}</span></h2>
    {issues_table(smells) if smells else '<p class="empty">No code smells found.</p>'}
  </div>

</div>
<div class="footer">
  Generated by Security Pipelines CI/CD &mdash; This is an automated report.
</div>
</body>
</html>"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project',    required=True)
    parser.add_argument('--sonar-url',  required=True)
    parser.add_argument('--output',     default='sonar-report.html')
    parser.add_argument('--token',      default='')
    args = parser.parse_args()

    base = args.sonar_url.rstrip('/')
    tok  = args.token

    print(f"Fetching SonarQube metrics for project '{args.project}' from {base}...")

    metrics  = get_metrics(base, args.project, tok)
    bugs     = get_issues(base, args.project, tok, 'BUG')
    vulns    = get_issues(base, args.project, tok, 'VULNERABILITY')
    smells   = get_issues(base, args.project, tok, 'CODE_SMELL')
    hotspots = get_hotspots(base, args.project, tok)

    html = generate_html(args.project, base, metrics, bugs, vulns, smells, hotspots)

    with open(args.output, 'w') as f:
        f.write(html)
    print(f"Report written to {args.output}")

if __name__ == '__main__':
    main()