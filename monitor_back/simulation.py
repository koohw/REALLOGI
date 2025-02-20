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
# 로그 설정 (파일 핸들러 제거, 콘솔에만 출력)
DEBUG_MODE = False
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
# --------------------------------------------------

##############################################################################
# MQTT 설정 (AGV1은 MQTT 통신 사용)
##############################################################################
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_COMMAND_TO_DEVICE = "simpy/commands"   # 서버 → 하드웨어 명령
TOPIC_STATUS_FROM_DEVICE = "agv/status"      # 하드웨어 → 서버 ACK/상태

mqtt_client = mqtt.Client(client_id="simulation_server", protocol=mqtt.MQTTv311)

def on_message(client, userdata, msg):
    """
    MQTT 콜백: 하드웨어(AGV 1)에서 각 좌표 이동 완료 시 ACK 메시지를 수신합니다.
    """
    try:
        payload = json.loads(msg.payload.decode())
        if payload.get("ack"):
            ack_location = tuple(payload.get("location"))
            with data_lock:
                shared_data["positions"]["AGV 1"] = ack_location
            logging.info("[SIM] ACK 수신, AGV 1 위치 업데이트: %s", ack_location)
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
# 전체 시뮬레이션용 맵 (AGV1 제외)
MAP = [
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0],
    [0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1, 0],
    [0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0],
    [0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
]
ROWS = len(MAP)
COLS = len(MAP[0])
exit_coords = [(0, c) for c in range(COLS) if MAP[0][c] == 2]
shelf_coords = [(5,4), (3,12), (9,12), (8,6)]

# AGV1 전용 맵 (좌표 (0,0)부터 (7,8) 영역)
AGV1_MAP = [
    [2, 2, 2, 2, 2, 2, 2, 2, 2],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 1, 1, 0, 1, 0, 1, 0],
    [0, 1, 1, 0, 0, 1, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 0, 1, 1, 0],
    [0, 0, 0, 1, 1, 0, 1, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0]
]
AGV1_ROWS = len(AGV1_MAP)
AGV1_COLS = len(AGV1_MAP[0])
AGV1_exit_coords = [(0, c) for c in range(AGV1_COLS) if AGV1_MAP[0][c] == 2]
AGV1_shelf_coords = [(3,3), (5,4), (8,6)]  # (8,6)은 범위 확인 필요

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
    "agv1_path": [],
    "agv1_expected_target": None,
    "agv1_last_command_time": 0,
    "order_completed": {
        "AGV 1": 0,
        "AGV 2": 0,
        "AGV 3": 0,
        "AGV 4": 0
    },
    "efficiency": {"AGV 1": 0, "AGV 2": 0, "AGV 3": 0, "AGV 4": 0},
    "overall_efficiency_history": [],
    # 사용 중인 loading/unloading 목표 추적 (AGV1 제외)
    "used_shelf_targets": set(),
    "used_exit_targets": set()
}

# 추가: 셀 예약 정보를 저장할 전역 변수 (cell : AGV key)
cell_reservations = {}

def reserve_cell(agv_key, cell):
    """
    해당 cell이 예약되어 있지 않으면 예약하고 True를 반환합니다.
    이미 다른 AGV가 예약한 경우 False 반환.
    """
    with data_lock:
        if cell not in cell_reservations:
            cell_reservations[cell] = agv_key
            return True
        elif cell_reservations[cell] == agv_key:
            return True
        else:
            return False

def release_cell(agv_key, cell):
    """
    해당 cell의 예약을 해제합니다.
    """
    with data_lock:
        if cell in cell_reservations and cell_reservations[cell] == agv_key:
            del cell_reservations[cell]

##############################################################################
# 3) BFS 경로 탐색 함수 (입력받은 grid의 크기를 사용)
##############################################################################
def bfs_path(grid, start, goal, obstacles):
    if not start or not goal:
        return None
    queue = deque([(start, [start])])
    visited = set([start])
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    rows = len(grid)
    cols = len(grid[0])
    while queue:
        current, path = queue.popleft()
        if current == goal:
            return path
        r, c = current
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                if grid[nr][nc] != 1 and ((nr, nc) == goal or (nr, nc) not in obstacles):
                    if (nr, nc) not in visited:
                        visited.add((nr, nc))
                        queue.append(((nr, nc), path + [(nr, nc)]))
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
# 5) MQTT 통신: 전체 경로 명령 전송 (AGV1 전용)
##############################################################################
def send_full_path_to_agv1(full_path):
    with data_lock:
        current = shared_data["positions"]["AGV 1"]
    if full_path and full_path[0] != current:
        full_path.insert(0, current)
    logging.debug("[SIM] send_full_path_to_agv1(full_path=%s)", full_path)
    payload = {
        "command": "PATH",
        "data": {
            "path": [list(p) for p in full_path]
        }
    }
    result = mqtt_client.publish(TOPIC_COMMAND_TO_DEVICE, json.dumps(payload))
    if result[0] == 0:
        logging.info("[SIM] PATH 명령 전송 성공: %s", payload)
        with data_lock:
            shared_data["agv1_path"] = full_path
            shared_data["agv1_last_command_time"] = time.time()
    else:
        logging.error("[SIM] PATH 명령 전송 실패: %s", payload)

