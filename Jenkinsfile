pipeline {
    agent any
    stages {

        stage('Build Backend (Spring Boot)') {
            steps {
                // web/dt_back 폴더에서 Spring Boot 프로젝트의 Docker 이미지 빌드
                dir('web/dt_back') {
                    sh 'docker build -t morjhkim/springboot:latest .'
                }
            }
        }

        stage('Build Frontend (React)') {
            steps {
                // web/dt_front 폴더에서 React 프로젝트의 Docker 이미지 빌드
                dir('web/dt_front') {
                    sh 'docker build -t morjhkim/react-dt:latest .'
                }
            }
        }

        stage('Push Images to Docker Hub') {
            steps {
                // Jenkins에 등록된 Docker Hub 자격증명을 사용
                withCredentials([usernamePassword(credentialsId: 'dockerhub-credentials', usernameVariable: 'DOCKER_HUB_USER', passwordVariable: 'DOCKER_HUB_PASS')]) {
                    sh 'docker login -u $DOCKER_HUB_USER -p $DOCKER_HUB_PASS'
                    sh 'docker push morjhkim/springboot:latest'
                    sh 'docker push morjhkim/react-dt:latest'
                }
            }
        }
    }
}
