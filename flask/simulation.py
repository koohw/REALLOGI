# import simpy
# import random
# from collections import deque
# from threading import Lock
# import time
# import logging
# from datetime import datetime  # 실제 현실시간 사용
# import paho.mqtt.client as mqtt
# import json

# # --------------------------------------------------
# # 로그 설정
# DEBUG_MODE = False
# logging.basicConfig(
#     level=logging.DEBUG if DEBUG_MODE else logging.INFO,
#     format='[%(asctime)s] %(levelname)s: %(message)s',
#     handlers=[
#         logging.StreamHandler(),
#         logging.FileHandler("simulation.log", encoding='utf-8')
#     ]
# )
# # --------------------------------------------------

# ##############################################################################
# # MQTT 설정 (AGV1은 MQTT 통신 사용)
# ##############################################################################
# BROKER = "broker.hivemq.com"
# PORT = 1883
# TOPIC_COMMAND_TO_DEVICE = "simpy/commands"   # 서버 → 하드웨어 명령
# TOPIC_STATUS_FROM_DEVICE = "agv/status"      # 하드웨어 → 서버 ACK/상태

# mqtt_client = mqtt.Client(client_id="simulation_server", protocol=mqtt.MQTTv311)

# def on_message(client, userdata, msg):
#     """
#     MQTT 콜백: 하드웨어(AGV 1)에서 각 좌표 이동 완료 시 ACK 메시지를 수신합니다.
#     """
#     try:
#         payload = json.loads(msg.payload.decode())
#         if payload.get("ack"):
#             ack_location = tuple(payload.get("location"))
#             with data_lock:
#                 shared_data["positions"]["AGV 1"] = ack_location
#             logging.info("[SIM] ACK 수신, AGV 1 위치 업데이트: %s", ack_location)
#         else:
#             logging.info("[SIM] ACK 아닌 메시지: %s", payload)
#     except Exception as e:
#         logging.error("[SIM] on_message 오류: %s", e)

# mqtt_client.on_message = on_message
# mqtt_client.connect(BROKER, PORT, 60)
# mqtt_client.subscribe(TOPIC_STATUS_FROM_DEVICE)
# mqtt_client.loop_start()

# ##############################################################################
# # 1) 맵 및 좌표 정의
# ##############################################################################
# map_data = [
#     [2, 2, 2, 2, 2, 2, 2],  # 출구 (0행)
#     [0, 0, 0, 0, 0, 0, 0],
#     [0, 1, 0, 1, 0, 1, 0],
#     [0, 1, 0, 1, 0, 1, 0],
#     [0, 0, 0, 0, 0, 0, 0],
#     [0, 1, 0, 1, 0, 1, 0],
#     [0, 1, 0, 1, 0, 1, 0],
#     [0, 0, 0, 0, 0, 0, 0],
#     [2, 2, 2, 2, 2, 2, 2]   # 출발 (8행)
# ]
# ROWS = len(map_data)
# COLS = len(map_data[0])

# shelf_coords = [(2, 2), (2, 4), (2, 6),
#                 (5, 2), (5, 4), (5, 6)]
# exit_coords = [(0, c) for c in range(COLS) if map_data[0][c] == 2]

# ##############################################################################
# # 2) 공유 데이터 및 락
# ##############################################################################
# data_lock = Lock()
# shared_data = {
#     "positions": {
#         "AGV 1": None,
#         "AGV 2": None,
#         "AGV 3": None,
#         "AGV 4": None
#     },
#     "logs": {
#         "AGV 1": [],
#         "AGV 2": [],
#         "AGV 3": [],
#         "AGV 4": []
#     },
#     "statuses": {
#         "AGV 1": "",
#         "AGV 2": "",
#         "AGV 3": "",
#         "AGV 4": ""
#     },
#     "directions": {
#         "AGV 1": "",
#         "AGV 2": "",
#         "AGV 3": "",
#         "AGV 4": ""
#     },
#     "target": {   # 각 AGV의 현재 목표(target)
#         "AGV 1": None,
#         "AGV 2": None,
#         "AGV 3": None,
#         "AGV 4": None
#     },
#     "agv1_target": None,
#     "agv1_moving_ack": False,
#     "agv1_path": [],
#     "agv1_expected_target": None,
#     "agv1_last_command_time": 0,
#     "order_completed": {
#         "AGV 1": 0,
#         "AGV 2": 0,
#         "AGV 3": 0,
#         "AGV 4": 0
#     },
#     "efficiency": {"AGV 1": 0, "AGV 2": 0, "AGV 3": 0, "AGV 4": 0},
#     "overall_efficiency_history": [],
#     # 사용 중인 loading/unloading 목표를 추적 (AGV1 제외)
#     "used_shelf_targets": set(),
#     "used_exit_targets": set()
# }

