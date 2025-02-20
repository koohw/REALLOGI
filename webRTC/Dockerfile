# Node.js LTS 버전 사용
FROM node:20-alpine AS builder

# 작업 디렉토리 설정
WORKDIR /usr/src/app

# 앱 종속성 설치를 위한 package.json 파일 복사
COPY package*.json ./

# 프로덕션 종속성만 설치
RUN npm ci --only=production

# 소스 코드 복사
COPY . .

# 포트 설정
EXPOSE 6033

# 앱 실행
CMD ["node", "server.js"]
