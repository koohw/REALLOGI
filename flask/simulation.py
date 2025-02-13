# # simulation2.py

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
# # MQTT 설정
# ##############################################################################
# BROKER = "broker.hivemq.com"
# PORT = 1883
# TOPIC_COMMAND_TO_DEVICE = "simpy/commands"   # 서버 → 하드웨어 명령
# TOPIC_STATUS_FROM_DEVICE = "agv/status"      # 하드웨어 → 서버 ACK/상태

# mqtt_client = mqtt.Client(client_id="simulation_server", protocol=mqtt.MQTTv311)

# def on_message(client, userdata, msg):
#     """MQTT 콜백: dummy 하드웨어(AGV1) ACK 수신 등"""
#     try:
#         payload = json.loads(msg.payload.decode())
#         if payload.get("ack"):
#             location = payload.get("location")
#             with data_lock:
#                 shared_data["positions"]["AGV 1"] = tuple(location)
#                 shared_data["agv1_moving_ack"] = True
#             logging.info("[SIM] ACK 수신, 위치 업데이트: %s", location)
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
#     "agv1_target": None,
#     "agv1_moving_ack": False,
#     "order_completed": {
#         "AGV 1": 0,
#         "AGV 2": 0,
#         "AGV 3": 0,
#         "AGV 4": 0
#     }
# }

# ##############################################################################
# # 3) BFS 경로 탐색 함수 (너비 우선 탐색)
# ##############################################################################
# def bfs_path(grid, start, goal, obstacles=set()):
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
# # 5) MQTT 통신: 전체 경로 명령 전송
# ##############################################################################
# def send_full_path_to_agv1(full_path):
#     logging.debug("[SIM] send_full_path_to_agv1(full_path=%s)", full_path)
#     payload = {"command": "PATH", "data": {"full_path": full_path}}
#     result = mqtt_client.publish(TOPIC_COMMAND_TO_DEVICE, json.dumps(payload))
#     if result[0] == 0:
#         logging.info("[SIM] PATH 명령 전송 성공: %s", payload)
#     else:
#         logging.error("[SIM] PATH 명령 전송 실패: %s", payload)

# ##############################################################################
# # 6) 전체 경로 계산 함수
# ##############################################################################
# def calculate_full_path(start, goal, obstacles=set()):
#     path = bfs_path(map_data, start, goal, obstacles)
#     if path is None:
#         logging.warning("경로 탐색 실패: 시작 %s, 목표 %s", start, goal)
#     return path

# ##############################################################################
# # 7) AGV 프로세스 및 이동 함수 (전체 경로 사용)
# ##############################################################################
# MOVE_INTERVAL = 1  # 1초마다 한 칸 이동
# WAIT_INTERVAL = 1
# SIMULATE_MQTT = True  # AGV1은 MQTT 연동

# def random_start_position():
#     return (8, 0)

# def agv_process(env, agv_id, agv_positions, logs, _, shelf_coords, exit_coords):
#     """
#     SimPy 프로세스 함수 (반드시 yield를 사용해야 함)
#     무한 루프로 선반→10초→출구→5초 반복
#     """
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
#         # 1) 선반(하역) 좌표로 이동
#         unloading_target = random.choice(shelf_coords)
#         with data_lock:
#             shared_data["statuses"][key] = "RUNNING"
#         # SimPy에서 이동 시작
#         yield from move_to(env, agv_id, agv_positions, logs, unloading_target)

#         # 하역 10초
#         with data_lock:
#             shared_data["statuses"][key] = "UNLOADING"
#             shared_data["directions"][key] = ""
#         yield env.timeout(10)

#         # 2) 출구 좌표로 이동
#         exit_target = random.choice(exit_coords)
#         with data_lock:
#             shared_data["statuses"][key] = "RUNNING"
#         yield from move_to(env, agv_id, agv_positions, logs, exit_target)

