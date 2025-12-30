# Trivy Installation & Jenkins Integration (RHEL 9.6)

## 1. Install Trivy on RHEL 9.6

    cat > /etc/yum.repos.d/trivy.repo <<EOF
    [trivy]
    name=Trivy Repository
    baseurl=https://aquasecurity.github.io/trivy-repo/rpm/releases/x86_64/
    gpgcheck=0
    enabled=1
    EOF

    dnf install -y trivy
    trivy --version

## 2. Permissions for Jenkins User (jenkin)

    mkdir -p /var/lib/trivy
    chown -R jenkin:jenkin /var/lib/trivy

    cat > /etc/profile.d/trivy.sh <<EOF
    export TRIVY_CACHE_DIR=/var/lib/trivy
    EOF

    source /etc/profile.d/trivy.sh

## 3. Jenkins Pipeline Commands

### A. Scan Docker Image

    trivy image --exit-code 1 --severity CRITICAL,HIGH my-image:latest

### B. Scan Filesystem

    trivy fs --exit-code 1 --severity CRITICAL,HIGH .

### C. Generate Table Report

    trivy image --format table --output trivy-report.txt my-image:latest

## 4. Full Jenkinsfile Stage

    pipeline {
        agent any
        stages {
            stage('Checkout') {
                steps { checkout scm }
            }

            stage('Build Docker Image') {
                steps { sh 'docker build -t my-image:latest .' }
            }

            stage('Trivy Security Scan') {
                steps {
                    sh '''
                    trivy image                     --severity CRITICAL,HIGH                     --exit-code 1                     --cache-dir /var/lib/trivy                     my-image:latest
                    '''
                }
            }
        }
    }
