import eventlet
eventlet.monkey_patch()

import json
import time
import random
import statistics
import simpy
from collections import deque, defaultdict

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit

# -----------------------------------------
# 전역 설정 및 변수
# -----------------------------------------
global_speed_factor = 1.0
SIM_RUNNING = False
SIM_DURATION = 0
SIM_ENV = None
SIM_STATS = None
SIM_AGVS = []

UPDATE_INTERVAL = 0.1
REPEAT_RUNS = 15
WARMUP_PERIOD = 30
CHECK_INTERVAL = 3000
STEP_SIZE = 0.01

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

# -----------------------------------------
# Flask 및 SocketIO 인스턴스를 먼저 선언
# -----------------------------------------
app = Flask(__name__)
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',
    ping_timeout=5000,
    ping_interval=2500
)

# -----------------------------------------
# BFS 경로, 클래스, 함수 등
# -----------------------------------------
def controlled_timeout(env, duration):
    yield env.timeout(duration / global_speed_factor)
    time.sleep(duration / global_speed_factor)

def bfs_path(start, goal, current_time, cell_blocked, congestion_count):
    # ... (이전 코드와 동일)
    if start == goal:
        return [start]
    visited = {start: None}
    queue = deque([start])
    while queue:
        r, c = queue.popleft()
        for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
            nr, nc = r+dr, c+dc
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

def find_nearest_exit(pos):
    # ... (이전 코드 동일)
    return min(exit_coords, key=lambda e: abs(pos[0]-e[0]) + abs(pos[1]-e[1]))

class AGV:
    # ... (이전 코드 동일)
    def __init__(self, agv_id, start_pos):
        self.id = agv_id
        self.start_pos = (float(start_pos[0]), float(start_pos[1]))
        self.pos = (float(start_pos[0]), float(start_pos[1]))
        self.path = []
        self.cargo = 0
        self.pickup_time = None

class Stats:
    # ... (이전 코드 동일)
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

def do_pick(agv, env, stats, cell_blocked):
    # ... (이전 코드 동일)
    now = env.now
    cell_blocked[agv.pos] = now + 10
    yield from controlled_timeout(env, 10)
    agv.cargo = 1
    if now >= WARMUP_PERIOD:
        agv.pickup_time = now
    stats.agv_stats[agv.id]["count"] += 1

def do_drop(agv, env, stats, cell_blocked):
    # ... (이전 코드 동일)
    start_drop = env.now
    cell_blocked[agv.pos] = start_drop + 10
    yield from controlled_timeout(env, 10)
    drop_finish = env.now
    if agv.pickup_time is not None:
        duration = drop_finish - agv.pickup_time
        stats.agv_stats[agv.id]["times"].append(duration)
        agv.pickup_time = None
    agv.cargo = 0
    stats.delivered_count += 1

def agv_process(agv, env, stats, sim_duration, cell_blocked):
    # ... (이전 코드 동일: effective_speed, STEP_SIZE 등)
    while env.now < sim_duration / global_speed_factor:
        if not agv.path or len(agv.path) <= 1:
            # 경로 설정
            if agv.cargo == 0:
                preferred = shelf_coords[agv.id % len(shelf_coords)]
                target = preferred if random.random() < 0.5 else random.choice(shelf_coords)
                path = bfs_path((int(agv.pos[0]), int(agv.pos[1])), target, env.now, cell_blocked, defaultdict(int))
                agv.path = path if path else []
            else:
                target = find_nearest_exit((int(agv.pos[0]), int(agv.pos[1])))
                path = bfs_path((int(agv.pos[0]), int(agv.pos[1])), target, env.now, cell_blocked, defaultdict(int))
                agv.path = path if path else []

        if len(agv.path) > 1:
            next_cell = agv.path[1]
            start_pos = agv.pos
            target_pos = (float(next_cell[0]), float(next_cell[1]))
            distance = ((target_pos[0]-start_pos[0])**2 + (target_pos[1]-start_pos[1])**2)**0.5
            effective_speed = 1 * global_speed_factor
            T_cell = distance / effective_speed
            num_steps = max(1, int(T_cell / STEP_SIZE))
            for i in range(num_steps):
                fraction = (i+1)/num_steps
                new_pos = (start_pos[0] + fraction*(target_pos[0]-start_pos[0]),
                           start_pos[1] + fraction*(target_pos[1]-start_pos[1]))
                yield from controlled_timeout(env, STEP_SIZE)
                agv.pos = new_pos
                stats.agv_stats[agv.id]["location_log"].append((env.now * global_speed_factor,
                                                                (round(new_pos[0],1), round(new_pos[1],1))))
            agv.pos = target_pos
            agv.path.pop(0)
        else:
            yield from controlled_timeout(env, 0.1)

        if agv.pos in shelf_coords and agv.cargo == 0:
            yield env.process(do_pick(agv, env, stats, cell_blocked))
            agv.path = []
            yield from controlled_timeout(env, random.uniform(0.5,1.5))
        elif agv.pos in exit_coords and agv.cargo == 1:
            yield env.process(do_drop(agv, env, stats, cell_blocked))
            agv.path = []
            yield from controlled_timeout(env, random.uniform(0.5,1.5))

