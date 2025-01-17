import matplotlib.pyplot as plt
import matplotlib.animation as animation
import simpy
import numpy as np
from collections import defaultdict
import heapq
import csv

# 격자 맵 정의 (0: 이동 가능, 1: 장애물)
grid_map = np.array([
    [0, 0, 0, 0, 0],
    [0, 1, 1, 1, 0],
    [0, 0, 0, 1, 0],
    [0, 1, 0, 0, 0],
    [0, 0, 0, 0, 0]
])

# AGV 상태 관리 클래스
class AGVStatus:
    """AGV의 상태를 관리하는 클래스"""
    def __init__(self, name):
        self.name = name
        self.position = (0, 0)  # 초기 위치
        self.distance_traveled = 0  # 총 이동 거리
        self.active_time = 0  # 동작 시간
        self.idle_time = 0  # 유휴 시간
        self.state = "moving"  # 초기 상태: moving

    def update_position(self, new_position):
        """AGV의 위치와 이동 거리를 업데이트"""
        self.distance_traveled += abs(new_position[0] - self.position[0]) + abs(new_position[1] - self.position[1])
        self.position = new_position

    def add_active_time(self, time):
        """동작 시간을 추가"""
        self.active_time += time

    def add_idle_time(self, time):
        """유휴 시간을 추가"""
        self.idle_time += time

    def set_state(self, state):
        """상태 변경"""
        self.state = state

    def __str__(self):
        """AGV 상태를 문자열로 출력"""
        return (f"{self.name} - Position: {self.position}, "
                f"Distance Traveled: {self.distance_traveled}, "
                f"Active Time: {self.active_time}, Idle Time: {self.idle_time}, "
                f"State: {self.state}")

# A* 알고리즘 구현
def heuristic(a, b):
    """맨해튼 거리 계산"""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def astar(grid, start, goal, occupied_positions):
    """A* 알고리즘 (다른 AGV를 고려)"""
    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}

    while open_set:
        current = heapq.heappop(open_set)[1]

        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            path.reverse()
            return path

        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            neighbor = (current[0] + dx, current[1] + dy)

            if not (0 <= neighbor[0] < grid.shape[0] and 0 <= neighbor[1] < grid.shape[1]):
                continue
            if grid[neighbor[0], neighbor[1]] == 1:
                continue
            if neighbor in occupied_positions:
                continue

            tentative_g_score = g_score[current] + 1
            if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                heapq.heappush(open_set, (f_score[neighbor], neighbor))

    return None  # 경로가 없을 경우

# 격자 맵 시각화 초기 설정
def initialize_grid_visualization(grid_map, agv_statuses, shared_data):
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.set_xlim(-0.5, grid_map.shape[1] - 0.5)
    ax.set_ylim(-0.5, grid_map.shape[0] - 0.5)
    ax.set_xticks(range(grid_map.shape[1]))
    ax.set_yticks(range(grid_map.shape[0]))
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.grid(True, which='both', color='gray', linestyle='--', linewidth=0.5)

    # Y축 방향을 뒤집어 일반적인 좌표 원점 방식으로 변경
    ax.invert_yaxis()

    # 장애물, AGV 위치 초기화
    obstacle_scatter = ax.scatter([], [], c='red', label='Obstacles', s=100)
    agv_scatter = ax.scatter([], [], c='blue', label='AGVs', s=100)
    ax.legend(loc='upper right')

    return fig, ax, obstacle_scatter, agv_scatter

# 업데이트 함수
def update_visualization(obstacle_scatter, agv_scatter, shared_data):
    """장애물 및 AGV 위치 시각화 업데이트"""
    # 장애물 위치를 2D 배열로 변환
    if shared_data["obstacles"]:
        obstacle_positions = np.array(shared_data["obstacles"]).reshape(-1, 2)
    else:
        obstacle_positions = np.empty((0, 2))  # 빈 배열 처리

    # AGV 위치를 2D 배열로 변환
    agv_positions = np.array([status.position for status in shared_data["statuses"]]).reshape(-1, 2)

    # 장애물 및 AGV 위치 업데이트
    obstacle_scatter.set_offsets(obstacle_positions)
    agv_scatter.set_offsets(agv_positions)

def run_simulation_with_visualization(env, grid_map, shared_data, agv_statuses):
    fig, ax, obstacle_scatter, agv_scatter = initialize_grid_visualization(grid_map, agv_statuses, shared_data)

    def update(frame):
        if env.peek() < float('inf'):
            env.step()
        update_visualization(obstacle_scatter, agv_scatter, shared_data)
        return obstacle_scatter, agv_scatter

    ani = animation.FuncAnimation(fig, update, interval=100, blit=False, cache_frame_data=False)
    plt.show()

def dynamic_obstacle_with_visualization(env, shared_data, position, duration):
    print(f"Obstacle added at {position} at time {env.now}")
    shared_data["obstacles"].append(position)
    yield env.timeout(duration)
    shared_data["obstacles"].remove(position)
    print(f"Obstacle removed from {position} at time {env.now}")

def agv_with_logging(env, status, goal, shared_data, grid_map):
    """AGV 동작 및 로그 기록"""
    shared_data["positions"][status.name] = status.position

    while status.position != goal:
        path = astar(grid_map, status.position, goal, set(shared_data["positions"].values()))
        if path and len(path) > 1:
            next_position = path[1]
            print(f"{status.name} moving from {status.position} to {next_position} at time {env.now}")
            status.update_position(next_position)
            shared_data["positions"][status.name] = next_position

            # 이동 기록 저장
            shared_data["logs"][status.name].append({
                "time": env.now,
                "position": status.position,
                "state": "moving"
            })
            yield env.timeout(1)
        else:
            print(f"{status.name} waiting at {status.position} at time {env.now}")
            shared_data["logs"][status.name].append({
                "time": env.now,
                "position": status.position,
                "state": "waiting"
            })
            yield env.timeout(1)

    print(f"{status.name} reached the goal at {goal} at time {env.now}")
    shared_data["logs"][status.name].append({
        "time": env.now,
        "position": status.position,
        "state": "reached"
    })

def save_logs_to_csv(shared_data):
    """AGV 이동 기록을 CSV 파일로 저장"""
    for agv_name, logs in shared_data["logs"].items():
        filename = f"{agv_name}_logs.csv"
        with open(filename, mode="w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["time", "position", "state"])
            writer.writeheader()
            writer.writerows(logs)
        print(f"Logs for {agv_name} saved to {filename}")

# Simpy 환경 생성
env = simpy.Environment()

# AGV 상태 초기화
agv_status_1 = AGVStatus("AGV 1")
agv_status_2 = AGVStatus("AGV 2")
shared_data = {
    "positions": {},  # AGV 위치
    "obstacles": [],  # 장애물 위치
    "statuses": [agv_status_1, agv_status_2],  # AGV 상태
    "logs": {"AGV 1": [], "AGV 2": []}  # AGV 이동 기록
}

# 장애물 및 AGV 프로세스 등록
env.process(dynamic_obstacle_with_visualization(env, shared_data, position=(2, 2), duration=5))
env.process(dynamic_obstacle_with_visualization(env, shared_data, position=(3, 3), duration=7))
env.process(agv_with_logging(env, agv_status_1, goal=(4, 4), shared_data=shared_data, grid_map=grid_map))
env.process(agv_with_logging(env, agv_status_2, goal=(0, 4), shared_data=shared_data, grid_map=grid_map))

# 시뮬레이션 실행 및 로그 저장
run_simulation_with_visualization(env, grid_map, shared_data, [agv_status_1, agv_status_2])
save_logs_to_csv(shared_data)
