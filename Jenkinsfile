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

        stage('Deploy Stack') {
            steps {
                configFileProvider([configFile(fileId: 'docker-compose-config', targetLocation: 'docker-compose.yml')]) {
                    script {
                        // 현재 스택 상태 확인
                        sh 'docker stack services dt-stack || true'
                        
                        // Credentials에서 가져온 설정 파일로 스택 업데이트
                        sh 'docker stack deploy -c docker-compose.yml dt-stack --with-registry-auth'
                        
                        // 업데이트 후 상태 확인
                        sh 'docker stack services dt-stack'
                    }
                }
            }
        }

        stage('Cleanup') {
            steps {
                sh 'docker system prune -f'
            }
        }
    }
}
