# Secret Scanning in Jenkins: Gitleaks & TruffleHog

> A practical guide for DevOps engineers — installation, configuration, and pipeline integration.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Terminologies](#terminologies)
3. [Tool Comparison](#tool-comparison)
4. [Prerequisites](#prerequisites)
5. [Installation](#installation)
6. [Configuration](#configuration)
7. [Jenkins Pipeline Integration](#jenkins-pipeline-integration)
8. [Sample Jenkinsfile](#sample-jenkinsfile)
9. [Understanding Results](#understanding-results)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)

---

## Introduction

Modern software development involves storing code in Git repositories. Developers sometimes accidentally commit sensitive information — API keys, passwords, tokens, or private certificates — directly into source code. Once a secret is pushed to a repository, it is potentially exposed to anyone with access, and even after deletion, it remains in Git history.

**Secret scanning** is the practice of automatically detecting these leaked credentials before they cause security incidents. Integrating secret scanning into your CI/CD pipeline (Jenkins) ensures every code commit is checked automatically.

This guide covers two industry-standard open-source tools:

- **Gitleaks** — fast regex-based scanner, catches everything
- **TruffleHog** — deep scanner with live secret verification

Used together, they provide both broad coverage and high-confidence alerting.

---

## Terminologies

| Term | Explanation |
|------|-------------|
| **Secret / Credential** | Sensitive data: API keys, passwords, tokens, private keys, connection strings |
| **False Positive** | A finding that looks like a secret but is not (e.g., a test token, dummy value) |
| **Entropy** | A measure of randomness in a string. High entropy = likely a real secret |
| **Regex** | Regular expression — a pattern used to match strings (e.g., `AKIA[A-Z0-9]{16}` matches AWS keys) |
| **Verified Secret** | A secret that has been confirmed as valid/active by calling the actual API (TruffleHog feature) |
| **Git History** | All previous commits in a repository — secrets hidden here are still dangerous |
| **UNSTABLE build** | Jenkins build status meaning: completed but with warnings — pipeline did not hard fail |
| **Allowlist / Ignore** | Rules telling the scanner to skip known false positives |
| **Scan depth** | How far back in Git history the tool scans |
| **SARIF** | Static Analysis Results Interchange Format — standard report format for security tools |
| **Exit code** | A number a program returns when it finishes: `0` = success, `1` = issue found |
| **`--only-verified`** | TruffleHog flag: only report secrets confirmed live by external API call |
| **htpasswd** | Apache-style password file — often stored in repos by mistake |
| **`.env` file** | Environment variable file — common source of leaked secrets |

---

## Tool Comparison

| Feature | Gitleaks | TruffleHog |
|---------|----------|-----------|
| Language | Go | Go |
| Detection method | Regex + entropy | Regex + entropy + live verification |
| Secret verification | No | Yes (`--only-verified`) |
| False positives | More (noisy) | Fewer (verified only) |
| Speed | Fast | Slower (API calls) |
| Git history scan | Yes | Yes (deep) |
| Filesystem scan | Yes | Yes |
| Docker/S3/GCS scan | No | Yes |
| Custom rules | Yes (`.gitleaks.toml`) | Limited |
| Output formats | JSON, CSV, SARIF | JSON |
| License | MIT | AGPL-3.0 |
| Best for | Fast gate, broad coverage | Confirming real active secrets |

**Recommended strategy:**
- Gitleaks = fast fail gate on every commit
- TruffleHog = deep verified scan (nightly or on PRs)

---

## Prerequisites

- Jenkins installed (master + slave setup)
- Jenkins slave running RHEL 9 / CentOS / OracleLinux
- Root or sudo access on Jenkins slave
- Node.js and npm (for reference — tools are Go binaries, no Node required)
- Internet access from slave (for TruffleHog secret verification)
- Git installed on slave

---

## Installation

### Install Gitleaks

```bash
# Get latest version
GITLEAKS_VERSION=$(curl -s https://api.github.com/repos/gitleaks/gitleaks/releases/latest | grep tag_name | cut -d '"' -f4 | tr -d v)
echo "Installing Gitleaks v${GITLEAKS_VERSION}"

# Download and extract
curl -L "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" \
  -o /tmp/gitleaks.tar.gz

tar xzf /tmp/gitleaks.tar.gz -C /usr/local/bin/ gitleaks
chmod +x /usr/local/bin/gitleaks

# Verify
gitleaks version
```

### Install TruffleHog

```bash
# Get latest version
TRUFFLEHOG_VERSION=$(curl -s https://api.github.com/repos/trufflesecurity/trufflehog/releases/latest | grep '"tag_name"' | cut -d '"' -f4 | tr -d v)
echo "Installing TruffleHog v${TRUFFLEHOG_VERSION}"

# Download and extract
curl -L "https://github.com/trufflesecurity/trufflehog/releases/download/v${TRUFFLEHOG_VERSION}/trufflehog_${TRUFFLEHOG_VERSION}_linux_amd64.tar.gz" \
  -o /tmp/trufflehog.tar.gz

tar xzf /tmp/trufflehog.tar.gz -C /usr/local/bin/ trufflehog
chmod +x /usr/local/bin/trufflehog

# Verify
trufflehog --version
```

### Fix ownership and permissions

```bash
chown root:root /usr/local/bin/gitleaks /usr/local/bin/trufflehog
chmod 755 /usr/local/bin/gitleaks /usr/local/bin/trufflehog

# Verify jenkins user can execute
su - jenkin -c "gitleaks version"
su - jenkin -c "trufflehog --version"
```

### Verify both installed

```bash
which gitleaks && gitleaks version
which trufflehog && trufflehog --version
```

Expected output:
```
/usr/local/bin/gitleaks
8.30.1
/usr/local/bin/trufflehog
trufflehog 3.95.3
```

---

## Configuration

### Gitleaks Configuration (`.gitleaks.toml`)

Create this file in the root of your repository to customize scan behavior:

```toml
# .gitleaks.toml
# Gitleaks configuration file
# Place in repository root

[extend]
# Use default built-in rules as base
useDefault = true

# -----------------------------------------------
# Allowlist: skip known false positives
# -----------------------------------------------
[allowlist]
description = "Global allowlist"

# Skip specific commits (e.g. old commits with known test data)
commits = [
  "abc123def456",
]

# Skip files matching these patterns
paths = [
  '''package-lock\.json''',
  '''yarn\.lock''',
  '''\.gitleaks\.toml''',
  '''test/fixtures/''',
  '''docs/''',
]

# Skip matches containing these strings/patterns
regexes = [
  '''(?i)(test|dummy|example|fake|sample|placeholder)''',
  '''(?i)changeme''',
  '''(?i)your[-_]?secret[-_]?here''',
]

# -----------------------------------------------
# Custom Rules (add your own patterns)
# -----------------------------------------------

# Example: detect internal API tokens
[[rules]]
id = "internal-api-token"
description = "Internal test API Token"
regex = '''test[-_]?token[-_]?[a-zA-Z0-9]{32}'''
tags = ["internal", "api"]
```

### TruffleHog — No config file needed

TruffleHog is controlled entirely via CLI flags:

```bash
# Scan only verified secrets (recommended for CI)
trufflehog git file://. --json --only-verified

# Scan all (verified + unverified) — more noisy
trufflehog git file://. --json

# Scan specific branch
trufflehog git file://. --branch main --json --only-verified

# Scan since specific commit
trufflehog git file://. --since-commit <commit_sha> --json --only-verified

# Scan filesystem (not git)
trufflehog filesystem /path/to/dir --json
```

---

## Jenkins Pipeline Integration

### Pipeline Stage Order

```
Checkout → Gitleaks Scan → TruffleHog Scan → Build → Test → Deploy
```

Secret scanning runs **before build** — fail fast, save time.

### Build Status Behavior

| Scenario | `Fail build` mode | `Warn only` mode |
|----------|------------------|-----------------|
| No secrets found | SUCCESS | SUCCESS |
| Gitleaks finds something | FAILURE | UNSTABLE |
| TruffleHog finds verified secret | FAILURE | UNSTABLE |
| Build still runs | No | Yes |

### Archived Reports

Both stages archive reports as Jenkins build artifacts:
- `gitleaks-report.json` — all findings with file, line, rule
- `trufflehog-report.json` — verified live secrets only

---

## Sample Jenkinsfile

```groovy
pipeline {
    agent any

    environment {
        // Report file names
        GITLEAKS_REPORT  = 'gitleaks-report.json'
        TRUFFLEHOG_REPORT = 'trufflehog-report.json'
    }

    stages {

        // -----------------------------------------------
        // Stage 1: Checkout
        // -----------------------------------------------
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        // -----------------------------------------------
        // Stage 2: Gitleaks — Fast regex scan
        //   - Scans all files for secret patterns
        //   - Does NOT verify secrets (may have false positives)
        //   - Result: UNSTABLE if findings exist
        // -----------------------------------------------
        stage('Secret Scan - Gitleaks') {
            steps {
                script {
                    def status = sh(
                        script: """
                            gitleaks detect \\
                              --source . \\
                              --report-format json \\
                              --report-path ${env.GITLEAKS_REPORT} \\
                              --redact \\
                              --exit-code 1 \\
                              2>/dev/null
                        """,
                        returnStatus: true
                    )

                    if (status != 0) {
                        echo "[WARN] Gitleaks detected potential secrets. Review ${env.GITLEAKS_REPORT}"
                        currentBuild.result = 'UNSTABLE'
                    } else {
                        echo "[OK] Gitleaks: No secrets found."
                    }
                }
            }
            post {
                always {
                    // Archive report regardless of result
                    archiveArtifacts artifacts: "${env.GITLEAKS_REPORT}", allowEmptyArchive: true
                }
            }
        }

        // -----------------------------------------------
        // Stage 3: TruffleHog — Deep verified scan
        //   - Scans full git history
        //   - Verifies secrets by calling live APIs
        //   - Only flags REAL active secrets
        //   - Result: UNSTABLE if verified secrets found
        // -----------------------------------------------
        stage('Secret Scan - TruffleHog') {
            steps {
                script {
                    sh """
                        trufflehog git file://. \\
                          --json \\
                          --only-verified \\
                          2>/dev/null > ${env.TRUFFLEHOG_REPORT} || true
                    """

                    // Check if report has content (non-zero byte = findings)
                    def reportSize = sh(
                        script: "wc -c < ${env.TRUFFLEHOG_REPORT}",
                        returnStdout: true
                    ).trim().toInteger()

                    if (reportSize > 0) {
                        echo "[WARN] TruffleHog found VERIFIED active secrets! Review ${env.TRUFFLEHOG_REPORT} immediately."
                        currentBuild.result = 'UNSTABLE'
                    } else {
                        echo "[OK] TruffleHog: No verified secrets found."
                    }
                }
            }
            post {
                always {
                    archiveArtifacts artifacts: "${env.TRUFFLEHOG_REPORT}", allowEmptyArchive: true
                }
            }
        }

        // -----------------------------------------------
        // Stage 4: Build
        //   - Runs even if scans found warnings (UNSTABLE)
        //   - Change currentBuild.result = 'FAILURE' above
        //     in scan stages if you want to block builds
        // -----------------------------------------------
        stage('Build') {
            steps {
                echo 'Running build...'
                // sh 'mvn clean package'
                // sh 'npm install && npm run build'
            }
        }

        // -----------------------------------------------
        // Stage 5: Test
        // -----------------------------------------------
        stage('Test') {
            steps {
                echo 'Running tests...'
                // sh 'mvn test'
            }
        }

        // -----------------------------------------------
        // Stage 6: Deploy
        // -----------------------------------------------
        stage('Deploy') {
            when {
                // Only deploy on clean or unstable builds
                expression { currentBuild.result != 'FAILURE' }
            }
            steps {
                echo 'Deploying...'
            }
        }
    }

    // -----------------------------------------------
    // Post pipeline actions
    // -----------------------------------------------
    post {
        unstable {
            echo '''
[WARN] Build marked UNSTABLE — secrets were detected.
Review archived reports: gitleaks-report.json / trufflehog-report.json
Take action: rotate any confirmed secrets immediately.
            '''
        }
        success {
            echo '[OK] Pipeline passed. No secrets detected.'
        }
        failure {
            echo '[ERR] Pipeline failed.'
        }
    }
}
```

---

## Understanding Results

### Gitleaks Report (`gitleaks-report.json`)

```json
[
  {
    "Description": "AWS Access Token",
    "RuleID": "aws-access-token",
    "Match": "REDACTED",
    "Secret": "REDACTED",
    "File": "src/config/settings.py",
    "SymlinkFile": "",
    "Line": 42,
    "Commit": "abc123",
    "Entropy": 3.5,
    "Author": "developer@example.com",
    "Date": "2024-01-15T10:30:00Z"
  }
]
```

Key fields:

| Field | Meaning |
|-------|---------|
| `RuleID` | Which rule triggered (e.g. `aws-access-token`) |
| `File` | File containing the secret |
| `Line` | Line number |
| `Commit` | Git commit SHA where secret was introduced |
| `Entropy` | Randomness score (higher = more likely real secret) |
| `Author` | Who committed it |

### TruffleHog Report (`trufflehog-report.json`)

```json
{
  "SourceMetadata": {
    "Data": {
      "Git": {
        "commit": "abc123",
        "file": "config/database.yml",
        "line": 10,
        "repository": "https://github.com/org/repo"
      }
    }
  },
  "SourceID": 1,
  "SourceType": 16,
  "DetectorType": 2,
  "DetectorName": "AWS",
  "Verified": true,
  "Raw": "AKIAIOSFODNN7EXAMPLE",
  "ExtraData": {
    "account": "123456789012",
    "arn": "arn:aws:iam::123456789012:user/developer"
  }
}
```

`"Verified": true` = **this secret is LIVE and active. Rotate immediately.**

### Empty TruffleHog Report

An empty `trufflehog-report.json` (zero bytes) with `--only-verified` flag means:
- No active/live secrets found, OR
- Secrets found but already rotated/expired

This is expected and normal for clean repositories.

---

## Best Practices

### Immediate actions when secrets found

1. **Rotate the secret immediately** — revoke/regenerate in the provider (AWS, GitHub, etc.)
2. **Remove from code** — delete the hardcoded value, use environment variables
3. **Clean Git history** — use `git filter-branch` or BFG Repo Cleaner
4. **Notify security team** — log the incident

### Prevent future leaks

```bash
# Install gitleaks as pre-commit hook (developer machine)
gitleaks protect --staged --source .

# Add to .git/hooks/pre-commit
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
gitleaks protect --staged --source . --exit-code 1
EOF
chmod +x .git/hooks/pre-commit
```

### Use environment variables, not hardcoded secrets

```bash
# Bad
DB_PASSWORD=supersecret123

# Good — use Jenkins credentials store
withCredentials([string(credentialsId: 'db-password', variable: 'DB_PASSWORD')]) {
    sh 'your-script.sh'
}
```

### Keep tools updated

```bash
# Check current versions
gitleaks version
trufflehog --version

# Re-run installation script periodically
# Or add version check to pipeline
```

---

## Troubleshooting

### Gitleaks finds too many false positives

Add to `.gitleaks.toml`:
```toml
[allowlist]
regexes = ['''(?i)(test|dummy|fake|example)''']
paths = ['''test/''', '''fixtures/''']
```

### TruffleHog report always empty

Check without `--only-verified`:
```bash
trufflehog git file://. --json 2>/dev/null | wc -l
```
If findings appear = secrets exist but already rotated (not live).
If still empty = repository is clean.

### Permission denied running tools

```bash
# Verify executable permissions
ls -la /usr/local/bin/gitleaks /usr/local/bin/trufflehog
# Should show: -rwxr-xr-x

# Fix if needed
chmod 755 /usr/local/bin/gitleaks /usr/local/bin/trufflehog
```

### Tools not found in Jenkins pipeline

```groovy
// Add tool path explicitly in Jenkinsfile
environment {
    PATH = "/usr/local/bin:${env.PATH}"
}
```

Or verify on Jenkins slave:
```bash
su - jenkin -c "which gitleaks"
su - jenkin -c "which trufflehog"
```

### Gitleaks fails on non-git directory

```bash
# Use --no-git flag for non-git directories
gitleaks detect --source /path --no-git --report-format json
```

### TruffleHog slow on large repos

```bash
# Limit scan to recent commits only
trufflehog git file://. --since-commit HEAD~50 --json --only-verified
```

---

## Quick Reference

```bash
# Manual scan — current directory
gitleaks detect --source . --report-format json --report-path report.json

# Manual scan — full git history
trufflehog git file://. --json --only-verified

# Test on specific file
gitleaks detect --source . --no-git --report-format json

# Check gitleaks rules
gitleaks rules

# Verbose TruffleHog output
trufflehog git file://. --json 2>&1 | head -100

# Count gitleaks findings
cat gitleaks-report.json | python3 -m json.tool | grep RuleID | wc -l
```

---

*Guide maintained by: DevOps Team*
*Tools: Gitleaks v8.30.1 | TruffleHog v3.95.3*
*Platform: RHEL 9 | Jenkins*
