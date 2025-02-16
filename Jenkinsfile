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

        stage('Update Services') {
            steps {
                script {
                    // 백엔드 서비스 업데이트
                    sh 'docker service update --image springboot-app:latest dt-stack_springboot --with-registry-auth'
                    
                    // 프론트엔드 서비스 업데이트
                    sh 'docker service update --image react-app:latest dt-stack_react --with-registry-auth'
                }
            }
        }
    }
}
