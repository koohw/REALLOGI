# # simulation.py

# import simpy
# import random
# import matplotlib.pyplot as plt
# import matplotlib.animation as animation
# import matplotlib.patches as patches
# from collections import deque
# from threading import Lock
# import time
# import logging
# from datetime import datetime  # 실제 현실시간 사용

# # --------------------------------------------------
# # 로그 설정: 개발/디버깅 시 DEBUG, 운영 시 INFO 레벨로 설정
# DEBUG_MODE = False  # 개발/디버깅: True, 운영: False
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
# # 1) 맵 및 좌표 정의
# ##############################################################################
# # 맵 데이터: 2는 출구 혹은 출발지, 1은 장애물, 0은 통로
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

# # 선반(하역) 좌표 목록
# shelf_coords = [(2, 2), (2, 4), (2, 6),
#                 (5, 2), (5, 4), (5, 6)]
# # 출구 좌표: 맵 첫 행에서 값이 2인 좌표
# exit_coords = [(0, c) for c in range(COLS) if map_data[0][c] == 2]

# ##############################################################################
# # 2) 공유 데이터 및 락 (SSE와 시뮬레이션 간 데이터 공유)
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
#     "agv1_target": None,
#     "agv1_moving_ack": False,
#     "order_completed": {  # 주문완료 카운터 추가
#         "AGV 1": 0,
#         "AGV 2": 0,
#         "AGV 3": 0,
#         "AGV 4": 0
#     }
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
# # 4-1) 보조 함수: 인접 이동 가능한 좌표 목록 반환
# ##############################################################################
# def available_moves(pos):
#     moves = []
#     for (dr, dc) in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
#         new_pos = (pos[0] + dr, pos[1] + dc)
#         if 0 <= new_pos[0] < ROWS and 0 <= new_pos[1] < COLS and map_data[new_pos[0]][new_pos[1]] != 1:
#             moves.append(new_pos)
#     return moves

# ##############################################################################
# # 4-2) 보조 함수: 주어진 위치가 데드락 상태인지 확인
# ##############################################################################
# def is_deadlocked(pos, occupied):
#     for m in available_moves(pos):
#         if m not in occupied:
#             return False
#     return True

# ##############################################################################
# # 5) MQTT 통신 (AGV1 하드웨어 연동용 플레이스홀더)
# ##############################################################################
# def send_command_to_agv1(next_pos):
#     logging.debug("[SIM] (플레이스홀더) send_command_to_agv1(next_pos=%s)", next_pos)
#     with data_lock:
#         shared_data["positions"]["AGV 1"] = next_pos
#         shared_data["agv1_moving_ack"] = True

# ##############################################################################
# # 6) AGV 프로세스 및 이동 함수
# ##############################################################################
# MOVE_INTERVAL = 1  # 1초마다 한 칸 이동
# WAIT_INTERVAL = 1

# # 운영 모드에서는 실제 하드웨어 연동 사용을 위해 SIMULATE_MQTT는 False로 설정합니다.
# SIMULATE_MQTT = False

# def random_start_position():
#     # 시작 좌표를 항상 (8, 0)으로 반환하도록 수정
#     return (8, 0)

# def get_next_position(current, target):
#     """
#     현재 위치(current)와 목표(target)를 기반으로 BFS 알고리즘을 사용하여 다음 좌표를 계산합니다.
#     운영 모드에서는 target이 None이면, 기본 동작으로 현재 위치에서 한 칸 위로 이동하는 기본 목표(default_target)를 사용합니다.
#     """
#     if target is None:
#         # 기본 목표: 현재 위치에서 한 칸 위로 이동
#         default_target = (current[0] - 1, current[1])
#         # 맵 경계 체크
#         if default_target[0] < 0 or default_target[0] >= ROWS or default_target[1] < 0 or default_target[1] >= COLS:
#             return current  # 경계를 벗어나면 현재 위치 유지
#         target = default_target
#     path = bfs_path(map_data, current, target, obstacles=set())
#     if path and len(path) > 1:
#         return path[1]
#     return current

# def agv_process(env, agv_id, agv_positions, logs, goal_pos, shelf_coords, exit_coords):
#     init_pos = random_start_position()
#     agv_positions[agv_id] = init_pos
#     logs[agv_id].append((datetime.now().isoformat(), init_pos))
#     key = f"AGV {agv_id+1}"
#     with data_lock:
#         shared_data["positions"][key] = init_pos
#         shared_data["logs"][key].append({"time": datetime.now().isoformat(), "position": init_pos})
#         shared_data["statuses"][key] = "RUNNING"
#     logging.debug("AGV %s 시작 위치: %s", agv_id, init_pos)

