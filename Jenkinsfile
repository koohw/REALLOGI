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

        stage('Update Stack Services') {
            steps {
                script {
                    // 백엔드와 프론트엔드 서비스 강제 업데이트
                    sh 'docker service update --image springboot-app:latest --force dt-stack_springboot'
                    sh 'docker service update --image react-app:latest --force dt-stack_react'
                }
            }
        }
    }
}
