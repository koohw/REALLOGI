# Stage 1: 빌드 단계
FROM node:20-alpine AS builder
WORKDIR /app

# ARG 추가
ARG REACT_APP_API_URL
ENV REACT_APP_API_URL=$REACT_APP_API_URL

COPY package.json yarn.lock ./
RUN yarn install
COPY . .
RUN yarn build

# Stage 2: 실행 단계
FROM node:20-alpine
RUN yarn global add serve
WORKDIR /app
COPY --from=builder /app/build ./build
EXPOSE 3000
CMD ["serve", "-s", "build", "-l", "3000"]