#     while True:
#         # 선반(하역) 좌표로 이동
#         unloading_target = random.choice(shelf_coords)
#         with data_lock:
#             shared_data["statuses"][key] = "RUNNING"
#         yield from move_to(env, agv_id, agv_positions, logs, unloading_target)
#         # 도착 후 10초간 하역 상태 유지
#         with data_lock:
#             shared_data["statuses"][key] = "UNLOADING"
#             shared_data["directions"][key] = ""
#         yield env.timeout(10)
#         # 출구 좌표로 이동
#         exit_target = random.choice(exit_coords)
#         with data_lock:
#             shared_data["statuses"][key] = "RUNNING"
#         yield from move_to(env, agv_id, agv_positions, logs, exit_target)
#         # 5초 멈춤 (출구에서 멈춤)이 완료된 후 주문완료 카운터 증가
#         yield env.timeout(5)
#         with data_lock:
#             shared_data["order_completed"][key] += 1

# def move_to(env, agv_id, agv_positions, logs, target):
#     key = f"AGV {agv_id+1}"
#     while True:
#         yield env.timeout(MOVE_INTERVAL)
#         curr_pos = agv_positions[agv_id]
#         others = {k: pos for k, pos in agv_positions.items() if k != agv_id}
#         path = bfs_path(map_data, curr_pos, target, set(others.values()))
#         if path and len(path) > 1:
#             next_pos = path[1]
#             direction = compute_direction(curr_pos, next_pos)
#             with data_lock:
#                 shared_data["directions"][key] = direction

#             if next_pos in others.values():
#                 blocker = None
#                 for k, pos in others.items():
#                     if pos == next_pos:
#                         blocker = k
#                         break
#                 our_path = bfs_path(map_data, curr_pos, target, set())
#                 our_distance = len(our_path) if our_path is not None else float('inf')
#                 blocker_path = bfs_path(map_data, agv_positions[blocker], target, set()) if blocker is not None else None
#                 blocker_distance = len(blocker_path) if blocker_path is not None else float('inf')
#                 occupied_for_blocker = set(agv_positions.values())
#                 occupied_for_blocker.discard(agv_positions[blocker])
#                 blocker_deadlocked = is_deadlocked(agv_positions[blocker], occupied_for_blocker)
#                 if our_distance > blocker_distance:
#                     with data_lock:
#                         shared_data["statuses"][key] = "STOPPED"
#                         shared_data["directions"][key] = ""
#                     yield env.timeout(WAIT_INTERVAL)
#                     continue
#                 elif our_distance == blocker_distance:
#                     if not blocker_deadlocked:
#                         with data_lock:
#                             shared_data["statuses"][key] = "STOPPED"
#                             shared_data["directions"][key] = ""
#                         yield env.timeout(WAIT_INTERVAL)
#                         continue

#             if agv_id == 0 and SIMULATE_MQTT:
#                 with data_lock:
#                     shared_data["agv1_target"] = next_pos
#                     shared_data["agv1_moving_ack"] = False
#                 send_command_to_agv1(next_pos)
#                 ack_received = False
#                 while not ack_received:
#                     yield env.timeout(0.2)
#                     with data_lock:
#                         if shared_data["agv1_moving_ack"]:
#                             ack_received = True
#                 with data_lock:
#                     agv_positions[agv_id] = shared_data["positions"]["AGV 1"]
#             else:
#                 agv_positions[agv_id] = next_pos

#             with data_lock:
#                 shared_data["statuses"][key] = "RUNNING"
#                 shared_data["positions"][key] = agv_positions[agv_id]
#                 shared_data["logs"][key].append({
#                     "time": datetime.now().isoformat(),
#                     "position": agv_positions[agv_id] 
#                 })
#         else:
#             if curr_pos == target:
#                 logs[agv_id].append((datetime.now().isoformat(), curr_pos))
#                 logging.info("[%s] AGV %s 도착 -> %s", datetime.now().isoformat(), agv_id, curr_pos)
#                 return
#         logs[agv_id].append((datetime.now().isoformat(), agv_positions[agv_id]))

# ##############################################################################
# # 7) 시뮬레이션 메인 함수 (실시간, 무한 실행)
# ##############################################################################
# try:
#     from simpy.rt import RealtimeEnvironment
# except ImportError:
#     RealtimeEnvironment = simpy.Environment