#         # 5초 멈춤
#         yield env.timeout(5)
#         with data_lock:
#             shared_data["order_completed"][key] += 1

# def move_to(env, agv_id, agv_positions, logs, target):
#     """
#     실제 이동 함수 (제너레이터).
#     BFS 경로를 한 칸씩 따라 이동하거나, AGV1이면 MQTT 전송 후 ACK 대기.
#     """
#     key = f"AGV {agv_id+1}"
#     current_pos = agv_positions[agv_id]
#     others = {k: pos for k,pos in agv_positions.items() if k!=agv_id}

#     path = calculate_full_path(current_pos, target, obstacles=set(others.values()))
#     if not path:
#         logging.error("경로 탐색 실패: %s -> %s", current_pos, target)
#         return  # 제너레이터이긴 하지만, 그냥 종료(짧은 프로세스)

#     logging.debug("AGV %s 전체 경로: %s", agv_id, path)

#     if agv_id==0 and SIMULATE_MQTT:
#         # AGV1은 MQTT 전체 경로 전송 후 ACK 대기
#         with data_lock:
#             shared_data["agv1_moving_ack"] = False

#         send_full_path_to_agv1(path)
#         ack_received = False
#         while not ack_received:
#             yield env.timeout(0.2)
#             with data_lock:
#                 if shared_data["agv1_moving_ack"]:
#                     ack_received = True
#         # ACK 수신 후, 현재 위치를 target으로 설정
#         with data_lock:
#             agv_positions[agv_id] = target
#     else:
#         # 나머지 AGV는 BFS 경로를 한 칸씩 이동
#         for idx in range(1, len(path)):
#             next_pos = path[idx]
#             direction = compute_direction(agv_positions[agv_id], next_pos)
#             with data_lock:
#                 shared_data["directions"][key] = direction
#                 shared_data["statuses"][key] = "RUNNING"

#             yield env.timeout(MOVE_INTERVAL)
#             agv_positions[agv_id] = next_pos
#             with data_lock:
#                 shared_data["positions"][key] = next_pos
#                 shared_data["logs"][key].append({
#                     "time": datetime.now().isoformat(),
#                     "position": next_pos
#                 })
#         logging.info("[%s] AGV %s 도착 -> %s", datetime.now().isoformat(), agv_id, target)

# ##############################################################################
# # 8) 시뮬레이션 메인 함수 (실시간, 무한 실행)
# ##############################################################################
# try:
#     from simpy.rt import RealtimeEnvironment
# except ImportError:
#     RealtimeEnvironment = simpy.Environment

# def simulation_main():
#     """
#     프로그램 실행 시 python simulation2.py 로 호출되는 메인 함수
#     """
#     env = RealtimeEnvironment(factor=1, strict=False)
#     NUM_AGV = 4
#     agv_positions = {}
#     logs = {}
#     for i in range(NUM_AGV):
#         agv_positions[i] = (0,0)
#         logs[i] = []

#     # 4대 AGV 프로세스 등록 (AGV1은 MQTT, AGV2~4는 시뮬레이션)
#     for i in range(NUM_AGV):
#         env.process(agv_process(env, i, agv_positions, logs, None, shelf_coords, exit_coords))
#     env.run(until=float('inf'))

# if __name__=="__main__":
#     simulation_main()




import simpy
import random
from collections import deque
from threading import Lock
import time
import logging
from datetime import datetime
import paho.mqtt.client as mqtt
import json

DEBUG_MODE = False
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("simulation.log", encoding='utf-8')
    ]
)

# --------------------
# MQTT 설정
# --------------------
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_COMMAND_TO_DEVICE = "simpy/commands"  # 서버→하드웨어
TOPIC_STATUS_FROM_DEVICE = "agv/status"     # 하드웨어→서버

mqtt_client = mqtt.Client(client_id="simulation_server", protocol=mqtt.MQTTv311)

