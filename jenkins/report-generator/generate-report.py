import json
from pathlib import Path
from datetime import datetime

# Load data
with open("sbom.json") as f: sbom = json.load(f)
with open("vuln-report.json") as f: vuln_report = json.load(f)

# Create component lookup
components = {f"{c.get('name')}:{c.get('version')}": c
              for c in sbom.get("components", []) if c.get('name') and c.get('version')}

# Process vulnerabilities
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

# Statistics
severity_counts = {}
for v in vuln_mapping:
    severity_counts[v['severity']] = severity_counts.get(v['severity'], 0) + 1

# HTML Template
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SBOM Vulnerability Report</title>

    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif; background:#f9fafb; color:#374151; line-height:1.6; }}
        .container {{ max-width:1400px; margin:0 auto; padding:0 20px; }}

        header {{ background:linear-gradient(135deg,#667eea 0%,#764ba2 100%); color:white; padding:2rem 0; }}
        .header-content {{ display:flex; justify-content:space-between; align-items:center; }}
        .logo {{ display:flex; align-items:center; gap:15px; }}
        .logo h1 {{ font-size:2.2rem; font-weight:600; }}

        .stats-container, .table-container {{ background:white; border-radius:12px; padding:25px; margin:30px 0; box-shadow:0 4px 15px rgba(0,0,0,0.05); }}
        .stats-title, .table-title {{ font-size:1.3rem; font-weight:600; margin-bottom:20px; color:#4b5563; display:flex; align-items:center; gap:10px; }}
        .stats-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:20px; }}
        .stat-card {{ background:#f8fafc; border-radius:10px; padding:20px; text-align:center; border:1px solid #e5e7eb; }}
        .stat-value {{ font-size:2.5rem; font-weight:700; margin-bottom:5px; }}

        table {{ width:100%; border-collapse:collapse; }}
        th {{ background:#f1f5f9; padding:16px 12px; text-align:left; font-weight:600; color:#475569; border-bottom:2px solid #e2e8f0; }}
        td {{ padding:14px 12px; border-bottom:1px solid #e5e7eb; }}
        tr:hover {{ background:#f8fafc; }}

        .severity-badge {{ display:inline-block; padding:5px 12px; border-radius:20px; font-size:0.8rem; font-weight:600; text-transform:uppercase; }}
        .severity-critical {{ background:#fee2e2; color:#991b1b; }}
        .severity-high {{ background:#ffedd5; color:#9a3412; }}
        .severity-medium {{ background:#fef3c7; color:#92400e; }}
        .severity-low {{ background:#dcfce7; color:#166534; }}

        footer {{ background:#f1f5f9; padding:25px 0; border-top:1px solid #e5e7eb; }}
        .footer-content {{ display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:20px; }}

        @media (max-width:768px) {{
            .header-content, .footer-content {{ flex-direction:column; text-align:center; gap:20px; }}
            th, td {{ padding:10px 8px; font-size:0.9rem; }}
        }}
    </style>
</head>

<body>

<header>
<div class="container">
    <div class="header-content">

        <div class="logo">
            🛡️
            <div>
                <h1>SBOM Vulnerability Report</h1>
                <p>Software Bill of Materials Security Analysis</p>
            </div>
        </div>

        <div>
            <p>📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            <p>📄 Components: {len(components)}</p>
        </div>

    </div>
</div>
</header>

<main class="container">

<div class="stats-container">

    <div class="stats-title">
        📊 Vulnerability Overview
    </div>

    <div class="stats-grid">

        <div class="stat-card">
            <div class="stat-value">{len(vuln_mapping)}</div>
            <div>Total Vulnerabilities</div>
        </div>

        <div class="stat-card">
            <div class="stat-value">{severity_counts.get('Critical',0)}</div>
            <div>Critical</div>
        </div>

        <div class="stat-card">
            <div class="stat-value">{severity_counts.get('High',0)}</div>
            <div>High</div>
        </div>

        <div class="stat-card">
            <div class="stat-value">{severity_counts.get('Medium',0)}</div>
            <div>Medium</div>
        </div>

        <div class="stat-card">
            <div class="stat-value">{severity_counts.get('Low',0)}</div>
            <div>Low</div>
        </div>

    </div>

</div>

<div class="table-container">

    <div class="table-title">
        📋 Detailed Vulnerability Findings
    </div>
"""

if vuln_mapping:
    html += """<table><thead><tr>
        <th>Package</th><th>Version</th><th>Vulnerability ID</th><th>Severity</th><th>Description</th><th>Fix Version</th><th>Locations</th>
    </tr></thead><tbody>"""

    for v in vuln_mapping:
        severity_class = f"severity-{v['severity'].lower()}"

        html += f"""<tr>
            <td><strong>{v['name']}</strong></td>
            <td>{v['version']}</td>
            <td>{v['vulnerability']}</td>
            <td><span class="severity-badge {severity_class}">{v['severity']}</span></td>
            <td>{v['description']}</td>
            <td>{v['fix_version']}</td>
            <td><small>{'<br>'.join(v['locations'])}</small></td>
        </tr>"""

    html += "</tbody></table>"
else:
    html += """<div style="text-align:center; padding:50px 20px;">
        <div style="font-size:60px;">✅</div>
        <h2>No Vulnerabilities Found</h2>
        <p>All components appear secure.</p>
    </div>"""

html += f"""
</div>

</main>

<footer>
<div class="container">
    <div class="footer-content">
        <div>🛡️ SBOM Security Scanner</div>
        <div>
            Report generated on {datetime.now().strftime('%B %d, %Y at %H:%M')}
        </div>
    </div>
</div>
</footer>

</body>
</html>
"""

# Save file
Path("vuln-report.html").write_text(html, encoding="utf-8")

print("HTML report generated: vuln-report.html")