# ##############################################################################
# # 3) BFS 경로 탐색 함수 (너비 우선 탐색)
# ##############################################################################
# def bfs_path(grid, start, goal, obstacles):
#     if not start or not goal:
#         return None
#     queue = deque([(start, [start])])
#     visited = set([start])
#     directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
#     while queue:
#         current, path = queue.popleft()
#         if current == goal:
#             return path
#         r, c = current
#         for dr, dc in directions:
#             nr, nc = r + dr, c + dc
#             if 0 <= nr < ROWS and 0 <= nc < COLS:
#                 if grid[nr][nc] != 1 and ((nr, nc) == goal or (nr, nc) not in obstacles):
#                     if (nr, nc) not in visited:
#                         visited.add((nr, nc))
#                         queue.append(((nr, nc), path + [(nr, nc)]))
#     return None

# ##############################################################################
# # 4) 이동 방향 계산 함수
# ##############################################################################
# def compute_direction(curr, nxt):
#     dr = nxt[0] - curr[0]
#     dc = nxt[1] - curr[1]
#     if dr == -1 and dc == 0:
#         return "u"
#     elif dr == 1 and dc == 0:
#         return "d"
#     elif dr == 0 and dc == 1:
#         return "R"
#     elif dr == 0 and dc == -1:
#         return "L"
#     else:
#         return ""

# ##############################################################################
# # 5) MQTT 통신: 전체 경로 명령 전송 (AGV1 전용)
# ##############################################################################
# def send_full_path_to_agv1(full_path):
#     with data_lock:
#         current = shared_data["positions"]["AGV 1"]
#     if full_path[0] != current:
#         full_path.insert(0, current)
#     logging.debug("[SIM] send_full_path_to_agv1(full_path=%s)", full_path)
#     payload = {
#         "command": "PATH",
#         "data": {
#             "full_path": [list(p) for p in full_path]
#         }
#     }
#     result = mqtt_client.publish(TOPIC_COMMAND_TO_DEVICE, json.dumps(payload))
#     if result[0] == 0:
#         logging.info("[SIM] PATH 명령 전송 성공: %s", payload)
#         with data_lock:
#             shared_data["agv1_path"] = full_path
#             shared_data["agv1_last_command_time"] = time.time()
#     else:
#         logging.error("[SIM] PATH 명령 전송 실패: %s", payload)

# ##############################################################################
# # 6) 전체 경로 계산 함수
# ##############################################################################
# def calculate_full_path(start, goal, obstacles):
#     path = bfs_path(map_data, start, goal, obstacles)
#     if path is None:
#         logging.warning("경로 탐색 실패: 시작 %s, 목표 %s, 장애물: %s", start, goal, obstacles)
#     else:
#         logging.debug("경로 탐색 성공: 시작 %s, 목표 %s, 경로: %s", start, goal, path)
#     return path

# ##############################################################################
# # 7) Manhattan 거리 계산 함수
# ##############################################################################
# def manhattan_distance(a, b):
#     return abs(a[0] - b[0]) + abs(a[1] - b[1])

# ##############################################################################
# # 8) Deadlock 체크 함수 (필요시 사용)
# ##############################################################################
# DEADLOCK_THRESHOLD = 5
# def check_deadlock(agv_positions, shared_data):
#     deadlock_list = []
#     with data_lock:
#         for key, pos in shared_data["positions"].items():
#             target = shared_data.get("target", {}).get(key)
#             if target is not None:
#                 rem = manhattan_distance(pos, target)
#                 if rem <= DEADLOCK_THRESHOLD:
#                     deadlock_list.append((key, rem))
#     if deadlock_list:
#         logging.debug("Deadlock 후보 리스트: %s", deadlock_list)
#     if len(deadlock_list) >= 3:
#         deadlock_list.sort(key=lambda x: x[1])
#         return [key for key, _ in deadlock_list]
#     else:
#         return []

