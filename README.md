# RealLogi - AGV 관리 시스템

---

## 프로젝트 소개

RealLogi는 물류센터 관리자를 위한 AGV(Automated Guided Vehicle) 관리 시스템입니다. 디지털 트윈 기술을 활용하여 AGV의 최적 경로를 제공하고, 센서 데이터를 바탕으로 돌발 상황을 감지하며, 물류 프로세스를 효율적으로 운영할 수 있도록 지원합니다.

### 주요 기능

- **AGV의 최적 경로 제공**: 격자 기반 맵과 가중치 시스템을 활용하여 실시간으로 최적 이동 경로 계산 및 전달
- **실시간 물류센터 정보 제공**: AGV 상태를 실시간으로 모니터링하여 데이터 제공
- **돌발 상황 감지 및 대응**: AGV에서 발생하는 돌발 상황(물건 부족, 충돌 등)을 감지하고 시뮬레이터에 영상 표시
- **원격 AGV 제어 기능**: 특정 AGV를 선택하여 실시간으로 명령 전달

## 프로젝트 특장점

### 기능 관점

1. **디지털 트윈 기술 도입**: 현실 물류센터와 가상 시뮬레이션을 통합하여 실제 AGV와 가상 AGV를 동시에 관리
2. **실시간 상태 모니터링**: 가상 및 현실 AGV의 위치, 유휴 시간, 동작 시간, 이동 거리 등을 통합적으로 제공
3. **현실과 가상 간의 동기화**: 현실 AGV의 돌발 상황을 감지하여 가상 시뮬레이터에 반영

### 기술 관점

1. **디지털 트윈의 실시간 동기화**: 현실 물류센터와 가상 시뮬레이션 간의 양방향 데이터 동기화 구현
2. **격자 기반 경로 최적화 알고리즘**: 물류센터를 격자 형태로 모델링하여 장애물 회피 및 경로 가중치 기반 최적화
3. **돌발 상황 실시간 처리**: 센서 데이터와 신호 기반으로 돌발 상황을 즉시 감지하고 시뮬레이터에 반영
4. **가상 환경과 현실 제어의 통합**: 가상 시뮬레이션 환경에서 사전 테스트 후 현실에 적용하여 운영 리스크 최소화

## AI 기술 활용

1. **돌발 상황 감지 및 대응**: 컴퓨터 비전(CV) 및 센서 데이터 분석 기술로 AGV의 충돌, 장애물, 물건 부족 등 감지
2. **수요 예측 및 자원 배분**: AI를 활용한 물류센터 수요 예측 및 AGV와 자원 배분 최적화

## 팀 구성 및 역할

### 시뮬레이터 개발

- 윤수한 (팀장)
- 이건욱

### IoT 개발

- 구희원
- 이상화

### 웹 파트 FE, BE 개발

- 김지홍
- 남정호

### 인프라 구축

- 김지홍

## 기술 스택

### 프론트엔드 (dt_front)

- React
- JavaScript
- HTML5
- Node.js

### 백엔드 (dt_back)

- Spring Boot
- Java 17
- Node.js
- Flask

### 데이터베이스

- MySQL

### 시뮬레이터

- Simpy
- Python
- HiveMQ
- Flask
- SSE

### AI/IoT

- OpenCV (Vision Detection)
- Jetson Orin Nano
- MiDaS
- Raspberry Pi (OrinCar\_라즈베리파이)

### CI/CD \& 인프라

- EC2(Ubuntu 22.04-AMD64)
- Jenkins (자동 빌드 및 배포)
- Docker, DockerHub (컨테이너화 및 배포)
- Docker Portainer (컨테이너 관리)
- GitLab CI/CD

### 개발 도구

- IntelliJ
- MySQL Workbench
- VSCode
- PyCharm
- Git, GitLab, SourceTree
- Jira
- Mattermost

## 폴더 구조

```bash
.
├── agv                      # AGV 관련 코드
│   ├── dc_motor_control     # DC 모터 제어
│   ├── move                 # AGV 이동 로직
│   ├── sensor               # 센서 데이터 처리
│   └── vision_detection     # 컴퓨터 비전 기반 감지 모듈
├── IoT                      # IoT 관련 모듈
├── monitor_back             # 모니터링 백엔드 (Flask 기반)
├── simulation               # 시뮬레이션 코드
├── web                      # 웹 관련 코드
│   ├── dt_back              # Spring Boot 백엔드
│   ├── dt_flask             # Flask 기반 데이터 처리
│   └── dt_front             # React 프론트엔드
```

## 설치 및 실행 방법

### 1. 프로젝트 클론

```bash
git clone https://lab.ssafy.com/s12-webmobile3-sub1/S12P11E101.git
cd S12P11E101
```

### 2. 백엔드 실행 (Spring Boot)

```bash
cd web/dt_back
./gradlew bootRun
```

### 3. 프론트엔드 실행 (React)

```bash
cd web/dt_front
yarn install
yarn start
```

### 4. Flask 서버 실행

```bash
cd web/dt_flask
source venv/bin/activate  # (Windows: venv\Scripts\activate)
python app.py
```

## CI/CD - Jenkins + Docker 기반 자동 배포

이 프로젝트는 Jenkins와 Docker를 활용한 CI/CD를 적용하여, 코드가 변경되면 자동으로 빌드 및 배포가 이루어지도록 설정되어 있습니다.

### CI/CD 파이프라인 흐름

1. GitLab Push 이벤트 발생 → GitLab Webhook이 Jenkins를 트리거함
2. Jenkins가 프로젝트를 빌드 (Gradle/Spring Boot, React, Flask 등)
3. Docker 이미지 빌드
4. 서버에서 최신 Docker 이미지를 pull \& 실행
5. Nginx를 통해 프론트엔드 서비스 제공

## 설계 문서

- 와이어프레임: https://www.figma.com/design/wJGdf2lM9Qdg1LK5ax7zxv/Untitled?node-id=0-1\&t=6lcB7t8WEBTDRzIw-1
- ERD: https://www.erdcloud.com/p/tikF6ZtWviX9RifWH
- API 문서: https://www.notion.so/RealLogi-API-1a059e7b696980da92f3cfb3a0b20ae7?pvs=4

# 아키텍쳐

![project101__2_](/uploads/888d4aefd3432ff059ad561e4be2dd5e/project101__2_.png)

## 배포 및 테스트

- 테스트 계정:
  - ID: ssafytest@ssafy.com
  - PW: ssafy1234!

<div style="text-align: center">⁂</div>
