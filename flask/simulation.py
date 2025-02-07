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

# --------------------------------------------------
# 로그 설정
DEBUG_MODE = True  # 개발/디버깅: True, 운영 시에는 False (INFO 또는 WARNING)
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
# 1) 맵 및 좌표 정의 (요구 조건 그대로)
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

# 선반(하역) 좌표
shelf_coords = [(2, 2), (2, 4), (2, 6),
                (5, 2), (5, 4), (5, 6)]
# 출구 좌표 (출구: 맵 첫 행에서 값이 2인 좌표)
exit_coords = [(0, c) for c in range(COLS) if map_data[0][c] == 2]

##############################################################################
# 2) 전역 공유 데이터 / 락 (SSE와 시뮬레이션 간 공유)
##############################################################################
data_lock = Lock()
shared_data = {
    # 각 AGV의 현재 위치와 로그(이동 기록)를 저장
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
    "agv1_target": None,
    "agv1_moving_ack": False
}

##############################################################################
# 3) BFS 경로 계산 함수
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
    path = bfs_path(map_data, current, target, obstacles=set())
    if path and len(path) > 1:
        return path[1]
    return current

##############################################################################
# 4) MQTT 통신 (AGV1 하드웨어 연동 placeholder)
##############################################################################
def send_command_to_agv1(next_pos):
    logging.debug("[SIM] (placeholder) send_command_to_agv1(next_pos=%s)", next_pos)
    with data_lock:
        shared_data["positions"]["AGV 1"] = next_pos
        shared_data["agv1_moving_ack"] = True

##############################################################################
# 5) AGV 프로세스 및 이동 함수
##############################################################################
MOVE_INTERVAL = 1   # 1초에 한 칸 이동
WAIT_INTERVAL = 1

# 시뮬레이션 모드: MQTT 연동 없이 순수 시뮬레이션 실행
SIMULATE_MQTT = False

def random_start_position():
    """출발은 8행(출발구역)에서, 값이 2인 좌표 중 하나 선택"""
    candidates = [(8, c) for c in range(COLS) if map_data[8][c] == 2]
    return random.choice(candidates) if candidates else (8, 0)

def agv_process(env, agv_id, agv_positions, logs, goal_pos, shelf_coords, exit_coords):
    # 각 AGV가 시작하면 8행에서 시작 (출발 좌표)
    init_pos = random_start_position()
    agv_positions[agv_id] = init_pos
    logs[agv_id].append((env.now, init_pos))
    key = f"AGV {agv_id+1}"
    with data_lock:
        shared_data["positions"][key] = init_pos
        shared_data["logs"][key].append({"time": env.now, "position": init_pos})
    logging.debug("AGV %s 시작 위치: %s", agv_id, init_pos)

    while True:
        # 선반 좌표로 이동 후 10초 대기
        unloading_target = random.choice(shelf_coords)
        yield from move_to(env, agv_id, agv_positions, logs, unloading_target)
        yield env.timeout(10)
        # 출구 좌표로 이동 후 5초 대기
        exit_target = random.choice(exit_coords)
        yield from move_to(env, agv_id, agv_positions, logs, exit_target)
        yield env.timeout(5)

def move_to(env, agv_id, agv_positions, logs, target):
    while True:
        yield env.timeout(MOVE_INTERVAL)
        curr_pos = agv_positions[agv_id]
        others = set(pos for k, pos in agv_positions.items() if k != agv_id)
        path = bfs_path(map_data, curr_pos, target, others)
        if path and len(path) > 1:
            next_pos = path[1]
            if next_pos in others:
                yield env.timeout(WAIT_INTERVAL)
                continue
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

            # 모든 AGV에 대해 shared_data 업데이트 (현재 위치 및 로그 기록)
            key = f"AGV {agv_id+1}"
            with data_lock:
                shared_data["positions"][key] = agv_positions[agv_id]
                shared_data["logs"][key].append({"time": env.now, "position": agv_positions[agv_id]})
        else:
            if curr_pos == target:
                logs[agv_id].append((env.now, curr_pos))
                logging.info("[%s] AGV %s 도착 -> %s", env.now, agv_id, curr_pos)
                return
        logs[agv_id].append((env.now, agv_positions[agv_id]))

##############################################################################
# 6) 시뮬레이션 메인 함수 (실시간, 무한 실행)
##############################################################################
# 실시간 연동을 위해 RealtimeEnvironment 사용 (1:1 비율)
try:
    from simpy.rt import RealtimeEnvironment
except ImportError:
    # 만약 simpy.rt 모듈이 없으면, 기본 Environment 사용(다만 실제 시간과는 다를 수 있음)
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
    # 무한 실행: 시뮬레이션이 시작된 이후부터 계속해서 위치와 로그가 업데이트됨
    env.run(until=float('inf'))

##############################################################################
# 7) 애니메이션 시각화 (원할 경우)
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
        ax.set_title(f"AGV Simulation - Time: {frame}")

    ani = animation.FuncAnimation(
        fig, update,
        frames=range(0, 1000),
        init_func=init,
        interval=1000,
        blit=False
    )
    plt.show()

##############################################################################
# 8) 메인 실행부
##############################################################################
if __name__ == "__main__":
    # 만약 애니메이션을 동시에 보고 싶다면, 시뮬레이션은 백그라운드 스레드로 실행한 후 animate_simulation() 호출
    simulation_main()
