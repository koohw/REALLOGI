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
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3],  # (4,10)가 목표(3)
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
]
ROWS = len(map_data)
COLS = len(map_data[0])

##############################################################################
# 2) 컨테이너 좌표들 (AGV가 물건을 받는 지점) - 새로 주신 좌표
#    주의: map_data[r][c] == 0 인지 꼭 확인하세요.
##############################################################################
container_coords = [
    # 첫 줄
    (1, 0), (1, 2), (1, 4), (1, 6), (1, 8),
    # 둘째 줄
    (2, 0), (2, 2), (2, 4), (2, 6), (2, 8),
    # 셋째 줄
    (3, 0), (3, 2), (3, 4), (3, 6), (3, 8),

    # 넷째 줄
    (5, 0), (5, 2), (5, 4), (5, 6), (5, 8),
    # 다섯째 줄
    (6, 0), (6, 2), (6, 4), (6, 6), (6, 8),
    # 여섯째 줄
    (7, 0), (7, 2), (7, 4), (7, 6), (7, 8),
]

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
                # 1=컨테이너(벽), obstacles=다른 AGV
                if grid[nr][nc] != 1 and (nr, nc) not in obstacles:
                    if (nr, nc) not in visited:
                        visited.add((nr, nc))
                        queue.append(((nr, nc), path + [(nr, nc)]))
    return None

##############################################################################
# 3) AGV 프로세스
#    - 컨테이너 -> 목표 -> 컨테이너 -> 목표 ... 무한 반복
##############################################################################
MOVE_INTERVAL = 1

def agv_process(env, agv_id, agv_positions, logs, goal_pos):
    """
    무한 루프:
      1) 무작위 container -> 현재 위치로 BFS
      2) 도착 -> 1초 대기
      3) 목표(3) -> 도착 -> 1초 대기
      4) 반복
    """
    # 초기 위치: 맵에서 0인 칸 중 임의 배치
    init_pos = random_free_position()
    agv_positions[agv_id] = init_pos
    logs[agv_id].append((env.now, init_pos))

    while True:
        # (a) 컨테이너로 이동
        container = random.choice(container_coords)
        yield from move_to(env, agv_id, agv_positions, logs, container)
        # 도착 후 1초
        yield env.timeout(1)

        # (b) 컨테이너에서 목표(3)로 이동
        yield from move_to(env, agv_id, agv_positions, logs, goal_pos)
        # 도착 후 1초
        yield env.timeout(1)
        # -> 다시 while 반복

def move_to(env, agv_id, agv_positions, logs, target):
    """ target까지 BFS로 1초마다 한 칸씩 이동, 경로 없으면 '제자리' """
    while True:
        yield env.timeout(MOVE_INTERVAL)
        curr_pos = agv_positions[agv_id]
        # 다른 AGV 위치
        others = set(pos for k,pos in agv_positions.items() if k != agv_id)

        path = bfs_path(map_data, curr_pos, target, others)
        if path and len(path) > 1:
            next_pos = path[1]
            agv_positions[agv_id] = next_pos
        else:
            # path가 없거나 이미 도착
            if curr_pos == target:
                # 목표 도달 -> return으로 함수를 끝내고 상위 루프로 돌아감
                logs[agv_id].append((env.now, curr_pos))
                print(f"[{env.now}] AGV{agv_id} 도착 -> {curr_pos}")
                return
            # 없으면 제자리(아무것도 안 함), 다음 스텝에 다시 BFS 재시도
        logs[agv_id].append((env.now, agv_positions[agv_id]))
        print(f"[{env.now}] AGV{agv_id} -> {agv_positions[agv_id]} (target={target})")

def random_free_position():
    """ 맵에서 0인 칸 중 임의 위치 """
    candidates = []
    for r in range(ROWS):
        for c in range(COLS):
            if map_data[r][c] == 0:
                candidates.append((r,c))
    return random.choice(candidates) if candidates else (0,0)

##############################################################################
# 4) 시뮬레이션 메인
##############################################################################
def main():
    env = simpy.Environment()
    NUM_AGV = 4
    SIM_TIME = 100  # 시뮬레이션 시간 100초

    # 목표(3) 위치 찾기
    goal_pos = None
    for r in range(ROWS):
        for c in range(COLS):
            if map_data[r][c] == 3:
                goal_pos = (r,c)
                break
        if goal_pos: 
            break

    # AGV 위치/로그
    agv_positions = {}
    logs = {}
    for i in range(NUM_AGV):
        agv_positions[i] = (0,0)
        logs[i] = []

    # 프로세스 등록
    for i in range(NUM_AGV):
        env.process(agv_process(env, i, agv_positions, logs, goal_pos))

    env.run(until=SIM_TIME)
    print("Simulation finished!")

    # 5) 애니메이션
    fig, ax = plt.subplots(figsize=(7,5))

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
                rect = patches.Rectangle((c,r),1,1,edgecolor='black',facecolor=color)
                ax.add_patch(rect)

        # 컨테이너 좌표(노란색)
        for (rr,cc) in container_coords:
            rect2 = patches.Rectangle((cc,rr),1,1,edgecolor='orange',facecolor='yellow',alpha=0.3)
            ax.add_patch(rect2)

        ax.set_xlim(0, COLS)
        ax.set_ylim(0, ROWS)
        ax.set_aspect('equal')
        ax.invert_yaxis()
        ax.set_xticks(range(COLS+1))
        ax.set_yticks(range(ROWS+1))
        ax.grid(False)
        ax.set_title("AGVs with new container_coords (100s simulation)")

    def init():
        draw_map()

    def update(frame):
        draw_map()
        ax.set_title(f"Time={frame}")
        colors = ["red","blue","orange","purple","cyan","green","brown","pink"]
        for agv_id in logs:
            # time <= frame 중 가장 최근 위치
            pos_list = [(t,p) for (t,p) in logs[agv_id] if t <= frame]
            if pos_list:
                _,(rr,cc) = pos_list[-1]
                circle = plt.Circle((cc+0.5, rr+0.5), 0.3,
                                    color=colors[agv_id % len(colors)])
                ax.add_patch(circle)

    ani = animation.FuncAnimation(
        fig, update,
        frames=range(SIM_TIME+1),
        init_func=init,
        interval=500,
        blit=False
    )

    plt.show()

if __name__ == "__main__":
    main()
