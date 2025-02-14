
import simpy
import random
from collections import deque
from threading import Lock
import time
import logging
from datetime import datetime  # 실제 현실시간 사용
import paho.mqtt.client as mqtt
import json

# --------------------------------------------------
# 로그 설정
DEBUG_MODE = False
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("simulation.log", encoding='utf-8')
    ]
)
# --------------------------------------------------

##############################################################################
# MQTT 설정
##############################################################################
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_COMMAND_TO_DEVICE = "simpy/commands"   # 서버 → 하드웨어 명령
TOPIC_STATUS_FROM_DEVICE = "agv/status"      # 하드웨어 → 서버 ACK/상태

mqtt_client = mqtt.Client(client_id="simulation_server", protocol=mqtt.MQTTv311)

def on_message(client, userdata, msg):
    """MQTT 콜백: dummy 하드웨어(AGV1) ACK 수신 등"""
    try:
        payload = json.loads(msg.payload.decode())
        if payload.get("ack"):
            location = payload.get("location")
            with data_lock:
                shared_data["positions"]["AGV 1"] = tuple(location)
                shared_data["agv1_moving_ack"] = True
            logging.info("[SIM] ACK 수신, 위치 업데이트: %s", location)
        else:
            logging.info("[SIM] ACK 아닌 메시지: %s", payload)
    except Exception as e:
        logging.error("[SIM] on_message 오류: %s", e)

mqtt_client.on_message = on_message
mqtt_client.connect(BROKER, PORT, 60)
mqtt_client.subscribe(TOPIC_STATUS_FROM_DEVICE)
mqtt_client.loop_start()

