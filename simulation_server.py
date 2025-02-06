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
# 전역 설정 & 전역 변수
# -----------------------------------------

global_speed_factor = 1.0  # 배속
SIM_RUNNING = False        # 시뮬레이션이 진행중인지 여부
SIM_DURATION = 0          # 시뮬레이션 종료 시간
SIM_ENV = None            # SimPy Environment
SIM_STATS = None          # 시뮬레이션 통계 객체
SIM_AGVS = []             # AGV 리스트

UPDATE_INTERVAL = 1.0     # 웹 전송 주기(초) - A안에서는 1초마다 상태 전송

# 시뮬레이션이 종료되면 True
SIM_FINISHED = False

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

# -----------------------------------------
# controlled_timeout: 실시간 sleep
# -----------------------------------------
def controlled_timeout(env, duration):
    """
    SimPy timeout 후, real-time으로 sleep(duration / global_speed_factor).
    배속이 4라면 sleep 1/4로 줄어듦 → 실제로 4배 속도로 진행.
    """
    yield env.timeout(duration)
    time.sleep(duration / global_speed_factor)

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
    return min(exit_coords, key=lambda e: abs(pos[0]-e[0]) + abs(pos[1]-e[1]))

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

def do_pick(agv, env, stats, cell_blocked):
    now = env.now
    cell_blocked[agv.pos] = now + 10
    yield from controlled_timeout(env, 10)
    agv.cargo = 1
    if now >= WARMUP_PERIOD:
        agv.pickup_time = now
    stats.agv_stats[agv.id]["count"] += 1

def do_drop(agv, env, stats, cell_blocked):
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
    while env.now < sim_duration:
        if not agv.path or len(agv.path) <= 1:
            if agv.cargo == 0:
                preferred = shelf_coords[agv.id % len(shelf_coords)]
                target = preferred if random.random() < 0.5 else random.choice(shelf_coords)
                path = bfs_path(
                    (int(agv.pos[0]), int(agv.pos[1])),
                    target,
                    env.now,
                    cell_blocked,
                    defaultdict(int)
                )
                agv.path = path if path is not None else []
            else:
                target = find_nearest_exit((int(agv.pos[0]), int(agv.pos[1])))
                path = bfs_path(
                    (int(agv.pos[0]), int(agv.pos[1])),
                    target,
                    env.now,
                    cell_blocked,
                    defaultdict(int)
                )
                agv.path = path if path is not None else []

        if len(agv.path) > 1:
            next_cell = agv.path[1]
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
                yield from controlled_timeout(env, STEP_SIZE)
                agv.pos = current_pos
                rounded_pos = (round(current_pos[0],1), round(current_pos[1],1))
                stats.agv_stats[agv.id]["location_log"].append((env.now, rounded_pos))

            remaining = distance - num_steps * STEP_SIZE
            if remaining > 0:
                current_pos = (
                    current_pos[0] + remaining * dx / distance,
                    current_pos[1] + remaining * dy / distance
                )
                yield from controlled_timeout(env, remaining)
                agv.pos = current_pos
                rounded_pos = (round(current_pos[0],1), round(current_pos[1],1))
                stats.agv_stats[agv.id]["location_log"].append((env.now, rounded_pos))

            agv.pos = (float(next_cell[0]), float(next_cell[1]))
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
    while env.now < sim_duration:
        stats.delivered_record[int(env.now)] = stats.delivered_count
        yield env.timeout(1)

def record_interval_stats(env, sim_duration, stats):
    t = CHECK_INTERVAL
    while t <= sim_duration:
        yield env.timeout(CHECK_INTERVAL)
        stats.delivered_history[t] = stats.delivered_count
        t += CHECK_INTERVAL

# -----------------------------------------
# 시뮬레이션 실행 (최종 결과)
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

    env.run(until=sim_duration)

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

# -----------------------------------------
# (A안) 실시간 시뮬레이션 + 별도 업데이트 루프
# -----------------------------------------

SIM_APP_RUNNING = False   # 이미 시뮬레이션이 도는지 여부
def run_simulation_task(agv_count, sim_duration):
    """시뮬레이션을 실시간으로 진행하는 그린스레드."""
    global SIM_RUNNING, SIM_ENV, SIM_STATS, SIM_AGVS, SIM_DURATION, SIM_FINISHED
    SIM_RUNNING = True
    SIM_FINISHED = False
    SIM_DURATION = sim_duration

    # 환경/통계/AGV 재초기화
    env = simpy.Environment()
    stats = Stats()
    agvs = []

    start_row = 8
    start_cols = [0,2,4,6,1,3,5]
    cell_blocked = {}

    for i in range(agv_count):
        pos = (start_row, start_cols[i % len(start_cols)])
        agv = AGV(i, pos)
        agvs.append(agv)
        env.process(agv_process(agv, env, stats, sim_duration, cell_blocked))

    env.process(record_stats(env, sim_duration, stats))
    env.process(record_interval_stats(env, sim_duration, stats))

    # 전역에 저장 → update_loop_task에서 상태 확인 가능
    SIM_ENV = env
    SIM_STATS = stats
    SIM_AGVS = agvs

    # 시뮬레이션 실행 (블로킹이지만 eventlet 그린스레드라 서버 전체는 안 막힘)
    env.run(until=sim_duration)
    # 시뮬레이션 완료
    SIM_RUNNING = False
    SIM_FINISHED = True
    print("시뮬레이션 종료")

