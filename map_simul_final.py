import simpy
import random
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.patches as patches
from collections import deque

##############################################################################
# 1) 맵 정의
##############################################################################
map_data = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3],  # (4,11)가 목표(3)
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
]
ROWS = len(map_data)
COLS = len(map_data[0])

##############################################################################
# 2) 섹터 정의
##############################################################################
def create_sectors():
    return {
        1: [(1, 0), (2, 0), (3, 0)],
        2: [(1, 2), (2, 2), (3, 2)],
        3: [(1, 4), (2, 4), (3, 4)],
        4: [(1, 6), (2, 6), (3, 6)],
        5: [(1, 8), (2, 8), (3, 8)],
        6: [(5, 0), (6, 0), (7, 0)],
        7: [(5, 2), (6, 2), (7, 2)],
        8: [(5, 4), (6, 4), (7, 4)],
        9: [(5, 6), (6, 6), (7, 6)],
        10: [(5, 8), (6, 8), (7, 8)],
    }

sectors = create_sectors()

##############################################################################
# 3) 컨테이너 좌표들 (섹터별로 구분)
##############################################################################
container_coords = [
    (1, 0), (2, 0), (3, 0),
    (1, 2), (2, 2), (3, 2),
    (1, 4), (2, 4), (3, 4),
    (1, 6), (2, 6), (3, 6),
    (1, 8), (2, 8), (3, 8),
    (5, 0), (6, 0), (7, 0),
    (5, 2), (6, 2), (7, 2),
    (5, 4), (6, 4), (7, 4),
    (5, 6), (6, 6), (7, 6),
    (5, 8), (6, 8), (7, 8),
]

def assign_containers_to_sectors(sectors):
    sector_containers = {}
    for sector_id, coords in sectors.items():
        sector_containers[sector_id] = [coord for coord in coords if coord in container_coords]
    return sector_containers

sector_containers = assign_containers_to_sectors(sectors)

##############################################################################
# BFS 함수 (다른 AGV 위치를 장애물로 간주)
##############################################################################
def bfs_path(grid, start, goal, obstacles):
    if not start or not goal:
        return None
    queue = deque([(start, [start])])
    visited = set([start])
    directions = [(0,1),(0,-1),(1,0),(-1,0)]

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
# 4) AGV 프로세스
##############################################################################
MOVE_INTERVAL = 1
WAIT_INTERVAL = 1

def agv_process(env, agv_id, agv_positions, logs, goal_pos, allowed_sectors):
    init_pos = random_free_position()
    agv_positions[agv_id] = init_pos
    logs[agv_id].append((env.now, init_pos))

    while True:
        # 지정된 섹터에서 랜덤으로 선택하여 컨테이너로 이동
        sector_id = random.choice(allowed_sectors)
        container = random.choice(sector_containers[sector_id])
        yield from move_to(env, agv_id, agv_positions, logs, container)
        yield env.timeout(1)

        # 목표 지점으로 이동
        yield from move_to(env, agv_id, agv_positions, logs, goal_pos)
        yield env.timeout(1)

def move_to(env, agv_id, agv_positions, logs, target):
    while True:
        yield env.timeout(MOVE_INTERVAL)
        curr_pos = agv_positions[agv_id]
        others = set(pos for k, pos in agv_positions.items() if k != agv_id)

        path = bfs_path(map_data, curr_pos, target, others)
        if path and len(path) > 1:
            next_pos = path[1]
            if next_pos in others:
                # 다음 칸에 다른 AGV가 있다면 대기
                yield env.timeout(WAIT_INTERVAL)
                continue
            agv_positions[agv_id] = next_pos
        else:
            if curr_pos == target:
                logs[agv_id].append((env.now, curr_pos))
                print(f"[{env.now}] AGV{agv_id} 도착 -> {curr_pos}")
                return
        logs[agv_id].append((env.now, agv_positions[agv_id]))

def random_free_position():
    candidates = []
    for r in range(ROWS):
        for c in range(COLS):
            if map_data[r][c] == 0:
                candidates.append((r, c))
    return random.choice(candidates) if candidates else (0, 0)

##############################################################################
# 5) 시뮬레이션 메인
##############################################################################
def main():
    env = simpy.Environment()
    NUM_AGV = 5
    SIM_TIME = 60

    goal_pos = None
    for r in range(ROWS):
        for c in range(COLS):
            if map_data[r][c] == 3:
                goal_pos = (r, c)
                break
        if goal_pos:
            break

    agv_positions = {}
    logs = {}
    for i in range(NUM_AGV):
        agv_positions[i] = (0, 0)
        logs[i] = []

    # AGV별로 허용된 섹터 지정
    agv_sectors = {
        0: [1, 6],  # AGV 1 (빨간색)
        1: [2, 7],  # AGV 2 (주황색)
        2: [3, 8],  # AGV 3 (노란색)
        3: [4, 9],  # AGV 4 (초록색)
        4: [5, 10], # AGV 5 (파란색)
    }

    for i in range(NUM_AGV):
        env.process(agv_process(env, i, agv_positions, logs, goal_pos, agv_sectors[i]))

    env.run(until=SIM_TIME)

    fig, ax = plt.subplots(figsize=(7, 5))

    def draw_map():
        ax.clear()
        for r in range(ROWS):
            for c in range(COLS):
                val = map_data[r][c]
                if val == 1:
                    color = 'gray'
                elif val == 3:
                    color = 'lightgreen'
                else:
                    color = 'white'
                rect = patches.Rectangle((c, r), 1, 1, edgecolor='black', facecolor=color)
                ax.add_patch(rect)

        for sector_id, coords in sectors.items():
            for r, c in coords:
                ax.text(c + 0.5, r + 0.5, f"S{sector_id}", color="blue", ha="center", va="center")

        for sector_id, containers in sector_containers.items():
            for r, c in containers:
                ax.text(c + 0.5, r + 0.5, f"C{sector_id}", color="red", ha="center", va="center")

        ax.set_xlim(0, COLS)
        ax.set_ylim(0, ROWS)
        ax.set_aspect('equal')
        ax.invert_yaxis()
        ax.set_xticks(range(COLS + 1))
        ax.set_yticks(range(ROWS + 1))
        ax.grid(False)

    def init():
        draw_map()

    def update(frame):
        draw_map()
        colors = ["red", "orange", "yellow", "green", "blue"]
        for agv_id in logs:
            pos_list = [(t, p) for (t, p) in logs[agv_id] if t <= frame]
            if pos_list:
                _, (rr, cc) = pos_list[-1]
                circle = plt.Circle((cc + 0.5, rr + 0.5), 0.3, color=colors[agv_id % len(colors)])
                ax.add_patch(circle)

    ani = animation.FuncAnimation(
        fig, update,
        frames=range(SIM_TIME + 1),
        init_func=init,
        interval=500,
        blit=False
    )

    plt.show()

if __name__ == "__main__":
    main()