def record_stats(env, sim_duration, stats):
    while env.now < sim_duration / global_speed_factor:
        reported_time = int(env.now * global_speed_factor)
        stats.delivered_record[reported_time] = stats.delivered_count
        yield env.timeout(1 / global_speed_factor)

def record_interval_stats(env, sim_duration, stats):
    t = CHECK_INTERVAL
    while t <= sim_duration:
        yield env.timeout(CHECK_INTERVAL / global_speed_factor)
        stats.delivered_history[t] = stats.delivered_count
        t += CHECK_INTERVAL

# -----------------------------------------
# run_one_sim, run_simulation_task 등
# -----------------------------------------
def run_one_sim(agv_count, sim_duration, run_id=1, output_mode="live"):
    env = simpy.Environment()
    cell_blocked = {}
    stats = Stats()
    agvs = []

    start_row = 8
    start_cols = [0,2,4,6,1,3,5]
    for i in range(agv_count):
        pos = (start_row, start_cols[i % len(start_cols)])
        agv = AGV(i, pos)
        agvs.append(agv)

    for agv in agvs:
        env.process(agv_process(agv, env, stats, sim_duration, cell_blocked))
    env.process(record_stats(env, sim_duration, stats))
    env.process(record_interval_stats(env, sim_duration, stats))

    env.run(until=sim_duration / global_speed_factor)

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

    result = {
        "end_time": sim_duration,
        "delivered_count": stats.delivered_count,
        "delivered_history": stats.delivered_history,
        "delivered_record": dict(stats.delivered_record),
        "agv_stats": final_agv_stats
    }
    return result

def run_simulation_task(agv_count, sim_duration):
    global SIM_RUNNING, SIM_ENV, SIM_STATS, SIM_AGVS, SIM_DURATION
    SIM_RUNNING = True
    SIM_DURATION = sim_duration

    env = simpy.Environment()
    stats = Stats()
    agvs = []
    cell_blocked = {}

    start_row = 8
    start_cols = [0,2,4,6,1,3,5]
    for i in range(agv_count):
        pos = (start_row, start_cols[i % len(start_cols)])
        agv = AGV(i, pos)
        agvs.append(agv)
        env.process(agv_process(agv, env, stats, sim_duration, cell_blocked))

    env.process(record_stats(env, sim_duration, stats))
    env.process(record_interval_stats(env, sim_duration, stats))

    global SIM_ENV, SIM_STATS, SIM_AGVS
    SIM_ENV = env
    SIM_STATS = stats
    SIM_AGVS = agvs

    env.run(until=sim_duration / global_speed_factor)
    SIM_RUNNING = False
    print("시뮬레이션 종료")

def update_loop_task():
    while True:
        if not SIM_RUNNING:
            eventlet.sleep(1.0)
            continue

        current_time = round(SIM_ENV.now * global_speed_factor, 2) if SIM_ENV else 0
        delivered_count = SIM_STATS.delivered_count if SIM_STATS else 0
        agv_positions = {}
        if SIM_AGVS is not None:
            for agv in SIM_AGVS:
                agv_positions[agv.id] = (round(agv.pos[0],1), round(agv.pos[1],1))
        state = {
            "sim_time": current_time,
            "agv_positions": agv_positions,
            "delivered_count": delivered_count
        }
        socketio.emit("simulation_update", state)
        eventlet.sleep(UPDATE_INTERVAL)