# ##############################################################################
# # 9) AGV 프로세스 및 이동 함수 (충돌 회피 및 장애물 고려)
# ##############################################################################
# MOVE_INTERVAL = 1  # 1초마다 한 칸 이동
# SIMULATE_MQTT = True  # AGV1은 MQTT로 전체 경로 명령 전송

# def random_start_position(agv_id):
#     col = (agv_id * 2) % COLS
#     return (ROWS - 1, col)

# def agv_process(env, agv_id, agv_positions, logs, shelf_coords, exit_coords):
#     init_pos = random_start_position(agv_id)
#     agv_positions[agv_id] = init_pos
#     logs[agv_id].append((datetime.now().isoformat(), init_pos))
#     key = f"AGV {agv_id+1}"
#     with data_lock:
#         shared_data["positions"][key] = init_pos
#         shared_data["logs"][key].append({"time": datetime.now().isoformat(), "position": init_pos})
#         shared_data["statuses"][key] = "RUNNING"
#         if "target" not in shared_data:
#             shared_data["target"] = {}
#     logging.debug("AGV %s 시작 위치: %s", agv_id, init_pos)

#     while True:
#         # Loading 단계: AGV1은 자유롭게, 나머지는 겹치지 않는 loading target 선택
#         if agv_id == 0:
#             loading_target = random.choice(shelf_coords)
#         else:
#             with data_lock:
#                 available = set(shelf_coords) - shared_data["used_shelf_targets"]
#                 if not available:
#                     available = set(shelf_coords)
#                 loading_target = random.choice(list(available))
#                 shared_data["used_shelf_targets"].add(loading_target)
#         with data_lock:
#             current = shared_data["positions"][key]
#         while loading_target == current:
#             loading_target = random.choice(shelf_coords)
#         with data_lock:
#             shared_data["target"][key] = loading_target
#             shared_data["statuses"][key] = "RUNNING"
#             if agv_id == 0:
#                 shared_data["agv1_expected_target"] = loading_target
#         yield from move_to(env, agv_id, agv_positions, logs, loading_target)
#         # 적재 완료 후 10초 대기
#         with data_lock:
#             shared_data["statuses"][key] = "LOADING"
#             shared_data["directions"][key] = ""
#         logging.info("[%s] %s 도착 -> %s (적재 완료, 10초 대기)", datetime.now().isoformat(), key, loading_target)
#         yield env.timeout(10)
#         loading_complete_time = env.now
#         if agv_id != 0:
#             with data_lock:
#                 shared_data["used_shelf_targets"].discard(loading_target)

#         # Unloading 단계: AGV1은 자유롭게, 나머지는 겹치지 않는 unloading target 선택
#         if agv_id == 0:
#             exit_target = random.choice(exit_coords)
#         else:
#             with data_lock:
#                 available = set(exit_coords) - shared_data["used_exit_targets"]
#                 if not available:
#                     available = set(exit_coords)
#                 exit_target = random.choice(list(available))
#                 shared_data["used_exit_targets"].add(exit_target)
#         with data_lock:
#             current = shared_data["positions"][key]
#         while exit_target == current:
#             exit_target = random.choice(exit_coords)
#         with data_lock:
#             shared_data["target"][key] = exit_target
#             shared_data["statuses"][key] = "UNLOADING"
#             if agv_id == 0:
#                 shared_data["agv1_expected_target"] = exit_target
#         yield from move_to(env, agv_id, agv_positions, logs, exit_target)
#         unloading_complete_time = env.now
#         cycle_eff = unloading_complete_time - loading_complete_time
#         with data_lock:
#             if shared_data["order_completed"][key] == 0:
#                 shared_data["efficiency"][key] = cycle_eff
#             else:
#                 alpha = 0.5
#                 shared_data["efficiency"][key] = alpha * cycle_eff + (1 - alpha) * shared_data["efficiency"][key]
#             shared_data["order_completed"][key] += 1
#             total_eff = sum(shared_data["efficiency"].values())
#             avg_eff = total_eff / len(shared_data["efficiency"]) if shared_data["efficiency"] else 0
#             shared_data["overall_efficiency_history"].append([datetime.now().isoformat(), avg_eff])
#             logging.info("[SIM] %s 사이클 효율: %.2f / 전체 평균 효율: %.2f", key, shared_data["efficiency"][key], avg_eff)
#         logging.info("[%s] %s 도착 -> %s (하역 완료, 5초 대기)", datetime.now().isoformat(), key, exit_target)
#         yield env.timeout(5)
#         if agv_id != 0:
#             with data_lock:
#                 shared_data["used_exit_targets"].discard(exit_target)

