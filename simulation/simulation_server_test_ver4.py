import eventlet
eventlet.monkey_patch()
import multiprocessing
import sys
import json
import time
import random
import statistics
import heapq
from simpy.rt import RealtimeEnvironment
from simpy import Environment
from collections import defaultdict
from flask import Flask, request, jsonify, Blueprint
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import logging
import os
logger = logging.getLogger(__name__)

global_speed_factor = 1.0
SIM_RUNNING = False
SIM_DURATION = 3000
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
RESERVED_CELLS = {}
TARGET_RESERVATIONS = {}
REPEAT_RUNS = 15
WARMUP_PERIOD = 30
CHECK_INTERVAL = 3000
MOVE_RATE = 1.0
STEP_SIZE = 0.01

# 15x15 불규칙 맵
MAP = [
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0],
    [0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1, 0],
    [0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 1, 1, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0],
    [0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2],
]
ROWS = len(MAP)
COLS = len(MAP[0])

# 출구 구역: row0의 모든 셀
exit_coords = [(0, c) for c in range(COLS) if MAP[0][c] == 2]

# 적재(선반) 구역: 맵 내부의 "들어간" 영역 (예: (3,3), (5,4), (3,12), (9,12), (8,6))
shelf_coords = [(3,3), (5,4), (3,12), (9,12), (8,6)]

def is_in_corridor(cell):
    row, col = cell
    return (2 <= row <= 4) and (2 <= col <= 4)

def is_cell_busy(cell, required_cargo):
    for agv in SIM_AGVS:
        if (int(round(agv.pos[0])), int(round(agv.pos[1]))) == cell:
            if agv.cargo == required_cargo:
                return True
    return False

