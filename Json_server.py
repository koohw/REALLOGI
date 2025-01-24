from flask import Flask, jsonify
import simpy
import threading
import time
import random

app = Flask(__name__)

# AGV 시뮬레이션에서 사용하는 shared_data
shared_data = {
    "positions": {},  # AGV 위치
    "obstacles": [],  # 장애물 위치
    "statuses": {},   # AGV 상태
    "logs": {         # AGV 이동 기록
        "AGV 1": [],
        "AGV 2": []
    }
}

# AGV 클래스 정의
class AGV:
    def __init__(self, env, name, speed):
        self.env = env
        self.name = name
        self.speed = speed
        self.position = (0, 0)
        self.status = "idle"

    def move(self, target_position):
        """AGV를 목표 위치로 이동시키는 프로세스"""
        shared_data["statuses"][self.name] = "moving"
        while self.position != target_position:
            # 위치 업데이트
            x, y = self.position
            target_x, target_y = target_position
            if x != target_x:
                x += 1 if x < target_x else -1
            elif y != target_y:
                y += 1 if y < target_y else -1
            self.position = (x, y)

            # 이동 기록 업데이트
            shared_data["logs"][self.name].append({
                "time": self.env.now,
                "position": self.position,
                "state": "moving"
            })

            # 딜레이
            yield self.env.timeout(1 / self.speed)

        shared_data["statuses"][self.name] = "idle"
        shared_data["logs"][self.name].append({
            "time": self.env.now,
            "position": self.position,
            "state": "idle"
        })

# Simpy 환경 설정
def simulation_environment():
    env = simpy.Environment()
    
    # AGV 생성
    agv1 = AGV(env, "AGV 1", speed=1)
    agv2 = AGV(env, "AGV 2", speed=1.5)
    shared_data["statuses"]["AGV 1"] = "idle"
    shared_data["statuses"]["AGV 2"] = "idle"

    # Simpy 프로세스 시작
    env.process(agv1.move((5, 5)))
    env.process(agv2.move((3, 7)))

    # Simpy 실행
    env.run(until=20)

# Simpy를 별도의 쓰레드로 실행
def run_simulation():
    while True:
        simulation_environment()
        time.sleep(1)

# Flask API 엔드포인트
@app.route('/api/logs', methods=['GET'])
def get_logs():
    """AGV 이동 기록을 JSON 형태로 반환"""
    return jsonify(shared_data["logs"])

# Flask 서버 실행
if __name__ == '__main__':
    # Simpy 쓰레드 시작
    simpy_thread = threading.Thread(target=run_simulation, daemon=True)
    simpy_thread.start()

    # Flask 서버 실행
    app.run(host='0.0.0.0', port=5000)
