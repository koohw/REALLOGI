pipeline {
    agent any
    stages {
        stage('Build Backend (Spring Boot)') {
            steps {
                dir('web/dt_back') {
                    sh 'chmod +x gradlew'
                    sh './gradlew clean build'
                    sh 'docker build -t springboot-app:latest .'
                }
            }
        }

        stage('Build Frontend (React)') {
            steps {
                dir('web/dt_front') {
                    sh 'docker build -t react-app:latest .'
                }
            }
        }

        stage('Redeploy Stack') {
            steps {
                configFileProvider([configFile(fileId: 'docker-compose-config', targetLocation: 'docker-compose.yml')]) {
                    script {
                        // 기존 스택 제거
                        sh 'docker stack rm dt-stack'
                        // 기존 네트워크 제거
                        sh 'docker network rm dt-stack_dt-stack-network || true'
                        // 충분한 대기 시간
                        sh 'sleep 15'
                        // 새로운 스택 배포
                        sh 'docker stack deploy -c docker-compose.yml dt-stack --with-registry-auth'
                    }
                }
            }
        }
    }
}
