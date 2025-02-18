import eventlet
eventlet.monkey_patch()
import multiprocessing
import sys
import json
import time
import random
import statistics
from simpy.rt import RealtimeEnvironment
from simpy import Environment
from collections import deque, defaultdict

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit

import logging

logger = logging.getLogger(__name__)

# -----------------------------------------
# 전역 설정 & 전역 변수
# -----------------------------------------
global_speed_factor = 1.0
SIM_RUNNING = False
SIM_DURATION = 3000  # 기본 종료 시각 (필요에 따라 조정)
SIM_ENV = None
SIM_STATS = None
SIM_AGVS = []
SIM_PAUSED = False
PREVIOUS_SPEED = 1.0

UPDATE_INTERVAL = 0.1
SIM_FINISHED = False
SIM_APP_RUNNING = False

current_time_paused = None
delivered_count_paused = None
current_positions = []
current_cargos = []
current_paths = []
is_paused = False

# 예약을 위한 전역 변수 (cell 좌표 -> AGV id)
RESERVED_CELLS = {}

# -----------------------------------------
# 시뮬레이션 기본 상수
# -----------------------------------------
REPEAT_RUNS = 15
WARMUP_PERIOD = 30
CHECK_INTERVAL = 3000
MOVE_RATE = 1.0
STEP_SIZE = 0.01

# 맵 정의
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
shelf_coords = [(2, 2), (2, 4), (2, 6), (5, 2), (5, 4), (5, 6)]
exit_coords = [(0, c) for c in range(COLS) if MAP[0][c] == 2]

# ─── 헬퍼 함수: 통로 영역 판별 ─────────────────────────────
def is_in_corridor(cell):
    """예제: 통로 영역을 row가 2~4, col이 2~4 인 영역으로 정의 (필요에 따라 수정)"""
    row, col = cell
    return (2 <= row <= 4) and (2 <= col <= 4)
# ─────────────────────────────────────────────────────

