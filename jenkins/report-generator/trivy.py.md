## Trivy Scan Report.

The Trivy Docker image scan stage performs a security assessment of the Docker image built by the Jenkins pipeline. It scans the image for known vulnerabilities in the operating system packages and application dependencies, such as Java, Node.js, Python, or other libraries. Trivy compares the contents of the image against its vulnerability database and identifies issues categorized by severity levels like LOW, MEDIUM, HIGH, and CRITICAL.

During the scan, Trivy generates a JSON report for automated processing and a table-format report that is displayed in the Jenkins console and saved as a text file. Based on the configured SEVERITY_FAIL_ON parameter, the pipeline can be configured to fail automatically if vulnerabilities of the specified severity or higher are detected, preventing insecure images from progressing further in the deployment process.

In the next stage, the generated JSON report is processed by a Python script to create a user-friendly HTML report. This HTML report provides a structured and readable summary of the identified vulnerabilities, making it easier for developers and security teams to review the findings and take appropriate remediation actions.


#### OUTPUT
![report.html](https://github.com/UnstopableSafar08/DevOps/blob/main/jenkins/images/trivy-report.html.png)

> `trivy.py` File's contents.

```py
#!/usr/bin/env python3
"""
Author      : Sagar Malla
Description : Standalone Trivy JSON -> HTML report generator.
              Renders output of `trivy image --format json ...` into a
              styled, searchable, sortable HTML report with dark mode.
              No dependency on report.py — fully self-contained.

              Usage:
                python3 trivy.py trivy-image-report.json
                python3 trivy.py trivy-image-report.json output.html
                python3 trivy.py trivy-image-report.json output.html --pipeline-name X --build-number 12 --branch main
"""

import sys
import json
import argparse
from html import escape
from pathlib import Path
from datetime import datetime

# ── Shared Constants ─────────────────────────────────────────────────────────

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


# ── Helpers ───────────────────────────────────────────────────────────────────

def severity_stats(items):
    counts = {s: 0 for s in SEV_ORDER}
    for item in items:
        sev = (item.get("severity") or "").upper()
        if sev in counts:
            counts[sev] += 1
    return counts


def build_stat_cards(items, extra_cards=None):
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
    return cards


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


def _pipeline_footer(info):
    if not info:
        return ""
    parts = []
    if info.get("name"):
        parts.append(f'Pipeline: <b>{info["name"]}</b>')
    if info.get("build_number"):
        parts.append(f'Build #<b>{info["build_number"]}</b>')
    if info.get("branch"):
        parts.append(f'Branch: <b>{info["branch"]}</b>')
    if not parts:
        return ""
    return f'<div style="margin-bottom:2px;">{" | ".join(parts)}</div>'


# ── Trivy JSON parsing ───────────────────────────────────────────────────────

def parse_trivy(json_path):
    with open(json_path) as f:
        data = json.load(f)

    results = data.get("Results", []) or []
    vuln_mapping = []
    targets = []

    for result in results:
        target = result.get("Target", "unknown")
        target_type = result.get("Class", result.get("Type", ""))
        targets.append(target)
        for vuln in result.get("Vulnerabilities", []) or []:
            fixed = vuln.get("FixedVersion", "")
            vuln_mapping.append({
                "name": vuln.get("PkgName", "unknown"),
                "version": vuln.get("InstalledVersion", "unknown"),
                "vulnerability": vuln.get("VulnerabilityID", "unknown"),
                "severity": (vuln.get("Severity") or "UNKNOWN").upper(),
                "description": vuln.get("Title") or vuln.get("Description") or "No description",
                "fix_version": fixed if fixed else "N/A",
                "locations": [f"{target} ({target_type})" if target_type else target],
            })

    return vuln_mapping, sorted(set(targets))


def build_rows(vuln_mapping):
    sev_class_map = {s: f"severity-{s.lower()}" for s in SEV_ORDER}
    sev_dot_map = {s: f'<span class="severity-dot sev-dot-{s.lower()}"></span>' for s in SEV_ORDER}

    rows = []
    for v in vuln_mapping:
        sev = v["severity"] if v["severity"] in SEV_ORDER else "LOW"
        desc = v["description"] or "No description"
        esc_desc = escape(desc)
        fix = v["fix_version"] if v["fix_version"] and v["fix_version"] != "N/A" else "N/A"
        fix_class = "fix-available" if fix != "N/A" else "fix-none"
        locs = v["locations"] or []
        loc_html = (
            '<div class="chips">' + ''.join(f'<span class="chip">{escape(l)}</span>' for l in locs) + '</div>'
            if locs else '<span style="color:#94a3b8;">&mdash;</span>'
        )
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
    return rows


# ── HTML Template ─────────────────────────────────────────────────────────────

def build_html(vuln_mapping, targets, pipeline_info=None):
    now = datetime.now()
    rows = build_rows(vuln_mapping)
    stat_cards = build_stat_cards(vuln_mapping, extra_cards=[("Targets Scanned", len(targets), SVG_SHIELD)])
    bar_segments, bar_legend = build_bar(vuln_mapping)
    header_meta = (
        f'<span>{SVG_CALENDAR} {now.strftime("%Y-%m-%d %H:%M")}</span>'
        f'<span>{SVG_PACKAGE} {len(targets)} target(s) scanned</span>'
    )

    title = "Trivy Vulnerability Report"
    subtitle = "Container Image Security Scan"

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

    th = (
        '<th onclick="sortTable(0)" data-col="0">Package <span class="sort-icon"></span></th>'
        '<th onclick="sortTable(1)" data-col="1">Version <span class="sort-icon"></span></th>'
        '<th onclick="sortTable(2)" data-col="2">Vulnerability <span class="sort-icon"></span></th>'
        '<th onclick="sortTable(3)" data-col="3">Severity <span class="sort-icon"></span></th>'
        '<th onclick="sortTable(4)" data-col="4">Description <span class="sort-icon"></span></th>'
        '<th onclick="sortTable(5)" data-col="5">Fix Version <span class="sort-icon"></span></th>'
        '<th>Target</th>'
    )
    sort_keys = ["name", "version", "vuln", "severity", "desc", "fix"]
    severity_col_idx = 3
    no_data_msg = "No vulnerabilities found"
    search_placeholder = "Search by package, CVE, description..."

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
.header-meta {{ margin-top:40px; text-align:right; font-size:0.85rem; opacity:0.9; line-height:1.8; }}
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

.severity-dot {{ width:8px; height:8px; border-radius:50%; background:currentColor; }}
.sev-dot-critical {{ background:#ef4444; }}
.sev-dot-high {{ background:#f97316; }}
.sev-dot-medium {{ background:#eab308; }}
.sev-dot-low {{ background:#22c55e; }}

.vuln-id {{ font-family:'JetBrains Mono','Fira Code',monospace; font-size:0.85rem; color:#6366f1; font-weight:500; }}
.fix-badge {{ display:inline-block; padding:2px 10px; border-radius:20px; font-size:0.75rem; font-weight:500; }}
.fix-available {{ background:#dbeafe; color:#1e40af; }}
.fix-none {{ background:#f1f5f9; color:#64748b; }}

.desc-text {{ color:#475569; max-width:320px; }}
.desc-truncated {{ display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; cursor:pointer; }}

.chips {{ display:flex; flex-wrap:wrap; gap:4px; }}
.chip {{ background:#f1f5f9; padding:2px 8px; border-radius:4px; font-size:0.75rem; color:#475569; }}

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
            <span class="logo-icon">🛡️</span>
            <div>
                <h1>{escape(title)}</h1>
                <p>{escape(subtitle)}</p>
            </div>
        </div>
        <div class="header-meta">
            {_pipeline_footer(pipeline_info)}
            {header_meta}
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
            <tr>{th}</tr>
        </thead>
        <tbody id="vuln-tbody"></tbody>
    </table>
    </div>
</div>

</main>

<footer>
<div class="container">
    <div class="footer-content">
        <div>Maintainer : <b style="color:#3db409;">Sagar Malla</b></div>
        <div>Generated on {now.strftime('%B %d, %Y at %H:%M')}</div>
        <div>Generated by Security Pipelines CI/CD &mdash; This is an automated report.</div>
    </div>
</div>
</footer>

<script>
const ROWS = {json.dumps(rows)};
const SEV_IDX = {json.dumps({s: i for i, s in enumerate(SEV_ORDER)})};
const SORT_KEYS = {json.dumps(sort_keys)};
const SEV_COL = {severity_col_idx};

let sortCol = -1;
let sortDir = 1;
let filterText = '';

function sevDot(sev) {{ return '<span class="severity-dot sev-dot-' + sev.toLowerCase() + '"></span>'; }}

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
                va = (a[key] || '').toString().toLowerCase();
                vb = (b[key] || '').toString().toLowerCase();
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

renderRows(ROWS);
function goToTop() {{ window.scrollTo({{top:0,behavior:'smooth'}}); }}
window.addEventListener('scroll',function(){{
    var btn=document.getElementById('goToTopBtn');
    if(btn) btn.style.display=window.scrollY>100?'flex':'none';
}});
</script>
</body>
</html>"""


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Render Trivy JSON scan output to a standalone HTML report.")
    parser.add_argument("input", help="Path to trivy image --format json output")
    parser.add_argument("output", nargs="?", default="trivy-report.html", help="Output HTML path")
    parser.add_argument("--pipeline-name", help="Pipeline or job name")
    parser.add_argument("--build-number", help="Build/run number")
    parser.add_argument("--branch", help="Git branch name")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    pipeline_info = {}
    if args.pipeline_name:
        pipeline_info["name"] = args.pipeline_name
    if args.build_number:
        pipeline_info["build_number"] = args.build_number
    if args.branch:
        pipeline_info["branch"] = args.branch

    vuln_mapping, targets = parse_trivy(args.input)
    html = build_html(vuln_mapping, targets, pipeline_info=pipeline_info)
    Path(args.output).write_text(html, encoding="utf-8")
    print(f"Report generated: {args.output}")


if __name__ == "__main__":
    main()
```
---

> `jenkinsfile.groovy` File's contents.

Jenkins Pipeline
```groovy
pipeline {
    agent { label 'jenkins-agent' }
    libraries {
        // lib('jenkins-library@master')
        lib('jenkins-security-library@main')
    }
    environment {
        TEAMS_WEBHOOK_URL = credentials('teams-webhook-url')
        HARBOR_CREDS      = credentials('harbor-registry-creds') // username+password binding
        REGISTRY          = 'prod-registry.sagar.com.np'
        REGISTRY_REPO     = 'sagar-misc'
    }

    options {
        disableConcurrentBuilds()
        timestamps()
        buildDiscarder(logRotator(
            numToKeepStr:         '5',
            artifactNumToKeepStr: '1'
        ))
    }

    parameters {
        choice(name: 'SEVERITY_FAIL_ON', choices: ['CRITICAL,HIGH', 'CRITICAL', 'NONE'],
               description: 'Fail build if Trivy finds these severities. NONE = report only (not recommended for prod).')
        booleanParam(name: 'PUSH_TO_REGISTRY', defaultValue: true,
               description: 'Push image to Harbor after scans pass')
    }

    stages {
        stage('App Name') {
            steps {
                script {
                    env.APP_NAME = env.JOB_BASE_NAME
                        .replaceAll('(?i)-ir$', '')
                        .replaceAll('(?i)^sagar_', '')
                        .toLowerCase()

                    // Reports are generated inside the workspace first (relative
                    // paths work cleanly with archiveArtifacts/publishHTML), then
                    // copied to the durable REPORTS_PATH for retention.
                    env.WORKSPACE_REPORTS_DIR = "reports"
                    sh "mkdir -p ${env.WORKSPACE_REPORTS_DIR}"

                    env.REPORTS_PATH = "/tmp/reports/${env.JOB_BASE_NAME}/${new java.util.Date().format('yyyy-MM-dd-HHmm')}"
                    sh "mkdir -p ${env.REPORTS_PATH}"

                    env.IMAGE_TAG  = "sagar-${env.APP_NAME}:${BUILD_NUMBER}"
                    env.IMAGE_FULL = "${REGISTRY}/${REGISTRY_REPO}/${env.APP_NAME}:${BUILD_NUMBER}"

                    env.PIPELINE_DETAILS = """
                        --pipeline-name '${env.JOB_BASE_NAME}' \
                        --build-number  '${env.BUILD_NUMBER}' \
                        --branch        '${params.Branch ?: "n/a"}'
                    """.trim()

                    echo "App: ${env.APP_NAME} | Workspace reports: ${env.WORKSPACE_REPORTS_DIR} | Archive path: ${env.REPORTS_PATH}"
                }
            }
        }

        stage('Docker Build') {
            steps {
                gitArchieve([
                    repo:     "git.sagar.com.np:sagar/sagar-props.git",
                    path:     "dockerfiles",
                    fileName: "sagar-base-img-jre-dockerfile"
                ])
                script {
                    sh "docker build --no-cache -t ${env.IMAGE_TAG} -f sagar-base-img-jre-dockerfile ."
                }
            }
        }

        stage('Vulnerability Scan (Trivy)') {
            steps {
                script {
                    def failFlag = params.SEVERITY_FAIL_ON == 'NONE' ? '' : "--exit-code 1 --severity ${params.SEVERITY_FAIL_ON}"
                    sh """
                        trivy image \
                            --format json \
                            --output ${env.WORKSPACE_REPORTS_DIR}/trivy-image-report.json \
                            ${env.IMAGE_TAG}

                        trivy image \
                            --format table \
                            ${failFlag} \
                            ${env.IMAGE_TAG} | tee ${env.WORKSPACE_REPORTS_DIR}/trivy-image-report.txt
                    """
                }
            }
        }

        stage('Render Trivy HTML Report') {
            steps {
                sh """
                    python3 /opt/trivy.py \
                    ${env.WORKSPACE_REPORTS_DIR}/trivy-image-report.json \
                    ${env.WORKSPACE_REPORTS_DIR}/trivy-report.html \
                    ${env.PIPELINE_DETAILS} || true
                """
            }
        }

        stage('Generate Vulnerability Report') {
            steps {
                sh """
                    syft ${env.IMAGE_TAG} -o cyclonedx-json > ${env.WORKSPACE_REPORTS_DIR}/sbom.json

                    grype sbom:${env.WORKSPACE_REPORTS_DIR}/sbom.json \
                    -o json > ${env.WORKSPACE_REPORTS_DIR}/vuln-report.json

                    python3 /opt/report.py \
                    ${env.WORKSPACE_REPORTS_DIR}/vuln-report.json \
                    ${env.WORKSPACE_REPORTS_DIR}/vuln-report.html \
                    ${env.PIPELINE_DETAILS} || true
                """

                sh "cp ${env.WORKSPACE_REPORTS_DIR}/sbom.json ${env.REPORTS_PATH}/ 2>/dev/null || true"
                sh "cp ${env.WORKSPACE_REPORTS_DIR}/vuln-report.* ${env.REPORTS_PATH}/ 2>/dev/null || true"
                sh "cp ${env.WORKSPACE_REPORTS_DIR}/trivy-image-report.* ${env.REPORTS_PATH}/ 2>/dev/null || true"
                sh "cp ${env.WORKSPACE_REPORTS_DIR}/trivy-report.html ${env.REPORTS_PATH}/ 2>/dev/null || true"

                archiveArtifacts(artifacts: "${env.WORKSPACE_REPORTS_DIR}/sbom.json,${env.WORKSPACE_REPORTS_DIR}/vuln-report.json,${env.WORKSPACE_REPORTS_DIR}/vuln-report.html,${env.WORKSPACE_REPORTS_DIR}/trivy-image-report.json,${env.WORKSPACE_REPORTS_DIR}/trivy-image-report.txt,${env.WORKSPACE_REPORTS_DIR}/trivy-report.html",
                                 fingerprint: true,
                                 allowEmptyArchive: true)

                publishHTML(target: [
                    reportDir:             env.WORKSPACE_REPORTS_DIR,
                    reportFiles:           'vuln-report.html,trivy-report.html',
                    reportName:            'Vulnerability Scan Report',
                    keepAll:               true,
                    alwaysLinkToLastBuild: true,
                    allowMissing:          true
                ])
                publishHTML(target: [
                    reportDir:             env.WORKSPACE_REPORTS_DIR,
                    reportFiles:           'trivy-report.html',
                    reportName:            'Trivy Scan Report',
                    keepAll:               true,
                    alwaysLinkToLastBuild: true,
                    allowMissing:          true
                ])
            }
        }

        stage('Push to Registry') {
            when { expression { params.PUSH_TO_REGISTRY } }
            steps {
                sh """
                    docker tag ${env.IMAGE_TAG} ${env.IMAGE_FULL}
                    echo "\$HARBOR_CREDS_PSW" | docker login -u "\$HARBOR_CREDS_USR" --password-stdin ${REGISTRY}
                    docker push ${env.IMAGE_FULL}
                    docker logout ${REGISTRY}
                """
            }
        }
    }

    post {
        always {
            echo "Build finished: ${currentBuild.currentResult}"
            script {
                sendSecurityReport(
                    reportsPath: env.REPORTS_PATH,
                    recipients:  'sagar.malla@sagar.com.np',
                    webhookUrl:  env.TEAMS_WEBHOOK_URL,
                    status:      currentBuild.currentResult,
                    jobName:     env.JOB_BASE_NAME,
                    buildNumber: env.BUILD_NUMBER,
                    buildUrl:    env.BUILD_URL
                )
            }
        }
        success  { echo "SUCCESS - ${env.IMAGE_TAG}"; cleanWs() }
        unstable { echo "UNSTABLE - review ${env.REPORTS_PATH}"; cleanWs() }
        failure  { echo "FAILURE - build or vuln scan failed, image NOT pushed."; cleanWs() }
        aborted  { cleanWs() }
    }
}
```
