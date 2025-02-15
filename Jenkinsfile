pipeline {
    agent any
    stages {
        stage('Build Backend (Spring Boot)') {
            steps {
                dir('web/dt_back') {
                    sh 'chmod +x gradlew'
                    sh './gradlew clean build'
                    sh 'docker build -t localhost:5000/springboot-app:latest .'
                    sh 'docker push localhost:5000/springboot-app:latest'
                }
            }
        }

        stage('Build Frontend (React)') {
            steps {
                dir('web/dt_front') {
                    sh 'docker build -t localhost:5000/react-app:latest .'
                    sh 'docker push localhost:5000/react-app:latest'
                }
            }
        }

        stage('Update Stack') {
            steps {
                sh 'docker stack deploy -c docker-compose.yml project101'
            }
        }
    }
}
