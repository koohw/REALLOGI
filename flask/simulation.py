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
# 로그 설정: 개발/디버깅 시 DEBUG, 운영 시 INFO 레벨로 설정
DEBUG_MODE = True  # 개발/디버깅: True, 운영: False
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
    # 각 AGV의 현재 위치 저장
    "positions": {
        "AGV 1": None,
        "AGV 2": None,
        "AGV 3": None,
        "AGV 4": None
    },
    # 각 AGV의 이동 기록 저장
    "logs": {
        "AGV 1": [],
        "AGV 2": [],
        "AGV 3": [],
        "AGV 4": []
    },
    # 각 AGV의 상태: "RUNNING"(운행중), "UNLOADING"(하역중), "STOPPED"(정지)
    "statuses": {
        "AGV 1": "",
        "AGV 2": "",
        "AGV 3": "",
        "AGV 4": ""
    },
    # 각 AGV의 이동 방향: "u", "d", "R", "L"
    # 단, UNLOADING이나 STOPPED 상태일 때는 빈 문자열("")로 표시
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
    # 시작이나 목표가 None이면 경로 없음 처리
    if not start or not goal:
        return None
    queue = deque([(start, [start])])
    visited = set([start])
    # 상, 하, 좌, 우 이동
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    while queue:
        current, path = queue.popleft()
        if current == goal:
            return path
        r, c = current
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS:
                # 장애물이 아니거나 목표일 경우
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
# 4) 이동 방향 계산 함수
##############################################################################
def compute_direction(curr, nxt):
    # 이전 위치(curr)와 다음 위치(nxt)의 차이를 계산하여 방향 반환
    dr = nxt[0] - curr[0]
    dc = nxt[1] - curr[1]
    if dr == -1 and dc == 0:
        return "u"    # 위쪽 이동
    elif dr == 1 and dc == 0:
        return "d"    # 아래쪽 이동
    elif dr == 0 and dc == 1:
        return "R"    # 오른쪽 이동
    elif dr == 0 and dc == -1:
        return "L"    # 왼쪽 이동
    else:
        return ""

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
MOVE_INTERVAL = 1   # 1초마다 한 칸 이동
WAIT_INTERVAL = 1

# 시뮬레이션 모드: MQTT 하드웨어 연동 없이 실행
SIMULATE_MQTT = False

def random_start_position():
    """8행(출발 구역)에서, 값이 2인 좌표 중 랜덤 선택"""
    candidates = [(8, c) for c in range(COLS) if map_data[8][c] == 2]
    return random.choice(candidates) if candidates else (8, 0)

def agv_process(env, agv_id, agv_positions, logs, goal_pos, shelf_coords, exit_coords):
    # 각 AGV는 8행에서 시작
    init_pos = random_start_position()
    agv_positions[agv_id] = init_pos
    logs[agv_id].append((env.now, init_pos))
    key = f"AGV {agv_id+1}"
    with data_lock:
        shared_data["positions"][key] = init_pos
        shared_data["logs"][key].append({"time": env.now, "position": init_pos})
        shared_data["statuses"][key] = "RUNNING"  # 초기 상태는 RUNNING
    logging.debug("AGV %s 시작 위치: %s", agv_id, init_pos)

    while True:
        # 선반(하역) 좌표로 이동
        unloading_target = random.choice(shelf_coords)
        with data_lock:
            shared_data["statuses"][key] = "RUNNING"
        yield from move_to(env, agv_id, agv_positions, logs, unloading_target)
        # 도착 후 10초 동안 UNLOADING 상태로 전환하며 방향은 빈 문자열로 설정
        with data_lock:
            shared_data["statuses"][key] = "UNLOADING"
            shared_data["directions"][key] = ""
        yield env.timeout(10)
        # 출구 좌표로 이동
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
        # 다른 AGV들의 위치를 장애물로 간주
        others = set(pos for k, pos in agv_positions.items() if k != agv_id)
        path = bfs_path(map_data, curr_pos, target, others)
        if path and len(path) > 1:
            next_pos = path[1]
            # 정상 이동 시 이동 방향 계산
            direction = compute_direction(curr_pos, next_pos)
            with data_lock:
                shared_data["directions"][key] = direction

            if next_pos in others:
                # 만약 이동하려는 칸이 다른 AGV로 막혀있으면 정지(Stop) 상태로 전환하고 방향을 빈 문자열로 설정
                with data_lock:
                    shared_data["statuses"][key] = "STOPPED"
                    shared_data["directions"][key] = ""
                yield env.timeout(WAIT_INTERVAL)
                continue

            # AGV1의 경우 MQTT 시뮬레이션 모드일 때 처리
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

            # 정상 이동 후, 상태를 RUNNING으로 업데이트하고 로그에 기록
            with data_lock:
                shared_data["statuses"][key] = "RUNNING"
                shared_data["positions"][key] = agv_positions[agv_id]
                shared_data["logs"][key].append({"time": env.now, "position": agv_positions[agv_id]})
        else:
            # 목표 위치에 도달한 경우 종료
            if curr_pos == target:
                logs[agv_id].append((env.now, curr_pos))
                logging.info("[%s] AGV %s 도착 -> %s", env.now, agv_id, curr_pos)
                return
        logs[agv_id].append((env.now, agv_positions[agv_id]))

##############################################################################
# 7) 시뮬레이션 메인 함수 (실시간, 무한 실행)
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
# 8) 애니메이션 시각화 (선택 사항)
##############################################################################
def animate_simulation(logs):
    fig, ax = plt.subplots(figsize=(7, 5))
    def draw_map():
        ax.clear()
        for r in range(ROWS):
            for c in range(COLS):
                val = map_data[r][c]
                # 장애물은 회색, 특정 값에 따라 색상 지정
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