# def simulation_main():
#     # 운영 모드에서는 AGV 1의 시뮬레이션 프로세스를 실행하지 않음 (하드웨어 연동 사용)
#     env = RealtimeEnvironment(factor=1, strict=False)
#     NUM_AGV = 4
#     agv_positions = {}
#     logs = {}
#     for i in range(NUM_AGV):
#         agv_positions[i] = (0, 0)
#         logs[i] = []
#     # for i in range(NUM_AGV):
#     #     if i == 0 and not DEBUG_MODE:
#     #         print("[운영 모드] AGV 1 시뮬레이션 프로세스 실행 중지 (하드웨어 연동 사용)")
#     #         continue
#     #     env.process(agv_process(env, i, agv_positions, logs, None, shelf_coords, exit_coords))
#     # env.run(until=float('inf'))
#     for i in range(NUM_AGV):
#         env.process(agv_process(env, i, agv_positions, logs, None, shelf_coords, exit_coords))
#     env.run(until=float('inf'))

# ##############################################################################
# # 8) 애니메이션 시각화 (선택 사항)
# ##############################################################################
# def animate_simulation(logs):
#     fig, ax = plt.subplots(figsize=(7, 5))
#     def draw_map():
#         ax.clear()
#         for r in range(ROWS):
#             for c in range(COLS):
#                 val = map_data[r][c]
#                 color = 'gray' if val == 1 else ('lightgreen' if val == 3 else 'white')
#                 rect = patches.Rectangle((c, r), 1, 1, edgecolor='black', facecolor=color)
#                 ax.add_patch(rect)
#         ax.set_xlim(0, COLS)
#         ax.set_ylim(0, ROWS)
#         ax.set_aspect('equal')
#         ax.invert_yaxis()
#         ax.set_xticks(range(COLS+1))
#         ax.set_yticks(range(ROWS+1))
#         ax.grid(False)
#     def init():
#         draw_map()
#     def update(frame):
#         draw_map()
#         colors = ["red", "orange", "yellow", "green"]
#         for agv_id in logs:
#             pos_list = [p for (t, p) in logs[agv_id] if t <= frame]
#             if pos_list:
#                 rr, cc = pos_list[-1]
#                 circle = plt.Circle((cc + 0.5, rr + 0.5), 0.3, color=colors[agv_id % len(colors)])
#                 ax.add_patch(circle)
#         # 주문 완료 카운터도 표시 (옵션)
#         order_completed = shared_data.get("order_completed", {})
#         ax.set_title(f"AGV 시뮬레이션 - 시간: {frame}, 주문완료: {order_completed}")
#     ani = animation.FuncAnimation(
#         fig, update,
#         frames=range(0, 1000),
#         init_func=init,
#         interval=100,  # 100ms 간격 (0.1초)
#         blit=False
#     )
#     plt.show()

# ##############################################################################
# # 9) 메인 실행부
# ##############################################################################
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
# 로그 설정: 개발/디버깅 시 DEBUG, 운영 시 INFO 레벨로 설정
DEBUG_MODE = False  # 개발/디버깅: True, 운영: False
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
TOPIC_STATUS_FROM_DEVICE = "agv/status"        # 하드웨어 → 서버 ACK 및 상태

mqtt_client = mqtt.Client(client_id="simulation_server", protocol=mqtt.MQTTv311)
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        if payload.get("ack"):
            location = payload.get("location")
            with data_lock:
                # ACK 시 dummy 하드웨어가 보내는 위치를 기록(디버깅용)
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
    "agv1_target": None,
    "agv1_moving_ack": False,
    "order_completed": {
        "AGV 1": 0,
        "AGV 2": 0,
        "AGV 3": 0,
        "AGV 4": 0
    }
}

##############################################################################
# 3) BFS 경로 탐색 함수 (너비 우선 탐색)
##############################################################################
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
# 4-1) 인접 좌표 반환 함수
##############################################################################
def available_moves(pos):
    moves = []
    for (dr, dc) in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        new_pos = (pos[0] + dr, pos[1] + dc)
        if 0 <= new_pos[0] < ROWS and 0 <= new_pos[1] < COLS and map_data[new_pos[0]][new_pos[1]] != 1:
            moves.append(new_pos)
    return moves

##############################################################################
# 4-2) 데드락 여부 확인 함수
##############################################################################
def is_deadlocked(pos, occupied):
    for m in available_moves(pos):
        if m not in occupied:
            return False
    return True

