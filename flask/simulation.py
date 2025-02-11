# simulation.py

import simpy
import random
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.patches as patches
from collections import deque
from threading import Lock
import time
import logging
from datetime import datetime  # 실제 현실시간 사용

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
# 1) 맵 및 좌표 정의
##############################################################################
# 맵 데이터: 2는 출구 혹은 출발지, 1은 장애물, 0은 통로
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

# 선반(하역) 좌표 목록
shelf_coords = [(2, 2), (2, 4), (2, 6),
                (5, 2), (5, 4), (5, 6)]
# 출구 좌표: 맵 첫 행에서 값이 2인 좌표
exit_coords = [(0, c) for c in range(COLS) if map_data[0][c] == 2]

##############################################################################
# 2) 공유 데이터 및 락 (SSE와 시뮬레이션 간 데이터 공유)
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
    "agv1_moving_ack": False
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

def get_next_position(current, target):
    if target is None:
        d = shared_data["directions"].get("AGV 1", "")
        print(f"[DEBUG] current: {current}, direction: {d}")
        if d == "u":
            candidate = (current[0] - 1, current[1])
        elif d == "d":
            candidate = (current[0] + 1, current[1])
        elif d == "R":
            candidate = (current[0], current[1] + 1)
        elif d == "L":
            candidate = (current[0], current[1] - 1)
        else:
            candidate = (current[0] - 1, current[1])
        print(f"[DEBUG] candidate before boundary check: {candidate}")
        row, col = candidate
        if row < 0 or row >= ROWS or col < 0 or col >= COLS:
            print("[DEBUG] candidate out-of-bound, returning current")
            return current
        print(f"[DEBUG] candidate accepted: {candidate}")
        return candidate
    else:
        path = bfs_path(map_data, current, target, obstacles=set())
        if path and len(path) > 1:
            return path[1]
        return current


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
# 4-1) 보조 함수: 인접 이동 가능한 좌표 목록 반환
##############################################################################
def available_moves(pos):
    moves = []
    for (dr, dc) in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        new_pos = (pos[0] + dr, pos[1] + dc)
        if 0 <= new_pos[0] < ROWS and 0 <= new_pos[1] < COLS and map_data[new_pos[0]][new_pos[1]] != 1:
            moves.append(new_pos)
    return moves

##############################################################################
# 4-2) 보조 함수: 주어진 위치가 데드락 상태인지 확인
##############################################################################
def is_deadlocked(pos, occupied):
    for m in available_moves(pos):
        if m not in occupied:
            return False
    return True

##############################################################################
# 5) MQTT 통신 (AGV1 하드웨어 연동용 플레이스홀더)
##############################################################################
def send_command_to_agv1(next_pos):
    logging.debug("[SIM] (플레이스홀더) send_command_to_agv1(next_pos=%s)", next_pos)
    with data_lock:
        shared_data["positions"]["AGV 1"] = next_pos
        shared_data["agv1_moving_ack"] = True

##############################################################################
# 6) AGV 프로세스 및 이동 함수
##############################################################################
MOVE_INTERVAL = 1
WAIT_INTERVAL = 1

# 시뮬레이션 모드: 실제 운영모드에서는 하드웨어 연동 사용을 위해 False로 설정합니다.
SIMULATE_MQTT = False

def random_start_position():
    candidates = [(8, c) for c in range(COLS) if map_data[8][c] == 2]
    return random.choice(candidates) if candidates else (8, 0)

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
        unloading_target = random.choice(shelf_coords)
        with data_lock:
            shared_data["statuses"][key] = "RUNNING"
        yield from move_to(env, agv_id, agv_positions, logs, unloading_target)
        with data_lock:
            shared_data["statuses"][key] = "UNLOADING"
            shared_data["directions"][key] = ""
        yield env.timeout(10)
        exit_target = random.choice(exit_coords)
        with data_lock:
            shared_data["statuses"][key] = "RUNNING"
        yield from move_to(env, agv_id, agv_positions, logs, exit_target)
        yield env.timeout(5)