def update_loop_task():
    """1초마다 현재 상태를 클라이언트에 전송하는 루프."""
    while True:
        # 시뮬레이션이 안 도는 상태면 대기
        if not SIM_RUNNING:
            eventlet.sleep(1.0)
            continue

        # 시뮬레이션 진행 중이면 상태 전송
        current_time = 0
        delivered_count = 0
        agv_positions = {}
        if SIM_ENV is not None and SIM_STATS is not None and SIM_AGVS is not None:
            current_time = round(SIM_ENV.now, 2)
            delivered_count = SIM_STATS.delivered_count
            for agv in SIM_AGVS:
                agv_positions[agv.id] = (round(agv.pos[0],1), round(agv.pos[1],1))

        state = {
            "sim_time": current_time,
            "agv_positions": agv_positions,
            "delivered_count": delivered_count
        }
        socketio.emit("simulation_update", state)
        eventlet.sleep(1.0)  # 1초마다 전송

# -----------------------------------------
# 최적화 분석
# -----------------------------------------
def simulate_for_agv_count(agv_count, sim_duration, speed):
    global global_speed_factor
    old_speed = global_speed_factor
    global_speed_factor = speed

    run_results = []
    for run_id in range(1, REPEAT_RUNS+1):
        res = run_one_sim(agv_count, sim_duration, run_id, output_mode="final")
        run_results.append(res)
    global_speed_factor = old_speed

    delivered_counts = [res["delivered_count"] for res in run_results]
    avg_delivered = statistics.mean(delivered_counts)
    std_delivered = statistics.stdev(delivered_counts) if len(delivered_counts) > 1 else 0
    throughput = avg_delivered / sim_duration * 3600
    delivered_per_agv = avg_delivered / agv_count

    all_cycle_times = []
    all_wait_times = []
    all_travel_times = []
    for res in run_results:
        for agv_stat in res["agv_stats"].values():
            all_cycle_times.extend(agv_stat["times"])
            all_wait_times.extend(agv_stat.get("wait_times", []))
            all_travel_times.extend(agv_stat.get("travel_times", []))

    avg_cycle = statistics.mean(all_cycle_times) if all_cycle_times else 0
    avg_wait = statistics.mean(all_wait_times) if all_wait_times else 0
    avg_travel = statistics.mean(all_travel_times) if all_travel_times else 0
    return {
        "agv_count": agv_count,
        "avg_delivered": avg_delivered,
        "std_delivered": std_delivered,
        "throughput_per_hour": throughput,
        "delivered_per_agv": delivered_per_agv,
        "avg_cycle": avg_cycle,
        "avg_wait": avg_wait,
        "avg_travel": avg_travel
    }


# -----------------------------------------
# Flask-SocketIO 설정
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
# 백그라운드 태스크 시작: update_loop_task
# -----------------------------------------
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

# -- 실시간 시뮬레이션 시작 --
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

        # 이미 실행 중이면 멈추고 다시 시작 가능
        if SIM_RUNNING:
            emit('error', {'message': 'Simulation is already running'})
            return

        socketio.start_background_task(run_simulation_task, agv_count, duration)

    except Exception as e:
        emit('error', {'message': str(e)})

# -- 최종 결과 요청 --
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
                agv["location_log"] = []  # 위치 로그 제거
        emit('simulation_final', result)

    except Exception as e:
        emit('error', {'message': str(e)})

# -- 최적화 분석 --
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
                emit('error', {'message': 'speed must be positive or "max"'})
                return

        results = []
        for agv_count in range(min_agv, max_agv+1):
            res = simulate_for_agv_count(agv_count, duration, speed)
            results.append(res)
        emit('simulation_opt', {"optimization_results": results})

    except Exception as e:
        emit('error', {'message': str(e)})

# -- 배속 업데이트 --
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
        print(f"[update_speed] Global speed factor updated to: {new_speed}")
    except Exception as e:
        emit('error', {'message': str(e)})

@app.route('/health')
def health_check():
    return jsonify({"status": "ok"})

# -----------------------------------------
# 서버 시작 시 update_loop_task 실행
# -----------------------------------------
def start_background_loops():
    """시작 시 update_loop_task를 백그라운드로 실행"""
    socketio.start_background_task(update_loop_task)

if __name__ == '__main__':
    # 서버 시작 시 update_loop_task 돌림
    start_background_loops()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