##############################################################################
# 5) MQTT 통신: 전체 경로 명령 전송 함수
##############################################################################
def send_full_path_to_agv1(full_path):
    logging.debug("[SIM] send_full_path_to_agv1(full_path=%s)", full_path)
    payload = {"command": "PATH", "data": {"full_path": full_path}}
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
# 7) AGV 프로세스 및 이동 함수 (전체 경로 사용)
##############################################################################
MOVE_INTERVAL = 1  # 1초마다 한 칸 이동
WAIT_INTERVAL = 1
SIMULATE_MQTT = True  # AGV1은 MQTT 연동

def random_start_position():
    return (8, 0)

def agv_process(env, agv_id, agv_positions, logs, goal_pos, shelf_coords, exit_coords):
    init_pos = random_start_position()
    agv_positions[agv_id] = init_pos
    logs[agv_id].append((datetime.now().isoformat(), init_pos))
    key = f"AGV {agv_id+1}"
    with data_lock:
        shared_data["positions"][key] = init_pos
        shared_data["logs"][key].append({"time": datetime.now().isoformat(), "position": init_pos})
        shared_data["statuses"][key] = "RUNNING"
    logging.debug("AGV %s 시작 위치: %s", agv_id, init_pos)

    while True:
        # 1단계: 선반(하역) 좌표로 이동 → 물건 하역 (10초 대기)
        unloading_target = random.choice(shelf_coords)
        with data_lock:
            shared_data["statuses"][key] = "RUNNING"
        yield from move_to(env, agv_id, agv_positions, logs, unloading_target)
        yield env.timeout(10)

        # 2단계: 출구 좌표로 이동 → 배송 (5초 대기)
        exit_target = random.choice(exit_coords)
        with data_lock:
            shared_data["statuses"][key] = "RUNNING"
        yield from move_to(env, agv_id, agv_positions, logs, exit_target)
        yield env.timeout(5)
        with data_lock:
            shared_data["order_completed"][key] += 1

def move_to(env, agv_id, agv_positions, logs, target):
    key = f"AGV {agv_id+1}"
    others = {k: pos for k, pos in agv_positions.items() if k != agv_id}
    full_path = calculate_full_path(agv_positions[agv_id], target, set(others.values()))
    if full_path is None:
        logging.error("경로 탐색 실패: %s에서 %s", agv_positions[agv_id], target)
        return
    logging.debug("AGV %s 전체 경로: %s", agv_id, full_path)

    # AGV1: MQTT 연동
    if agv_id == 0 and SIMULATE_MQTT:
        with data_lock:
            shared_data["agv1_moving_ack"] = False
        send_full_path_to_agv1(full_path)
        ack_received = False
        while not ack_received:
            yield env.timeout(0.2)
            with data_lock:
                if shared_data["agv1_moving_ack"]:
                    ack_received = True
        # 여기서는 dummy 하드웨어가 올바른 목표 좌표로 이동했다고 가정하고, 현재 위치를 target으로 업데이트
        with data_lock:
            agv_positions[agv_id] = target
    else:
        # 나머지 AGV는 순차적으로 full_path 따라 이동
        for idx in range(1, len(full_path)):
            next_pos = full_path[idx]
            if next_pos in others.values():
                logging.info("[%s] AGV %s 경로 차단 발생 (다른 AGV 위치: %s), 재경로 요청",
                             datetime.now().isoformat(), agv_id, next_pos)
                with data_lock:
                    shared_data["statuses"][key] = "STOPPED"
                    shared_data["directions"][key] = ""
                yield env.timeout(WAIT_INTERVAL)
                return
            direction = compute_direction(agv_positions[agv_id], next_pos)
            with data_lock:
                shared_data["directions"][key] = direction
                shared_data["statuses"][key] = "RUNNING"
            yield env.timeout(MOVE_INTERVAL)
            agv_positions[agv_id] = next_pos
            with data_lock:
                shared_data["positions"][key] = next_pos
                shared_data["logs"][key].append({"time": datetime.now().isoformat(), "position": next_pos})
            logging.debug("AGV %s 이동: %s -> %s", agv_id, full_path[idx-1], next_pos)
        logging.info("[%s] AGV %s 도착 -> %s", datetime.now().isoformat(), agv_id, target)

##############################################################################
# 8) 시뮬레이션 메인 함수
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
        agv_positions[i] = (0, 0)
        logs[i] = []
    for i in range(NUM_AGV):
        env.process(agv_process(env, i, agv_positions, logs, None, shelf_coords, exit_coords))
    env.run(until=float('inf'))

##############################################################################
# 9) 메인 실행부
##############################################################################
if __name__ == "__main__":
    simulation_main()

