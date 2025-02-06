FROM openjdk:23-slim
WORKDIR /app
COPY build/libs/*.jar app.jar
EXPOSE 8080
# 실행 시 prod 프로파일 활성화 : mysql 데이터소스가 mysql-container를 참조하도록 설정
ENTRYPOINT ["java", "-Dspring.profiles.active=prod", "-jar", "app.jar"]
