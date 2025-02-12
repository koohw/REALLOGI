import simpy
from collections import deque, defaultdict
import math

# ------------------------------
# 테스트용 그리드 및 상수 설정
# ------------------------------
# MAP 정의 (9x7 그리드)
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
STEP_SIZE = 0.1  # 한 칸 이동을 위한 시간 단위 (예시)

# 충돌 체크를 위한 안전 거리(threshold)
SAFETY_MARGIN = 0.5

# ------------------------------
# 헬퍼 함수들
# ------------------------------

def is_in_cell(pos, cell):
    """
    pos: (x, y) 연속 좌표, cell: (row, col) 정수 좌표.
    각 셀의 중심을 (row, col)이라고 가정하고,
    pos가 cell에 속하는지 판단 (반올림 비교)
    """
    return int(round(pos[0])) == cell[0] and int(round(pos[1])) == cell[1]

def bfs_path(start, goal, current_time, cell_blocked, congestion_count, avoid_corridor=False):
    """
    단순 BFS로 start에서 goal까지의 경로를 찾는다.
    avoid_corridor 옵션은 테스트 시 사용하지 않아도 됨.
    """
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
            # 여기서는 avoid_corridor 옵션은 단순히 무시
            if (nr, nc) in cell_blocked and cell_blocked[(nr, nc)] > current_time:
                congestion_count[(nr, nc)] += 1
                continue
            if (nr, nc) in visited:
                continue
            visited[(nr, nc)] = (r, c)
            queue.append((nr, nc))
            if (nr, nc) == goal:
                # 역추적하여 경로 생성
                path = []
                cur = (nr, nc)
                while cur is not None:
                    path.append(cur)
                    cur = visited[cur]
                path.reverse()
                return path
    return None

# ------------------------------
# AGV 클래스 및 프로세스
# ------------------------------
class AGV:
    def __init__(self, agv_id, start_pos, goal):
        self.id = agv_id
        self.pos = (float(start_pos[0]), float(start_pos[1]))
        self.goal = goal  # 목표 셀 (정수 좌표)
        self.path = []  # 경로 (목표까지의 셀 목록)
        self.last_moved_time = 0  # 마지막으로 위치가 바뀐 시각

def agv_process(env, agv, cell_blocked):
    """
    AGV가 자신의 목표까지 BFS 경로를 계산한 후, 한 칸씩 이동하는 프로세스.
    각 이동 후에는 위치를 업데이트하며, 이동 시간이 STEP_SIZE 단위로 지연된다.
    """
    # 초기 경로 계산
    congestion = defaultdict(int)
    agv.path = bfs_path((int(round(agv.pos[0])), int(round(agv.pos[1]))),
                         agv.goal, env.now, cell_blocked, congestion)
    agv.last_moved_time = env.now

    while agv.path and env.now < 1000:
        # 다음 셀 선택 (경로의 첫 칸은 현재 위치)
        if len(agv.path) > 1:
            next_cell = agv.path[1]
        else:
            break  # 도착

        # 간단하게 한 칸 이동 처리: 선형 보간 (여기서는 한 칸 이동에 STEP_SIZE 소요)
        yield env.timeout(STEP_SIZE)
        # 바로 다음 셀로 "점프"하는 대신, 선형 보간 없이 바로 업데이트할 수도 있음
        agv.pos = (float(next_cell[0]), float(next_cell[1]))
        agv.last_moved_time = env.now

        # 경로에서 첫 셀 제거
        agv.path.pop(0)

        # 만약 경로가 비었거나 아직 도착하지 않았다면, 다시 경로 계산
        if (int(round(agv.pos[0])), int(round(agv.pos[1]))) != agv.goal:
            agv.path = bfs_path((int(round(agv.pos[0])), int(round(agv.pos[1]))),
                                 agv.goal, env.now, cell_blocked, defaultdict(int))
        else:
            break  # 도착

# ------------------------------
# 모니터링 프로세스 (충돌, 정체 감지)
# ------------------------------
def monitor_process(env, agvs, collision_flag, deadlock_flag, deadlock_time_threshold=5):
    """
    주기적으로 각 AGV의 위치를 검사하여:
      - 두 AGV간의 거리가 safety margin 이하이면 collision_flag를 True로 설정
      - 각 AGV가 deadlock_time_threshold 시간 동안 위치 변화가 없으면 deadlock_flag를 True로 설정
    """
    while env.now < 1000:
        # 충돌 검사: 모든 쌍에 대해
        for i in range(len(agvs)):
            for j in range(i+1, len(agvs)):
                pos_i = agvs[i].pos
                pos_j = agvs[j].pos
                dist = math.hypot(pos_i[0]-pos_j[0], pos_i[1]-pos_j[1])
                if dist < SAFETY_MARGIN:
                    collision_flag[0] = True

        # 정체(교착) 검사: 각 AGV의 마지막 이동시간과 현재시간 비교
        for agv in agvs:
            if env.now - agv.last_moved_time > deadlock_time_threshold:
                deadlock_flag[0] = True

        yield env.timeout(0.1)

# ------------------------------
# 메인 시뮬레이션 함수
# ------------------------------
def run_simulation():
    # 시뮬레이션 환경 생성
    env = simpy.Environment()

    # 두 AGV를 생성합니다.
    # 예) AGV0는 좌측 하단에서 위쪽 왼쪽 모서리로, AGV1은 우측 하단에서 위쪽 오른쪽 모서리로 이동
    # (이렇게 하면 두 AGV의 경로가 교차할 가능성이 있습니다)
    agv0 = AGV(0, start_pos=(8, 1), goal=(0, 1))
    agv1 = AGV(1, start_pos=(8, 5), goal=(0, 5))
    agvs = [agv0, agv1]

    # cell_blocked는 여기서는 사용하지 않음
    cell_blocked = {}

    # 충돌 및 정체 감지를 위한 플래그 (리스트의 첫 원소로 플래그 값을 저장)
    collision_flag = [False]
    deadlock_flag = [False]

    # 각 AGV 프로세스 생성
    for agv in agvs:
        env.process(agv_process(env, agv, cell_blocked))

    # 모니터링 프로세스 생성
    env.process(monitor_process(env, agvs, collision_flag, deadlock_flag, deadlock_time_threshold=5))

    # 시뮬레이션 실행 (최대 1000 시간 단위)
    env.run(until=1000)

    # 결과 출력
    print("시뮬레이션 종료")
    if collision_flag[0]:
        print("결과: 충돌 발생!")
    else:
        print("결과: 충돌 없음.")

    if deadlock_flag[0]:
        print("결과: 교착(정체) 발생!")
    else:
        print("결과: 교착 없음.")

    # 각 AGV 최종 위치 출력
    for agv in agvs:
        print(f"AGV{agv.id} 최종 위치: {agv.pos}")

if __name__ == '__main__':
    run_simulation()