# def move_to(env, agv_id, agv_positions, logs, target):
#     """
#     이동 단계: 각 이동 단계마다 다른 AGV의 현재 위치를 장애물로 포함해 BFS 경로를 계산.
#     AGV1은 전체 경로를 미리 계산해 MQTT로 전송.
#     비AGV1은 대기 중 5초 이상이면 상태를 STOP으로 전환하고 새로운 목표를 재설정.
#     """
#     key = f"AGV {agv_id+1}"
    
#     with data_lock:
#         current = agv_positions[agv_id]
#     if current == target:
#         logging.info("%s: 이미 목표에 도착함 (%s)", key, target)
#         return

#     # 만약 목표 셀이 다른 AGV에 의해 점유되어 있으면 대기하면서 대기시간 체크
#     wait_start = env.now
#     while True:
#         with data_lock:
#             occupied = any(pos == target for k, pos in shared_data["positions"].items() if k != key)
#         if not occupied:
#             break
#         if agv_id != 0 and (env.now - wait_start) > 5:
#             # STOP 상태 전환 및 목표 재설정
#             with data_lock:
#                 shared_data["statuses"][key] = "STOP"
#                 current_target = shared_data["target"][key]
#             new_target = current_target
#             if current_target in shelf_coords:
#                 with data_lock:
#                     available = set(shelf_coords) - shared_data["used_shelf_targets"]
#                     if available:
#                         available.discard(current_target)
#                         new_target = random.choice(list(available))
#                         shared_data["used_shelf_targets"].discard(current_target)
#                         shared_data["used_shelf_targets"].add(new_target)
#             elif current_target in exit_coords:
#                 with data_lock:
#                     available = set(exit_coords) - shared_data["used_exit_targets"]
#                     if available:
#                         available.discard(current_target)
#                         new_target = random.choice(list(available))
#                         shared_data["used_exit_targets"].discard(current_target)
#                         shared_data["used_exit_targets"].add(new_target)
#             with data_lock:
#                 shared_data["target"][key] = new_target
#                 shared_data["statuses"][key] = "RUNNING"
#             logging.info("%s: STOP 상태 5초 초과 -> 새로운 목표 재설정: %s", key, new_target)
#             wait_start = env.now  # 타이머 초기화
#         yield env.timeout(1)

#     # AGV1은 MQTT 전송 후 진행
#     if agv_id == 0 and SIMULATE_MQTT:
#         with data_lock:
#             current = agv_positions[agv_id]
#             obstacles = { pos for k, pos in shared_data["positions"].items() if k != key }
#         path = calculate_full_path(current, target, obstacles)
#         if not path or len(path) < 2:
#             logging.warning("%s: 경로 없음, 재계산 시도 (현재: %s, 목표: %s)", key, current, target)
#             yield env.timeout(0.5)
#         else:
#             send_full_path_to_agv1(path)
#             while True:
#                 yield env.timeout(0.5)
#                 with data_lock:
#                     current = shared_data["positions"][key]
#                     agv_positions[agv_id] = current
#                 try:
#                     idx = path.index(current)
#                     if idx < len(path) - 1:
#                         with data_lock:
#                             shared_data["directions"][key] = compute_direction(current, path[idx+1])
#                 except ValueError:
#                     pass
#                 if current == target:
#                     break
#             with data_lock:
#                 agv_positions[agv_id] = target
#         return

