# Jenkins Android AAR Build & Artifactory Upload Guide

**Author:** Sagar Malla  
**Project:** Android android SDK  
**Stack:** Jenkins · Gradle 9.4.1 · JDK 17 · JFrog Artifactory · RHEL/EL9  
**Last Updated:** April 2025

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Option A — Without Artifactory Plugin (curl-based)](#option-a--without-artifactory-plugin-curl-based)
   - [JFrog Artifactory Setup on EL9](#jfrog-artifactory-setup-on-el9)
   - [Create Repository and User in Artifactory](#create-repository-and-user-in-artifactory)
   - [Jenkins Configuration](#jenkins-configuration-option-a)
   - [Pipeline Script](#pipeline-script-option-a)
5. [Option B — With Artifactory Plugin](#option-b--with-artifactory-plugin)
   - [Install Artifactory Plugin in Jenkins](#install-artifactory-plugin-in-jenkins)
   - [Configure Artifactory in Jenkins](#configure-artifactory-in-jenkins)
   - [Pipeline Script](#pipeline-script-option-b)
6. [Gradle Commands Reference](#gradle-commands-reference)
7. [Artifactory Upload Path Structure](#artifactory-upload-path-structure)
8. [Troubleshooting](#troubleshooting)

---

## Overview

This guide documents two approaches for building an Android AAR library package using Jenkins and uploading it to JFrog Artifactory:

- **Option A** — Pure `curl`-based upload. No Artifactory plugin required. JFrog Artifactory is installed on a separate EL9 Linux server. Best for minimal Jenkins footprint and direct REST API control.
- **Option B** — Uses the official Jenkins Artifactory plugin. Provides richer metadata, build info tracking, and native UI integration inside Jenkins.

Both options use the same Gradle build pipeline. The only difference is the upload stage.

---

## Architecture

```
┌─────────────────────────────┐        ┌──────────────────────────────┐
│       Jenkins Server        │        │     JFrog Artifactory Server  │
│                             │        │                              │
│  Pipeline:                  │  curl  │  http://10.10.10.100:8081   │
│  1. Checkout (GitLab)       │───────►│                              │
│  2. Gradle Clean            │        │  Repo: android-sdk    │
│  3. Gradle Build            │        │  User: sdk-admin             │
│  4. Gradle Assemble (AAR)   │        │                              │
│  5. Upload AAR ─────────────┼───────►│  Path:                       │
│                             │        │  android-sdk/         │
│  Agent: master              │        │    DevDebug/                 │
│  User:  jenkin              │        │      15-f6fb52f/             │
│  JDK:   jdk17               │        │        app-devdebug.aar      │
│  Gradle: 9.4.1              │        │                              │
└─────────────────────────────┘        └──────────────────────────────┘
         │
         │ git clone
         ▼
┌─────────────────────┐
│  GitLab             │
│  sagar-android.git   │
│  branch: develop    │
└─────────────────────┘
```

---

## Prerequisites

### Jenkins Server

| Requirement | Value |
|---|---|
| Jenkins version | 2.400+ (LTS recommended) |
| Agent label | `master` |
| Jenkins OS user | `jenkin` |
| JDK | JDK 17 (configured in Jenkins Tools as `jdk17`) |
| Gradle | Gradle 9.4.1 installed at `/home/jenkin/gradle-9.4.1` (configured in Jenkins Tools as `gradle941`) |
| Git | Any version available on PATH |
| curl | Must support HTTP (`curl --version` shows `http` in Protocols) |

### Gradle Tool Setup in Jenkins

```
Jenkins → Manage Jenkins → Tools → Gradle Installations

Name         : gradle941
GRADLE_HOME  : /home/jenkin/gradle-9.4.1
```

### JDK Tool Setup in Jenkins

```
Jenkins → Manage Jenkins → Tools → JDK Installations

Name         : jdk17
JAVA_HOME    : /path/to/jdk17
```

### Jenkins Credentials Required

| Credential ID | Type | Usage |
|---|---|---|
| `gitlab-sdk-creds` | Username/Password | GitLab repository clone |
| `jfrog-creds` | Username/Password | Artifactory upload |

---

## Option A — Without Artifactory Plugin (curl-based)

This approach uses the JFrog Artifactory REST API directly via `curl`. No Jenkins plugin installation is required. JFrog Artifactory is installed fresh on a separate EL9 server.

---

### JFrog Artifactory Setup on EL9

#### Step 1 — System Prerequisites

Run on the **Artifactory server** as root:

```bash
# Update system
dnf update -y

# Install required packages
dnf install -y java-17-openjdk wget curl net-tools

# Verify Java
java -version
```

#### Step 2 — Create Dedicated System User

```bash
useradd -r -m -d /opt/jfrog -s /sbin/nologin artifactory
```

#### Step 3 — Download and Install Artifactory OSS

```bash
# Download Artifactory OSS (free version)
wget -O /tmp/artifactory.tar.gz \
  "https://releases.jfrog.io/artifactory/artifactory-pro/org/artifactory/pro/jfrog-artifactory-pro/7.77.7/jfrog-artifactory-pro-7.77.7-linux.tar.gz"

# Extract to /opt/jfrog
mkdir -p /opt/jfrog
tar -xzf /tmp/artifactory.tar.gz -C /opt/jfrog --strip-components=1

# Set ownership
chown -R artifactory:artifactory /opt/jfrog
```

> **Note:** Replace `7.77.7` with the latest stable version from https://jfrog.com/open-source/

#### Step 4 — Configure Artifactory as a systemd Service

```bash
# Copy the provided service script
cp /opt/jfrog/artifactory/bin/artifactory.service /etc/systemd/system/

# Reload systemd and enable
systemctl daemon-reload
systemctl enable artifactory
systemctl start artifactory

# Verify status
systemctl status artifactory
```

#### Step 5 — Firewall Configuration

```bash
# Allow Artifactory port through firewalld
firewall-cmd --permanent --add-port=8081/tcp
firewall-cmd --permanent --add-port=8082/tcp
firewall-cmd --reload

# Verify
firewall-cmd --list-ports
```

#### Step 6 — Verify Artifactory is Running

```bash
# Should return: OK
curl http://localhost:8081/artifactory/api/system/ping

# Access UI
# http://<server-ip>:8082/ui
# Default credentials: admin / password
```

> **Important:** Change the default `admin` password immediately after first login via the UI.

---

### Create Repository and User in Artifactory

#### Create Repository `android-sdk`

```
Artifactory UI → Administration → Repositories → Add Repositories → Local Repository
```

| Field | Value |
|---|---|
| Package Type | Generic |
| Repository Key | `android-sdk` |
| Layout | `simple-default` |
| Description | Android android SDK AAR artifacts |

Click **Save & Finish**.

#### Create User `sdk-admin`

```
Administration → Identity and Access → Users → New User
```

| Field | Value |
|---|---|
| Username | `sdk-admin` |
| Password | (set a strong password) |
| Email | sdk-admin@sagar.com.np |
| Admin | No |

Click **Save**.

#### Assign Deploy Permission

```
Administration → Identity and Access → Permissions → New Permission
```

| Field | Value |
|---|---|
| Name | `android-sdk-deploy` |
| Repositories | `android-sdk` |
| Users | `sdk-admin` |
| Permissions | Read, Deploy/Cache, Annotate |

Click **Save**.

#### Verify Upload Works from Jenkins Server

Run this from the Jenkins agent machine before running the pipeline:

```bash
# Ping test
curl -u sdk-admin:'YOUR_PASSWORD' \
  "http://10.10.10.100:8081/artifactory/api/system/ping"
# Expected: OK

# Upload test
echo "test" > /tmp/test.txt
curl -f -u sdk-admin:'YOUR_PASSWORD' \
  -T /tmp/test.txt \
  "http://10.10.10.100:8081/artifactory/android-sdk/test/test.txt"
# Expected: JSON response with downloadUri
```

---

### Jenkins Configuration (Option A)

#### Add `jfrog-creds` Credential

```
Jenkins → Manage Jenkins → Credentials → System → Global Credentials → Add Credentials
```

| Field | Value |
|---|---|
| Kind | Username with password |
| Username | `sdk-admin` |
| Password | (your Artifactory password) |
| ID | `jfrog-creds` |
| Description | JFrog Artifactory SDK Admin |

---

### Pipeline Script (Option A)

```groovy
pipeline {
    agent { label 'master' }

    tools {
        gradle 'gradle941'
        jdk 'jdk17'
    }

    options {
        disableConcurrentBuilds()
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '30'))
        timeout(time: 30, unit: 'MINUTES')
    }

    parameters {
        string(
            name: 'BRANCH',
            defaultValue: 'develop',
            description: 'Git branch to build'
        )
        choice(
            name: 'BUILD_VARIANT',
            choices: ['DevDebug', 'DevRelease', 'LiveDebug', 'LiveRelease'],
            description: 'Android build variant'
        )
        booleanParam(
            name: 'PUBLISH_TO_ARTIFACTORY',
            defaultValue: true,
            description: 'Upload AAR to JFrog Artifactory'
        )
    }

    environment {
        JVM_OPTIONS      = '-Xms2g -Xmx4g -XX:+UseG1GC'
        ARTIFACTORY_URL  = 'http://10.10.10.100:8081/artifactory'
        ARTIFACTORY_REPO = 'android-sdk'
    }

    stages {

        stage('Checkout') {
            steps {
                cleanWs()
                git branch: "${params.BRANCH}",
                    credentialsId: 'gitlab-sdk-creds',
                    url: 'https://gitlab-sdk.sagar.com.np/sagar/sagar-android.git'
            }
        }

        stage('Init') {
            steps {
                script {
                    env.SHORT_COMMIT = sh(
                        script: 'git rev-parse --short HEAD',
                        returnStdout: true
                    ).trim()

                    env.BUILD_VERSION = "${BUILD_NUMBER}-${env.SHORT_COMMIT}"
                }

                sh 'java -version'
                sh 'gradle -v'

                echo "--------------------------------------------"
                echo "Branch        : ${params.BRANCH}"
                echo "Build Variant : ${params.BUILD_VARIANT}"
                echo "Build Version : ${env.BUILD_VERSION}"
                echo "Publish       : ${params.PUBLISH_TO_ARTIFACTORY}"
                echo "--------------------------------------------"
            }
        }

        stage('Clean') {
            steps {
                sh "./gradlew clean -Dorg.gradle.jvmargs='${env.JVM_OPTIONS}'"
            }
        }

        stage('Build Android Package') {
            steps {
                sh """
                    ./gradlew assemble${params.BUILD_VARIANT} \
                        --parallel \
                        --build-cache \
                        -Dorg.gradle.jvmargs='${env.JVM_OPTIONS}'
                """
            }
        }

        stage('Run Unit Tests') {
            steps {
                sh "./gradlew test${params.BUILD_VARIANT}UnitTest -Dorg.gradle.jvmargs='${env.JVM_OPTIONS}'"
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: '**/TEST-*.xml'
                }
            }
        }

        stage('Locate Android Package') {
            steps {
                script {
                    sh "echo '[INFO] AAR scan:' && find . -path '*/build/outputs/aar/*.aar' -ls"

                    env.AAR_FILE = sh(
                        script: "find . -path '*/build/outputs/aar/*.aar' | head -n 1",
                        returnStdout: true
                    ).trim()

                    if (!env.AAR_FILE) {
                        error "[ERROR] AAR not found. Verify the module applies 'com.android.library' plugin."
                    }

                    env.FILE_NAME = sh(
                        script: "basename ${env.AAR_FILE}",
                        returnStdout: true
                    ).trim()

                    echo "[INFO] AAR located : ${env.AAR_FILE}"
                    echo "[INFO] File name   : ${env.FILE_NAME}"
                }
            }
        }

        stage('Archive Android Package') {
            steps {
                archiveArtifacts artifacts: '**/*.aar', fingerprint: true
            }
        }

        stage('Upload to Artifactory') {
            when {
                expression { return params.PUBLISH_TO_ARTIFACTORY }
            }
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'jfrog-creds',
                    usernameVariable: 'JF_USER',
                    passwordVariable: 'JF_PASS'
                )]) {
                    script {
                        def targetUrl = "${env.ARTIFACTORY_URL}/${env.ARTIFACTORY_REPO}/${params.BUILD_VARIANT}/${env.BUILD_VERSION}/${env.FILE_NAME}"

                        echo "[INFO] Uploading  : ${env.FILE_NAME}"
                        echo "[INFO] Target URL : ${targetUrl}"

                        sh """
                            HTTP_CODE=\$(curl -s \
                                -o /tmp/artifactory-response-${BUILD_NUMBER}.json \
                                -w "%{http_code}" \
                                -u \$JF_USER:\$JF_PASS \
                                -T "${env.AAR_FILE}" \
                                "${targetUrl}")

                            echo "[INFO] Artifactory response:"
                            cat /tmp/artifactory-response-${BUILD_NUMBER}.json || true
                            echo ""
                            echo "[INFO] HTTP Status: \$HTTP_CODE"

                            if [ "\$HTTP_CODE" -lt 200 ] || [ "\$HTTP_CODE" -gt 299 ]; then
                                echo "[ERROR] Upload failed with HTTP \$HTTP_CODE"
                                exit 1
                            fi

                            echo "[OK] Upload successful: ${targetUrl}"
                        """
                    }
                }
            }
        }
    }

    post {
        success {
            echo "[SUCCESS] Build ${env.BUILD_VERSION} | Variant: ${params.BUILD_VARIANT} | Branch: ${params.BRANCH}"
        }
        failure {
            echo "[FAILED] Build ${env.BUILD_VERSION} failed. Check logs above."
        }
        aborted {
            echo "[ABORTED] Build ${env.BUILD_VERSION} was aborted."
        }
        always {
            sh "rm -f /tmp/artifactory-response-${BUILD_NUMBER}.json || true"
            cleanWs()
        }
    }
}
```

---

## Option B — With Artifactory Plugin

The Artifactory Plugin for Jenkins provides native build integration, automatic SHA1/MD5 checksum verification, build info publishing, and artifact promotion support — all without writing any curl commands.

---

### Install Artifactory Plugin in Jenkins

```
Jenkins → Manage Jenkins → Plugins → Available Plugins

Search: "Artifactory"
Install: "Artifactory Plugin" by JFrog
Restart Jenkins after install
```

---

### Configure Artifactory in Jenkins

```
Jenkins → Manage Jenkins → System → JFrog
```

Add a new JFrog Platform instance:

| Field | Value |
|---|---|
| Instance ID | `artifactory-main` |
| JFrog Platform URL | `http://10.10.10.100:8082` |
| Default Deployer Credentials | `jfrog-creds` |

Click **Test Connection** — should return: `Found Artifactory 7.x.x`  
Click **Save**.

---

### Pipeline Script (Option B)

```groovy
pipeline {
    agent { label 'master' }

    tools {
        gradle 'gradle941'
        jdk 'jdk17'
    }

    options {
        disableConcurrentBuilds()
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '30'))
        timeout(time: 30, unit: 'MINUTES')
    }

    parameters {
        string(
            name: 'BRANCH',
            defaultValue: 'develop',
            description: 'Git branch to build'
        )
        choice(
            name: 'BUILD_VARIANT',
            choices: ['DevDebug', 'DevRelease', 'LiveDebug', 'LiveRelease'],
            description: 'Android build variant'
        )
        booleanParam(
            name: 'PUBLISH_TO_ARTIFACTORY',
            defaultValue: true,
            description: 'Upload AAR to JFrog Artifactory'
        )
    }

    environment {
        JVM_OPTIONS      = '-Xms2g -Xmx4g -XX:+UseG1GC'
        ARTIFACTORY_REPO = 'android-sdk'
    }

    stages {

        stage('Checkout') {
            steps {
                cleanWs()
                git branch: "${params.BRANCH}",
                    credentialsId: 'gitlab-sdk-creds',
                    url: 'https://gitlab-sdk.sagar.com.np/sagar/sagar-android.git'
            }
        }

        stage('Init') {
            steps {
                script {
                    env.SHORT_COMMIT = sh(
                        script: 'git rev-parse --short HEAD',
                        returnStdout: true
                    ).trim()

                    env.BUILD_VERSION = "${BUILD_NUMBER}-${env.SHORT_COMMIT}"
                }

                sh 'java -version'
                sh 'gradle -v'

                echo "--------------------------------------------"
                echo "Branch        : ${params.BRANCH}"
                echo "Build Variant : ${params.BUILD_VARIANT}"
                echo "Build Version : ${env.BUILD_VERSION}"
                echo "Publish       : ${params.PUBLISH_TO_ARTIFACTORY}"
                echo "--------------------------------------------"
            }
        }

        stage('Clean') {
            steps {
                sh "./gradlew clean -Dorg.gradle.jvmargs='${env.JVM_OPTIONS}'"
            }
        }

        stage('Build Android Package') {
            steps {
                rtGradle(
                    tool: 'gradle941',
                    useWrapper: true,
                    tasks: "assemble${params.BUILD_VARIANT} --parallel --build-cache -Dorg.gradle.jvmargs='${env.JVM_OPTIONS}'",
                    deployerId: 'artifactory-main',
                    deployerRepo: "${env.ARTIFACTORY_REPO}"
                )
            }
        }

        stage('Run Unit Tests') {
            steps {
                sh "./gradlew test${params.BUILD_VARIANT}UnitTest -Dorg.gradle.jvmargs='${env.JVM_OPTIONS}'"
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: '**/TEST-*.xml'
                }
            }
        }

        stage('Locate Android Package') {
            steps {
                script {
                    sh "echo '[INFO] AAR scan:' && find . -path '*/build/outputs/aar/*.aar' -ls"

                    env.AAR_FILE = sh(
                        script: "find . -path '*/build/outputs/aar/*.aar' | head -n 1",
                        returnStdout: true
                    ).trim()

                    if (!env.AAR_FILE) {
                        error "[ERROR] AAR not found. Verify the module applies 'com.android.library' plugin."
                    }

                    env.FILE_NAME = sh(
                        script: "basename ${env.AAR_FILE}",
                        returnStdout: true
                    ).trim()

                    echo "[INFO] AAR located : ${env.AAR_FILE}"
                    echo "[INFO] File name   : ${env.FILE_NAME}"
                }
            }
        }

        stage('Archive Android Package') {
            steps {
                archiveArtifacts artifacts: '**/*.aar', fingerprint: true
            }
        }

        stage('Upload to Artifactory') {
            when {
                expression { return params.PUBLISH_TO_ARTIFACTORY }
            }
            steps {
                script {
                    def uploadSpec = """{
                        "files": [{
                            "pattern": "${env.AAR_FILE}",
                            "target": "${env.ARTIFACTORY_REPO}/${params.BUILD_VARIANT}/${env.BUILD_VERSION}/",
                            "props": "build.number=${BUILD_NUMBER};build.variant=${params.BUILD_VARIANT};git.commit=${env.SHORT_COMMIT};branch=${params.BRANCH}"
                        }]
                    }"""

                    def server = Artifactory.server 'artifactory-main'

                    def buildInfo = server.upload spec: uploadSpec

                    server.publishBuildInfo buildInfo

                    echo "[OK] Upload complete: ${env.ARTIFACTORY_REPO}/${params.BUILD_VARIANT}/${env.BUILD_VERSION}/${env.FILE_NAME}"
                }
            }
        }
    }

    post {
        success {
            echo "[SUCCESS] Build ${env.BUILD_VERSION} | Variant: ${params.BUILD_VARIANT} | Branch: ${params.BRANCH}"
        }
        failure {
            echo "[FAILED] Build ${env.BUILD_VERSION} failed. Check logs above."
        }
        aborted {
            echo "[ABORTED] Build ${env.BUILD_VERSION} was aborted."
        }
        always {
            cleanWs()
        }
    }
}
```

---

## Gradle Commands Reference

| Stage | Command | Description |
|---|---|---|
| Clean | `./gradlew clean` | Removes all previous build outputs from `build/` directories |
| Compile | `./gradlew compile` | Compiles source files only, no packaging |
| Build | `./gradlew build` | Compiles, runs tests, and assembles all outputs |
| Assemble | `./gradlew assemble` | Packages the AAR without running tests |
| Assemble (variant) | `./gradlew assembleDevDebug` | Packages a specific variant AAR |
| Test | `./gradlew testDevDebugUnitTest` | Runs unit tests for a specific variant |

> `./gradlew` uses the Gradle Wrapper version defined in `gradle/wrapper/gradle-wrapper.properties`. When the Jenkins `tools` block declares `gradle 'gradle941'`, the `gradle` binary (without `./`) uses the Jenkins-managed installation at `/home/jenkin/gradle-9.4.1/bin/gradle`.

---

## Artifactory Upload Path Structure

Every AAR is uploaded to a versioned path under the repository:

```
android-sdk/
└── DevDebug/
│   └── 15-f6fb52f/
│       └── app-devdebug.aar
└── LiveRelease/
    └── 16-a3cd91b/
        └── app-liverelease.aar
```

Path format:

```
{ARTIFACTORY_REPO}/{BUILD_VARIANT}/{BUILD_NUMBER}-{SHORT_COMMIT}/{FILE_NAME}
```

| Token | Example | Source |
|---|---|---|
| `ARTIFACTORY_REPO` | `android-sdk` | Pipeline environment variable |
| `BUILD_VARIANT` | `DevDebug` | Pipeline parameter |
| `BUILD_NUMBER` | `15` | Jenkins built-in variable |
| `SHORT_COMMIT` | `f6fb52f` | `git rev-parse --short HEAD` |
| `FILE_NAME` | `app-devdebug.aar` | Gradle output filename |

---

## Comparison: Option A vs Option B

| Feature | Option A (curl) | Option B (Plugin) |
|---|---|---|
| Plugin required | No | Yes (Artifactory Plugin) |
| HTTP response validation | Manual (`$HTTP_CODE` check) | Automatic |
| Checksum verification | No | Yes (SHA1 + MD5) |
| Build info in Artifactory UI | No | Yes |
| Artifact properties/metadata | No | Yes (via `props`) |
| Setup complexity | Low | Medium |
| JFrog server dependency | REST API only | Artifactory 6+ |
| Recommended for | Simple pipelines, minimal plugins | Full traceability, audit trail |

---

## Troubleshooting

### `Could not create parent directory for lock file`

```
Exception: Could not create parent directory for lock file /opt/gradle-cache/...
```

**Cause:** The `jenkin` user has no write access to `GRADLE_USER_HOME`.

**Fix:**
```bash
sudo chown -R jenkin:jenkin /opt/gradle-cache
sudo chmod -R 775 /opt/gradle-cache
```

---

### `curl: (1) Protocol http not supported or disabled in libcurl`

**Cause:** Invisible characters in the URL (copy-paste artifact from browser or PDF).

**Fix:** Type the URL manually. Use `cat -A` to detect hidden characters:
```bash
echo "http://10.10.10.100:8081/artifactory/..." | cat -A
```

---

### `403 Forbidden` on Upload

**Cause:** Repository does not exist, or user lacks Deploy permission.

**Fix:**
1. Verify repository `android-sdk` exists in Artifactory UI.
2. Verify `sdk-admin` has Deploy/Cache permission on that repository.
3. Test manually: `curl -f -u sdk-admin:PASS -T /tmp/test.txt "http://.../android-sdk/test/test.txt"`

---

### AAR Not Found

```
[ERROR] AAR not found. Verify the module applies 'com.android.library' plugin.
```

**Cause:** The module uses `com.android.application` which produces an APK, not an AAR.

**Fix:** Check `app/build.gradle.kts`:
```kotlin
// Must be this for AAR output
plugins {
    id("com.android.library")
}

// NOT this (produces APK)
plugins {
    id("com.android.application")
}
```

---

### `junit` Stage Fails with No Test Results

**Cause:** `junit` step fails hard when no XML files are found.

**Fix:** Always use `allowEmptyResults: true`:
```groovy
junit allowEmptyResults: true, testResults: '**/TEST-*.xml'
```

---

*Guide maintained by Sagar Malla — DevOps & Android Infrastructure*
