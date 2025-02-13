pipeline {
    agent any
    stages {

        stage('Build Backend (Spring Boot)') {
            steps {
                dir('web/dt_back') {
                    // gradlew 파일에 실행 권한 추가
                    sh 'chmod +x gradlew'
                    // gradle 빌드 실행 (이후 build/libs 폴더에 jar 파일 생성되어야 합니다)
                    sh './gradlew clean build'
                    // Docker 이미지 빌드
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