##############################################################################
# 6) 전체 경로 계산 함수 (grid를 파라미터로 사용)
##############################################################################
def calculate_full_path(grid, start, goal, obstacles):
    path = bfs_path(grid, start, goal, obstacles)
    if path is None:
        logging.warning("경로 탐색 실패: 시작 %s, 목표 %s, 장애물: %s", start, goal, obstacles)
    else:
        logging.debug("경로 탐색 성공: 시작 %s, 목표 %s, 경로: %s", start, goal, path)
    return path

##############################################################################
# 7) Manhattan 거리 계산 함수
##############################################################################
def manhattan_distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

##############################################################################
# 8) Deadlock 체크 함수 (필요시 사용)
##############################################################################
DEADLOCK_THRESHOLD = 5
def check_deadlock(agv_positions, shared_data):
    deadlock_list = []
    with data_lock:
        for key, pos in shared_data["positions"].items():
            target = shared_data.get("target", {}).get(key)
            if target is not None:
                rem = manhattan_distance(pos, target)
                if rem <= DEADLOCK_THRESHOLD:
                    deadlock_list.append((key, rem))
    if deadlock_list:
        logging.debug("Deadlock 후보 리스트: %s", deadlock_list)
    if len(deadlock_list) >= 3:
        deadlock_list.sort(key=lambda x: x[1])
        return [key for key, _ in deadlock_list]
    else:
        return []

##############################################################################
# 9) AGV 프로세스 및 이동 함수 (충돌 회피 및 장애물 고려, 셀 예약 적용)
##############################################################################
MOVE_INTERVAL = 1  # 다른 AGV는 1초마다 한 칸 이동
SIMULATE_MQTT = True  # AGV1은 MQTT로 전체 경로 명령 전송
WAIT_TIMEOUT = 3   # 셀 예약 대기 타임아웃 (초)
BACKOFF_MIN = 0.2
BACKOFF_MAX = 0.8
MAX_RESERVE_ATTEMPTS = 1  # 예약 시도 횟수를 1로 설정

def random_start_position(agv_id):
    col = (agv_id * 2) % COLS
    return (ROWS - 1, col)

