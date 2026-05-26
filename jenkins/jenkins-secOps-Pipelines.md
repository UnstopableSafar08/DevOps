# DevSecOps Pipeline — Security Scanning Integration

This document outlines the DevSecOps tools integrated into the CI/CD pipeline, their purpose, trade-offs, and reference Jenkins pipeline configurations.

---

## Tools Overview

### 1. Gitleaks — Secrets Scanning

**Intro:** Gitleaks is a static-analysis tool for detecting hardcoded secrets like passwords, API keys, and tokens in Git repositories.

**Why required:** Secrets accidentally committed to source code are a leading cause of security breaches. Gitleaks scans for patterns and entropy-based matches before code reaches production.

**Pros:**
- Fast and lightweight — scans large repos in seconds
- JSON output can be trivially converted to HTML reports
- Supports `.gitleaks.toml` config for custom allowlists/rules
- `--no-git` mode for directory scanning without history

**Cons:**
- Prone to false positives with entropy-based detection
- Only scans what's on disk (requies `--no-git` if cloning full history is undesirable)
- Does not verify whether a detected secret is still valid

**Usage:**
```bash
gitleaks detect --source . --report-format json --report-path gitleaks-report.json --redact --no-git || true
```

---

### 2. TruffleHog — Secrets Scanning

**Intro:** TruffleHog scans Git repositories, filesystems, and S3 buckets for secrets using entropy detection and regex patterns, with optional credential verification.

**Why required:** Catches secrets that Gitleaks may miss, especially when using `--only-verified` to reduce false positives by actually testing the detected credential.

**Pros:**
- `--only-verified` mode actively validates credentials (reduces false positives)
- Supports JSONL output for streaming/partial results
- Detects a wide range of secret types via regex + entropy
- Can scan non-Git sources (filesystems, S3, APIs)

**Cons:**
- Verification step is slower than pure pattern matching
- JSONL format is less common and requires line-by-line parsing
- May trigger account lockouts or alerts on external services during verification

**Usage:**
```bash
trufflehog git file://. --json --only-verified 2>/dev/null > trufflehog-report.json || true
```

---

### 3. OWASP Dependency-Check — Dependency Scanning

**Intro:** OWASP Dependency-Check is a Software Composition Analysis (SCA) tool that identifies known vulnerabilities (CVEs) in project dependencies.

**Why required:** Modern applications rely heavily on open-source libraries. Dependency-Check cross-references dependency names and versions against the NVD (National Vulnerability Database) to surface known vulnerabilities.

**Pros:**
- Mature, widely adopted, OWASP-backed
- Jenkins plugin provides native pipeline integration
- Produces both XML (for custom parsing) and HTML (for human review)
- Supports multiple ecosystems: Java, Python, JavaScript, .NET, Ruby, etc.

**Cons:**
- Slow on large projects due to NVD data download
- Requires internet access for vulnerability database updates
- High false-positive rate for some ecosystems
- Database update can fail in air-gapped environments

**Usage (Jenkins declarative):**
```groovy
dependencyCheck additionalArguments: '''--scan . --format XML --format HTML --out . --project myproject''', odcInstallation: 'dc'
```

**Conversion to enhanced HTML:**
```bash
python3 /opt/report.py dependency-check-report.xml dependency-check-report.html
```

---

### 4. SonarQube — Static Analysis (SAST)

**Intro:** SonarQube is a leading Static Application Security Testing (SAST) and code quality platform. It analyzes source code for bugs, vulnerabilities, code smells, and security hotspots.

**Why required:** Provides continuous code quality and security feedback. Catches issues like SQL injection, XSS, and other security anti-patterns early in development. Enforces quality gates before merge.

**Pros:**
- Comprehensive rule sets for 30+ languages
- Quality Gates enforce minimum standards before promotion
- Web dashboard with trending/history
- Rich REST API for custom reporting
- Supports Incremental analysis

**Cons:**
- Requires a server/DB (PostgreSQL) — operational overhead
- Full analysis is slow on large monorepos
- Free tier has limited language coverage vs Developer/Enterprise
- Custom rule writing requires knowledge of AST (Abstract Syntax Trees)

**Usage:**
```bash
sonar-scanner \
    -Dsonar.projectKey=myproject \
    -Dsonar.projectName=myproject \
    -Dsonar.sources=. \
    -Dsonar.login=${SONAR_TOKEN}
```

**Custom HTML report generation:**
```bash
python3 /opt/sonar-report.py --project myproject --sonar-url http://sonar:9000 --output sonar-report.html --token $SONAR_TOKEN
```

---

### 5. Trivy — Vulnerability Scanner (Containers & Filesystem)

