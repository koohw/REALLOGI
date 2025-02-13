pipeline {
    agent any
    stages {

        stage('Build Backend (Spring Boot)') {
            steps {
                dir('web/dt_back') {
                    // Gradle 빌드를 실행하여 jar 파일을 생성합니다.
                    sh './gradlew clean build'
                    // 빌드 산출물이 존재하는지 확인
                    sh 'ls -la build/libs'
                    // Dockerfile이 위치한 동일 디렉토리 기준으로 docker build를 실행합니다.
                    sh 'docker build -t morjhkim/springboot:latest .'
                }
            }
        }

        stage('Build Frontend (React)') {
            steps {
                dir('web/dt_front') {
                    sh 'docker build -t morjhkim/react-dt:latest .'
                }
            }
        }

        stage('Push Images to Docker Hub') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-credentials', usernameVariable: 'DOCKER_HUB_USER', passwordVariable: 'DOCKER_HUB_PASS')]) {
                    sh 'docker login -u $DOCKER_HUB_USER -p $DOCKER_HUB_PASS'
                    sh 'docker push morjhkim/springboot:latest'
                    sh 'docker push morjhkim/react-dt:latest'
                }
            }
        }
    }
}
