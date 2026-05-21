# SBOM Security Scanning Pipeline
### Syft + Grype + Jenkins CI/CD
> Infrastructure & DevSecOps Guide — Example Corp Internal Documentation

---

## Table of Contents

1. [Overview](#1-overview)
2. [Installation](#2-installation)
3. [Jenkins Pipeline Stages](#3-jenkins-pipeline-stages)
4. [Jenkins CSP Fix for HTML Reports](#4-jenkins-csp-fix-for-html-reports)
5. [End-to-End Pipeline Flow](#5-end-to-end-pipeline-flow)
6. [Output Files Reference](#6-output-files-reference)
7. [Troubleshooting](#7-troubleshooting)
8. [Quick Reference](#8-quick-reference)

---

## 1. Overview

This document describes the end-to-end SBOM (Software Bill of Materials) security scanning pipeline integrated into Jenkins CI/CD. The pipeline uses **Syft** to generate SBOMs and **Grype** to detect known vulnerabilities, producing structured HTML reports published directly in the Jenkins build dashboard.

### 1.1 What is an SBOM?

An SBOM (Software Bill of Materials) is a formal, machine-readable inventory of all software components, libraries, and dependencies that make up an application. It is the software equivalent of an ingredient label — providing full visibility into what is inside a container image or codebase.

### 1.2 Tool Summary

| Tool | Role | Output |
|------|------|--------|
| **Syft** | SBOM generator — scans image/FS for components | `sbom.json` (CycloneDX) |
| **Grype** | Vulnerability scanner — matches SBOM against CVE DBs | `vuln-report.json` |
| **Python script** | Report renderer — converts JSON to human-readable HTML | `vuln-report.html` |
| **Jenkins** | CI/CD orchestrator — runs all stages, archives results | Build artifacts + HTML report |
| **Trivy** | Supplementary scanner — container image + filesystem scan | `trivy-fs-report.html` |
| **OWASP Dep-Check** | Java dependency CVE scan — checks `build/libs` JARs | `dependency-check-report/` |

---

## 2. Installation

Both Syft and Grype must be installed on the Jenkins agent node that runs the pipeline. The installation commands below download and place the binaries in `/usr/local/bin`, making them available to all pipeline stages.

### 2.1 Install Syft

Syft is the SBOM generator developed by Anchore. It supports container images, directories, archives, and individual files.

```bash
# Download and install Syft
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh

# Move binary to system PATH
mv bin/syft /usr/local/bin/

# Verify installation
syft version
```

> **TIP:** By default, Syft installs into a local `./bin` directory. The `mv` step is required to make it available system-wide for Jenkins.

### 2.2 Install Grype

Grype is the vulnerability scanner, also by Anchore. It consumes SBOM files produced by Syft and matches components against multiple CVE databases (NVD, GitHub Advisory, etc.).

```bash
# Download and install Grype
curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh

# Move binary to system PATH
mv bin/grype /usr/local/bin/

# Verify installation
grype version
```

### 2.3 Verify Both Tools

```bash
# Check both tools are reachable
which syft && syft version
which grype && grype version

# Expected: /usr/local/bin/syft  and  /usr/local/bin/grype
```

---

## 3. Jenkins Pipeline Stages

The pipeline executes the following stages in sequence.

| # | Stage | Purpose |
|---|-------|---------|
| 1 | **App Name** | Derive normalized, lowercase app name from job name → set as `env.APP_NAME` |
| 2 | **Preparation** | Verify tool versions — Java, Gradle on agent |
| 3 | **Git Checkout** | Clone the configured branch from GitLab |
| 4 | **App Build** | Compile and test with Gradle (`gradle clean build`) |
| 5 | **Sonar Scan** | Static code analysis via SonarQube Scanner |
| 6 | **Quality Gate** | Await SonarQube quality gate result (2-min timeout) |
| 7 | **OWASP Check** | Scan JAR dependencies for known CVEs |
| 8 | **Docker Build** | Build container image: `<app-name>:<build-number>` |
| 9 | **Trivy Image** | Scan Docker image for CRITICAL/HIGH CVEs |
| 10 | **Trivy FS** | Scan entire workspace filesystem — table + HTML output |
| 11 | **Results** | Archive Trivy and OWASP reports as build artifacts |
| 12 | **Generate SBOM** | Run Syft on Docker image → `sbom.json` (CycloneDX format) |
| 13 | **Grype Scan** | Run Grype on `sbom.json` → `vuln-report.json` |
| 14 | **HTML Report** | Python script renders `vuln-report.json` → `vuln-report.html` |
| 15 | **Publish Report** | Archive `vuln-report.html`, `sbom.json`, `vuln-report.json` |
| 16 | **Publish Artifact** | Upload JAR to artifact server (when `ARCHIVE=YES`) |

---

### 3.1 Stage: App Name

Derives a normalized, lowercase app name from the Jenkins job name and stores it as a global environment variable accessible to all downstream stages.

```groovy
stage('App Name') {
    steps {
        script {
            env.APP_NAME = env.JOB_BASE_NAME
                .replaceAll('-rel', '')
                .replaceAll('(?i)^RELEASE-', '')
                .toLowerCase()
            echo "App Name: ${env.APP_NAME}"
            // output: my-app
        }
    }
}
```

---

### 3.2 Stage: Generate SBOM (Syft)

Syft scans the built Docker image and generates a CycloneDX-format SBOM as JSON. The image name is read from `env.APP_NAME` set in the previous stage.

```groovy
stage('Generate Scan Report') {
    steps {
        script {
            def imageName = "${env.APP_NAME}:${BUILD_NUMBER}"
            sh """
                syft ${imageName} -o cyclonedx-json > sbom.json
            """
        }
    }
}
```

| Flag | Value | Description |
|------|-------|-------------|
| `-o` | `cyclonedx-json` | Output format: CycloneDX JSON (industry standard, Grype-compatible) |
| `> sbom.json` | stdout redirect | Save SBOM output to `sbom.json` in workspace root |

---

### 3.3 Stage: Vulnerability Scan (Grype)

Grype reads `sbom.json` and matches every component against its vulnerability database. The `sbom:` prefix tells Grype to treat the argument as an SBOM file rather than a live image reference.

```groovy
// Runs inside the same 'Generate Scan Report' stage script block:
sh """
    grype sbom:sbom.json -o json > vuln-report.json
"""
```

| Argument | Meaning |
|----------|---------|
| `sbom:sbom.json` | Input source — reads an SBOM file (not a live image pull) |
| `-o json` | Output format: structured JSON, consumable by the report generator |
| `> vuln-report.json` | Write vulnerability findings to `vuln-report.json` |

---

### 3.4 Stage: Generate HTML Report

A Python script at `/opt/generate-report.py` reads `vuln-report.json` and renders a styled HTML report saved as `vuln-report.html`. The script must be pre-deployed to `/opt/` on the Jenkins agent.

`generate-report.py` download link [Download-generate-report.py](https://github.com/UnstopableSafar08/DevOps/blob/main/jenkins/report-generator/generate-report.py)

```groovy
sh """
    python3 /opt/generate-report.py
"""

# Expected output:
# HTML report generated: vuln-report.html
```

> **ALT:** If Python is not installed on the agent, run the script inside a Docker container instead:
> ```bash
> docker run --rm \
>     -v $PWD:/workspace \
>     -w /workspace \
>     python:3.12-alpine \
>     python generate-report.py
> ```

---

### 3.5 Stage: Publish Scan Report

Archives the three scan output files as Jenkins build artifacts.

> **NOTE:** `publishHTML` requires the **HTML Publisher** plugin. If it is not installed, remove the `publishHTML` block — `archiveArtifacts` alone is sufficient to retain all output files.

```groovy
stage('Publish Scan Report') {
    steps {
        // Option A: HTML Publisher plugin required
        publishHTML([
            allowMissing:          false,
            alwaysLinkToLastBuild: true,
            keepAll:               true,
            reportDir:             '.',
            reportFiles:           'vuln-report.html',
            reportName:            'Security Vulnerability Report'
        ])

        // Always archive the raw files (no plugin required)
        archiveArtifacts artifacts: 'vuln-report.html,sbom.json,vuln-report.json',
                         fingerprint: true
    }
}
```

---

### 3.6 Full Pipeline (Combined Groovy)

```groovy
def remote = [:]
pipeline {
    agent {
        label 'jenkins-agent'
    }
    libraries {
        lib('jenkins-library@master')
    }
    environment {
        SCANNER_HOME = tool 'sonarqube'
        SONAR_TOKEN  = credentials('sonar-login-token')
    }
    tools {
        jdk    'java21'
        gradle 'gradle86'
    }
    options {
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '2'))
    }
    parameters {
        string(name: "Branch",  defaultValue: 'main', description: 'Branch to deploy')
        choice(choices: ['YES', 'NO'], name: 'ARCHIVE', description: 'Archive WAR for production?')
    }
    stages {

        stage('App Name') {
            steps {
                script {
                    env.APP_NAME = env.JOB_BASE_NAME
                        .replaceAll('-rel', '')
                        .replaceAll('(?i)^RELEASE-', '')
                        .toLowerCase()
                    echo "App Name: ${env.APP_NAME}"
                    // output: my-app
                }
            }
        }

        stage('Preparation') {
            steps {
                sh 'java -version'
                sh 'gradle -v'
            }
        }

        stage('Git Checkout') {
            steps {
                git branch: "${Branch}",
                    credentialsId: 'gitlab.example.com',
                    url: 'http://gitlab.example.com/example-corp/my-app.git'
            }
        }

        stage('App Build') {
            steps {
                sh 'gradle clean build'
            }
        }

        stage('Sonar Code Scan') {
            steps {
                withSonarQubeEnv('sonarqube') {
                    sh """
                        ${SCANNER_HOME}/bin/sonar-scanner \
                        -Dsonar.projectName=My-App \
                        -Dsonar.projectKey=My-App \
                        -Dsonar.token=${SONAR_TOKEN} \
                        -Dsonar.sources=src \
                        -Dsonar.java.binaries=build/classes/java/main \
                        -Dsonar.java.test.binaries=build/classes/java/test \
                        -Dsonar.java.libraries=build/libs/*.jar \
                        -Dsonar.sourceEncoding=UTF-8
                    """
                }
            }
        }

        stage('Sonar Quality Gate') {
            steps {
                timeout(time: 2, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: false
                }
            }
        }

        stage('OWASP Dependency-Check') {
            steps {
                sh 'mkdir -p dependency-check-report'
                dependencyCheck additionalArguments: '--scan . --format XML --format HTML --out dependency-check-report',
                                odcInstallation: 'dc'
                dependencyCheckPublisher pattern: 'dependency-check-report/dependency-check-report.xml'
            }
        }

        stage('Docker Image Build') {
            steps {
                sh "cp -af /opt/dockerfile/my-app-dockerfile ."
                sh "docker build -t ${env.APP_NAME}:${BUILD_NUMBER} -f my-app-dockerfile ."
            }
        }

        stage('Trivy Docker Image Scan') {
            steps {
                sh """
                    trivy image \
                        --severity CRITICAL,HIGH \
                        --cache-dir /var/lib/trivy \
                        ${env.APP_NAME}:\$BUILD_NUMBER
                """
            }
            post {
                failure {
                    echo "Trivy Image Scan found vulnerabilities!"
                }
            }
        }

        stage('Trivy FileSystem Scan') {
            steps {
                sh '''
                    trivy fs --format table --output trivy-fs-report.txt .
                    trivy fs --format template \
                        --template "/opt/html.tpl" \
                        --output trivy-fs-report.html .
                '''
            }
        }

        stage('Results') {
            steps {
                archiveArtifacts artifacts: '''
                    trivy-fs-report.html,
                    trivy-fs-report.txt,
                    dependency-check-report/dependency-check-report.xml,
                    dependency-check-report/dependency-check-report.html
                ''', fingerprint: true
            }
        }

        stage('Generate Scan Report') {
            steps {
                script {
                    def imageName = "${env.APP_NAME}:${BUILD_NUMBER}"
                    sh """
                        syft ${imageName} -o cyclonedx-json > sbom.json
                        grype sbom:sbom.json -o json > vuln-report.json
                        python3 /opt/generate-report.py
                    """
                }
            }
        }

        stage('Publish Scan Report') {
            steps {
                archiveArtifacts artifacts: 'vuln-report.html,sbom.json,vuln-report.json',
                                 fingerprint: true
            }
        }

        stage('Publish Artifact') {
            steps {
                script {
                    if ("${ARCHIVE}" == 'YES') {
                        echo "Archiving JAR for production deployment"
                        remote.name     = "${env.server_name}"
                        remote.host     = "${env.artifact_url}"
                        remote.user     = "${env.artifact_username}"
                        remote.password = "${env.artifact_password}"
                        runCommand([
                            remote:  remote,
                            command: "mkdir -p /home/artifact-user/prod/${Branch}"
                        ])
                        uploadTomcat([
                            remote:       remote,
                            artifactFrom: "build/libs/my-app-1.0.0.jar",
                            artifactTo:   "/home/artifact-user/prod/${Branch}/MyApp.jar",
                            propsFrom:    "",
                            propsTo:      ""
                        ])
                    } else {
                        echo "ARCHIVE=NO — skipping artifact upload"
                    }
                }
            }
        }

    }
}
```

---

## 4. Jenkins CSP Fix for HTML Reports

Jenkins applies a strict Content Security Policy (CSP) by default that blocks inline JavaScript and CSS inside archived HTML files. This causes `vuln-report.html` to render without styles or interactive elements.

> **WARN:** Relaxing CSP is appropriate for internal CI/CD environments where only trusted reports are published.

### 4.1 Apply the CSP Fix (Runtime)

Navigate to **Jenkins Dashboard → Manage Jenkins → Script Console** and run:

```groovy
System.setProperty(
  "hudson.model.DirectoryBrowserSupport.CSP",
  "default-src 'self' 'unsafe-inline' 'unsafe-eval'; img-src 'self' data:;"
)
```

### 4.2 Make the Fix Persistent (Across Restarts)

The `System.setProperty` call is not persistent. To make it permanent, add the JVM flag to the Jenkins startup config:

```bash
# Location varies by OS:
#   RHEL/EL9:  /etc/sysconfig/jenkins
#   Debian:    /etc/default/jenkins

# Add to JENKINS_JAVA_OPTIONS:
JENKINS_JAVA_OPTIONS="-Dhudson.model.DirectoryBrowserSupport.CSP=\
  default-src 'self' 'unsafe-inline' 'unsafe-eval'; img-src 'self' data:;"
```

---

## 5. End-to-End Pipeline Flow

```
Git Repository
    │
    ▼
gradle clean build
    │  → Compiled classes + JAR/WAR
    ▼
docker build
    │  → Container image: <app-name>:<build-number>
    ▼
syft <image> -o cyclonedx-json
    │  → sbom.json  (CycloneDX SBOM)
    ▼
grype sbom:sbom.json -o json
    │  → vuln-report.json  (CVE findings)
    ▼
python3 /opt/generate-report.py
    │  → vuln-report.html  (rendered HTML report)
    ▼
archiveArtifacts / publishHTML
    └  → Jenkins build artifacts + sidebar report link
```

---

## 6. Output Files Reference

| File | Format | Description |
|------|--------|-------------|
| `sbom.json` | CycloneDX JSON | Full SBOM — all packages, versions, licenses found in the image |
| `vuln-report.json` | Grype JSON | Raw CVE findings: CVE IDs, severity, affected packages, fix versions |
| `vuln-report.html` | HTML | Styled human-readable vulnerability report from Python renderer |
| `trivy-fs-report.txt` | Text table | Trivy filesystem scan in plain table format |
| `trivy-fs-report.html` | HTML | Trivy filesystem scan rendered via `/opt/html.tpl` template |
| `dependency-check-report.xml` | XML | OWASP Dependency-Check findings (machine-readable) |
| `dependency-check-report.html` | HTML | OWASP Dependency-Check findings (human-readable) |

---

## 7. Troubleshooting

### 7.1 `publishHTML`: No such DSL method

**Cause:** HTML Publisher plugin is not installed.

**Fix:** Install via Manage Jenkins → Plugins → search `HTML Publisher`. Or remove the `publishHTML` block — `archiveArtifacts` preserves all files without the plugin.

---

### 7.2 Syft / Grype: `command not found`

**Cause:** Binaries not in PATH for the Jenkins agent user.

```bash
# Verify PATH as jenkins user
sudo -u jenkins which syft
sudo -u jenkins which grype

# If missing, re-run install as root and confirm /usr/local/bin is in PATH
echo $PATH
```

---

### 7.3 HTML Report Renders Without Styles

**Cause:** Jenkins CSP blocks inline CSS/JS in archived HTML files.

**Fix:** Apply the CSP override described in [Section 4](#4-jenkins-csp-fix-for-html-reports).

---

### 7.4 Grype DB Not Updated

Grype downloads its vulnerability database on first run. On air-gapped systems, pre-populate the DB manually.

```bash
# Update Grype vulnerability database
grype db update

# Check DB status
grype db status

# For air-gapped: set custom DB URL in ~/.grype.yaml
# db:
#   update-url: http://internal-mirror/grype/listing.json
```

---

### 7.5 Trivy Cache Permission Error

The pipeline uses `--cache-dir /var/lib/trivy`. Ensure the Jenkins agent user has write permission.

```bash
mkdir -p /var/lib/trivy
chown jenkins:jenkins /var/lib/trivy
```

---

### 7.6 Python Script Not Found

```bash
# Verify script exists on agent
ls -la /opt/generate-report.py

# Verify Python is available
python3 --version

# If Python missing on agent, use Docker alternative (see Section 3.4)
```

---

## 8. Quick Reference

### 8.1 Key Commands

```bash
# Generate SBOM from Docker image
syft <image>:<tag> -o cyclonedx-json > sbom.json

# Generate SBOM from local directory
syft dir:/path/to/project -o cyclonedx-json > sbom.json

# Scan SBOM for vulnerabilities
grype sbom:sbom.json -o json > vuln-report.json

# Scan and fail pipeline on HIGH+ CVEs
grype sbom:sbom.json --fail-on high -o json > vuln-report.json

# Update Grype vulnerability DB
grype db update

# Check Grype DB status
grype db status
```

### 8.2 Supported SBOM Formats

| Format | Syft Flag | Notes |
|--------|-----------|-------|
| CycloneDX JSON | `-o cyclonedx-json` | Recommended — best Grype compatibility |
| CycloneDX XML | `-o cyclonedx-xml` | Alternative for XML-based tooling |
| SPDX JSON | `-o spdx-json` | SPDX 2.3 format |
| SPDX Tag-Value | `-o spdx-tv` | Human-readable SPDX |
| Syft JSON | `-o json` | Syft-native format, most verbose |
| Table | `-o table` | Human-readable terminal output only |

### 8.3 Grype Severity Levels

| Level | CVSS Range | Recommended Action |
|-------|------------|-------------------|
| **CRITICAL** | 9.0 – 10.0 | Block deployment, fix immediately |
| **HIGH** | 7.0 – 8.9 | Fix before next release |
| **MEDIUM** | 4.0 – 6.9 | Track and fix in sprint |
| **LOW** | < 4.0 | Fix opportunistically |
| **NEGLIGIBLE** | — | Monitor only |

---

*SBOM Security Scanning Pipeline — Example Corp Internal Documentation*