#     # 비AGV1의 경우, 한 칸씩 이동하며 경로 재계산
#     while True:
#         with data_lock:
#             current = agv_positions[agv_id]
#             if current == target:
#                 logging.info("%s: 이미 목표에 도착함 (%s)", key, target)
#                 return
#             obstacles = { pos for k, pos in shared_data["positions"].items() if k != key }
#             # AGV1의 진행 경로(현재 및 다음 셀)를 장애물에 포함
#             agv1_key = "AGV 1"
#             if agv1_key in shared_data["positions"] and shared_data["positions"][agv1_key]:
#                 obstacles.add(shared_data["positions"][agv1_key])
#                 agv1_path = shared_data.get("agv1_path", [])
#                 if agv1_path:
#                     try:
#                         idx = agv1_path.index(shared_data["positions"][agv1_key])
#                         if idx < len(agv1_path) - 1:
#                             obstacles.add(agv1_path[idx+1])
#                     except ValueError:
#                         pass
#             # 다른 AGV들이 STOP, LOADING, UNLOADING 상태인 경우(자신 제외)
#             for k, status in shared_data["statuses"].items():
#                 if k != key and status in ("STOP", "LOADING", "UNLOADING"):
#                     pos = shared_data["positions"].get(k)
#                     if pos:
#                         obstacles.add(pos)
#         path = calculate_full_path(current, target, obstacles)
#         if not path or len(path) < 2:
#             logging.warning("%s: 경로 없음, 재계산 시도 (현재: %s, 목표: %s, 장애물: %s)", key, current, target, obstacles)
#             yield env.timeout(0.5)
#             continue
#         logging.debug("%s 전체 경로: %s", key, path)
#         moved = False
#         for next_pos in path[1:]:
#             occupied = False
#             with data_lock:
#                 for k, pos in shared_data["positions"].items():
#                     if k != key and pos == next_pos:
#                         occupied = True
#                         break
#             if occupied:
#                 logging.info("%s: 다음 셀 %s 점유됨 - 경로 재계산", key, next_pos)
#                 break
#             direction = compute_direction(current, next_pos)
#             with data_lock:
#                 shared_data["directions"][key] = direction
#             yield env.timeout(MOVE_INTERVAL)
#             with data_lock:
#                 agv_positions[agv_id] = next_pos
#                 shared_data["positions"][key] = next_pos
#                 shared_data["logs"][key].append({
#                     "time": datetime.now().isoformat(),
#                     "position": next_pos
#                 })
#             moved = True
#             if next_pos == target:
#                 logging.info("[%s] %s 도착 -> %s", datetime.now().isoformat(), key, target)
#                 return
#             current = next_pos
#         if not moved:
#             yield env.timeout(0.5)

# ##############################################################################
# # 10) 시뮬레이션 메인 함수
# ##############################################################################
# try:
#     from simpy.rt import RealtimeEnvironment
# except ImportError:
#     RealtimeEnvironment = simpy.Environment

# def simulation_main():
#     env = RealtimeEnvironment(factor=1, strict=False)
#     NUM_AGV = 4
#     agv_positions = {}
#     logs = {}
#     for i in range(NUM_AGV):
#         agv_positions[i] = None
#         logs[i] = []
#     for i in range(NUM_AGV):
#         env.process(agv_process(env, i, agv_positions, logs, shelf_coords, exit_coords))
#     env.run(until=float('inf'))

# if __name__ == "__main__":
#     simulation_main()










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
    # 사용 중인 loading/unloading 목표를 추적 (AGV1 제외)
    "used_shelf_targets": set(),
    "used_exit_targets": set()
}

##############################################################################
# 3) BFS 경로 탐색 함수 (너비 우선 탐색)
##############################################################################
from collections import deque

def bfs_path(grid, start, goal, obstacles):
    if not start or not goal:
        return None
    queue = deque([(start, [start])])
    visited = set([start])
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    while queue:
        current, path = queue.popleft()
        if current == goal:
            return path
        r, c = current
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS:
                # 장애물이 아닌 칸, or 최종 goal이면 OK
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
            "full_path": [list(p) for p in full_path]
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
# 6) 전체 경로 계산 함수
##############################################################################
def calculate_full_path(start, goal, obstacles):
    path = bfs_path(map_data, start, goal, obstacles)
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
# 9) AGV 프로세스 및 이동 함수 (충돌 회피 및 장애물 고려)
##############################################################################
MOVE_INTERVAL = 1  # 1초마다 한 칸 이동
SIMULATE_MQTT = False  # AGV1은 MQTT로 전체 경로 명령 전송