def on_message(client, userdata, msg):
    """ 하드웨어(AGV1)에서 오는 메시지 처리: ACK/blocked 등 """
    try:
        payload = json.loads(msg.payload.decode())
        if payload.get("ack"):
            location = payload.get("location")
            with data_lock:
                # 위치 업데이트 & ACK 플래그
                shared_data["positions"]["AGV 1"] = tuple(location)
                shared_data["agv1_moving_ack"] = True
            logging.info("[SIM] ACK 수신, AGV1 위치: %s", location)
        elif payload.get("blocked"):
            logging.info("[SIM] blocked 메시지: %s", payload)
        else:
            logging.info("[SIM] 기타 메시지: %s", payload)
    except Exception as e:
        logging.error("[SIM] on_message 예외: %s", e)

mqtt_client.on_message = on_message
mqtt_client.connect(BROKER, PORT, 60)
mqtt_client.subscribe(TOPIC_STATUS_FROM_DEVICE)
mqtt_client.loop_start()

# --------------------
# 맵/좌표 정의
# --------------------
map_data = [
    [2,2,2,2,2,2,2],
    [0,0,0,0,0,0,0],
    [0,1,0,1,0,1,0],
    [0,1,0,1,0,1,0],
    [0,0,0,0,0,0,0],
    [0,1,0,1,0,1,0],
    [0,1,0,1,0,1,0],
    [0,0,0,0,0,0,0],
    [2,2,2,2,2,2,2]
]
ROWS = len(map_data)
COLS = len(map_data[0])
shelf_coords = [(2,2),(2,4),(2,6),
                (5,2),(5,4),(5,6)]
exit_coords = [(0,c) for c in range(COLS) if map_data[0][c]==2]

# --------------------
# 공유 데이터
# --------------------
data_lock = Lock()
shared_data = {
    "positions":  {"AGV 1":None, "AGV 2":None, "AGV 3":None, "AGV 4":None},
    "logs":       {"AGV 1":[],   "AGV 2":[],   "AGV 3":[],   "AGV 4":[]},
    "statuses":   {"AGV 1":"",   "AGV 2":"",   "AGV 3":"",   "AGV 4":""},
    "directions": {"AGV 1":"",   "AGV 2":"",   "AGV 3":"",   "AGV 4":""},
    "agv1_target": None,
    "agv1_moving_ack": False,
    "order_completed": {"AGV 1":0,"AGV 2":0,"AGV 3":0,"AGV 4":0}
}

# --------------------
# BFS 함수
# --------------------
def bfs_path(grid, start, goal, obstacles=set()):
    if not start or not goal:
        return None
    queue = deque([(start,[start])])
    visited = set([start])
    directions = [(0,1),(0,-1),(1,0),(-1,0)]
    while queue:
        curr, path = queue.popleft()
        if curr==goal:
            return path
        r,c = curr
        for dr,dc in directions:
            nr,nc = r+dr, c+dc
            if 0<=nr<ROWS and 0<=nc<COLS:
                if grid[nr][nc]!=1 and ((nr,nc)==goal or (nr,nc) not in obstacles):
                    if (nr,nc) not in visited:
                        visited.add((nr,nc))
                        queue.append(((nr,nc), path+[(nr,nc)]))
    return None

def compute_direction(curr, nxt):
    dr = nxt[0]-curr[0]
    dc = nxt[1]-curr[1]
    if dr==-1 and dc==0:
        return "u"
    elif dr==1 and dc==0:
        return "d"
    elif dr==0 and dc==1:
        return "R"
    elif dr==0 and dc==-1:
        return "L"
    else:
        return ""

def send_full_path_to_agv1(full_path):
    payload = {"command":"PATH","data":{"full_path": full_path}}
    result = mqtt_client.publish(TOPIC_COMMAND_TO_DEVICE, json.dumps(payload))
    if result[0]==0:
        logging.info("[SIM] 경로(PATH) 명령 전송: %s", full_path)
    else:
        logging.error("[SIM] 경로 전송 실패")

