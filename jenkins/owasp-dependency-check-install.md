# OWASP Dependency-Check Installation & Jenkins Integration (RHEL 9.6)

## 1. Install OWASP Dependency-Check

    mkdir -p /opt/owasp
    cd /opt/owasp

    dnf install -y wget unzip java-17-openjdk

    wget https://github.com/jeremylong/DependencyCheck/releases/latest/download/dependency-check.zip

    unzip dependency-check.zip
    mv dependency-check dependency-check-latest

    chown -R jenkin:jenkin /opt/owasp

    ln -sf /opt/owasp/dependency-check-latest/bin/dependency-check.sh /usr/local/bin/dependency-check

## 2. Update NVD Database

    sudo -u jenkin /usr/local/bin/dependency-check --updateonly

## 3. Jenkins Integration

### Option A: Jenkins Plugin

Install **OWASP Dependency-Check Plugin**.

Configure: - Name: `DC` - Path: `/opt/owasp/dependency-check-latest`

### Option B: Jenkinsfile (CLI)

    stage('OWASP Scan') {
        steps {
            sh '''
                dependency-check               --project "MyProject"               --scan .               --format HTML               --out owasp-report
            '''
        }

        post {
            always {
                publishHTML([
                    reportDir: 'owasp-report',
                    reportFiles: 'dependency-check-report.html',
                    reportName: 'OWASP Vulnerability Report'
                ])
            }
        }
    }

## 4. Freestyle Job

    dependency-check   --project "$JOB_NAME"   --scan .   --format "ALL"   --out "owasp-report"

## 5. Optional: Use Local NVD Cache

    mkdir -p /opt/owasp/data
    chown -R jenkin:jenkin /opt/owasp/data

    echo "data.directory=/opt/owasp/data" >> /opt/owasp/dependency-check-latest/etc/dependencycheck.properties

## 6. Verify

    dependency-check --version