**Intro:** Trivy is an all-in-one vulnerability scanner for container images, filesystems, and Git repos. It detects vulnerabilities in OS packages (Alpine, Debian, etc.) and language-specific dependencies.

**Why required:** Container images can contain known-vulnerable packages. Trivy scans both the image layers and the filesystem to surface CVEs with severity ratings.

**Pros:**
- Extremely fast — scans in seconds
- No database to maintain (downloads vulnerability DB on first run, caches)
- Supports multiple output formats: table, JSON, HTML (via Go template)
- Scans both OS packages and language-specific libraries

**Cons:**
- HTML output requires a Go template (not built-in)
- Only shows known CVEs — no zero-day detection
- Limited to package-level scanning, not code-level analysis
- Scan depth is limited to SBOM-detectable components

**Usage (image scan):**
```bash
trivy image --severity CRITICAL,HIGH --cache-dir /var/lib/trivy \
    --format template --template /opt/html.tpl \
    --output trivy-image-report.html myimage:latest
```

**Usage (filesystem scan):**
```bash
trivy fs --format table --output trivy-fs-report.txt .
trivy fs --format template --template /opt/html.tpl --output trivy-fs-report.html .
```

---

### 6. Syft — SBOM Generation

**Intro:** Syft generates Software Bill of Materials (SBOM) from container images and filesystems in CycloneDX or SPDX formats.

**Why required:** An SBOM is the foundation of dependency vulnerability management. Syft catalogs every package in an image — OS packages, language libraries, and binaries — which Grype then scans for CVEs.

**Pros:**
- Multiple output formats (CycloneDX JSON, SPDX, Syft JSON)
- Fast — generates SBOM for typical images in seconds
- Supports all major package ecosystems (dpkg, RPM, APK, npm, pip, etc.)
- Integrates seamlessly with Grype (`grype sbom:sbom.json`)

**Cons:**
- Outputs only the package manifest (no vulnerability data)
- CycloneDX format can be verbose for large images
- May miss packages installed via non-standard methods

**Usage:**
```bash
syft myimage:latest -o cyclonedx-json > sbom.json
```

---

### 7. Grype — Vulnerability Scanner (SBOM-based)

**Intro:** Grype is a vulnerability scanner that takes a Syft-generated SBOM and cross-references it against vulnerability databases (NVD, RedHat, Alpine, GitHub Advisory, etc.).

**Why required:** Decouples SBOM generation from vulnerability matching. Grype updates its vulnerability DB independently, so re-scanning an existing SBOM catches newly disclosed CVEs without rebuilding the image.

**Pros:**
- Re-scans existing SBOMs without needing the original image
- Fast — operates on the package manifest, not the filesystem
- Produces structured JSON output suitable for custom HTML generation
- Rich matching: exact version, fuzzy range, distro-specific advisories

**Cons:**
- Only as good as the input SBOM (missing packages = missing findings)
- Vulnerability DB is large (~1GB) on first download
- Some CVEs may not have fix versions, making triage harder

**Usage:**
```bash
grype sbom:sbom.json -o json > vuln-report.json
```

---

## Report Generation

All scanner outputs are converted to self-contained HTML reports using Python scripts. Features include:

- **Severity color-coding** (CRITICAL=red, HIGH=orange, MEDIUM=yellow, LOW=green)
- **Summary cards** with counts per severity
- **Severity distribution bar**
- **Sortable columns** with live JavaScript sorting
- **Live search/filter** across all fields
- **Dark/light theme toggle** (persisted to localStorage)
- **Go to Top button** (appears on scroll > 400px)

### Unified Report Script

```bash
# Auto-detect format and generate HTML
python3 /opt/report.py                                # sbom.json + vuln-report.json
python3 /opt/report.py dependency-check.xml            # OWASP Dependency-Check
python3 /opt/report.py gitleaks-report.json            # Gitleaks
python3 /opt/report.py trufflehog-report.json          # TruffleHog
python3 /opt/report.py trivy-report.json               # Trivy
python3 /opt/report.py sbom.json vuln-report.json      # SBOM + Grype
```

### Standalone Scripts

```bash
python3 /opt/sonar-report.py --project myproject --sonar-url http://sonar:9000 --output sonar-report.html
python3 /opt/leaks-report.py gitleaks-report.json --output leaks-report.html
```

---

## Example Jenkins Pipelines

### Full Production Pipeline

This pipeline runs all security scans, generates reports, publishes them, and sends email notifications.

