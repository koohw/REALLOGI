import simpy
from datetime import datetime
from threading import Lock
import math
import random

# ------------------------------
# MAP 및 관련 변수 정의
# ------------------------------
MAP = [
    [2, 2, 2, 2, 2, 2, 2],  # 도착지점 (출구)
    [0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0],
    [2, 2, 2, 2, 2, 2, 2]   # 출발지점
]

ROWS = len(MAP)
COLS = len(MAP[0])

# 선반 좌표 (하역 구역) – 예시로 지정 (MAP상의 값은 0이지만, 해당 좌표는 하역 전용으로 취급)
shelf_coords = [(2, 2), (2, 4), (2, 6), (5, 2), (5, 4), (5, 6)]
# 출구 좌표: MAP의 첫 행에서 값이 2인 모든 열
exit_coords = [(0, c) for c in range(COLS) if MAP[0][c] == 2]

# 전역으로 선반 사용 여부를 관리 (선반 좌표가 사용 중이면 True)
shelf_in_use = {coord: False for coord in shelf_coords}

# 전역 공유 데이터 및 락 (모든 AGV의 상태, 위치 등을 기록)
data_lock = Lock()
shared_data = {
    "positions": {
        "AGV 1": (0, 0),
        "AGV 2": (0, 0),
        "AGV 3": (0, 0),
        "AGV 4": (0, 0)
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
    }
}

# ------------------------------
# 함수: 사용 가능한 선반 좌표 선택
# ------------------------------
def select_available_shelf():
    """
    shelf_coords 목록 중 현재 사용 중이지 않은 선반 좌표를 선택하여 반환합니다.
    모두 사용 중이면 우선순위로 첫 번째 좌표를 반환합니다.
    """
    for coord in shelf_coords:
        if not shelf_in_use.get(coord, False):
            return coord
    return shelf_coords[0]

# ------------------------------
# 함수: 인접 셀 중 목표와의 맨해튼 거리가 줄어드는 셀 선택
# ------------------------------
def get_next_position(current, target):
    """
    현재 위치 current (row, col)에서 목표 target까지 이동할 때,
    상하좌우 인접 셀 중 MAP 값이 0 또는 2인 셀(통로나 출발/도착 영역)만 고려하여,
    현재 위치와의 맨해튼 거리가 기준이 되어 목표까지의 거리가 줄어드는 셀을 후보로 선택합니다.
    단, 후보가 선반 좌표에 해당하고 해당 선반이 사용 중이면 후보에서 제외합니다.
    후보가 없으면 현재 위치를 반환합니다.
    """
    if current == target:
        return current

    r, c = current
    tr, tc = target
    current_dist = abs(r - tr) + abs(c - tc)
    candidates = [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]
    valid_moves = []
    for nr, nc in candidates:
        if 0 <= nr < ROWS and 0 <= nc < COLS:
            if MAP[nr][nc] == 1:
                continue
            # 만약 후보가 선반 좌표인데 이미 사용 중이면 제외 (단, 목표가 해당 선반이면 허용)
            if (nr, nc) in shelf_coords and shelf_in_use.get((nr, nc), False) and (nr, nc) != target:
                continue
            new_dist = abs(nr - tr) + abs(nc - tc)
            if new_dist < current_dist:
                valid_moves.append(((nr, nc), new_dist))
    if not valid_moves:
        return current
    best_move = min(valid_moves, key=lambda x: x[1])[0]
    return best_move

