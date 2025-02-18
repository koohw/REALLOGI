import simpy
import math
import random
from collections import deque, defaultdict
from heapq import heappush, heappop

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
# 통로 판별 함수 (예시)
# ------------------------------
def is_in_corridor(cell):
    """예시: row가 2~4, col이 2~4인 영역을 통로로 간주"""
    row, col = cell
    return (2 <= row <= 4) and (2 <= col <= 4)

# ------------------------------
# 다익스트라 알고리즘을 이용한 경로 탐색 함수
# ------------------------------
def dijkstra_path(start, goal, current_time, cell_blocked, congestion_count):
    # 시작 셀과 목표 셀이 같으면 바로 리턴
    if start == goal:
        return [start]

    dist = {}     # 각 셀까지의 최소 비용
    prev = {}     # 최단 경로를 재구성하기 위한 부모 노드 정보
    dist[start] = 0
    # 우선순위 큐: (누적 비용, 셀)
    heap = [(0, start)]
    
    while heap:
        cost, cell = heappop(heap)
        if cell == goal:
            break
        if cost > dist.get(cell, float('inf')):
            continue
        r, c = cell
        for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
            nr, nc = r+dr, c+dc
            neighbor = (nr, nc)
            # 경계 검사 및 장애물 건너뛰기
            if not (0 <= nr < ROWS and 0 <= nc < COLS):
                continue
            if MAP[nr][nc] == 1:
                continue
            # 기본 이동 비용은 1
            base_cost = 1
            penalty = 0
            # 만약 셀이 cell_blocked에 있고, 아직 블록이 유지되고 있다면 높은 패널티 부여
            if neighbor in cell_blocked and cell_blocked[neighbor] > current_time:
                penalty += 10
            # congestion_count(혼잡도)도 비용에 추가
            penalty += congestion_count[neighbor]
            # 만약 해당 셀이 통로에 속한다면(위험도가 높다고 가정) 추가 비용 부여
            if is_in_corridor(neighbor):
                penalty += 2
            new_cost = cost + base_cost + penalty
            if new_cost < dist.get(neighbor, float('inf')):
                dist[neighbor] = new_cost
                prev[neighbor] = cell
                heappush(heap, (new_cost, neighbor))
    
    # 목표 셀이 도달 불가능하다면 None 리턴
    if goal not in dist:
        return None

    # 경로 재구성
    path = []
    cell = goal
    while cell is not None:
        path.append(cell)
        cell = prev.get(cell)
    path.reverse()
    return path

# ------------------------------
# AGV 클래스
# ------------------------------
class AGV:
    def __init__(self, agv_id, start_pos, goal):
        self.id = agv_id
        # 현재 위치: 실수 좌표 (셀 중심)
        self.pos = (float(start_pos[0]), float(start_pos[1]))
        self.goal = goal            # 목표 셀 (정수 좌표)
        self.path = []              # 경로 (다익스트라 결과: 정수 좌표 리스트)
        self.last_moved_time = 0    # 마지막 이동 시각

# ------------------------------
# AGV 이동 프로세스 (속도 변동성 부여)
# ------------------------------
def agv_process(env, agv, cell_blocked):
    """
    AGV가 다익스트라 알고리즘을 이용하여 경로를 계산한 후,
    경로 상의 각 셀 사이를 TIME_STEP마다 보간(interpolate)하며 이동합니다.
    각 세그먼트 이동 시, BASE_SPEED에 [SPEED_VARIABILITY] 범위의 랜덤 계수를 곱하여 속도 변동성을 부여합니다.
    """
    # 혼잡도 정보 (이 함수 내에서만 사용)
    congestion = defaultdict(int)
    current_cell = (int(round(agv.pos[0])), int(round(agv.pos[1])))
    # 초기 경로 계산 (다익스트라 사용)
    agv.path = dijkstra_path(current_cell, agv.goal, env.now, cell_blocked, defaultdict(int))
    agv.last_moved_time = env.now

    while agv.path and env.now < 1000:
        # 목표 도착 시 종료
        if len(agv.path) <= 1:
            break

        # 다음 셀 선택: 경로의 두 번째 원소
        next_cell = agv.path[1]

        # 현재 셀과 다음 셀의 중심 좌표
        current_center = (float(agv.pos[0]), float(agv.pos[1]))
        next_center = (float(next_cell[0]), float(next_cell[1]))
        dx = next_center[0] - current_center[0]
        dy = next_center[1] - current_center[1]
        distance = math.sqrt(dx*dx + dy*dy)
        
        # 매 세그먼트마다 속도 변동성을 반영한 effective_speed 결정
        effective_speed = BASE_SPEED * random.uniform(*SPEED_VARIABILITY)
        interp_distance = effective_speed * TIME_STEP
        num_steps = max(1, int(distance / interp_distance))
        step_dx = dx / num_steps
        step_dy = dy / num_steps

        # 보간 이동: 각 TIME_STEP마다 이동
        for _ in range(num_steps):
            yield env.timeout(TIME_STEP)
            new_x = agv.pos[0] + step_dx
            new_y = agv.pos[1] + step_dy
            agv.pos = (new_x, new_y)
            agv.last_moved_time = env.now

        # 보간 이동 후 정확히 다음 셀 중심으로 보정
        agv.pos = (next_center[0], next_center[1])
        agv.last_moved_time = env.now
        # 경로 업데이트: 도착한 셀 제거
        agv.path.pop(0)
        current_cell = (int(round(agv.pos[0])), int(round(agv.pos[1])))
        if current_cell != agv.goal:
            # 남은 경로 재계산 (다익스트라 사용)
            agv.path = dijkstra_path(current_cell, agv.goal, env.now, cell_blocked, defaultdict(int))
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
                dist = math.hypot(pos_i[0]-pos_j[0], pos_i[1]-pos_j[1])
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

    # 두 AGV 생성: 예시) AGV0: (8,1)에서 (0,1)로, AGV1: (8,5)에서 (0,5)로 이동
    agv0 = AGV(0, start_pos=(8, 1), goal=(0, 1))
    agv1 = AGV(1, start_pos=(8, 5), goal=(0, 5))
    agvs = [agv0, agv1]

    cell_blocked = {}  # 테스트에서는 사용하지 않음
    collision_counter = [0]  # 충돌 이벤트 횟수
    deadlock_counter = [0]   # deadlock 이벤트 횟수

    # 각 AGV 이동 프로세스 시작 (다익스트라 경로와 속도 변동성이 반영됨)
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
