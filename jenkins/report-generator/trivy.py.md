### Trivy Scan Report.

The Trivy Docker image scan stage performs a security assessment of the Docker image built by the Jenkins pipeline. It scans the image for known vulnerabilities in the operating system packages and application dependencies, such as Java, Node.js, Python, or other libraries. Trivy compares the contents of the image against its vulnerability database and identifies issues categorized by severity levels like LOW, MEDIUM, HIGH, and CRITICAL.

During the scan, Trivy generates a JSON report for automated processing and a table-format report that is displayed in the Jenkins console and saved as a text file. Based on the configured SEVERITY_FAIL_ON parameter, the pipeline can be configured to fail automatically if vulnerabilities of the specified severity or higher are detected, preventing insecure images from progressing further in the deployment process.

In the next stage, the generated JSON report is processed by a Python script to create a user-friendly HTML report. This HTML report provides a structured and readable summary of the identified vulnerabilities, making it easier for developers and security teams to review the findings and take appropriate remediation actions.

> `trivy.py` File's contents.

```py
#!/usr/bin/env python3
"""
Author      : Sagar Malla
Description : Renders Trivy image/filesystem JSON scan output
              (trivy image --format json ...) into the same styled
              HTML report format used by report.py.
              Reuses the shared HTML/CSS/JS template so both reports
              look and behave identically.

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

# Reuse the shared template engine, constants, and helpers from report.py
# so both reports share identical styling/behavior and any template fix
# only needs to happen in one place.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from report import (
    build_html, severity_stats, build_stat_cards, build_bar,
    SEV_ORDER, SVG_SHIELD, SVG_CALENDAR, SVG_PACKAGE,
)


def handle_trivy(json_path, pipeline_info=None):
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

    targets = sorted(set(targets))

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

    stat_cards, _ = build_stat_cards(vuln_mapping, 0,
                                      extra_cards=[("Targets Scanned", len(targets), SVG_SHIELD)])
    bar_segments, bar_legend = build_bar(vuln_mapping)
    header_meta = (
        f'<span>{SVG_CALENDAR} {datetime.now().strftime("%Y-%m-%d %H:%M")}</span>'
        f'<span>{SVG_PACKAGE} {len(targets)} target(s) scanned</span>'
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

    html = build_html(
        title="Trivy Vulnerability Report",
        subtitle="Container Image Security Scan",
        project_label="\U0001f6e1\ufe0f",
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
        pipeline_info=pipeline_info,
    )
    return html


def main():
    parser = argparse.ArgumentParser(description="Render Trivy JSON scan output to HTML.")
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

    html = handle_trivy(args.input, pipeline_info=pipeline_info)
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
