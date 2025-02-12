import simpy
from collections import deque, defaultdict
import math

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
STEP_SIZE = 0.1  # 한 칸 이동에 걸리는 시간

# 안전거리 (충돌로 판단하는 최소 거리)
SAFETY_MARGIN = 0.5

# ------------------------------
# 헬퍼 함수
# ------------------------------
def bfs_path(start, goal, current_time, cell_blocked, congestion_count, avoid_corridor=False):
    """
    단순 BFS를 사용하여 start에서 goal까지의 경로(정수 셀 좌표 리스트)를 찾는다.
    """
    if start == goal:
        return [start]
    visited = {start: None}
    queue = deque([start])
    while queue:
        r, c = queue.popleft()
        for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < ROWS and 0 <= nc < COLS):
                continue
            if MAP[nr][nc] == 1:
                continue
            # avoid_corridor 옵션은 여기서는 사용하지 않음.
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
        # pos를 float형 좌표로 관리. (시뮬레이션에서는 각 셀의 중심 좌표를 사용)
        self.pos = (float(start_pos[0]), float(start_pos[1]))
        self.goal = goal  # 목표 셀 (정수 좌표)
        self.path = []   # 경로: 목표까지의 정수 좌표 목록
        self.last_moved_time = 0  # 마지막으로 위치가 바뀐 시각

# ------------------------------
# AGV 이동 프로세스
# ------------------------------
def agv_process(env, agv, cell_blocked):
    """
    AGV가 BFS 경로를 계산하여 목표까지 한 칸씩 이동하는 프로세스.
    각 이동 후에 STEP_SIZE만큼 시간 지연하며, 이동 시마다 마지막 이동 시간을 업데이트.
    """
    congestion = defaultdict(int)
    current_cell = (int(round(agv.pos[0])), int(round(agv.pos[1])))
    agv.path = bfs_path(current_cell, agv.goal, env.now, cell_blocked, congestion)
    agv.last_moved_time = env.now

    while agv.path and env.now < 1000:
        # 경로의 첫 셀은 현재 위치이므로, 다음 셀로 이동
        if len(agv.path) > 1:
            next_cell = agv.path[1]
        else:
            break  # 도착
        
        # 한 셀 이동 (여기서는 단순히 시간 STEP_SIZE 후에 바로 위치 업데이트)
        yield env.timeout(STEP_SIZE)
        agv.pos = (float(next_cell[0]), float(next_cell[1]))
        agv.last_moved_time = env.now
        # 경로에서 현재 셀 제거
        agv.path.pop(0)
        current_cell = (int(round(agv.pos[0])), int(round(agv.pos[1])))
        if current_cell != agv.goal:
            agv.path = bfs_path(current_cell, agv.goal, env.now, cell_blocked, defaultdict(int))
        else:
            break  # 도착

# ------------------------------
# 모니터링 프로세스 (충돌, 교착 감지)
# ------------------------------
def monitor_process(env, agvs, collision_counter, deadlock_counter, deadlock_time_threshold=5):
    """
    0.1 시간 단위로 각 AGV의 위치를 검사하여:
      - 두 AGV 사이의 거리가 SAFETY_MARGIN 미만이면(교차하면) collision 이벤트로 간주.
      - 각 AGV가 deadlock_time_threshold 시간 이상 위치 변화가 없으면 deadlock 이벤트로 간주.
    
    단, 한 번의 충돌/교착 이벤트가 지속될 경우 연속해서 카운트되지 않도록
    (즉, 상태 변화가 있을 때만 카운트) 합니다.
    """
    # collision_state: 이전 시간에 충돌이 있었는지 여부 (전체 AGV 쌍)
    collision_state = False
    # 각 AGV별로 deadlock 상태를 추적하는 딕셔너리
    deadlock_state = {agv.id: False for agv in agvs}

    while env.now < 1000:
        # --- 충돌 감지 ---
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

        # --- 교착(Deadlock) 감지 ---
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
    # 시뮬레이션 환경 생성
    env = simpy.Environment()

    # 두 대의 AGV를 생성합니다.
    # 예를 들어, AGV0는 아래쪽에서 위쪽으로, AGV1은 오른쪽 아래에서 위쪽 오른쪽으로 이동하도록 설정
    # (두 경로가 교차하는 상황을 테스트합니다)
    agv0 = AGV(0, start_pos=(8, 1), goal=(0, 1))
    agv1 = AGV(1, start_pos=(8, 5), goal=(0, 5))
    agvs = [agv0, agv1]

    # cell_blocked는 여기서는 사용하지 않으므로 빈 dict 사용
    cell_blocked = {}

    # 충돌 및 교착(Deadlock) 이벤트 카운터 (리스트의 첫 원소에 카운트를 저장)
    collision_counter = [0]
    deadlock_counter = [0]

    # 각 AGV의 프로세스 시작
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