# ------------------------------
# AGV 클래스
# ------------------------------
class AGV:
    def __init__(self, env, name, speed, start, shelf_target, exit_target):
        """
        :param env: SimPy 환경
        :param name: AGV 이름 (예: "AGV 2")
        :param speed: 이동 속도 (초당 이동 횟수)
        :param start: 출발지점 좌표 (row, col)
        :param shelf_target: 하역(선반) 좌표 (row, col)
        :param exit_target: 도착지(출구) 좌표 (row, col)
        """
        self.env = env
        self.name = name
        self.speed = speed
        self.start = start
        self.shelf_target = shelf_target
        self.exit_target = exit_target
        self.position = start
        self.phase = "to_shelf"  # "to_shelf" → 하역 → "to_exit" 로 전환
        self.unloaded = False   # 하역 여부

    def move(self):
        # 초기 상태 기록
        with data_lock:
            shared_data["statuses"][self.name] = "moving"
            shared_data["positions"][self.name] = self.position
            shared_data["logs"][self.name].append({
                "time": datetime.now().isoformat(),
                "position": self.position,
                "direction": "start",
                "state": "moving",
                "source": "simulation"
            })

        # 첫 번째 목표: 선반(하역) 지점으로 이동
        current_target = self.shelf_target

        while self.position != current_target:
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

            self.position = next_pos
            # 이동한 방향을 단순 비교로 판별 (필요 시 개선)
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

        # 선반(하역) 구역에 도착한 경우 처리
        if self.phase == "to_shelf":
            # 해당 선반 좌표를 사용 중으로 표시
            shelf_in_use[self.position] = True
            with data_lock:
                shared_data["statuses"][self.name] = "unloading"
                shared_data["logs"][self.name].append({
                    "time": datetime.now().isoformat(),
                    "position": self.position,
                    "direction": "N/A",
                    "state": "unloading",
                    "source": "simulation"
                })
            # 10초간 하역 대기 (그 동안 해당 선반 구역은 다른 AGV가 지나갈 수 없음)
            yield self.env.timeout(10)
            # 하역 완료 후 선반 좌표 사용 해제
            shelf_in_use[self.position] = False
            self.unloaded = True
            # 전환: 다음 목표는 도착지(출구)
            self.phase = "to_exit"
            current_target = self.exit_target

        # 두 번째 목표: 도착지(출구)로 이동
        while self.position != current_target:
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

            self.position = next_pos
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

        # 도착지(출구)에 도달하면 idle 상태로 전환
        with data_lock:
            shared_data["statuses"][self.name] = "idle"
            shared_data["logs"][self.name].append({
                "time": datetime.now().isoformat(),
                "position": self.position,
                "direction": shared_data["directions"][self.name],
                "state": "idle",
                "source": "simulation"
            })

# ------------------------------
# simulation_once 함수: 데모용 시뮬레이션 실행
# ------------------------------
def simulation_once():
    """
    데모용: AGV 2, AGV 3, AGV 4가
      - 출발지점(출발지: MAP의 9번째 행)에서
      - 각자의 선반(하역) 지점(사용 가능한 선반 좌표 중 선택)에 도착하여 10초 동안 하역 후
      - 도착지(출구: MAP의 첫 행)로 이동하도록 시뮬레이션합니다.
    
    예시)
      - AGV 2: 시작 (8, 0) → 선반 (사용 가능한 좌표 중 하나) → 도착 (0, 2)
      - AGV 3: 시작 (8, 3) → 선반 (사용 가능한 좌표 중 하나) → 도착 (0, 4)
      - AGV 4: 시작 (8, 6) → 선반 (사용 가능한 좌표 중 하나) → 도착 (0, 6)
    """
    env = simpy.Environment()

    # 각 AGV에 대해 출발, 도착 좌표는 지정하고, 선반(하역) 좌표는 실행 시 사용 가능한 좌표를 선택합니다.
    agv2 = AGV(env, "AGV 2", speed=1, start=(8, 0), shelf_target=None, exit_target=(0, 2))
    agv3 = AGV(env, "AGV 3", speed=1, start=(8, 3), shelf_target=None, exit_target=(0, 4))
    agv4 = AGV(env, "AGV 4", speed=1, start=(8, 6), shelf_target=None, exit_target=(0, 6))
    
    # AGV 생성 시, 만약 shelf_target이 None이면 사용 가능한 선반 좌표를 선택합니다.
    for agv in [agv2, agv3, agv4]:
        if agv.shelf_target is None:
            agv.shelf_target = select_available_shelf()

    env.process(agv2.move())
    env.process(agv3.move())
    env.process(agv4.move())

    # 60초 동안 시뮬레이션 실행 (필요에 따라 조절 가능)
    env.run(until=60)
