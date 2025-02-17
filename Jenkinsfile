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

        stage('Build Backend (Flask)') {
            steps {
                dir('monitor_back') {
                    sh 'docker build -t flask-app:latest .'
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
                configFileProvider([configFile(fileId: 'docker-composer-add', variable: 'DOCKER_COMPOSE_FILE')]) {
                    sh 'docker-compose -f $DOCKER_COMPOSE_FILE down'
                    sh 'docker-compose -f $DOCKER_COMPOSE_FILE up -d'
                }
            }
        }
    }
}