```groovy
pipeline {
    agent { label 'jenkins-agent' }
    
    parameters {
        string(name: 'Branch', defaultValue: 'main', description: 'Branch to build')
        booleanParam(name: 'DOCKER_PUSH', defaultValue: false, description: 'Push Docker image to registry')
    }
    
    environment {
        SONAR_TOKEN    = credentials('sonar-token')
        FULL_IMAGE     = "registry.example.com/myapp:${env.BUILD_NUMBER}"
    }
    
    stages {
        stage('Preparation') {
            steps {
                cleanWs()
                checkout scm
                sh 'curl -sL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/html.tpl -o /opt/html.tpl'
            }
        }
        
        stage('Secret Scan — Gitleaks') {
            steps {
                sh 'gitleaks detect --source . --report-format json --report-path gitleaks-report.json --redact --no-git || true'
                sh 'python3 /opt/report.py gitleaks-report.json gitleaks-report.html || true'
                archiveArtifacts artifacts: 'gitleaks-report.*'
            }
        }
        
        stage('Secret Scan — TruffleHog') {
            steps {
                sh 'trufflehog git file://. --json --only-verified 2>/dev/null > trufflehog-report.json || true'
                sh 'python3 /opt/report.py trufflehog-report.json trufflehog-report.html || true'
                archiveArtifacts artifacts: 'trufflehog-report.*'
            }
        }
        
        stage('Clean Build') {
            steps {
                sh 'gradle clean bootWar -x test --no-daemon'
            }
        }
        
        stage('SonarQube Scan') {
            steps {
                withSonarQubeEnv('SonarQube') {
                    sh '''${SCANNER_HOME}/bin/sonar-scanner \
                        -Dsonar.projectKey=myproject \
                        -Dsonar.projectName=myproject \
                        -Dsonar.sources=. \
                        -Dsonar.login=${SONAR_TOKEN}'''
                }
            }
        }
        
        stage('OWASP Dependency Check') {
            steps {
                dependencyCheck additionalArguments: '''--scan . --format XML --format HTML --out . --project myproject''', odcInstallation: 'dc'
                sh 'python3 /opt/report.py dependency-check-report.xml dependency-check-report.html'
            }
        }
        
        stage('Docker Build') {
            when { expression { params.DOCKER_PUSH } }
            steps {
                sh "docker build -t ${FULL_IMAGE} ."
                sh "docker push ${FULL_IMAGE}"
            }
        }
        
        stage('Trivy Image Scan') {
            when { expression { params.DOCKER_PUSH } }
            steps {
                sh "trivy image --severity CRITICAL,HIGH --cache-dir /var/lib/trivy \
                    --format template --template /opt/html.tpl \
                    --output trivy-image-report.html ${FULL_IMAGE}"
            }
        }
        
        stage('Trivy Filesystem Scan') {
            steps {
                sh 'trivy fs --format table --output trivy-fs-report.txt . || true'
                sh 'trivy fs --format template --template /opt/html.tpl --output trivy-fs-report.html . || true'
            }
        }
        
        stage('Generate Scan Report') {
            steps {
                sh 'syft ${FULL_IMAGE} -o cyclonedx-json > sbom.json'
                sh 'grype sbom:sbom.json -o json > vuln-report.json'
                sh 'python3 /opt/report.py'
            }
        }
        
        stage('SonarQube Report') {
            steps {
                sh 'python3 /opt/sonar-report.py --project myproject --sonar-url http://sonar:9000 --output sonar-report.html --token $SONAR_TOKEN'
            }
        }
        
        stage('Publish Reports') {
            steps {
                publishHTML(target: [reportDir: '.', reportFiles: 'trivy-image-report.html', reportName: 'Trivy Image Scan'])
                publishHTML(target: [reportDir: '.', reportFiles: 'trivy-fs-report.html', reportName: 'Trivy Filesystem Scan'])
                publishHTML(target: [reportDir: '.', reportFiles: 'vuln-report.html', reportName: 'Vulnerability Report'])
                publishHTML(target: [reportDir: '.', reportFiles: 'gitleaks-report.html', reportName: 'Gitleaks Report'])
                publishHTML(target: [reportDir: '.', reportFiles: 'trufflehog-report.html', reportName: 'TruffleHog Report'])
                publishHTML(target: [reportDir: '.', reportFiles: 'dependency-check-report.html', reportName: 'Dependency Check'])
                publishHTML(target: [reportDir: '.', reportFiles: 'sonar-report.html', reportName: 'SonarQube Report'])
                archiveArtifacts artifacts: '*-report.html,*-report.json,*.txt,sbom.json'
            }
        }
    }
    
    post {
        always {
            script {
                def attachments = [
                    'dependency-check-report.html',
                    'vuln-report.html',
                    'sonar-report.html',
                    'gitleaks-report.html',
                    'trufflehog-report.html'
                ].join(',')
                sendReport(
                    recipients: 'soc@example.com,devsecops@example.com',
                    status: currentBuild.result ?: 'SUCCESS',
                    reports: attachments,
                    subject: "Security Scan Report - ${env.JOB_NAME} #${env.BUILD_NUMBER}"
                )
            }
        }
    }
}
```