def move_to(env, agv_id, agv_positions, logs, target, grid):
    key = f"AGV {agv_id+1}"
    # AGV1: MQTT 로직 사용 (단, 장애물 처리 시 현재 위치만 반영)
    if agv_id == 0 and SIMULATE_MQTT:
        with data_lock:
            current = agv_positions[agv_id]
        if current == target:
            logging.info("%s: 이미 목표에 도착함 (%s)", key, target)
            return
        with data_lock:
            obstacles = {pos for k, pos in shared_data["positions"].items() if k != key}
        path = calculate_full_path(grid, current, target, obstacles)
        if not path or len(path) < 2:
            logging.warning("%s: 경로 없음, 재계산 시도 (현재: %s, 목표: %s)", key, current, target)
            yield env.timeout(3.3)
        else:
            send_full_path_to_agv1(path)
            while True:
                yield env.timeout(3.3)  # AGV1은 각 격자 이동마다 3.3초 대기
                with data_lock:
                    current = shared_data["positions"][key]
                    agv_positions[agv_id] = current
                try:
                    idx = path.index(current)
                    if idx < len(path) - 1:
                        with data_lock:
                            shared_data["directions"][key] = compute_direction(current, path[idx+1])
                except ValueError:
                    pass
                if current == target:
                    break
            with data_lock:
                agv_positions[agv_id] = target
        return

    # AGV1(후반부) 및 다른 AGV: 한 칸씩 이동하면서 경로 재계산 (셀 예약 적용)
    with data_lock:
        current = agv_positions[agv_id]
    prev_cell = current  

    max_recalc_attempts = 10  # 전체 경로 재계산 시도 횟수 제한
    recalc_attempts = 0

    while True:
        with data_lock:
            if shared_data["statuses"][key] == "STOP":
                logging.info("%s: 정지 상태 감지, 이동 중단", key)
                return
            current = agv_positions[agv_id]
            if current == target:
                logging.info("%s: 이미 목표에 도착함 (%s)", key, target)
                return
            obstacles = {pos for k, pos in shared_data["positions"].items() if k != key}
        path = calculate_full_path(grid, current, target, obstacles)
        if not path or len(path) < 2:
            logging.warning("%s: 경로 없음, 재계산 시도 (현재: %s, 목표: %s, 장애물: %s)",
                            key, current, target, obstacles)
            yield env.timeout(0.5)
            recalc_attempts += 1
            if recalc_attempts >= max_recalc_attempts:
                logging.error("%s: 최대 경로 재계산 시도 횟수 초과. 이동 중단.", key)
                return
            continue

        logging.debug("%s 전체 경로: %s", key, path)
        moved = False
        # 각 셀로 이동 전에 예약 시도 (예약 대기 타임아웃 적용)
        for i, next_pos in enumerate(path[1:], start=1):
            with data_lock:
                if shared_data["statuses"][key] == "STOP":
                    logging.info("%s: STOP 명령 감지됨 - 경로 취소", key)
                    return
            attempts = 0
            start_wait = time.time()
            while not reserve_cell(key, next_pos):
                yield env.timeout(random.uniform(BACKOFF_MIN, BACKOFF_MAX))
                attempts += 1
                if attempts >= MAX_RESERVE_ATTEMPTS or time.time() - start_wait > WAIT_TIMEOUT:
                    logging.info("%s: 셀 %s 예약 시도 실패(%d회), 경로 재계산", key, next_pos, attempts)
                    moved = False
                    break
            if attempts >= MAX_RESERVE_ATTEMPTS:
                break
            yield env.timeout(MOVE_INTERVAL)
            with data_lock:
                agv_positions[agv_id] = next_pos
                shared_data["positions"][key] = next_pos
                shared_data["logs"][key].append({
                    "time": datetime.now().isoformat(),
                    "position": next_pos
                })
            moved = True
            release_cell(key, prev_cell)
            prev_cell = next_pos
            try:
                idx = path.index(next_pos)
                if idx < len(path) - 1:
                    with data_lock:
                        shared_data["directions"][key] = compute_direction(next_pos, path[idx+1])
            except ValueError:
                pass
            if next_pos == target:
                logging.info("[%s] %s 도착 -> %s", datetime.now().isoformat(), key, target)
                return
            current = next_pos

        if not moved:
            recalc_attempts += 1
            logging.info("%s: 경로 재계산을 위해 대기 (%s)", key, current)
            yield env.timeout(0.5)
            if recalc_attempts >= max_recalc_attempts:
                logging.error("%s: 최대 재계산 시도 횟수 초과. 이동 중단.", key)
                return