def calculate_full_path(start, goal, obstacles=set()):
    path = bfs_path(map_data, start, goal, obstacles)
    if path is None:
        logging.warning("BFS 실패: %s -> %s", start, goal)
    return path

# --------------------
# SimPy 이동 로직
# --------------------
MOVE_INTERVAL = 1
WAIT_INTERVAL = 1
SIMULATE_MQTT = True  # AGV1만 MQTT

def random_start_position():
    return (8,0)

def agv_process(env, agv_id, agv_positions, logs, _, shelf_coords, exit_coords):
    init_pos = random_start_position()
    agv_positions[agv_id] = init_pos
    logs[agv_id].append((datetime.now().isoformat(), init_pos))
    key = f"AGV {agv_id+1}"
    with data_lock:
        shared_data["positions"][key] = init_pos
        shared_data["logs"][key].append({"time": datetime.now().isoformat(),"position":init_pos})
        shared_data["statuses"][key] = "RUNNING"

    while True:
        # 1) 선반 이동
        unloading_target = random.choice(shelf_coords)
        with data_lock:
            shared_data["statuses"][key] = "RUNNING"
        yield from move_to(env, agv_id, agv_positions, logs, unloading_target)

        # 10초 하역
        with data_lock:
            shared_data["statuses"][key] = "UNLOADING"
            shared_data["directions"][key] = ""
        yield env.timeout(10)

        # 2) 출구 이동
        exit_target = random.choice(exit_coords)
        with data_lock:
            shared_data["statuses"][key] = "RUNNING"
        yield from move_to(env, agv_id, agv_positions, logs, exit_target)

        # 5초 대기 후 order_completed++
        yield env.timeout(5)
        with data_lock:
            shared_data["order_completed"][key]+=1

def move_to(env, agv_id, agv_positions, logs, target):
    key = f"AGV {agv_id+1}"
    current_pos = agv_positions[agv_id]
    others = {k:pos for k,pos in agv_positions.items() if k!=agv_id}
    path = calculate_full_path(current_pos, target, obstacles=set(others.values()))
    if not path:
        logging.error("move_to() BFS 실패: %s->%s", current_pos, target)
        return
    logging.debug("AGV %s BFS 경로: %s", agv_id, path)

    if agv_id==0 and SIMULATE_MQTT:
        with data_lock:
            shared_data["agv1_moving_ack"] = False
        send_full_path_to_agv1(path)
        ack_received = False
        # ACK 기다림
        while not ack_received:
            yield env.timeout(0.2)
            with data_lock:
                if shared_data["agv1_moving_ack"]:
                    ack_received = True
        # ACK 후 위치=목표
        agv_positions[agv_id] = target
    else:
        # BFS 경로 따라 1초씩 이동
        for idx in range(1, len(path)):
            nxt = path[idx]
            direction = compute_direction(agv_positions[agv_id], nxt)
            with data_lock:
                shared_data["directions"][key] = direction
                shared_data["statuses"][key] = "RUNNING"
            yield env.timeout(MOVE_INTERVAL)
            agv_positions[agv_id] = nxt
            with data_lock:
                shared_data["positions"][key] = nxt
                shared_data["logs"][key].append({
                    "time": datetime.now().isoformat(),
                    "position": nxt
                })
        logging.info("[%s] AGV %s 도착 -> %s", datetime.now().isoformat(), agv_id, target)

try:
    from simpy.rt import RealtimeEnvironment
except ImportError:
    RealtimeEnvironment = simpy.Environment

def simulation_main():
    env = RealtimeEnvironment(factor=1, strict=False)
    NUM_AGV=4
    agv_positions={}
    logs={}
    for i in range(NUM_AGV):
        agv_positions[i]=(0,0)
        logs[i]=[]
    for i in range(NUM_AGV):
        env.process(agv_process(env, i, agv_positions, logs, None, shelf_coords, exit_coords))
    env.run(until=float('inf'))

if __name__=="__main__":
    simulation_main()