# -----------------------------------------
# 최적화 함수 (옵션)
# -----------------------------------------
def simulate_for_agv_count(agv_count, sim_duration, speed):
    global global_speed_factor
    old_speed = global_speed_factor
    global_speed_factor = speed

    runs = []
    for i in range(REPEAT_RUNS):
        r = run_one_sim(agv_count, sim_duration, run_id=i+1)
        runs.append(r)

    global_speed_factor = old_speed

    counts = [r["delivered_count"] for r in runs]
    avg_delivered = statistics.mean(counts)
    std_delivered = statistics.stdev(counts) if len(counts) > 1 else 0
    throughput = avg_delivered/sim_duration*3600
    delivered_per_agv = avg_delivered/agv_count

    all_cycle_times = []
    for r in runs:
        for agv_stat in r["agv_stats"].values():
            all_cycle_times.extend(agv_stat["times"])
    avg_cycle = statistics.mean(all_cycle_times) if all_cycle_times else 0

    return {
        "agv_count": agv_count,
        "avg_delivered": avg_delivered,
        "std_delivered": std_delivered,
        "throughput_per_hour": throughput,
        "delivered_per_agv": delivered_per_agv,
        "avg_cycle": avg_cycle
    }

# -----------------------------------------
# SocketIO 이벤트
# -----------------------------------------
@socketio.on('connect')
def handle_connect():
    print("클라이언트가 연결되었습니다.")
    emit('status', {'message': 'Simulator connected'})

@socketio.on('disconnect')
def handle_disconnect():
    print("클라이언트 연결 종료")

@socketio.on('simulate_stream')
def handle_simulate_stream(data):
    global global_speed_factor, SIM_RUNNING
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

        socketio.start_background_task(run_simulation_task, agv_count, duration)
        emit('status', {'message': f'시뮬레이션 시작: AGV={agv_count}, 종료={duration}s, 배속={global_speed_factor}'})
    except Exception as e:
        emit('error', {'message': str(e)})

@socketio.on('simulate_final')
def handle_simulate_final(data):
    global global_speed_factor
    try:
        agv_count = int(data.get('agv_count', 3))
        duration = int(data.get('duration', 3000))
        initial_speed_str = data.get('initial_speed', "1")
        if initial_speed_str == "max":
            global_speed_factor = 1.0
        else:
            global_speed_factor = float(initial_speed_str)
            if global_speed_factor <= 0:
                emit('error', {'message': 'speed must be positive or "max"'})
                return

        result = run_one_sim(agv_count, duration)
        for agv in result["agv_stats"].values():
            agv["location_log"] = []
        emit('simulation_final', result)
    except Exception as e:
        emit('error', {'message': str(e)})

@socketio.on('simulate_opt')
def handle_simulate_opt(data):
    try:
        min_agv = int(data.get('min_agv', 3))
        max_agv = int(data.get('max_agv', 6))
        duration = int(data.get('duration', 3000))
        speed_str = data.get('speed', "1")

        if speed_str == "max":
            speed = 1.0
        else:
            speed = float(speed_str)
            if speed <= 0:
                emit('error', {'message': 'speed must be positive'})
                return

        results = []
        for agv_count in range(min_agv, max_agv+1):
            r = simulate_for_agv_count(agv_count, duration, speed)
            results.append(r)
        emit('simulation_opt', {"optimization_results": results})
    except Exception as e:
        emit('error', {'message': str(e)})

@socketio.on('update_speed')
def handle_update_speed(data):
    global global_speed_factor
    try:
        new_speed = float(data.get('speed'))
        if new_speed <= 0:
            emit('error', {'message': 'speed must be positive'})
            return
        global_speed_factor = new_speed
        emit('status', {'message': f'Speed updated to {new_speed}'})
    except Exception as e:
        emit('error', {'message': str(e)})

@socketio.on('report')
def handle_report(data):
    global SIM_STATS, SIM_ENV
    if SIM_STATS and SIM_ENV:
        rep = {
            "sim_time": round(SIM_ENV.now * global_speed_factor, 2),
            "delivered_count": SIM_STATS.delivered_count,
            "agv_stats": {str(k): v for k,v in SIM_STATS.agv_stats.items()}
        }
        emit('simulation_report', rep)
    else:
        emit('simulation_report', {"message": "No simulation data available."})

# -----------------------------------------
# HTTP 라우트 & 서버 시작
# -----------------------------------------
@app.route('/health')
def health_check():
    return jsonify({"status": "ok"})

def start_background_loops():
    socketio.start_background_task(update_loop_task)

if __name__ == "__main__":
    start_background_loops()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