def agv_process(env, agv_id, agv_positions, logs, shelf_coords, exit_coords):
    """
    각 AGV별 메인 로직.
    AGV1 (agv_id==0)는 초기 경로를 5개의 세그먼트로 나누어,
    하드웨어에서 QR을 인식해 위치 좌표가 수신되면 다음 세그먼트를 전송합니다.
    이후 loading/unloading 작업은 기존 BFS 방식으로 진행합니다.
    나머지 AGV는 전체 MAP을 사용합니다.
    """
    key = f"AGV {agv_id+1}"
    if agv_id == 0:
        init_pos = (7, 0)
        grid = AGV1_MAP
    else:
        init_pos = random_start_position(agv_id)
        grid = MAP
    agv_positions[agv_id] = init_pos
    logs[agv_id].append((datetime.now().isoformat(), init_pos))
    with data_lock:
        shared_data["positions"][key] = init_pos
        shared_data["logs"][key].append({"time": datetime.now().isoformat(), "position": init_pos})
        shared_data["statuses"][key] = "RUNNING"
        shared_data["target"][key] = None
    logging.debug("%s 시작 위치: %s", key, init_pos)

    # AGV1: 초기 하드코딩 경로 실행 (세그먼트별)
    if agv_id == 0:
        segments = [
            [(7, 0), (6, 0), (5, 0), (4, 0)],
            [(4, 1), (4, 2), (4, 3)],
            [(3, 3)],
            [(3, 3), (3, 4)],
            [(2, 4), (1, 4), (0, 4)]
        ]
        for i, segment in enumerate(segments):
            send_full_path_to_agv1(segment)
            logging.info("[SIM] %s 세그먼트 %d 전송: %s", key, i+1, segment)
            target_coord = segment[-1]
            while True:
                # AGV1는 각 격자 이동마다 3.3초 대기 (실제 하드웨어 속도 반영)
                yield env.timeout(3.3)
                with data_lock:
                    current = shared_data["positions"][key]
                if current == target_coord:
                    logging.info("[SIM] %s 세그먼트 %d 완료, 도착: %s", key, i+1, current)
                    break
            # 각 세그먼트 전환 시 5초 대기 (회전 등 하드웨어 동작 반영)
            yield env.timeout(5)
        with data_lock:
            shared_data["statuses"][key] = "RUNNING"
        exit_target = random.choice(exit_coords)
        with data_lock:
            current = shared_data["positions"][key]
        while exit_target == current:
            exit_target = random.choice(exit_coords)
        with data_lock:
            shared_data["target"][key] = exit_target
            shared_data["agv1_expected_target"] = exit_target
        yield from move_to(env, agv_id, agv_positions, logs, exit_target, grid)
        with data_lock:
            shared_data["statuses"][key] = "UNLOADING"
        logging.info("[%s] %s 도착 -> %s (하역 완료, 5초 대기)", datetime.now().isoformat(), key, exit_target)
        yield env.timeout(5)
        logging.info("[%s] %s 0,4에서 5초간 정지", datetime.now().isoformat(), key)
        yield env.timeout(5)

    while True:
        if agv_id == 0:
            loading_target = random.choice(shelf_coords)
        else:
            with data_lock:
                available = set(shelf_coords) - shared_data["used_shelf_targets"]
                if not available:
                    available = set(shelf_coords)
                loading_target = random.choice(list(available))
                shared_data["used_shelf_targets"].add(loading_target)
        with data_lock:
            current = shared_data["positions"][key]
        while loading_target == current:
            loading_target = random.choice(shelf_coords)
        with data_lock:
            shared_data["target"][key] = loading_target
            shared_data["statuses"][key] = "RUNNING"
            if agv_id == 0:
                shared_data["agv1_expected_target"] = loading_target
        yield from move_to(env, agv_id, agv_positions, logs, loading_target, grid)
        with data_lock:
            shared_data["statuses"][key] = "LOADING"
            shared_data["directions"][key] = ""
        logging.info("[%s] %s 도착 -> %s (적재 완료, 10초 대기)", datetime.now().isoformat(), key, loading_target)
        loading_complete_time = env.now
        yield env.timeout(10)
        if agv_id != 0:
            with data_lock:
                shared_data["used_shelf_targets"].discard(loading_target)

        if agv_id == 0:
            exit_target = random.choice(exit_coords)
        else:
            with data_lock:
                available = set(exit_coords) - shared_data["used_exit_targets"]
                if not available:
                    available = set(exit_coords)
                exit_target = random.choice(list(available))
                shared_data["used_exit_targets"].add(exit_target)
        with data_lock:
            current = shared_data["positions"][key]
        while exit_target == current:
            exit_target = random.choice(exit_coords)
        with data_lock:
            shared_data["target"][key] = exit_target
            shared_data["statuses"][key] = "RUNNING"
            if agv_id == 0:
                shared_data["agv1_expected_target"] = exit_target
        yield from move_to(env, agv_id, agv_positions, logs, exit_target, grid)
        with data_lock:
            shared_data["statuses"][key] = "UNLOADING"
        unloading_complete_time = env.now
        with data_lock:
            shared_data["efficiency"][key] = unloading_complete_time - loading_complete_time
            shared_data["overall_efficiency_history"].clear()
            shared_data["overall_efficiency_history"].append(
                [datetime.now().isoformat(), unloading_complete_time - loading_complete_time]
            )
            shared_data["order_completed"][key] += 1
            logging.info("[SIM] %s 이번 사이클 효율: %.2f", key, unloading_complete_time - loading_complete_time)
            logging.info("[SIM] 전체 기록을 삭제 후 새 효율성만 반영: %.2f", unloading_complete_time - loading_complete_time)
        logging.info("[%s] %s 도착 -> %s (하역 완료, 5초 대기)", datetime.now().isoformat(), key, exit_target)
        yield env.timeout(5)
        if agv_id != 0:
            with data_lock:
                shared_data["used_exit_targets"].discard(exit_target)

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
        agv_positions[i] = None
        logs[i] = []
    for i in range(NUM_AGV):
        if i == 0:
            env.process(agv_process(env, i, agv_positions, logs, AGV1_shelf_coords, AGV1_exit_coords))
        else:
            env.process(agv_process(env, i, agv_positions, logs, shelf_coords, exit_coords))
    env.run(until=float('inf'))

if __name__ == "__main__":
    simulation_main()