def manhattan(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

def a_star_path(start, goal, current_time, cell_blocked, congestion_count, current_agv_id=None):
    if start == goal:
        return [start]
    open_set = []
    heapq.heappush(open_set, (manhattan(start, goal), 0, start))
    came_from = {start: None}
    cost_so_far = {start: 0}
    while open_set:
        priority, current_cost, current = heapq.heappop(open_set)
        if current == goal:
            path = []
            while current is not None:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return path
        for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
            neighbor = (current[0]+dr, current[1]+dc)
            if not (0 <= neighbor[0] < ROWS and 0 <= neighbor[1] < COLS):
                continue
            if MAP[neighbor[0]][neighbor[1]] == 1:
                continue
            if neighbor in cell_blocked and cell_blocked[neighbor] > current_time:
                congestion_count[neighbor] += 1
                continue
            if neighbor in RESERVED_CELLS and current_agv_id is not None and RESERVED_CELLS[neighbor] != current_agv_id:
                continue
            new_cost = cost_so_far[current] + 1 + 0.1 * congestion_count.get(neighbor, 0)
            if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                cost_so_far[neighbor] = new_cost
                priority = new_cost + manhattan(neighbor, goal)
                heapq.heappush(open_set, (priority, new_cost, neighbor))
                came_from[neighbor] = current
    return None

# 시작지점: row 11, 열은 [0, 3, 6, 9, 12] (5대 기준)
def get_start_position(i):
    start_row = 11
    start_cols = [0, 3, 6, 9, 12]
    col = start_cols[i % len(start_cols)]
    return (start_row, col)

# 목적지 선정 함수 – 후보군에서 이미 낮은 ID가 예약한 좌표는 제외
def find_nearest_exit(pos, current_agv_id=None):
    if pos in exit_coords:
        return pos
    candidates = []
    for ex in exit_coords:
        if is_cell_busy(ex, 1):
            continue
        if ex in TARGET_RESERVATIONS:
            reserved_id = TARGET_RESERVATIONS[ex]
            # 이미 낮은 id가 예약한 경우 후보에서 제외
            if reserved_id < current_agv_id:
                continue
        candidates.append(ex)
    if candidates:
        chosen = min(candidates, key=lambda e: abs(pos[0]-e[0]) + abs(pos[1]-e[1]))
        TARGET_RESERVATIONS[chosen] = current_agv_id
        return chosen
    else:
        chosen = min(exit_coords, key=lambda e: abs(pos[0]-e[0]) + abs(pos[1]-e[1]))
        # 재할당: 낮은 id가 있다면 갱신
        TARGET_RESERVATIONS[chosen] = current_agv_id
        return chosen

def find_nearest_shelf(pos, current_agv_id=None):
    if pos in shelf_coords:
        return pos
    candidates = []
    for sh in shelf_coords:
        if is_cell_busy(sh, 0):
            continue
        if sh in TARGET_RESERVATIONS:
            reserved_id = TARGET_RESERVATIONS[sh]
            if reserved_id < current_agv_id:
                continue
        candidates.append(sh)
    if candidates:
        chosen = min(candidates, key=lambda s: abs(pos[0]-s[0]) + abs(pos[1]-s[1]))
        TARGET_RESERVATIONS[chosen] = current_agv_id
        return chosen
    else:
        chosen = min(shelf_coords, key=lambda s: abs(pos[0]-s[0]) + abs(pos[1]-s[1]))
        TARGET_RESERVATIONS[chosen] = current_agv_id
        return chosen

def create_app(port):
    app = Flask(__name__)
    sim_prefix = f"/sim{port - 2024}"
    sim_bp = Blueprint('sim', __name__, url_prefix=sim_prefix)

    @sim_bp.route('/')
    def index():
        return f"Simulation running on port {port} at {sim_prefix}"

    app.register_blueprint(sim_bp)
    # CORS(app)

    socketio = SocketIO(app, cors_allowed_origins=[os.environ.get('FRONTEND_URL')],
                        path=sim_prefix,
                        async_mode='eventlet',
                        logger=True,
                        engineio_logger=True,
                        ping_timeout=5000,
                        ping_interval=2500)
    bfs_path = a_star_path

    class AGV:
        def __init__(self, agv_id, start_pos):
            self.id = agv_id
            self.start_pos = (float(start_pos[0]), float(start_pos[1]))
            self.pos = (float(start_pos[0]), float(start_pos[1]))
            self.path = []
            self.cargo = 0
            self.pickup_time = None
            self.arrival_time = 0
            self.last_pos = self.pos
            self.stuck_steps = 0

    class Stats:
        def __init__(self):
            self.delivered_count = 0
            self.delivered_record = defaultdict(int)
            self.delivered_history = {}
            self.agv_stats = defaultdict(lambda: {"count": 0, "times": [], "wait_times": [], "travel_times": [], "location_log": []})

    def compute_simulation_result(stats, sim_duration, agv_count):
        final_agv_stats = {}
        for agv_id, data in stats.agv_stats.items():
            count = data["count"]
            times = data["times"]
            avg_time = sum(times) / len(times) if times else 0
            utilization = sum(times) / sim_duration if sim_duration > 0 else 0
            final_agv_stats[agv_id] = {"count": count, "times": times, "avg_time": avg_time,
                                       "wait_times": data["wait_times"], "travel_times": data["travel_times"],
                                       "location_log": data["location_log"], "utilization": utilization}
        res = {"end_time": sim_duration, "delivered_count": stats.delivered_count,
               "delivered_history": stats.delivered_history, "delivered_record": dict(stats.delivered_record),
               "agv_stats": final_agv_stats, "agv_count": agv_count}
        delivered_counts = res["delivered_count"]
        throughput = delivered_counts / sim_duration * 3600
        delivered_per_agv = delivered_counts / agv_count
        result = {"throughput_per_hour": throughput, "delivered_per_agv": delivered_per_agv,
                  "avg_cycle": statistics.mean([d["avg_time"] for d in final_agv_stats.values()]) if final_agv_stats else 0,
                  "avg_wait": statistics.mean([statistics.mean(d["wait_times"]) if d["wait_times"] else 0 for d in final_agv_stats.values()]),
                  "avg_travel": statistics.mean([statistics.mean(d["travel_times"]) if d["travel_times"] else 0 for d in final_agv_stats.values()])}
        res.update(result)
        return res

    def compute_single_run_result(stats, sim_duration, agv_count):
        base = compute_simulation_result(stats, sim_duration, agv_count)
        return {"end_time": base["end_time"], "delivered_count": base["delivered_count"],
                "throughput_per_hour": base["throughput_per_hour"], "delivered_per_agv": base["delivered_per_agv"],
                "avg_cycle": base["avg_cycle"], "avg_wait": base["avg_wait"],
                "avg_travel": base["avg_travel"], "analysis_type": "single"}

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
        saved_positions = [agv.pos for agv in SIM_AGVS]
        saved_cargos = [agv.cargo for agv in SIM_AGVS]
        saved_paths = [agv.path.copy() for agv in SIM_AGVS]
        delivered_count = SIM_STATS.delivered_count
        SIM_RUNNING = False
        env = RealtimeEnvironment(factor=global_speed_factor, initial_time=current_time)
        stats = Stats()
        stats.delivered_count = delivered_count
        new_agvs = []
        cell_blocked = {}
        for i, (pos, cargo, path) in enumerate(zip(saved_positions, saved_cargos, saved_paths)):
            agv = AGV(i, pos)
            agv.cargo = cargo
            agv.path = path
            new_agvs.append(agv)
            env.process(agv_process(agv, env, stats, SIM_DURATION, cell_blocked))
        env.process(record_stats(env, SIM_DURATION, stats))
        env.process(record_interval_stats(env, SIM_DURATION, stats))
        if env.now >= SIM_DURATION - 1:
            SIM_DURATION = env.now + 3000
        SIM_ENV = env
        SIM_STATS = stats
        SIM_AGVS = new_agvs
        socketio.start_background_task(run_continued_simulation, env, SIM_DURATION, len(new_agvs))

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
            # 동적 목적지 재할당: 만약 이미 정해진 경로의 최종 목적지(dest)가 TARGET_RESERVATIONS에 등록되어 있고, 
            # 그 예약이 자신보다 낮은(우선순위 높은) AGV에 의한 것이라면 재할당
            current_cell = (int(round(agv.pos[0])), int(round(agv.pos[1])))
            if agv.path:
                dest = agv.path[-1]
                if dest in TARGET_RESERVATIONS:
                    if TARGET_RESERVATIONS[dest] < agv.id:
                        # 다른 AGV(우선순위 높음)가 해당 목적지를 예약한 상태이므로 재할당
                        if agv.cargo == 0:
                            new_target = find_nearest_shelf(current_cell, agv.id)
                        else:
                            new_target = find_nearest_exit(current_cell, agv.id)
                        new_path = bfs_path(current_cell, new_target, env.now, cell_blocked, defaultdict(int), current_agv_id=agv.id)
                        if new_path and len(new_path) > 1:
                            agv.path = new_path
                        else:
                            agv.path = []
                    else:
                        TARGET_RESERVATIONS[dest] = agv.id

            if abs(agv.pos[0] - agv.last_pos[0]) < 0.001 and abs(agv.pos[1] - agv.last_pos[1]) < 0.001:
                agv.stuck_steps += 1
            else:
                agv.stuck_steps = 0
            agv.last_pos = agv.pos
            if agv.stuck_steps > 50:
                agv.path = []
                current_cell = (int(round(agv.pos[0])), int(round(agv.pos[1])))
                RESERVED_CELLS[current_cell] = agv.id
            current_cell = (int(round(agv.pos[0])), int(round(agv.pos[1])))
            # 하역: cargo==1이면 출구로 이동
            if agv.cargo == 1 and current_cell in exit_coords:
                available_exit = find_nearest_exit(current_cell, agv.id)
                if available_exit != current_cell:
                    new_path = bfs_path(current_cell, available_exit, env.now, cell_blocked, defaultdict(int), current_agv_id=agv.id)
                    if new_path and len(new_path) > 1:
                        agv.path = new_path
                    yield env.timeout(0.1)
                    continue
            # 적재: cargo==0이고 현재 위치가 적재 구역
            if agv.cargo == 0 and current_cell in shelf_coords:
                busy = any(other.id != agv.id and (int(round(other.pos[0])), int(round(other.pos[1]))) == current_cell and other.cargo == 0 for other in SIM_AGVS)
                if busy:
                    new_target = find_nearest_shelf(current_cell, agv.id)
                    if new_target != current_cell:
                        new_path = bfs_path(current_cell, new_target, env.now, cell_blocked, defaultdict(int), current_agv_id=agv.id)
                        if new_path and len(new_path) > 1:
                            agv.path = new_path
                        yield env.timeout(0.1)
                        continue
                yield env.process(do_pick(agv, env, stats, cell_blocked))
                target = find_nearest_exit(current_cell, agv.id)
                new_path = bfs_path(current_cell, target, env.now, cell_blocked, defaultdict(int), current_agv_id=agv.id)
                if new_path and len(new_path) > 1:
                    agv.path = new_path
                yield env.timeout(random.uniform(0.5, 1.5))
                continue
            if not agv.path or len(agv.path) <= 1:
                if agv.cargo == 0:
                    target = find_nearest_shelf(current_cell, agv.id)
                    path = bfs_path(current_cell, target, env.now, cell_blocked, defaultdict(int), current_agv_id=agv.id)
                    agv.path = path if path is not None else []
                else:
                    target = find_nearest_exit(current_cell, agv.id)
                    path = bfs_path(current_cell, target, env.now, cell_blocked, defaultdict(int), current_agv_id=agv.id)
                    agv.path = path if path is not None else []
            if len(agv.path) > 1:
                next_cell = agv.path[1]
                occupied_cells = {(int(round(other.pos[0])), int(round(other.pos[1]))) for other in SIM_AGVS if other.id != agv.id}
                if next_cell in occupied_cells or (next_cell in RESERVED_CELLS and RESERVED_CELLS[next_cell] != agv.id):
                    yield env.timeout(random.uniform(0.1, 0.3))
                    continue
                if next_cell not in RESERVED_CELLS:
                    RESERVED_CELLS[next_cell] = agv.id
                current_pos = agv.pos
                dx = next_cell[0] - current_pos[0]
                dy = next_cell[1] - current_pos[1]
                distance = (dx**2 + dy**2)**0.5
                num_steps = int(distance / STEP_SIZE)
                for _ in range(num_steps):
                    current_pos = (current_pos[0] + STEP_SIZE * dx / distance, current_pos[1] + STEP_SIZE * dy / distance)
                    yield env.timeout(STEP_SIZE)
                    agv.pos = current_pos
                remaining = distance - num_steps * STEP_SIZE
                if remaining > 0:
                    current_pos = (current_pos[0] + remaining * dx / distance, current_pos[1] + remaining * dy / distance)
                    yield env.timeout(remaining)
                    agv.pos = current_pos
                agv.pos = (float(next_cell[0]), float(next_cell[1]))
                agv.arrival_time = env.now
                if next_cell in RESERVED_CELLS and RESERVED_CELLS[next_cell] == agv.id:
                    del RESERVED_CELLS[next_cell]
                agv.path.pop(0)
            else:
                yield env.timeout(0.1)
            current_int_cell = (int(round(agv.pos[0])), int(round(agv.pos[1])))
            if agv.cargo == 0 and current_int_cell in shelf_coords:
                busy = any(other.id != agv.id and (int(round(other.pos[0])), int(round(other.pos[1]))) == current_int_cell and other.cargo == 0 for other in SIM_AGVS)
                if busy:
                    new_target = find_nearest_shelf(current_int_cell, agv.id)
                    if new_target != current_int_cell:
                        new_path = bfs_path(current_int_cell, new_target, env.now, cell_blocked, defaultdict(int), current_agv_id=agv.id)
                        if new_path and len(new_path) > 1:
                            agv.path = new_path
                        yield env.timeout(0.1)
                        continue
                yield env.process(do_pick(agv, env, stats, cell_blocked))
                target = find_nearest_exit(current_int_cell, agv.id)
                new_path = bfs_path(current_int_cell, target, env.now, cell_blocked, defaultdict(int), current_agv_id=agv.id)
                if new_path and len(new_path) > 1:
                    agv.path = new_path
                yield env.timeout(random.uniform(0.5, 1.5))
            elif agv.cargo == 1 and current_int_cell in exit_coords:
                available_exit = find_nearest_exit(current_int_cell, agv.id)
                if available_exit != current_int_cell:
                    new_path = bfs_path(current_int_cell, available_exit, env.now, cell_blocked, defaultdict(int), current_agv_id=agv.id)
                    if new_path and len(new_path) > 1:
                        agv.path = new_path
                    yield env.timeout(0.1)
                    continue
                yield env.process(do_drop(agv, env, stats, cell_blocked))
                target = find_nearest_shelf(current_int_cell, agv.id)
                new_path = bfs_path(current_int_cell, target, env.now, cell_blocked, defaultdict(int), current_agv_id=agv.id)
                if new_path and len(new_path) > 1:
                    agv.path = new_path
                yield env.timeout(random.uniform(0.5, 1.5))

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
        for i in range(agv_count):
            pos = get_start_position(i)
            agv = AGV(i, pos)
            agvs.append(agv)
            env.process(agv_process(agv, env, stats, sim_duration, {}))
        env.process(record_stats(env, sim_duration, stats))
        env.process(record_interval_stats(env, sim_duration, stats))
        SIM_ENV = env
        SIM_STATS = stats
        SIM_AGVS = agvs
        env.run(until=sim_duration)
        SIM_RUNNING = False
        SIM_FINISHED = True
        print("시뮬레이션 종료")
        result = compute_single_run_result(stats, sim_duration, agv_count)
        socketio.emit('simulation_final', result)

    def run_one_sim_analysis(agv_count, sim_duration):
        env = Environment()
        stats = Stats()
        agvs = []
        for i in range(agv_count):
            pos = get_start_position(i)
            agv = AGV(i, pos)
            agvs.append(agv)
        for agv in agvs:
            env.process(agv_process(agv, env, stats, sim_duration, {}))
        env.process(record_stats(env, sim_duration, stats))
        env.process(record_interval_stats(env, sim_duration, stats))
        env.run(until=sim_duration)
        result = compute_simulation_result(stats, sim_duration, agv_count)
        return result

    def run_multiple_sim_analysis(agv_count, sim_duration, repeat_runs=REPEAT_RUNS):
        results = []
        for i in range(repeat_runs):
            res = run_one_sim_analysis(agv_count, sim_duration)
            results.append(res)
        avg_throughput = statistics.mean([r["throughput_per_hour"] for r in results]) if results else 0
        std_throughput = statistics.stdev([r["throughput_per_hour"] for r in results]) if len(results) > 1 else 0
        avg_delivered = statistics.mean([r["delivered_per_agv"] for r in results]) if results else 0
        std_delivered = statistics.stdev([r["delivered_per_agv"] for r in results]) if len(results) > 1 else 0
        avg_cycle = statistics.mean([r["avg_cycle"] for r in results]) if results else 0
        avg_wait = statistics.mean([r["avg_wait"] for r in results]) if results else 0
        avg_travel = statistics.mean([r["avg_travel"] for r in results]) if results else 0
        util_list = []
        for r in results:
            if "agv_stats" in r and r["agv_stats"]:
                vals = [data.get("utilization", 0) for data in r["agv_stats"].values()]
                util_list.append(statistics.mean(vals))
        avg_util = statistics.mean(util_list) if util_list else 0
        avg_result = {"repeat_runs": repeat_runs, "agv_count": agv_count, "throughput_per_hour": avg_throughput,
                      "std_throughput_per_hour": std_throughput, "delivered_per_agv": avg_delivered,
                      "std_delivered_per_agv": std_delivered, "avg_cycle": avg_cycle, "avg_wait": avg_wait,
                      "avg_travel": avg_travel, "avg_utilization": avg_util, "analysis_type": "deep"}
        return avg_result

    def analysis_worker(agv_count, sim_duration, repeat_runs, output_queue):
        res = run_multiple_sim_analysis(agv_count, sim_duration, repeat_runs=repeat_runs)
        output_queue.put(res)

    def run_simulation_task_analysis(agv_count, sim_duration):
        from multiprocessing import Process, Queue
        q = Queue()
        p = Process(target=analysis_worker, args=(agv_count, sim_duration, REPEAT_RUNS, q))
        p.start()
        result = None
        while result is None:
            if not q.empty():
                result = q.get()
            else:
                eventlet.sleep(0.1)
        p.join()
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
        global SIM_PAUSED, SIM_RUNNING, is_paused, global_speed_factor
        try:
            data = json.loads(message) if isinstance(message, str) else message
            logger.info(f"Received message: {data}")
            if 'command' in data:
                command = data['command']
                if command == 'start':
                    if is_paused:
                        is_paused = False
                        resume_simulation()
                        return
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
            logger.error(f"Error processing message: {str(e)}")
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
            result = run_multiple_sim_analysis(agv_count, duration, repeat_runs=REPEAT_RUNS)
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
        global SIM_RUNNING, SIM_ENV, SIM_STATS, SIM_AGVS, SIM_DURATION, delivered_count_paused, current_time_paused, current_positions, current_cargos, current_paths
        if not SIM_RUNNING:
            return
        current_time_paused = SIM_ENV.now
        current_positions.clear()
        current_cargos.clear()
        current_paths.clear()
        for agv in SIM_AGVS:
            current_positions.append(agv.pos)
            current_cargos.append(agv.cargo)
            current_paths.append(agv.path.copy() if agv.path else [])
        delivered_count_paused = SIM_STATS.delivered_count
        SIM_RUNNING = False

    def resume_simulation():
        global SIM_RUNNING, SIM_ENV, SIM_STATS, SIM_AGVS, SIM_DURATION, delivered_count_paused, current_time_paused
        env = RealtimeEnvironment(factor=global_speed_factor, initial_time=current_time_paused)
        stats = Stats()
        stats.delivered_count = delivered_count_paused
        new_agvs = []
        cell_blocked = {}
        for i, (pos, cargo, path) in enumerate(zip(current_positions, current_cargos, current_paths)):
            agv = AGV(i, pos)
            agv.cargo = cargo
            agv.path = path
            new_agvs.append(agv)
            env.process(agv_process(agv, env, stats, SIM_DURATION, cell_blocked))
        env.process(record_stats(env, SIM_DURATION, stats))
        env.process(record_interval_stats(env, SIM_DURATION, stats))
        if env.now >= SIM_DURATION - 1:
            SIM_DURATION = env.now + 3000
        SIM_ENV = env
        SIM_STATS = stats
        SIM_AGVS = new_agvs
        socketio.start_background_task(run_continued_simulation, env, SIM_DURATION, len(new_agvs))

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
                if current_positions:
                    state = [{'agv_id': i, 'location_x': pos[0], 'location_y': pos[1]} for i, pos in enumerate(current_positions)]
                    socketio.emit('message', {'agv_count': len(current_positions), 'agvs': state})
                eventlet.sleep(UPDATE_INTERVAL)
                continue
            current_time = round(SIM_ENV.now, 2) if SIM_ENV else 0
            delivered_count = SIM_STATS.delivered_count if SIM_STATS else 0
            state = []
            for agv in SIM_AGVS:
                state.append({'agv_id': agv.id, 'location_x': agv.pos[0], 'location_y': agv.pos[1]})
            socketio.emit('message', {'agv_count': len(SIM_AGVS), 'agvs': state})
            eventlet.sleep(UPDATE_INTERVAL)

    socketio.start_background_task(update_loop_task)
    return app, socketio

def run_server(port):
    try:
        multiprocessing.set_start_method('spawn')
    except RuntimeError:
        pass
    app, socketio = create_app(port)
    # 포트 번호에 따라 URL 접두사가 결정됩니다.
    sim_prefix = f"/sim{port - 2024}"
    print(f"Starting server on port {port} with URL prefix: {sim_prefix}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False)

def start_multi_server():
    ports = [2025, 2026, 2027, 2028]
    processes = []
    try:
        for port in ports:
            process = multiprocessing.Process(target=run_server, args=(port,))
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