##############################################################################
# 1) 맵 및 좌표 정의
##############################################################################
map_data = [
    [2, 2, 2, 2, 2, 2, 2],  # 출구 (0행)
    [0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [2, 2, 2, 2, 2, 2, 2]   # 출발 (8행)
]
ROWS = len(map_data)
COLS = len(map_data[0])

shelf_coords = [(2, 2), (2, 4), (2, 6),
                (5, 2), (5, 4), (5, 6)]
exit_coords = [(0, c) for c in range(COLS) if map_data[0][c] == 2]

##############################################################################
# 2) 공유 데이터 및 락
##############################################################################
data_lock = Lock()
shared_data = {
    "positions": {
        "AGV 1": None,
        "AGV 2": None,
        "AGV 3": None,
        "AGV 4": None
    },
    "logs": {
        "AGV 1": [],
        "AGV 2": [],
        "AGV 3": [],
        "AGV 4": []
    },
    "statuses": {
        "AGV 1": "",
        "AGV 2": "",
        "AGV 3": "",
        "AGV 4": ""
    },
    "directions": {
        "AGV 1": "",
        "AGV 2": "",
        "AGV 3": "",
        "AGV 4": ""
    },
    "target": {   # 각 AGV의 현재 목표(target)
        "AGV 1": None,
        "AGV 2": None,
        "AGV 3": None,
        "AGV 4": None
    },
    "agv1_target": None,
    "agv1_moving_ack": False,
    "order_completed": {
        "AGV 1": 0,
        "AGV 2": 0,
        "AGV 3": 0,
        "AGV 4": 0
    },
    "efficiency": {"AGV 1": 0, "AGV 2": 0, "AGV 3": 0, "AGV 4": 0},
    "overall_efficiency_history": []
}

##############################################################################
# 3) BFS 경로 탐색 함수 (너비 우선 탐색)
##############################################################################
def bfs_path(grid, start, goal, obstacles=set()):
    if not start or not goal:
        return None
    queue = deque([(start, [start])])
    visited = set([start])
    directions = [(0,1), (0,-1), (1,0), (-1,0)]
    while queue:
        current, path = queue.popleft()
        if current == goal:
            return path
        r, c = current
        for dr, dc in directions:
            nr, nc = r+dr, c+dc
            if 0 <= nr < ROWS and 0 <= nc < COLS:
                if grid[nr][nc] != 1 and ((nr, nc) == goal or (nr, nc) not in obstacles):
                    if (nr, nc) not in visited:
                        visited.add((nr, nc))
                        queue.append(((nr, nc), path+[(nr, nc)]))
    return None

##############################################################################
# 4) 이동 방향 계산 함수
##############################################################################
def compute_direction(curr, nxt):
    dr = nxt[0] - curr[0]
    dc = nxt[1] - curr[1]
    if dr == -1 and dc == 0:
        return "u"
    elif dr == 1 and dc == 0:
        return "d"
    elif dr == 0 and dc == 1:
        return "R"
    elif dr == 0 and dc == -1:
        return "L"
    else:
        return ""

##############################################################################
# 5) MQTT 통신: 전체 경로 명령 전송
##############################################################################
def send_full_path_to_agv1(full_path):
    """
    AGV1(또는 잿슨)으로 전체 경로를 MQTT로 전송하는 함수.
    full_path 예: [(8, 0), (7, 0), (6, 0), ... (2,2)]
    """
    logging.debug("[SIM] send_full_path_to_agv1(full_path=%s)", full_path)
    payload = {
        "command": "PATH",
        "data": {
            # 경로 좌표 리스트를 그대로 전송 (예: [[8,0], [7,0], ...])
            "full_path": [list(p) for p in full_path]
        }
    }
    result = mqtt_client.publish(TOPIC_COMMAND_TO_DEVICE, json.dumps(payload))
    if result[0] == 0:
        logging.info("[SIM] PATH 명령 전송 성공: %s", payload)
    else:
        logging.error("[SIM] PATH 명령 전송 실패: %s", payload)

##############################################################################
# 6) 전체 경로 계산 함수
##############################################################################
def calculate_full_path(start, goal, obstacles=set()):
    path = bfs_path(map_data, start, goal, obstacles)
    if path is None:
        logging.warning("경로 탐색 실패: 시작 %s, 목표 %s", start, goal)
    return path

##############################################################################
# 7) Manhattan 거리 계산 함수
##############################################################################
def manhattan_distance(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

##############################################################################
# 8) Deadlock 체크 함수
##############################################################################
DEADLOCK_THRESHOLD = 5  # 목표까지 남은 맨해튼 거리가 이 값 이하이면 deadlock zone으로 판단

def check_deadlock(agv_positions, shared_data):
    deadlock_list = []
    with data_lock:
        for key, pos in shared_data["positions"].items():
            target = shared_data.get("target", {}).get(key)
            if target is not None:
                rem = manhattan_distance(pos, target)
                if rem <= DEADLOCK_THRESHOLD:
                    deadlock_list.append((key, rem))
    if len(deadlock_list) >= 3:
        deadlock_list.sort(key=lambda x: x[1])
        # 반환은 우선순위가 높은 AGV(목표에 가장 가까운)가 가장 앞에 오도록 함.
        return [key for key, _ in deadlock_list]
    else:
        return []

##############################################################################
# 9) AGV 프로세스 및 이동 함수 (전체 경로 계산 시 장애물 및 deadlock 고려)
##############################################################################
MOVE_INTERVAL = 1  # 1초마다 한 칸 이동
SIMULATE_MQTT = True  # 여기서는 시뮬레이션으로 진행

def random_start_position():
    return (8, 0)

def agv_process(env, agv_id, agv_positions, logs, _, shelf_coords, exit_coords):
    init_pos = random_start_position()
    agv_positions[agv_id] = init_pos
    logs[agv_id].append((datetime.now().isoformat(), init_pos))
    key = f"AGV {agv_id+1}"
    with data_lock:
        shared_data["positions"][key] = init_pos
        shared_data["logs"][key].append({"time": datetime.now().isoformat(), "position": init_pos})
        shared_data["statuses"][key] = "RUNNING"
        if "target" not in shared_data:
            shared_data["target"] = {}
    logging.debug("AGV %s 시작 위치: %s", agv_id, init_pos)

    while True:
        # 1) 선반(적재) 이동: 목표 업데이트 후 이동
        loading_target = random.choice(shelf_coords)
        with data_lock:
            shared_data["target"][key] = loading_target
            shared_data["statuses"][key] = "RUNNING"
        yield from move_to(env, agv_id, agv_positions, logs, loading_target)

        # 10초 대기 (적재) – 상태를 LOADING으로 지정
        with data_lock:
            shared_data["statuses"][key] = "LOADING"
            shared_data["directions"][key] = ""
        yield env.timeout(10)
        loading_complete_time = env.now

        # 2) 출구(하역) 이동: 목표 업데이트 후 이동
        exit_target = random.choice(exit_coords)
        with data_lock:
            shared_data["target"][key] = exit_target
            shared_data["statuses"][key] = "UNLOADING"
        yield from move_to(env, agv_id, agv_positions, logs, exit_target)
        unloading_complete_time = env.now

        # 사이클 효율: 하역 완료까지 걸린 시간
        cycle_eff = unloading_complete_time - loading_complete_time

        # EMA 방식으로 개별 AGV의 효율 업데이트 (alpha=0.5 사용)
        with data_lock:
            if shared_data["order_completed"][key] == 0:
                shared_data["efficiency"][key] = cycle_eff
            else:
                alpha = 0.5
                shared_data["efficiency"][key] = alpha * cycle_eff + (1 - alpha) * shared_data["efficiency"][key]
            shared_data["order_completed"][key] += 1

            # 전체 효율은 모든 AGV의 효율의 평균으로 계산
            total_eff = sum(shared_data["efficiency"].values())
            avg_eff = total_eff / len(shared_data["efficiency"]) if shared_data["efficiency"] else 0
            shared_data["overall_efficiency_history"].append([datetime.now().isoformat(), avg_eff])
            logging.info("[SIM] %s 사이클 효율: %.2f / 전체 평균 효율: %.2f", key, shared_data["efficiency"][key], avg_eff)

        # 5초 대기 후 다음 사이클 시작
        yield env.timeout(5)

def move_to(env, agv_id, agv_positions, logs, target):
    """
    전체 경로를 미리 계산하면서, 다른 AGV들의 현재 위치를 장애물로 반영하고,
    deadlock zone 내에서는 우선순위에 따라 정지(STOP)하도록 처리하는 함수.
    """
    key = f"AGV {agv_id+1}"
    while True:
        with data_lock:
            current_pos = agv_positions[agv_id]
        # 목표에 도달했으면 종료
        if current_pos == target:
            break

        # Deadlock 체크: deadlock zone 내에 3개 이상의 AGV가 있으면,
        # 우선순위(목표에 가장 가까운 AGV)가 아니라면 잠시 정지(STOP)
        deadlock_list = check_deadlock(agv_positions, shared_data)
        if deadlock_list and key in deadlock_list:
            if deadlock_list[0] != key:
                with data_lock:
                    shared_data["statuses"][key] = "STOP"
                yield env.timeout(1)
                continue

        # 장애물 구성: 다른 AGV들의 현재 위치와 상태, 남은 거리 비교
        with data_lock:
            my_remaining = manhattan_distance(current_pos, target)
            obstacles = set()
            for other_id, pos in agv_positions.items():
                if other_id == agv_id:
                    continue
                other_key = f"AGV {other_id+1}"
                other_status = shared_data["statuses"][other_key]
                if other_status in ["LOADING", "UNLOADING"]:
                    obstacles.add(pos)
                elif other_status == "RUNNING":
                    other_target = shared_data.get("target", {}).get(other_key)
                    if other_target is not None:
                        other_remaining = manhattan_distance(pos, other_target)
                        if other_remaining < my_remaining:
                            obstacles.add(pos)
                    else:
                        obstacles.add(pos)
        path = calculate_full_path(current_pos, target, obstacles=obstacles)
        if not path or len(path) < 2:
            yield env.timeout(0.5)
            continue
        break

    logging.debug("AGV %s 전체 경로: %s", agv_id, path)

    # 이동: 한 칸씩 진행
    if agv_id == 0 and SIMULATE_MQTT:
        with data_lock:
            shared_data["agv1_moving_ack"] = False
        send_full_path_to_agv1(path)
        ack_received = False
        while not ack_received:
            yield env.timeout(0.2)
            with data_lock:
                if shared_data["agv1_moving_ack"]:
                    ack_received = True
        with data_lock:
            agv_positions[agv_id] = target
    else:
        for idx in range(1, len(path)):
            next_pos = path[idx]
            direction = compute_direction(agv_positions[agv_id], next_pos)
            with data_lock:
                shared_data["directions"][key] = direction
                # 상태가 RUNNING일 때만 이동 (STOP이면 대기)
                if shared_data["statuses"][key] != "STOP":
                    shared_data["statuses"][key] = "RUNNING"
            yield env.timeout(MOVE_INTERVAL)
            with data_lock:
                agv_positions[agv_id] = next_pos
                shared_data["positions"][key] = next_pos
                shared_data["logs"][key].append({
                    "time": datetime.now().isoformat(),
                    "position": next_pos
                })
        logging.info("[%s] %s 도착 -> %s", datetime.now().isoformat(), key, target)

##############################################################################
# 10) 시뮬레이션 메인 함수
##############################################################################
try:
    from simpy.rt import RealtimeEnvironment
except ImportError:
    RealtimeEnvironment = simpy.Environment

def simulation_main():
    env = RealtimeEnvironment(factor=1, strict=False)
    NUM_AGV = 4
    agv_positions = {}
    logs = {}
    for i in range(NUM_AGV):
        agv_positions[i] = (0,0)
        logs[i] = []
    for i in range(NUM_AGV):
        env.process(agv_process(env, i, agv_positions, logs, None, shelf_coords, exit_coords))
    env.run(until=float('inf'))

if __name__ == "__main__":
    simulation_main()
