# simulation.py
import simpy
from datetime import datetime
from threading import Lock
from collections import deque

# ------------------------------
# 맵 및 좌표 정의
# ------------------------------
MAP = [
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
ROWS = len(MAP)
COLS = len(MAP[0])

# 선반(하역) 좌표, 출구 좌표
shelf_coords = [(2, 2), (2, 4), (2, 6),
                (5, 2), (5, 4), (5, 6)]
exit_coords = [(0, c) for c in range(COLS) if MAP[0][c] == 2]

# 선반 사용 여부 관리 (True면 다른 AGV가 못 지나감)
shelf_in_use = {coord: False for coord in shelf_coords}

# ------------------------------
# 전역 공유 데이터 / 락
# ------------------------------
data_lock = Lock()

shared_data = {
    "positions": {
        "AGV 1": (8, 0),   # 초기값 (시뮬레이터상)
        "AGV 2": (8, 0),
        "AGV 3": (8, 3),
        "AGV 4": (8, 6)
    },
    "statuses": {
        "AGV 1": "idle",
        "AGV 2": "idle",
        "AGV 3": "idle",
        "AGV 4": "idle"
    },
    "logs": {
        "AGV 1": [],
        "AGV 2": [],
        "AGV 3": [],
        "AGV 4": []
    },
    "directions": {
        "AGV 1": "N/A",
        "AGV 2": "N/A",
        "AGV 3": "N/A",
        "AGV 4": "N/A"
    },
    # --- [AGV1 이동 명령/ACK 상태] ---
    "agv1_target": None,         # AGV1에게 "다음 칸" 명령을 내릴 때 기록
    "agv1_moving_ack": False     # 잿슨(AGV1)이 해당 칸 도착을 보고하면 True
}


# ------------------------------
# BFS 유틸 함수
# ------------------------------
def get_neighbors(pos):
    r, c = pos
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    neighbors = []
    for dr, dc in directions:
        nr, nc = r + dr, c + dc
        if 0 <= nr < ROWS and 0 <= nc < COLS:
            neighbors.append((nr, nc))
    return neighbors

def bfs_path(start, goal):
    """
    (start)->(goal) 까지의 경로를 BFS로 찾고,
    경로 리스트를 반환. 못찾으면 [].
    """
    from collections import deque
    queue = deque([start])
    came_from = {start: None}

    while queue:
        current = queue.popleft()
        if current == goal:
            break
        for nxt in get_neighbors(current):
            # 장애물(1)은 못 지나감
            if MAP[nxt[0]][nxt[1]] == 1:
                continue
            # 아직 방문 안한 칸만
            if nxt not in came_from:
                came_from[nxt] = current
                queue.append(nxt)

    # goal까지 못 갔으면 빈 리스트
    if goal not in came_from:
        return []

    path = []
    cur = goal
    while cur is not None:
        path.append(cur)
        cur = came_from[cur]
    path.reverse()
    return path

def get_next_position(current, target):
    """
    current에서 target까지 BFS 경로 중
    '다음 칸'을 반환. 경로 없으면 current 그대로.
    """
    path = bfs_path(current, target)
    if len(path) >= 2:
        return path[1]
    return current

def select_available_shelf():
    """ 
    아직 사용 중이지 않은 선반 좌표를 하나 선택 
    (모두 사용 중이면 맨 첫번째 반환)
    """
    for coord in shelf_coords:
        if not shelf_in_use[coord]:
            return coord
    return shelf_coords[0]


# ------------------------------
# (placeholder) AGV1 명령 전송 함수
# 실제론 mqtt_client.publish(...)
# ------------------------------
def send_command_to_agv1(next_pos):
    """
    실제 환경:
      mqtt_client.publish("simpy/commands", json.dumps({
          "command": "경로",
          "data": {"next_location": next_pos}
      }))
    """
    print(f"[SIM] (placeholder) send_command_to_agv1(next_pos={next_pos})")


# ------------------------------
# AGV 클래스
# ------------------------------
class AGV:
    def __init__(self, env, name, speed, start, shelf_target, exit_target):
        """
        env: simpy Environment
        name: AGV 이름 (문자열)
        speed: 이동 속도 (초당 1칸을 (1/speed)초에 이동)
        start: (row, col) 시작 좌표
        shelf_target: 하역(선반) 좌표
        exit_target: 출구 좌표
        """
        self.env = env
        self.name = name
        self.speed = speed
        self.start = start
        self.shelf_target = shelf_target
        self.exit_target = exit_target

        self.position = start
        self.phase = "to_shelf"  # "to_shelf"->하역->"to_exit"->출구->반복
        self.unloaded = False

    def move(self):
        # AGV1과 AGV2..4 로직 분기
        if self.name == "AGV 1":
            while True:
                # 출구 도착하면 idle 후 리셋
                if (self.phase == "to_exit") and (self.position == self.exit_target):
                    with data_lock:
                        shared_data["statuses"][self.name] = "idle"
                        shared_data["logs"][self.name].append({
                            "time": datetime.now().isoformat(),
                            "position": self.position,
                            "direction": "reset",
                            "state": "idle",
                            "source": "simulation"
                        })
                    yield self.env.timeout(2)

                    # 시작점 복귀, 선반 다시 선택
                    self.position = self.start
                    self.phase = "to_shelf"
                    new_shelf = select_available_shelf()
                    self.shelf_target = new_shelf
                    continue

                # 현재 목표
                if self.phase == "to_shelf":
                    current_target = self.shelf_target
                else:
                    current_target = self.exit_target

                if self.position != current_target:
                    # 다음 칸
                    next_pos = get_next_position(self.position, current_target)
                    if next_pos == self.position:
                        # 더 이상 못가면 stop
                        with data_lock:
                            shared_data["statuses"][self.name] = "stop"
                            shared_data["logs"][self.name].append({
                                "time": datetime.now().isoformat(),
                                "position": self.position,
                                "direction": "none",
                                "state": "stop",
                                "source": "simulation"
                            })
                        yield self.env.timeout(1)
                        continue

                    # 1) MQTT 명령 전송 (placeholder)
                    with data_lock:
                        shared_data["agv1_target"] = next_pos
                        shared_data["agv1_moving_ack"] = False
                    send_command_to_agv1(next_pos)

                    # 2) 잿슨 이동 완료 ack 대기
                    ack_received = False
                    while not ack_received:
                        yield self.env.timeout(0.2)  # 0.2초마다 ack 확인
                        with data_lock:
                            if shared_data["agv1_moving_ack"]:
                                ack_received = True

                    # 3) ack 받았으면 시뮬레이터 내 position 동기화
                    with data_lock:
                        self.position = shared_data["positions"][self.name]
                        shared_data["directions"][self.name] = "R"  # 예시
                        shared_data["statuses"][self.name] = "moving"
                        shared_data["logs"][self.name].append({
                            "time": datetime.now().isoformat(),
                            "position": self.position,
                            "direction": "R",
                            "state": "moving",
                            "source": "simulation"
                        })

                    yield self.env.timeout(1 / self.speed)

                else:
                    # 목표 도달
                    if self.phase == "to_shelf":
                        # 선반 도착 → 하역
                        with data_lock:
                            shelf_in_use[self.position] = True
                            shared_data["statuses"][self.name] = "unloading"
                            shared_data["logs"][self.name].append({
                                "time": datetime.now().isoformat(),
                                "position": self.position,
                                "direction": "N/A",
                                "state": "unloading",
                                "source": "simulation"
                            })
                        yield self.env.timeout(10)  # 10초 하역
                        with data_lock:
                            shelf_in_use[self.position] = False
                        self.unloaded = True
                        self.phase = "to_exit"
                    else:
                        # 출구거나 등등
                        yield self.env.timeout(1)

        else:
            # AGV 2,3,4 로직 (즉시 한칸 이동)
            while True:
                if (self.phase == "to_exit") and (self.position == self.exit_target):
                    with data_lock:
                        shared_data["statuses"][self.name] = "idle"
                        shared_data["logs"][self.name].append({
                            "time": datetime.now().isoformat(),
                            "position": self.position,
                            "direction": "reset",
                            "state": "idle",
                            "source": "simulation"
                        })
                    yield self.env.timeout(2)

                    # 리셋
                    self.position = self.start
                    self.phase = "to_shelf"
                    new_shelf = select_available_shelf()
                    self.shelf_target = new_shelf
                    continue

                if self.phase == "to_shelf":
                    current_target = self.shelf_target
                else:
                    current_target = self.exit_target

                if self.position != current_target:
                    next_pos = get_next_position(self.position, current_target)
                    if next_pos == self.position:
                        with data_lock:
                            shared_data["statuses"][self.name] = "stop"
                            shared_data["logs"][self.name].append({
                                "time": datetime.now().isoformat(),
                                "position": self.position,
                                "direction": "none",
                                "state": "stop",
                                "source": "simulation"
                            })
                        yield self.env.timeout(1)
                        continue

                    # 한 칸 즉시 이동
                    self.position = next_pos
                    # 방향 판별 (단순)
                    r, c = self.position
                    tr, tc = current_target
                    if r < tr:
                        direction = "D"
                    elif r > tr:
                        direction = "U"
                    elif c < tc:
                        direction = "R"
                    elif c > tc:
                        direction = "L"
                    else:
                        direction = "N/A"

                    with data_lock:
                        shared_data["positions"][self.name] = self.position
                        shared_data["directions"][self.name] = direction
                        shared_data["statuses"][self.name] = "moving"
                        shared_data["logs"][self.name].append({
                            "time": datetime.now().isoformat(),
                            "position": self.position,
                            "direction": direction,
                            "state": "moving",
                            "source": "simulation"
                        })
                    yield self.env.timeout(1 / self.speed)
                else:
                    # 목표 도달 (선반→하역 or 출구→idle)
                    if self.phase == "to_shelf":
                        with data_lock:
                            shelf_in_use[self.position] = True
                            shared_data["statuses"][self.name] = "unloading"
                            shared_data["logs"][self.name].append({
                                "time": datetime.now().isoformat(),
                                "position": self.position,
                                "direction": "N/A",
                                "state": "unloading",
                                "source": "simulation"
                            })
                        yield self.env.timeout(10)  # 하역
                        with data_lock:
                            shelf_in_use[self.position] = False
                        self.unloaded = True
                        self.phase = "to_exit"
                    else:
                        yield self.env.timeout(1)


def simulation_run():
    """
    시뮬레이션 실행 함수.
    Flask 등에서 threading으로 호출하거나, 
    메인에서 직접 호출해서 실행 가능.
    """
    import threading

    env = simpy.Environment()

    # AGV들 생성
    agv1 = AGV(env, "AGV 1", speed=1, start=(8, 0), shelf_target=None, exit_target=(0, 0))
    agv2 = AGV(env, "AGV 2", speed=1, start=(8, 0), shelf_target=None, exit_target=(0, 2))
    agv3 = AGV(env, "AGV 3", speed=1, start=(8, 3), shelf_target=None, exit_target=(0, 4))
    agv4 = AGV(env, "AGV 4", speed=1, start=(8, 6), shelf_target=None, exit_target=(0, 6))

    for agv in [agv1, agv2, agv3, agv4]:
        if agv.shelf_target is None:
            agv.shelf_target = select_available_shelf()

    env.process(agv1.move())
    env.process(agv2.move())
    env.process(agv3.move())
    env.process(agv4.move())

    try:
        env.run()
    except KeyboardInterrupt:
        print("[Simulation] KeyboardInterrupt, 종료합니다.")
