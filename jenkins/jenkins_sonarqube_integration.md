# Jenkins SonarQube Integration Setup

This guide covers only the Jenkins integration for SonarQube on RHEL 9.6.

---

## 1. Install Required Jenkins Plugins

1. Go to **Jenkins → Manage Jenkins → Manage Plugins → Available**
2. Install the following plugins:
   - **SonarQube Scanner**
   - **Pipeline Utility Steps**
3. Restart Jenkins after installation.

---

## 2. Add SonarQube Server to Jenkins

1. Go to **Manage Jenkins → Configure System → SonarQube servers → Add SonarQube**
2. Fill in the following details:
   - **Name:** `SonarServer` (any descriptive name)
   - **Server URL:** `http://<your-sonarqube-ip>:9000`
   - **Server Authentication Token:** Generate in SonarQube → **My Account → Security → Generate Token** and paste it here
3. Click **Save**

---

## 3. Add SonarScanner Tool in Jenkins

1. Go to **Manage Jenkins → Global Tool Configuration → SonarQube Scanner → Add SonarQube Scanner**
2. Fill in:
   - **Name:** `sonar-scanner-latest` (or any name)
   - Check **Install automatically → Install from official site (latest)**
3. Click **Save**

---

## 4. Pipeline Integration Example

```groovy
pipeline {
    agent any

    stages {

        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv(installationName: 'SonarServer') {
                    sh '''
                        sonar-scanner \
                          -Dsonar.projectKey=myproject \
                          -Dsonar.sources=. \
                          -Dsonar.host.url=http://<your-sonarqube-ip>:9000
                    '''
                }
            }
        }

        stage('Quality Gate') {
            steps {
                timeout(time: 2, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

    }
}
```

**Notes:**
- Replace `<your-sonarqube-ip>` with your SonarQube server IP or hostname.
- Use the exact `installationName` configured in Jenkins (`SonarServer`).
- Ensure Jenkins node has Java installed and `sonar-scanner` in PATH.