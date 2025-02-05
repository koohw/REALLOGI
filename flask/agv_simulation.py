import simpy
import random
import json
import time
import threading
import paho.mqtt.client as mqtt

# ------------------------------
# MAP 및 관련 변수 정의
# ------------------------------
MAP = [
    [2, 2, 2, 2, 2, 2, 2],  # 도착지점 (출구)
    [0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [2, 2, 2, 2, 2, 2, 2]   # 출발지점
]

ROWS = len(MAP)
COLS = len(MAP[0])

# MQTT 설정
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_SIMPY_TO_AGV = "simpy/commands"  # 시뮬레이터(AGV)가 수신할 명령 토픽

# ------------------------------
# AGV 시뮬레이션 클래스
# ------------------------------
class AGV:
    def __init__(self, env, start_pos):
        """
        env: simpy 환경
        start_pos: (row, col) 형태의 시작 좌표
        """
        self.env = env
        self.pos = start_pos  # 현재 위치
        self.target = None    # 목표 좌표 (명령으로 지정)
        self.running = True
        self.process = env.process(self.run())

    def run(self):
        while self.running:
            # 만약 target이 설정되어 있으면, target으로 이동 시도
            if self.target:
                new_row, new_col = self.target
                if 0 <= new_row < ROWS and 0 <= new_col < COLS:
                    # 간단하게 즉시 이동하는 방식 (좀 더 부드러운 이동 로직을 원한다면 경로 생성 필요)
                    self.pos = (new_row, new_col)
                    print(f"[{self.env.now}] AGV moved to {self.pos} (target reached)")
                else:
                    print(f"[{self.env.now}] 받은 목표 좌표 {self.target} 가 맵 범위를 벗어남")
                self.target = None  # 목표 달성 후 초기화
            else:
                # 명령이 없으면 기본 동작 (예: 대기 또는 무작위 이동)
                d_row = random.choice([-1, 0, 1])
                d_col = random.choice([-1, 0, 1])
                new_row = self.pos[0] + d_row
                new_col = self.pos[1] + d_col

                if 0 <= new_row < ROWS and 0 <= new_col < COLS:
                    self.pos = (new_row, new_col)
                    print(f"[{self.env.now}] AGV randomly moved to {self.pos}")
                else:
                    print(f"[{self.env.now}] Random move ({new_row}, {new_col}) out of bounds, ignored")
            yield self.env.timeout(1)

    def stop(self):
        self.running = False

    def set_target(self, target):
        # target: (row, col)
        if 0 <= target[0] < ROWS and 0 <= target[1] < COLS:
            self.target = target
            print(f"[{self.env.now}] New target set: {self.target}")
        else:
            print(f"[{self.env.now}] Invalid target {target}, ignored")

# ------------------------------
# MQTT 수신용 스레드 함수
# ------------------------------
def mqtt_listener(agv):
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print(f"[AGV] MQTT 브로커에 성공적으로 연결됨 (rc={rc})")
        else:
            print(f"[AGV] 연결 실패, 반환 코드 {rc}")
        client.subscribe(TOPIC_SIMPY_TO_AGV)

    def on_message(client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            command = data.get("command")
            payload = data.get("data")
            print(f"[AGV] Received command: {command} {payload}")
            if command == "경로" and payload:
                # Controller에서 보낸 "경로" 명령의 경우, payload에 "next_location"이 있어야 함.
                next_location = payload.get("next_location")
                if next_location and isinstance(next_location, list) or isinstance(next_location, tuple):
                    agv.set_target(tuple(next_location))
            elif command == "정지":
                # 필요 시 정지 로직 구현
                print(f"[{agv.env.now}] AGV stopping...")
            elif command == "재개":
                # 필요 시 재개 로직 구현
                print(f"[{agv.env.now}] AGV resuming...")
        except Exception as e:
            print(f"[AGV] 메시지 처리 오류: {e}")

    client = mqtt.Client(protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    client.loop_forever()

# ------------------------------
# 시뮬레이션 환경 설정 및 실행
# ------------------------------
env = simpy.Environment()
start_pos = (ROWS - 1, 0)  # 예: 출발지점 중 하나
agv = AGV(env, start_pos)

# MQTT 수신은 별도 스레드에서 실행 (SimPy와 병행 실행)
mqtt_thread = threading.Thread(target=mqtt_listener, args=(agv,), daemon=True)
mqtt_thread.start()

try:
    env.run(until=50)  # 50 시간 단위 실행
except KeyboardInterrupt:
    print("시뮬레이션 종료")
    agv.stop()
