import simpy
import math
import random
from collections import deque, defaultdict

# ------------------------------
# 테스트용 그리드 및 상수 설정
# ------------------------------
MAP = [
    [2, 2, 2, 2, 2, 2, 2],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [2, 2, 2, 2, 2, 2, 2]
]
ROWS = len(MAP)
COLS = len(MAP[0])

# 시뮬레이션 시간 step (보간시 시간 간격)
TIME_STEP = 0.1  
# 기본 AGV의 이동 속도 (셀/시간 단위)
BASE_SPEED = 0.5  
# 속도 변동성: 실제 속도는 BASE_SPEED * factor, factor는 [0.8, 1.2] 범위 (예시)
SPEED_VARIABILITY = (0.8, 1.2)
# AGV들이 서로 충돌했다고 판단하는 최소 거리 (cell 단위)
SAFETY_MARGIN = 0.5

# ------------------------------
# BFS 경로 탐색 함수 (변경 없음)
# ------------------------------
def bfs_path(start, goal, current_time, cell_blocked, congestion_count):
    if start == goal:
        return [start]
    visited = {start: None}
    queue = deque([start])
    while queue:
        r, c = queue.popleft()
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < ROWS and 0 <= nc < COLS):
                continue
            if MAP[nr][nc] == 1:
                continue
            if (nr, nc) in cell_blocked and cell_blocked[(nr, nc)] > current_time:
                congestion_count[(nr, nc)] += 1
                continue
            if (nr, nc) in visited:
                continue
            visited[(nr, nc)] = (r, c)
            queue.append((nr, nc))
            if (nr, nc) == goal:
                path = []
                cur = (nr, nc)
                while cur is not None:
                    path.append(cur)
                    cur = visited[cur]
                path.reverse()
                return path
    return None

# ------------------------------
# AGV 클래스
# ------------------------------
class AGV:
    def __init__(self, agv_id, start_pos, goal):
        self.id = agv_id
        # 현재 위치: 실수 좌표 (셀 중심)
        self.pos = (float(start_pos[0]), float(start_pos[1]))
        self.goal = goal            # 목표 셀 (정수 좌표)
        self.path = []              # 경로 (BFS 결과: 정수 좌표 리스트)
        self.last_moved_time = 0    # 마지막 이동 시각

# ------------------------------
# AGV 이동 프로세스 (속도 변동성을 부여)
# ------------------------------
def agv_process(env, agv, cell_blocked):
    """
    AGV가 BFS 경로를 계산한 후, 경로 상의 각 셀 사이를 이동합니다.
    단, 각 TIME_STEP마다 실제 이동 속도는 BASE_SPEED에 일정한 변동성을 가진 랜덤 계수를 곱한 값으로 결정됩니다.
    """
    congestion = defaultdict(int)
    current_cell = (int(round(agv.pos[0])), int(round(agv.pos[1])))
    # 초기 경로 계산
    agv.path = bfs_path(current_cell, agv.goal, env.now, cell_blocked, defaultdict(int))
    agv.last_moved_time = env.now

    while agv.path and env.now < 1000:
        # 경로가 1칸 이하면 종료 (목표 도달)
        if len(agv.path) <= 1:
            break

        # 다음 셀 선택: 경로의 두 번째 원소
        next_cell = agv.path[1]

        # 현재 셀과 다음 셀의 중심 좌표 (실수형)
        current_center = (float(agv.pos[0]), float(agv.pos[1]))
        next_center = (float(next_cell[0]), float(next_cell[1]))
        dx = next_center[0] - current_center[0]
        dy = next_center[1] - current_center[1]
        distance = math.sqrt(dx*dx + dy*dy)
        
        # 매 step마다 속도 변동성을 부여하여 실제 속도 결정
        # effective_speed = BASE_SPEED * random_factor (random_factor ∈ [SPEED_VARIABILITY[0], SPEED_VARIABILITY[1]])
        effective_speed = BASE_SPEED * random.uniform(*SPEED_VARIABILITY)
        interp_distance = effective_speed * TIME_STEP
        num_steps = max(1, int(distance / interp_distance))
        step_dx = dx / num_steps
        step_dy = dy / num_steps

        # 보간 이동: 매 TIME_STEP마다 이동
        for _ in range(num_steps):
            yield env.timeout(TIME_STEP)
            # 매 step마다 속도 변동성을 다시 적용할 수도 있지만 여기서는 각 세그먼트에 대해 한 번의 effective_speed로 진행
            new_x = agv.pos[0] + step_dx
            new_y = agv.pos[1] + step_dy
            agv.pos = (new_x, new_y)
            agv.last_moved_time = env.now

        # 보간 후 정확히 다음 셀 중심으로 보정
        agv.pos = (next_center[0], next_center[1])
        agv.last_moved_time = env.now
        # 도착한 셀은 경로에서 제거
        agv.path.pop(0)
        current_cell = (int(round(agv.pos[0])), int(round(agv.pos[1])))
        if current_cell != agv.goal:
            # 남은 경로 재계산 (BFS)
            agv.path = bfs_path(current_cell, agv.goal, env.now, cell_blocked, defaultdict(int))
        else:
            break

