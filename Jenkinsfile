pipeline {
    agent any
    environment {
        // Jenkins Credentials에서 환경변수 가져오기
        REACT_ENV = credentials('react-env-credentials')
    }
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
        
        stage('Build Simulation') {
            steps {
                dir('simulation') {
                    sh 'docker build -t simulation-app:latest .'
                }
            }
        }

        stage('Build Frontend (React)') {
            steps {
                dir('web/dt_front') {
                    // 환경변수를 임시 .env 파일로 생성
                    sh '''
                        echo "REACT_APP_API_URL=${REACT_ENV}" > .env
                        docker build \
                            --build-arg REACT_APP_API_URL=${REACT_ENV} \
                            -t react-app:latest .
                        rm .env
                    '''
                }
            }
        }


        stage('Build WebRTC Signaling Server') {
            steps {
                dir('webRTC') {  // WebRTC 서버 코드가 있는 디렉토리
                    sh '''
                        docker build -t webrtc-signaling:latest .
                    '''
                }
            }
        }

        stage('Deploy Containers') {
            steps {
                configFileProvider([configFile(fileId: 'docker-composer-add', variable: 'DOCKER_COMPOSE_FILE')]) {
                    sh 'docker-compose -f $DOCKER_COMPOSE_FILE down'
                    sh 'docker system prune -f'  // 불필요한 리소스 정리
                    sh 'docker-compose -f $DOCKER_COMPOSE_FILE up -d'
                }
            }
        }
    }
    
    post {
        always {
            // 빌드 완료 후 정리
            cleanWs()
        }
        failure {
            // 실패 시 로그 출력
            sh 'docker-compose -f $DOCKER_COMPOSE_FILE logs'
        }
    }
}