def create_app(port):
    """Create Flask application with specific port configuration"""
    app = Flask(__name__)
    CORS(app)
    socketio = SocketIO(
        app,
        cors_allowed_origins=["http://localhost:3000"],
        path='socket.io',
        async_mode='eventlet',
        logger=True,
        engineio_logger=True,
        ping_timeout=5000,
        ping_interval=2500
    )

    # -----------------------------------------
    # BFS 경로 탐색
    # -----------------------------------------
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

    # --- 실시간 목표 재설계 함수 ---
    def find_nearest_exit(pos, current_agv_id=None):
        available = []
        for ex in exit_coords:
            occupied = False
            for agv in SIM_AGVS:
                if current_agv_id is not None and agv.id == current_agv_id:
                    continue
                if (int(round(agv.pos[0])), int(round(agv.pos[1]))) == ex:
                    occupied = True
                    break
            if not occupied:
                available.append(ex)
        if available:
            return min(available, key=lambda e: abs(pos[0]-e[0]) + abs(pos[1]-e[1]))
        else:
            return min(exit_coords, key=lambda e: abs(pos[0]-e[0]) + abs(pos[1]-e[1]))

    def find_alternative_exit(pos, exclude, current_agv_id=None):
        available = []
        for ex in exit_coords:
            if ex == exclude:
                continue
            occupied = False
            for agv in SIM_AGVS:
                if current_agv_id is not None and agv.id == current_agv_id:
                    continue
                if (int(round(agv.pos[0])), int(round(agv.pos[1]))) == ex:
                    occupied = True
                    break
            if not occupied:
                available.append(ex)
        if available:
            return min(available, key=lambda e: abs(pos[0]-e[0]) + abs(pos[1]-e[1]))
        else:
            return min(exit_coords, key=lambda e: abs(pos[0]-e[0]) + abs(pos[1]-e[1]))

    def find_nearest_shelf(pos, current_agv_id=None):
        available = []
        for sh in shelf_coords:
            occupied = False
            for agv in SIM_AGVS:
                if current_agv_id is not None and agv.id == current_agv_id:
                    continue
                if (int(round(agv.pos[0])), int(round(agv.pos[1]))) == sh:
                    occupied = True
                    break
            if not occupied:
                available.append(sh)
        if available:
            return min(available, key=lambda s: abs(pos[0]-s[0]) + abs(pos[1]-s[1]))
        else:
            return min(shelf_coords, key=lambda s: abs(pos[0]-s[0]) + abs(pos[1]-s[1]))
    # --- 끝 ---

    # -----------------------------------------
    # AGV, Stats, Processes
    # -----------------------------------------
    class AGV:
        def __init__(self, agv_id, start_pos):
            self.id = agv_id
            self.start_pos = (float(start_pos[0]), float(start_pos[1]))
            self.pos = (float(start_pos[0]), float(start_pos[1]))
            self.path = []
            self.cargo = 0
            self.pickup_time = None
            self.arrival_time = 0  # 마지막 도착 시각

    class Stats:
        def __init__(self):
            self.delivered_count = 0
            self.delivered_record = defaultdict(int)
            self.delivered_history = {}
            self.agv_stats = defaultdict(lambda: {
                "count": 0,
                "times": [],
                "wait_times": [],
                "travel_times": [],
                "location_log": []
            })

    def compute_simulation_result(stats, sim_duration, agv_count):
        final_agv_stats = {}
        for agv_id, data in stats.agv_stats.items():
            count = data["count"]
            times = data["times"]
            avg_time = sum(times)/len(times) if times else 0
            final_agv_stats[agv_id] = {
                "count": count,
                "times": times,
                "avg_time": avg_time,
                "wait_times": data["wait_times"],
                "travel_times": data["travel_times"],
                "location_log": data["location_log"]
            }
        res = {
            "end_time": sim_duration,
            "delivered_count": stats.delivered_count,
            "delivered_history": stats.delivered_history,
            "delivered_record": dict(stats.delivered_record),
            "agv_stats": final_agv_stats
        }
        delivered_counts = res["delivered_count"]
        throughput = delivered_counts / sim_duration * 3600
        delivered_per_agv = delivered_counts / agv_count
        all_cycle_times = []
        all_wait_times = []
        all_travel_times = []
        for agv_stat in res["agv_stats"].values():
            all_cycle_times.extend(agv_stat["times"])
            all_wait_times.extend(agv_stat.get("wait_times", []))
            all_travel_times.extend(agv_stat.get("travel_times", []))
        avg_cycle = statistics.mean(all_cycle_times) if all_cycle_times else 0
        avg_wait = statistics.mean(all_wait_times) if all_wait_times else 0
        avg_travel = statistics.mean(all_travel_times) if all_travel_times else 0
        result = {
            "agv_count": agv_count,
            "throughput_per_hour": throughput,
            "delivered_per_agv": delivered_per_agv,
            "avg_cycle": avg_cycle,
            "avg_wait": avg_wait,
            "avg_travel": avg_travel
        }
        return result

    def do_pick(agv, env, stats, cell_blocked):
        now = env.now
        cell_blocked[agv.pos] = now + 10
        yield env.timeout(10)
        agv.cargo = 1
        if now >= WARMUP_PERIOD:
            agv.pickup_time = now
        stats.agv_stats[agv.id]["count"] += 1

    def do_drop(agv, env, stats, cell_blocked):
        start_drop = env.now
        cell_blocked[agv.pos] = start_drop + 10
        yield env.timeout(10)
        drop_finish = env.now
        if agv.pickup_time is not None:
            duration = drop_finish - agv.pickup_time
            stats.agv_stats[agv.id]["times"].append(duration)
            agv.pickup_time = None
        agv.cargo = 0
        stats.delivered_count += 1

    def extend_sim_duration_if_needed(current_time):
        global SIM_DURATION
        if current_time >= SIM_DURATION - 1:
            SIM_DURATION = current_time + 3000
            print(f"[extend_sim_duration_if_needed] SIM_DURATION extended to {SIM_DURATION}")

    def restart_simulation_with_current_state():
        global SIM_RUNNING, SIM_ENV, SIM_STATS, SIM_AGVS, SIM_DURATION, global_speed_factor
        if not SIM_RUNNING:
            return
        current_time = SIM_ENV.now
        extend_sim_duration_if_needed(current_time)
        current_positions = []
        current_cargos = []
        current_paths = []
        for agv in SIM_AGVS:
            current_positions.append(agv.pos)
            current_cargos.append(agv.cargo)
            current_paths.append(agv.path.copy() if agv.path else [])
        delivered_count = SIM_STATS.delivered_count
        SIM_RUNNING = False
        env = RealtimeEnvironment(factor=global_speed_factor, initial_time=current_time)
        stats = Stats()
        stats.delivered_count = delivered_count
        agvs = []
        cell_blocked = {}
        for i, (pos, cargo, path) in enumerate(zip(current_positions, current_cargos, current_paths)):
            agv = AGV(i, pos)
            agv.cargo = cargo
            agv.path = path
            agvs.append(agv)
            env.process(agv_process(agv, env, stats, SIM_DURATION, cell_blocked))
        env.process(record_stats(env, SIM_DURATION, stats))
        env.process(record_interval_stats(env, SIM_DURATION, stats))
        SIM_ENV = env
        SIM_STATS = stats
        SIM_AGVS = agvs
        socketio.start_background_task(run_continued_simulation, env, SIM_DURATION, len(agvs))

    def run_continued_simulation(env, sim_duration, agv_count):
        global SIM_RUNNING, SIM_FINISHED
        SIM_RUNNING = True
        SIM_FINISHED = False
        try:
            env.run(until=sim_duration)
        except Exception as e:
            print(f"Simulation error: {e}")
        finally:
            SIM_RUNNING = False
            SIM_FINISHED = True
            print("시뮬레이션 종료")
            result = compute_simulation_result(SIM_STATS, sim_duration, agv_count)
            socketio.emit('simulation_final', result)

    def agv_process(agv, env, stats, sim_duration, cell_blocked):
        while env.now < sim_duration:
            # ① 현재 셀에 낮은 id를 가진 AGV가 있으면 대기
            current_cell = (int(round(agv.pos[0])), int(round(agv.pos[1])))
            conflict_found = False
            for other in SIM_AGVS:
                if other.id < agv.id:
                    other_cell = (int(round(other.pos[0])), int(round(other.pos[1])))
                    if current_cell == other_cell:
                        conflict_found = True
                        break
            if conflict_found:
                yield env.timeout(0.1)
                continue

            # ② cargo 상태에 따라 적재/하역 위치 재설계
            if agv.cargo == 1 and current_cell in exit_coords:
                available_exit = find_nearest_exit(current_cell, agv.id)
                if available_exit != current_cell:
                    new_path = bfs_path(current_cell, available_exit, env.now, cell_blocked, defaultdict(int))
                    if new_path and len(new_path) > 1:
                        agv.path = new_path
                    yield env.timeout(0.1)
                    continue
            if agv.cargo == 0 and current_cell in shelf_coords:
                available_shelf = find_nearest_shelf(current_cell, agv.id)
                if available_shelf != current_cell:
                    new_path = bfs_path(current_cell, available_shelf, env.now, cell_blocked, defaultdict(int))
                    if new_path and len(new_path) > 1:
                        agv.path = new_path
                    yield env.timeout(0.1)
                    continue

            # ③ 경로가 없거나 1칸 이하이면 새 경로 생성
            if not agv.path or len(agv.path) <= 1:
                if agv.cargo == 0:
                    target = find_nearest_shelf(current_cell, agv.id)
                    path = bfs_path(current_cell, target, env.now, cell_blocked, defaultdict(int))
                    agv.path = path if path is not None else []
                else:
                    target = find_nearest_exit(current_cell, agv.id)
                    path = bfs_path(current_cell, target, env.now, cell_blocked, defaultdict(int))
                    agv.path = path if path is not None else []

            # ④ 경로 실행 (다음 셀로 이동)
            if len(agv.path) > 1:
                next_cell = agv.path[1]

                # [추가] 현재 다른 AGV의 정수 위치들을 확인하여, 만약 next_cell가 이미 다른 AGV의 현재 위치라면 바로 재설계
                occupied_cells = {(int(round(other.pos[0])), int(round(other.pos[1]))) for other in SIM_AGVS if other.id != agv.id}
                if next_cell in occupied_cells:
                    if agv.cargo == 0:
                        target = find_nearest_shelf(current_cell, agv.id)
                    else:
                        target = find_nearest_exit(current_cell, agv.id)
                    new_path = bfs_path(current_cell, target, env.now, cell_blocked, defaultdict(int))
                    if new_path and len(new_path) > 1:
                        agv.path = new_path
                        next_cell = agv.path[1]
                    else:
                        yield env.timeout(0.1)
                        continue

                # ★ 수정된 부분: 수직 통로에서 반대 방향 진행 시 후진 처리 (오직 둘 다 통로 내에 있을 때만)
                cur_dir = (next_cell[0] - current_cell[0], next_cell[1] - current_cell[1])
                if abs(cur_dir[0]) > 0 and abs(cur_dir[1]) < 1e-6:  # 수직 이동인 경우
                    for other in SIM_AGVS:
                        if other.id == agv.id:
                            continue
                        other_cell = (int(round(other.pos[0])), int(round(other.pos[1])))
                        # 오직 두 AGV 모두 통로 내에 있을 때만 후진 시도
                        if is_in_corridor(current_cell) and is_in_corridor(other_cell):
                            if other.path and len(other.path) > 1:
                                other_dir = (other.path[1][0] - other_cell[0], other.path[1][1] - other_cell[1])
                            else:
                                other_dir = (0, 0)
                            if abs(other_dir[0]) > 0 and abs(other_dir[1]) < 1e-6 and (cur_dir[0] * other_dir[0] < 0):
                                reverse_cell = (current_cell[0] - cur_dir[0], current_cell[1] - cur_dir[1])
                                if 0 <= reverse_cell[0] < ROWS and 0 <= reverse_cell[1] < COLS and MAP[reverse_cell[0]][reverse_cell[1]] != 1:
                                    occupied = any((int(round(o.pos[0])), int(round(o.pos[1]))) == reverse_cell for o in SIM_AGVS)
                                    if not occupied and reverse_cell not in RESERVED_CELLS:
                                        # 후진 경로: 현재 셀 -> reverse_cell -> 현재 셀 (대기)
                                        agv.path = [current_cell, reverse_cell, current_cell] + agv.path[1:]
                                        next_cell = agv.path[1]
                                        break
                    # (else 분기는 제거)

                # ④-1. 다음 셀 예약 및 충돌 회피 (낮은 id 우선 및 스왑 충돌 체크)
                wait_count = 0
                max_wait = 50  # 0.1초씩 약 5초 대기
                while True:
                    collision = False
                    for other in SIM_AGVS:
                        if other.id == agv.id:
                            continue
                        other_current = (int(round(other.pos[0])), int(round(other.pos[1])))
                        if other.path and len(other.path) > 1:
                            other_next = other.path[1]
                        else:
                            other_next = other_current
                        if next_cell == other_next and other.id < agv.id:
                            collision = True
                            break
                        if next_cell == other_current and other_next == current_cell:
                            collision = True
                            break
                        dist = ((other.pos[0] - next_cell[0])**2 + (other.pos[1] - next_cell[1])**2)**0.5
                        if dist < 0.2 and other.id < agv.id:
                            collision = True
                            break
                    if collision:
                        wait_count += 1
                        if wait_count > max_wait:
                            if agv.cargo == 0:
                                target = find_nearest_shelf(current_cell, agv.id)
                            else:
                                target = find_nearest_exit(current_cell, agv.id)
                            new_path = bfs_path(current_cell, target, env.now, cell_blocked, defaultdict(int))
                            if new_path and len(new_path) > 1:
                                agv.path = new_path
                                next_cell = agv.path[1]
                                wait_count = 0
                                continue
                        yield env.timeout(0.1)
                        continue
                    else:
                        break

                # ④-2. 예약 처리: 만약 다음 셀이 이미 다른 AGV에 의해 예약되어 있으면 대기
                while next_cell in RESERVED_CELLS and RESERVED_CELLS[next_cell] != agv.id:
                    yield env.timeout(0.1)
                RESERVED_CELLS[next_cell] = agv.id

                # ④-3. 이동 (부드러운 STEP_SIZE 단위 이동)
                current_pos = agv.pos
                dx = next_cell[0] - current_pos[0]
                dy = next_cell[1] - current_pos[1]
                distance = (dx**2 + dy**2)**0.5
                num_steps = int(distance / STEP_SIZE)
                for _ in range(num_steps):
                    current_pos = (
                        current_pos[0] + STEP_SIZE * dx / distance,
                        current_pos[1] + STEP_SIZE * dy / distance
                    )
                    yield env.timeout(STEP_SIZE)
                    agv.pos = current_pos
                    rounded_pos = (round(current_pos[0], 1), round(current_pos[1], 1))
                    stats.agv_stats[agv.id]["location_log"].append((env.now, rounded_pos))
                remaining = distance - num_steps * STEP_SIZE
                if remaining > 0:
                    current_pos = (
                        current_pos[0] + remaining * dx / distance,
                        current_pos[1] + remaining * dy / distance
                    )
                    yield env.timeout(remaining)
                    agv.pos = current_pos
                    rounded_pos = (round(current_pos[0], 1), round(current_pos[1], 1))
                    stats.agv_stats[agv.id]["location_log"].append((env.now, rounded_pos))
                # 이동 완료: 도착 처리 및 예약 해제
                agv.pos = (float(next_cell[0]), float(next_cell[1]))
                agv.arrival_time = env.now
                if next_cell in RESERVED_CELLS and RESERVED_CELLS[next_cell] == agv.id:
                    del RESERVED_CELLS[next_cell]
                agv.path.pop(0)
            else:
                yield env.timeout(0.1)

            # ⑤ 적재/하역 조건 처리 (실시간 대체 가능 장소 체크)
            current_int_cell = (int(round(agv.pos[0])), int(round(agv.pos[1])))
            if agv.cargo == 0 and current_int_cell in shelf_coords:
                available_shelf = find_nearest_shelf(current_int_cell, agv.id)
                if available_shelf != current_int_cell:
                    new_path = bfs_path(current_int_cell, available_shelf, env.now, cell_blocked, defaultdict(int))
                    if new_path and len(new_path) > 1:
                        agv.path = new_path
                    yield env.timeout(0.1)
                    continue
                yield env.process(do_pick(agv, env, stats, cell_blocked))
                target = find_nearest_exit(current_int_cell, agv.id)
                new_path = bfs_path(current_int_cell, target, env.now, cell_blocked, defaultdict(int))
                if new_path and len(new_path) > 1:
                    agv.path = new_path
                yield env.timeout(random.uniform(0.5, 1.5)) # 결과값을 유동적으로 적용 
            elif agv.cargo == 1 and current_int_cell in exit_coords:
                available_exit = find_nearest_exit(current_int_cell, agv.id)
                if available_exit != current_int_cell:
                    new_path = bfs_path(current_int_cell, available_exit, env.now, cell_blocked, defaultdict(int))
                    if new_path and len(new_path) > 1:
                        agv.path = new_path
                    yield env.timeout(0.1)
                    continue
                yield env.process(do_drop(agv, env, stats, cell_blocked))
                target = find_nearest_shelf(current_int_cell, agv.id)
                new_path = bfs_path(current_int_cell, target, env.now, cell_blocked, defaultdict(int))
                if new_path and len(new_path) > 1:
                    agv.path = new_path
                yield env.timeout(random.uniform(0.5, 1.5)) # 이동에 대안 변동성 부여
        # end while
    # end agv_process

    def record_stats(env, sim_duration, stats):
        while env.now < sim_duration:
            stats.delivered_record[int(env.now)] = stats.delivered_count
            yield env.timeout(1)

    def record_interval_stats(env, sim_duration, stats):
        t = CHECK_INTERVAL
        while t <= sim_duration:
            yield env.timeout(CHECK_INTERVAL)
            stats.delivered_history[t] = stats.delivered_count
            t += CHECK_INTERVAL

    def run_one_sim(agv_count, sim_duration, run_id=1, output_mode="live"):
        env = RealtimeEnvironment(factor=1)
        cell_blocked = {}
        stats = Stats()
        agvs = []
        start_row = 8
        start_cols = [0, 2, 4, 6, 1, 3, 5]
        for i in range(agv_count):
            pos = (start_row, start_cols[i % len(start_cols)])
            agv = AGV(i, pos)
            agvs.append(agv)
        for agv in agvs:
            env.process(agv_process(agv, env, stats, sim_duration, cell_blocked))
        env.process(record_stats(env, sim_duration, stats))
        env.process(record_interval_stats(env, sim_duration, stats))
        env.run(until=sim_duration)
        final_agv_stats = {}
        for agv_id, data in stats.agv_stats.items():
            count = data["count"]
            times = data["times"]
            avg_time = sum(times) / len(times) if times else 0
            final_agv_stats[agv_id] = {
                "count": count,
                "times": times,
                "avg_time": avg_time,
                "wait_times": data["wait_times"],
                "travel_times": data["travel_times"],
                "location_log": data["location_log"]
            }
        result = {
            "end_time": sim_duration,
            "delivered_count": stats.delivered_count,
            "delivered_history": stats.delivered_history,
            "delivered_record": dict(stats.delivered_record),
            "agv_stats": final_agv_stats
        }
        return result

    SIM_APP_RUNNING = False
    def run_simulation_task(agv_count, sim_duration):
        global SIM_RUNNING, SIM_ENV, SIM_STATS, SIM_AGVS, SIM_DURATION, SIM_FINISHED
        SIM_RUNNING = True
        SIM_FINISHED = False
        if SIM_ENV is not None and SIM_ENV.now >= sim_duration - 1:
            sim_duration = SIM_ENV.now + 3000
            global SIM_DURATION
            SIM_DURATION = sim_duration
        env = RealtimeEnvironment(factor=1)
        stats = Stats()
        agvs = []
        start_row = 8
        start_cols = [0, 2, 4, 6, 1, 3, 5]
        cell_blocked = {}
        for i in range(agv_count):
            pos = (start_row, start_cols[i % len(start_cols)])
            agv = AGV(i, pos)
            agvs.append(agv)
            env.process(agv_process(agv, env, stats, sim_duration, cell_blocked))
        env.process(record_stats(env, sim_duration, stats))
        env.process(record_interval_stats(env, sim_duration, stats))
        SIM_ENV = env
        SIM_STATS = stats
        SIM_AGVS = agvs
        env.run(until=sim_duration)
        SIM_RUNNING = False
        SIM_FINISHED = True
        print("시뮬레이션 종료")
        result = compute_simulation_result(stats, sim_duration, agv_count)
        socketio.emit('simulation_final', result)

    def run_simulation_task_analysis(agv_count, sim_duration):
        global SIM_RUNNING, SIM_ENV, SIM_STATS, SIM_AGVS, SIM_DURATION, SIM_FINISHED
        SIM_RUNNING = True
        SIM_FINISHED = False
        if SIM_ENV is not None and SIM_ENV.now >= sim_duration - 1:
            sim_duration = SIM_ENV.now + 3000
            global SIM_DURATION
            SIM_DURATION = sim_duration
        env = Environment()
        stats = Stats()
        agvs = []
        start_row = 8
        start_cols = [0, 2, 4, 6, 1, 3, 5]
        cell_blocked = {}
        for i in range(agv_count):
            pos = (start_row, start_cols[i % len(start_cols)])
            agv = AGV(i, pos)
            agvs.append(agv)
            env.process(agv_process(agv, env, stats, sim_duration, cell_blocked))
        env.process(record_stats(env, sim_duration, stats))
        env.process(record_interval_stats(env, sim_duration, stats))
        SIM_ENV = env
        SIM_STATS = stats
        SIM_AGVS = agvs
        env.run(until=sim_duration)
        SIM_RUNNING = False
        SIM_FINISHED = True
        print("시뮬레이션 종료")
        result = compute_simulation_result(stats, sim_duration, agv_count)
        socketio.emit('simulation_final', result)

    @socketio.on('connect')
    def handle_connect():
        print("클라이언트가 시뮬레이터에 연결되었습니다.")
        emit('status', {'message': 'Simulator connected'})

    @socketio.on('disconnect')
    def handle_disconnect():
        print("클라이언트 연결이 끊어졌습니다.")

    @socketio.on('ping')
    def handle_ping(data):
        emit('pong', {'timestamp': time.time()})

    @socketio.on('message')
    def handle_message(message):
        global SIM_PAUSED, SIM_RUNNING, is_paused
        try:
            data = json.loads(message) if isinstance(message, str) else message
            logger.info(f'Received message: {data}')
            if 'command' in data:
                command = data['command']
                if command == 'start':
                    if is_paused:
                        is_paused = False
                        resume_simulation()
                        return
                    global global_speed_factor
                    agv_count = int(data.get('agv_count', 3))
                    duration = int(data.get('duration', 3000))
                    speed_str = data.get('speed', "1")
                    if speed_str == "max":
                        global_speed_factor = 1.0
                    else:
                        global_speed_factor = float(speed_str)
                        if global_speed_factor <= 0:
                            socketio.emit('message', {'error': 'speed must be positive or "max"'})
                            return
                    if SIM_RUNNING:
                        socketio.emit('message', {'error': 'Simulation is already running'})
                        return
                    SIM_PAUSED = False
                    socketio.start_background_task(run_simulation_task, agv_count, duration)
                elif command == 'stop':
                    pause_simulation()
                    is_paused = True
                elif command == 'analyze':
                    agv_count = int(data.get('agv_count', 3))
                    duration = int(data.get('duration', 3000))
                    speed_str = data.get('speed', "1")
                    if speed_str == "max":
                        global_speed_factor = 1.0
                    else:
                        global_speed_factor = float(speed_str)
                        if global_speed_factor <= 0:
                            pause_simulation()
                            is_paused = True
                            return
                    if SIM_RUNNING:
                        socketio.emit('message', {'error': 'Simulation is already running'})
                        return
                    socketio.start_background_task(run_simulation_task_analysis, agv_count, duration)
            if 'speed' in data:
                try:
                    new_speed = float(data['speed'])
                    if new_speed <= 0:
                        socketio.emit('message', {'error': 'speed must be positive'})
                        return
                    global_speed_factor = 1.0 / new_speed
                    restart_simulation_with_current_state()
                except Exception as e:
                    socketio.emit('message', {'error': str(e)})
            if 'agv_count' in data:
                try:
                    new_count = int(data['agv_count'])
                    if new_count <= 0:
                        socketio.emit('message', {'error': 'AGV count must be positive'})
                        return
                except ValueError as e:
                    socketio.emit('message', {'error': str(e)})
            if data.get('type') == 'ping':
                socketio.emit('message', {'type': 'pong', 'timestamp': time.time()})
        except Exception as e:
            logger.error(f'Error processing message: {str(e)}')
            socketio.emit('message', {'error': str(e)})

    @socketio.on('simulate_stream')
    def handle_simulate_stream(data):
        global global_speed_factor, SIM_RUNNING, SIM_PAUSED
        try:
            agv_count = int(data.get('agv_count', 3))
            duration = int(data.get('duration', 3000))
            speed_str = data.get('initial_speed', "1")
            if speed_str == "max":
                global_speed_factor = 1.0
            else:
                global_speed_factor = float(speed_str)
                if global_speed_factor <= 0:
                    emit('error', {'message': 'speed must be positive or "max"'})
                    return
            if SIM_RUNNING:
                emit('error', {'message': 'Simulation is already running'})
                return
            SIM_PAUSED = False
            socketio.start_background_task(run_simulation_task, agv_count, duration)
            emit('simulation_status', {'status': 'running'})
        except Exception as e:
            emit('error', {'message': str(e)})

    @socketio.on('simulate_final')
    def handle_simulate_final(data):
        global global_speed_factor
        try:
            agv_count = int(data.get('agv_count', 3))
            duration = int(data.get('duration', 3000))
            initial_speed_str = data.get('initial_speed', "1")
            output_mode = data.get('output', "final")
            if initial_speed_str == "max":
                global_speed_factor = 1.0
            else:
                global_speed_factor = float(initial_speed_str)
                if global_speed_factor <= 0:
                    emit('error', {'message': 'speed must be positive or "max"'})
                    return
            result = run_one_sim(agv_count, duration, output_mode=output_mode)
            if output_mode == "final":
                for agv in result["agv_stats"].values():
                    agv["location_log"] = []
            emit('simulation_final', result)
        except Exception as e:
            emit('error', {'message': str(e)})

    @socketio.on('update_speed')
    def handle_update_speed(data):
        global global_speed_factor
        try:
            new_speed = 1.0 / float(data.get('speed'))
            if new_speed <= 0:
                emit('error', {'message': 'speed must be positive'})
                return
            global_speed_factor = new_speed
            restart_simulation_with_current_state()
            emit('status', {'message': f'Speed updated to {new_speed}'})
            print(f"[update_speed] Global speed factor updated to: {new_speed}")
        except Exception as e:
            emit('error', {'message': str(e)})

    @app.route('/health')
    def health_check():
        return jsonify({"status": "ok"})

    def pause_simulation():
        global SIM_RUNNING, SIM_ENV, SIM_STATS, SIM_AGVS, SIM_DURATION, global_speed_factor, delivered_count_paused, current_time_paused, current_positions, current_cargos, current_paths
        if not SIM_RUNNING:
            return
        current_time_paused = SIM_ENV.now
        current_positions = []
        current_cargos = []
        current_paths = []
        for agv in SIM_AGVS:
            current_positions.append(agv.pos)
            current_cargos.append(agv.cargo)
            current_paths.append(agv.path.copy() if agv.path else [])
        delivered_count_paused = SIM_STATS.delivered_count
        SIM_RUNNING = False

    def resume_simulation():
        global SIM_RUNNING, SIM_ENV, SIM_STATS, SIM_AGVS, SIM_DURATION, global_speed_factor, delivered_count_paused, current_time_paused
        env = RealtimeEnvironment(factor=global_speed_factor, initial_time=current_time_paused)
        stats = Stats()
        stats.delivered_count = delivered_count_paused
        agvs = []
        cell_blocked = {}
        for i, (pos, cargo, path) in enumerate(zip(current_positions, current_cargos, current_paths)):
            agv = AGV(i, pos)
            agv.cargo = cargo
            agv.path = path
            agvs.append(agv)
            env.process(agv_process(agv, env, stats, SIM_DURATION, cell_blocked))
        env.process(record_stats(env, SIM_DURATION, stats))
        env.process(record_interval_stats(env, SIM_DURATION, stats))
        if env.now >= SIM_DURATION - 1:
            SIM_DURATION = env.now + 3000
        SIM_ENV = env
        SIM_STATS = stats
        SIM_AGVS = agvs
        socketio.start_background_task(run_continued_simulation, env, SIM_DURATION, len(agvs))

    @socketio.on('pause_simulation')
    def handle_pause():
        try:
            pause_simulation()
            emit('simulation_status', {'status': 'paused'})
            emit('status', {'message': 'Simulation paused'})
        except Exception as e:
            emit('error', {'message': str(e)})

    @socketio.on('resume_simulation')
    def handle_resume():
        try:
            resume_simulation()
            emit('simulation_status', {'status': 'running'})
            emit('status', {'message': 'Simulation resumed'})
        except Exception as e:
            emit('error', {'message': str(e)})

    def update_loop_task():
        while True:
            if not SIM_RUNNING:
                eventlet.sleep(1.0)
                continue
            current_time = 0
            delivered_count = 0
            agv_positions = {}
            cnt = 0
            state = []
            if SIM_ENV is not None and SIM_STATS is not None and SIM_AGVS is not None:
                current_time = round(SIM_ENV.now, 2)
                delivered_count = SIM_STATS.delivered_count
                for agv in SIM_AGVS:
                    cnt += 1
                    state.append({'agv_id': agv.id, 'location_x': agv.pos[0], 'location_y': agv.pos[1]})
                    agv_positions[agv.id] = (round(agv.pos[0], 1), round(agv.pos[1], 1))
            positions = {
                'sim_time': current_time,
                'agv_positions': agv_positions,
                'delivered_count': delivered_count,
                'paused': SIM_PAUSED
            }
            socketio.emit('message', {'agv_count': cnt, 'agvs': state})
            eventlet.sleep(UPDATE_INTERVAL)

    socketio.start_background_task(update_loop_task)
    return app, socketio

def run_server(port):
    try:
        multiprocessing.set_start_method('spawn')
    except RuntimeError:
        pass
    app, socketio = create_app(port)
    print(f"Starting server on port {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False)

def start_multi_server():
    # 4개의 포트에 대한 값값
    ports = [5001, 5002, 5003, 5004]
    processes = []
    try:
        for port in ports:
            process = multiprocessing.Process(
                target=run_server,
                args=(port,)
            )
            process.start()
            processes.append(process)
            print(f"Started server process on port {port}")
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        print("\nShutting down servers...")
        for process in processes:
            process.terminate()
        for process in processes:
            process.join()
        print("All servers shut down successfully")
        sys.exit(0)

if __name__ == '__main__':
    multiprocessing.set_start_method('spawn')
    start_multi_server()