def move_to(env, agv_id, agv_positions, logs, target):
    key = f"AGV {agv_id+1}"
    while True:
        yield env.timeout(MOVE_INTERVAL)
        curr_pos = agv_positions[agv_id]
        others = {k: pos for k, pos in agv_positions.items() if k != agv_id}
        path = bfs_path(map_data, curr_pos, target, set(others.values()))
        if path and len(path) > 1:
            next_pos = path[1]
            direction = compute_direction(curr_pos, next_pos)
            with data_lock:
                shared_data["directions"][key] = direction

            if next_pos in others.values():
                blocker = None
                for k, pos in others.items():
                    if pos == next_pos:
                        blocker = k
                        break
                our_path = bfs_path(map_data, curr_pos, target, set())
                our_distance = len(our_path) if our_path is not None else float('inf')
                blocker_path = bfs_path(map_data, agv_positions[blocker], target, set()) if blocker is not None else None
                blocker_distance = len(blocker_path) if blocker_path is not None else float('inf')
                occupied_for_blocker = set(agv_positions.values())
                occupied_for_blocker.discard(agv_positions[blocker])
                blocker_deadlocked = is_deadlocked(agv_positions[blocker], occupied_for_blocker)

                if our_distance > blocker_distance:
                    with data_lock:
                        shared_data["statuses"][key] = "STOPPED"
                        shared_data["directions"][key] = ""
                    yield env.timeout(WAIT_INTERVAL)
                    continue
                elif our_distance == blocker_distance:
                    if blocker_deadlocked:
                        pass
                    else:
                        with data_lock:
                            shared_data["statuses"][key] = "STOPPED"
                            shared_data["directions"][key] = ""
                        yield env.timeout(WAIT_INTERVAL)
                        continue

            # AGV1의 경우, SIMULATE_MQTT가 True면 시뮬레이션 모드, 아니면 하드웨어 ACK 기반 처리
            if agv_id == 0 and SIMULATE_MQTT:
                with data_lock:
                    shared_data["agv1_target"] = next_pos
                    shared_data["agv1_moving_ack"] = False
                send_command_to_agv1(next_pos)
                ack_received = False
                while not ack_received:
                    yield env.timeout(0.2)
                    with data_lock:
                        if shared_data["agv1_moving_ack"]:
                            ack_received = True
                with data_lock:
                    agv_positions[agv_id] = shared_data["positions"]["AGV 1"]
            else:
                agv_positions[agv_id] = next_pos

            with data_lock:
                shared_data["statuses"][key] = "RUNNING"
                shared_data["positions"][key] = agv_positions[agv_id]
                shared_data["logs"][key].append({
                    "time": datetime.now().isoformat(),
                    "position": agv_positions[agv_id]
                })
        else:
            if curr_pos == target:
                logs[agv_id].append((datetime.now().isoformat(), curr_pos))
                logging.info("[%s] AGV %s 도착 -> %s", datetime.now().isoformat(), agv_id, curr_pos)
                return
        logs[agv_id].append((datetime.now().isoformat(), agv_positions[agv_id]))

##############################################################################
# 7) 시뮬레이션 메인 함수 (실시간, 무한 실행)
##############################################################################
try:
    from simpy.rt import RealtimeEnvironment
except ImportError:
    RealtimeEnvironment = simpy.Environment

def simulation_main():
    # 운영 모드에서는 AGV1의 시뮬레이션 프로세스를 실행하지 않음
    env = RealtimeEnvironment(factor=1, strict=False)
    NUM_AGV = 4
    agv_positions = {}
    logs = {}
    for i in range(NUM_AGV):
        agv_positions[i] = (0, 0)
        logs[i] = []
    for i in range(NUM_AGV):
        if i == 0 and not DEBUG_MODE:
            print("[운영 모드] AGV 1 시뮬레이션 프로세스 실행 중지 (하드웨어 연동 사용)")
            continue
        env.process(agv_process(env, i, agv_positions, logs, None, shelf_coords, exit_coords))
    env.run(until=float('inf'))

##############################################################################
# 8) 애니메이션 시각화 (선택 사항)
##############################################################################
def animate_simulation(logs):
    fig, ax = plt.subplots(figsize=(7, 5))
    def draw_map():
        ax.clear()
        for r in range(ROWS):
            for c in range(COLS):
                val = map_data[r][c]
                color = 'gray' if val == 1 else ('lightgreen' if val == 3 else 'white')
                rect = patches.Rectangle((c, r), 1, 1, edgecolor='black', facecolor=color)
                ax.add_patch(rect)
        ax.set_xlim(0, COLS)
        ax.set_ylim(0, ROWS)
        ax.set_aspect('equal')
        ax.invert_yaxis()
        ax.set_xticks(range(COLS+1))
        ax.set_yticks(range(ROWS+1))
        ax.grid(False)
    def init():
        draw_map()
    def update(frame):
        draw_map()
        colors = ["red", "orange", "yellow", "green"]
        for agv_id in logs:
            pos_list = [p for (t, p) in logs[agv_id] if t <= frame]
            if pos_list:
                rr, cc = pos_list[-1]
                circle = plt.Circle((cc + 0.5, rr + 0.5), 0.3, color=colors[agv_id % len(colors)])
                ax.add_patch(circle)
        ax.set_title(f"AGV 시뮬레이션 - 시간: {frame}")
    ani = animation.FuncAnimation(
        fig, update,
        frames=range(0, 1000),
        init_func=init,
        interval=1000,
        blit=False
    )
    plt.show()

##############################################################################
# 9) 메인 실행부
##############################################################################
if __name__ == "__main__":
    simulation_main()