def random_start_position(agv_id):
    col = (agv_id * 2) % COLS
    return (ROWS - 1, col)

def agv_process(env, agv_id, agv_positions, logs, shelf_coords, exit_coords):
    """
    각 AGV별 메인 로직. loading/unloading 반복, 경로 BFS, 충돌 회피, 효율성 계산 등 수행.
    """
    init_pos = random_start_position(agv_id)
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
        # 1) Loading 단계: (AGV1 자유, 나머지는 중복 없는 선반)
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
        yield from move_to(env, agv_id, agv_positions, logs, loading_target)

        with data_lock:
            shared_data["statuses"][key] = "LOADING"
            shared_data["directions"][key] = ""
        logging.info("[%s] %s 도착 -> %s (적재 완료, 10초 대기)",
                     datetime.now().isoformat(), key, loading_target)
        loading_complete_time = env.now
        yield env.timeout(10)

        if agv_id != 0:
            with data_lock:
                shared_data["used_shelf_targets"].discard(loading_target)

        # 2) Unloading 단계: (AGV1 자유, 나머지는 중복 없는 출구)
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
            shared_data["statuses"][key] = "UNLOADING"
            if agv_id == 0:
                shared_data["agv1_expected_target"] = exit_target
        yield from move_to(env, agv_id, agv_positions, logs, exit_target)

        unloading_complete_time = env.now
        cycle_eff = unloading_complete_time - loading_complete_time

        # *** 여기서 효율성 로직을 수정: 이전 기록을 모두 지우고 이번 값만 반영 ***
        with data_lock:
            # 이번 사이클 효율만 기록
            shared_data["efficiency"][key] = cycle_eff
            # 전체 history를 지우고 현재 효율성만 반영
            shared_data["overall_efficiency_history"].clear()
            shared_data["overall_efficiency_history"].append(
                [datetime.now().isoformat(), cycle_eff]
            )
            shared_data["order_completed"][key] += 1

            logging.info("[SIM] %s 이번 사이클 효율: %.2f", key, cycle_eff)
            logging.info("[SIM] 전체 기록을 삭제 후 새 효율성만 반영: %.2f", cycle_eff)

        logging.info("[%s] %s 도착 -> %s (하역 완료, 5초 대기)",
                     datetime.now().isoformat(), key, exit_target)
        yield env.timeout(5)
        if agv_id != 0:
            with data_lock:
                shared_data["used_exit_targets"].discard(exit_target)