### Minimal Example Pipeline

A lightweight pipeline for teams that want only the essential security scans:

```groovy
pipeline {
    agent any
    
    environment {
        SONAR_TOKEN = credentials('sonar-token')
    }
    
    stages {
        stage('Setup') {
            steps {
                sh 'mkdir -p security-reports'
            }
        }
        
        stage('OWASP Dependency Check') {
            steps {
                dependencyCheck additionalArguments: '''--scan . --format XML --format HTML --out security-reports --project myproject''', odcInstallation: 'dc'
                sh 'python3 /opt/report.py security-reports/dependency-check-report.xml security-reports/dependency-check-report.html'
            }
        }
        
        stage('Generate SBOM & Vuln Report') {
            steps {
                sh 'syft dir:. -o cyclonedx-json > security-reports/sbom.json'
                sh 'grype sbom:security-reports/sbom.json -o json > security-reports/vuln-report.json'
                sh 'python3 /opt/report.py security-reports/sbom.json security-reports/vuln-report.json security-reports/vuln-report.html'
            }
        }
        
        stage('Gitleaks Secrets Scan') {
            steps {
                sh 'gitleaks detect --source . --report-format json --report-path security-reports/gitleaks-report.json --no-git || true'
                sh 'python3 /opt/report.py security-reports/gitleaks-report.json security-reports/leaks-report.html'
            }
        }
        
        stage('TruffleHog Secrets Scan') {
            steps {
                sh 'trufflehog git file://. --json --only-verified 2>/dev/null > security-reports/trufflehog-report.json || true'
                sh 'python3 /opt/report.py security-reports/trufflehog-report.json security-reports/trufflehog-report.html'
            }
        }
        
        stage('SonarQube Report') {
            steps {
                sh 'python3 /opt/sonar-report.py --project myproject --sonar-url http://sonar:9000 --output security-reports/sonar-report.html --token $SONAR_TOKEN'
            }
        }
    }
    
    post {
        always {
            publishHTML(target: [reportDir: 'security-reports', reportFiles: 'dependency-check-report.html', reportName: 'Dependency Check'])
            publishHTML(target: [reportDir: 'security-reports', reportFiles: 'vuln-report.html', reportName: 'Vulnerability Report'])
            publishHTML(target: [reportDir: 'security-reports', reportFiles: 'leaks-report.html', reportName: 'Secret Leaks Report'])
            publishHTML(target: [reportDir: 'security-reports', reportFiles: 'sonar-report.html', reportName: 'SonarQube Report'])
            archiveArtifacts artifacts: 'security-reports/*'
        }
    }
}
```

---

## Pipeline Stages Reference

| Stage | Tool | Type | Output |
|---|---|---|---|
| Secret Scan | Gitleaks | Secrets Scanning | `gitleaks-report.json` → HTML |
| Secret Scan | TruffleHog | Secrets Scanning | `trufflehog-report.json` → HTML |
| Static Analysis | SonarQube | SAST | Dashboards + `sonar-report.html` |
| Dependency Scan | OWASP Dep-Check | SCA | XML → `dependency-check-report.html` |
| Container Scan | Trivy | Container Security | `trivy-image-report.html` |
| Filesystem Scan | Trivy | Vulnerability Scanning | `trivy-fs-report.html` |
| SBOM Generation | Syft | Software Bill of Materials | `sbom.json` (CycloneDX) |
| Vulnerability Scan | Grype | SCA | `vuln-report.json` → HTML |

---

## Email Notification

The `send-report.py` script emails all generated reports as attachments with a summary table.

```bash
python3 /opt/send-report.py \
    --recipients "soc@example.com" \
    --status "${currentBuild.result}" \
    --reports "dependency-check-report.html,vuln-report.html,sonar-report.html,gitleaks-report.html,trufflehog-report.html" \
    --subject "Security Scan Report - ${JOB_NAME} #${BUILD_NUMBER}" \
    --pipeline-url "${env.BUILD_URL}"
```

SMTP configuration is read from environment variables:
- `SMTP_SERVER` (default: `localhost`)
- `SMTP_PORT` (default: `25`)
- `SMTP_USERNAME` / `SMTP_PASSWORD` (for authenticated relays)
- `EMAIL_FROM` (default: `jenkins@example.com`)

---
