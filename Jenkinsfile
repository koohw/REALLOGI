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

        stage('Update Stack') {
            steps {
                // 스택 업데이트를 위해 Editor에서 Update stack 실행
                sh 'docker stack deploy -c docker-compose.yml project101'
            }
        }
    }
}
