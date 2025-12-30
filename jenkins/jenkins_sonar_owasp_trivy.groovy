pipeline {
    agent any
    environment {
        SCANNER_HOME = tool 'sonarqube'
        SONAR_TOKEN = credentials('sonarqube-new-login-token')
    }
    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/UnstopableSafar08/jenkins-demo.git'
            }
        }

        stage('SonarQube Check') {
            steps {
                // squ_031f19ae2bf871338147381809a0834bef5b8bf6
                withSonarQubeEnv(
                        installationName: 'sonarqube',
                        credentialsId: 'sonarqube-new-login-token') {
                    sh "$SCANNER_HOME/bin/sonar-scanner -Dsonar.projectName=NodeJsTest -Dsonar.projectKey=NodeJsTest"
                        }
            }
        }

        stage('Sonar Quality Gate Scan') {
            steps {
                timeout(time: 2, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: false
                }
            }
        }

        // stage('OWASP Dependency CHeck') {
        //     steps {
        //         dependencyCheck additionalArguments: '--scan ./', odcInstallation: 'dc' // dc is the name of the Dependency-Check installation in Jenkins global tools configuration
        //         dependencyCheckPublisher pattern: '**/dependency-check-report.html'
        //     }
        // }

        stage('OWASP Dependency-Check') {
            steps {
                // Run Dependency-Check
                dependencyCheck additionalArguments: '--scan . --format HTML --out .', odcInstallation: 'dc'

                // Publish report
                dependencyCheckPublisher pattern: 'dependency-check-report.html'
            }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t my-static-site .'
            }
        }

        stage('Deploy') {
            steps {
                sh '''
                docker rm -f static-site || true
                docker run -d --name static-site -p 8081:80 my-static-site
                '''
            }
        }

        stage('Trivy Image Scan') {
            steps {
                sh 'trivy -v'
                sh '''
                trivy image \
                    --severity CRITICAL,HIGH \
                    --exit-code 1 \
                    --cache-dir /var/lib/trivy \
                    my-static-site
                '''
            }
        }

        // stage('Trivy file-system Scan') {
        //     steps {
        //         sh 'trivy fs --formate table -o trivy-fs-report.html .'
        //     }
        // }

        stage('Trivy FS HTML Scan') {
            steps {
                sh '''
                    trivy fs \
                        --format template \
                        --template "/opt/html.tpl" \
                        --output trivy-fs-report.html .
                    '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'trivy-fs-report.html'
                }
            }
        }
    }
}