# ------------------------------
# 모니터링 프로세스 (충돌 및 deadlock 감지)
# ------------------------------
def monitor_process(env, agvs, collision_counter, deadlock_counter, deadlock_time_threshold=5):
    """
    0.1 시간 간격으로 각 AGV의 위치를 검사하여,
      - 두 AGV 간의 거리가 SAFETY_MARGIN 미만이면 충돌 이벤트로 감지
      - 각 AGV가 마지막 이동 이후 deadlock_time_threshold 시간 이상 움직이지 않으면 deadlock 이벤트로 감지
    연속 이벤트는 한 번만 카운트합니다.
    """
    collision_state = False
    deadlock_state = {agv.id: False for agv in agvs}

    while env.now < 1000:
        # 충돌 감지
        collision_detected = False
        for i in range(len(agvs)):
            for j in range(i+1, len(agvs)):
                pos_i = agvs[i].pos
                pos_j = agvs[j].pos
                dist = math.hypot(pos_i[0] - pos_j[0], pos_i[1] - pos_j[1])
                if dist < SAFETY_MARGIN:
                    collision_detected = True
                    break
            if collision_detected:
                break
        if collision_detected and not collision_state:
            collision_counter[0] += 1
            collision_state = True
        elif not collision_detected:
            collision_state = False

        # 교착(Deadlock) 감지
        for agv in agvs:
            if env.now - agv.last_moved_time > deadlock_time_threshold and not deadlock_state[agv.id]:
                deadlock_counter[0] += 1
                deadlock_state[agv.id] = True
            if env.now - agv.last_moved_time <= deadlock_time_threshold:
                deadlock_state[agv.id] = False

        yield env.timeout(0.1)

# ------------------------------
# 메인 시뮬레이션 함수
# ------------------------------
def run_simulation():
    env = simpy.Environment()

    # 두 AGV 생성: 예시) AGV0은 (8,1)에서 (0,1)로, AGV1은 (8,5)에서 (0,5)로 이동
    agv0 = AGV(0, start_pos=(8, 1), goal=(0, 1))
    agv1 = AGV(1, start_pos=(8, 5), goal=(0, 5))
    agvs = [agv0, agv1]

    cell_blocked = {}  # 테스트에서는 사용하지 않음
    collision_counter = [0]  # 충돌 이벤트 횟수
    deadlock_counter = [0]   # deadlock 이벤트 횟수

    # 각 AGV 이동 프로세스 시작 (속도 변동성을 반영하여 uniform하게 이동하되 매 step마다 랜덤 변동)
    for agv in agvs:
        env.process(agv_process(env, agv, cell_blocked))
    # 모니터링 프로세스 시작
    env.process(monitor_process(env, agvs, collision_counter, deadlock_counter, deadlock_time_threshold=5))

    # 시뮬레이션 실행 (최대 1000 시간 단위)
    env.run(until=1000)

    # 결과 출력
    print("시뮬레이션 종료")
    print(f"충돌 이벤트 횟수: {collision_counter[0]}")
    print(f"교착(Deadlock) 이벤트 횟수: {deadlock_counter[0]}")
    for agv in agvs:
        print(f"AGV{agv.id} 최종 위치: {agv.pos}")

if __name__ == '__main__':
    run_simulation()
