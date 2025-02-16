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

        stage('Deploy Containers') {
            steps {
                script {
                    // 기존 컨테이너 중지 및 제거
                    sh 'docker compose down'
                    
                    // 새로운 컨테이너 시작
                    sh 'docker compose up -d'
                }
            }
        }
    }
}