def move_to(env, agv_id, agv_positions, logs, target):
    """
    이동 단계: BFS로 경로를 계산, 충돌 회피, AGV1은 MQTT로 전체 경로를 전송.
    비AGV1은 대기 중 5초 이상이면 STOP 상태로 전환, 새로운 목표 재설정.
    """
    key = f"AGV {agv_id+1}"

    # STOP 상태 대기
    while True:
        with data_lock:
            if shared_data["statuses"][key] != "STOP":
                break
            else:
                logging.info("%s: 정지 상태. 재가동 명령 대기 중", key)
        yield env.timeout(1)

    with data_lock:
        current = agv_positions[agv_id]
    if current == target:
        logging.info("%s: 이미 목표에 도착함 (%s)", key, target)
        return

    # 목표 셀이 다른 AGV에 의해 점유되어 있으면 대기 + 5초 이상이면 STOP 처리
    wait_start = env.now
    while True:
        with data_lock:
            occupied = any(pos == target for k, pos in shared_data["positions"].items() if k != key)
        if not occupied:
            break
        if agv_id != 0 and (env.now - wait_start) > 5:
            with data_lock:
                shared_data["statuses"][key] = "STOP"
                current_target = shared_data["target"][key]
            new_target = current_target
            if current_target in shelf_coords:
                with data_lock:
                    available = set(shelf_coords) - shared_data["used_shelf_targets"]
                    if available:
                        available.discard(current_target)
                        new_target = random.choice(list(available))
                        shared_data["used_shelf_targets"].discard(current_target)
                        shared_data["used_shelf_targets"].add(new_target)
            elif current_target in exit_coords:
                with data_lock:
                    available = set(exit_coords) - shared_data["used_exit_targets"]
                    if available:
                        available.discard(current_target)
                        new_target = random.choice(list(available))
                        shared_data["used_exit_targets"].discard(current_target)
                        shared_data["used_exit_targets"].add(new_target)
            with data_lock:
                shared_data["target"][key] = new_target
                shared_data["statuses"][key] = "RUNNING"
            logging.info("%s: STOP 상태 5초 초과 -> 새로운 목표 재설정: %s", key, new_target)
            wait_start = env.now
        yield env.timeout(1)

    # AGV1이면 MQTT로 전체 경로 전송
    if agv_id == 0 and SIMULATE_MQTT:
        with data_lock:
            current = agv_positions[agv_id]
            obstacles = {pos for k, pos in shared_data["positions"].items() if k != key}
        path = calculate_full_path(current, target, obstacles)
        if not path or len(path) < 2:
            logging.warning("%s: 경로 없음, 재계산 시도 (현재: %s, 목표: %s)",
                            key, current, target)
            yield env.timeout(0.5)
        else:
            send_full_path_to_agv1(path)
            while True:
                yield env.timeout(0.5)
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

    # 비AGV1: 한 칸씩 이동 (BFS 재계산)
    while True:
        with data_lock:
            if shared_data["statuses"][key] == "STOP":
                logging.info("%s: 정지 상태 감지, 이동 중단", key)
                yield env.timeout(1)
                continue
            current = agv_positions[agv_id]
            if current == target:
                logging.info("%s: 이미 목표에 도착함 (%s)", key, target)
                return
            obstacles = {pos for k, pos in shared_data["positions"].items() if k != key}
            # AGV1의 경로도 장애물에 포함
            agv1_key = "AGV 1"
            if agv1_key in shared_data["positions"] and shared_data["positions"][agv1_key]:
                obstacles.add(shared_data["positions"][agv1_key])
                agv1_path = shared_data.get("agv1_path", [])
                if agv1_path:
                    try:
                        idx = agv1_path.index(shared_data["positions"][agv1_key])
                        if idx < len(agv1_path) - 1:
                            obstacles.add(agv1_path[idx+1])
                    except ValueError:
                        pass
            # 다른 AGV들의 STOP, LOADING, UNLOADING 셀도 장애물
            for k, status in shared_data["statuses"].items():
                if k != key and status in ("STOP", "LOADING", "UNLOADING"):
                    pos = shared_data["positions"].get(k)
                    if pos:
                        obstacles.add(pos)
        path = calculate_full_path(current, target, obstacles)
        if not path or len(path) < 2:
            logging.warning("%s: 경로 없음, 재계산 시도 (현재: %s, 목표: %s, 장애물: %s)",
                            key, current, target, obstacles)
            yield env.timeout(0.5)
            continue
        logging.debug("%s 전체 경로: %s", key, path)

        moved = False
        for next_pos in path[1:]:
            occupied = False
            with data_lock:
                for k, pos in shared_data["positions"].items():
                    if k != key and pos == next_pos:
                        occupied = True
                        break
            if occupied:
                logging.info("%s: 다음 셀 %s 점유됨 - 경로 재계산", key, next_pos)
                break
            direction = compute_direction(current, next_pos)
            with data_lock:
                shared_data["directions"][key] = direction
            yield env.timeout(MOVE_INTERVAL)
            with data_lock:
                agv_positions[agv_id] = next_pos
                shared_data["positions"][key] = next_pos
                shared_data["logs"][key].append({
                    "time": datetime.now().isoformat(),
                    "position": next_pos
                })
            moved = True
            if next_pos == target:
                logging.info("[%s] %s 도착 -> %s", datetime.now().isoformat(), key, target)
                return
            current = next_pos

        if not moved:
            yield env.timeout(0.5)

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
        env.process(agv_process(env, i, agv_positions, logs, shelf_coords, exit_coords))
    env.run(until=float('inf'))

if __name__ == "__main__":
    simulation_main()

