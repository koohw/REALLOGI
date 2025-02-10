import eventlet
eventlet.monkey_patch()
import multiprocessing
import sys
import json
import time
import random
import statistics
from simpy.rt import RealtimeEnvironment
from collections import deque, defaultdict
import math

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
SIM_DURATION = 0
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
    # 동적 목표 선택 helper 함수
    # -----------------------------------------
    def select_shelf(current_pos, current_agv):
        current_grid = (int(round(current_pos[0])), int(round(current_pos[1])))
        occupied = set()
        for other in SIM_AGVS:
            if other.id != current_agv.id:
                other_grid = (int(round(other.pos[0])), int(round(other.pos[1])))
                if other_grid in shelf_coords:
                    occupied.add(other_grid)
        available = [s for s in shelf_coords if s not in occupied]
        if available:
            return min(available, key=lambda s: abs(current_grid[0]-s[0]) + abs(current_grid[1]-s[1]))
        else:
            return min(shelf_coords, key=lambda s: abs(current_grid[0]-s[0]) + abs(current_grid[1]-s[1]))

    def select_exit(current_pos, current_agv):
        current_grid = (int(round(current_pos[0])), int(round(current_pos[1])))
        occupied = set()
        for other in SIM_AGVS:
            if other.id != current_agv.id:
                other_grid = (int(round(other.pos[0])), int(round(other.pos[1])))
                if other_grid in exit_coords:
                    occupied.add(other_grid)
        available = [e for e in exit_coords if e not in occupied]
        if available:
            return min(available, key=lambda e: abs(current_grid[0]-e[0]) + abs(current_grid[1]-e[1]))
        else:
            return min(exit_coords, key=lambda e: abs(current_grid[0]-e[0]) + abs(current_grid[1]-e[1]))

    # -----------------------------------------
    # 시간 확장 BFS 및 예약 테이블 관련 함수
    # -----------------------------------------
    def build_reservation_table(current_time, cell_blocked, current_agv_id, margin=1):
        reservations = set()
        start_t = int(math.floor(current_time)) + 1
        for (r, c), t_block in cell_blocked.items():
            t_block_int = int(math.ceil(t_block))
            for t in range(start_t, t_block_int + 1):
                for dr in range(-margin, margin + 1):
                    for dc in range(-margin, margin + 1):
                        reservations.add((r + dr, c + dc, t))
        if SIM_AGVS is not None:
            for other in SIM_AGVS:
                if other.id == current_agv_id:
                    continue
                t_other = int(math.floor(current_time))
                pos = (int(round(other.pos[0])), int(round(other.pos[1])))
                for dr in range(-margin, margin + 1):
                    for dc in range(-margin, margin + 1):
                        reservations.add((pos[0] + dr, pos[1] + dc, t_other))
                if other.path:
                    for i, cell in enumerate(other.path[1:], start=1):
                        for dr in range(-margin, margin + 1):
                            for dc in range(-margin, margin + 1):
                                reservations.add((cell[0] + dr, cell[1] + dc, t_other + i))
                elif hasattr(other, 'schedule') and other.schedule:
                    for entry in other.schedule[1:]:
                        cell, t_entry = entry
                        for dr in range(-margin, margin + 1):
                            for dc in range(-margin, margin + 1):
                                reservations.add((cell[0] + dr, cell[1] + dc, t_entry))
        return reservations

    def time_augmented_bfs_path(start, goal, start_time, reservations, max_time=1000):
        start_t = int(math.floor(start_time))
        queue = deque()
        queue.append((start[0], start[1], start_t, [(start, start_t)]))
        visited = dict()
        visited[(start[0], start[1])] = start_t

        while queue:
            r, c, t, path = queue.popleft()
            if (r, c) == goal:
                return path
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1), (0, 0)]:
                nr, nc = r + dr, c + dc
                nt = t + 1
                if nt > max_time:
                    continue
                if not (0 <= nr < ROWS and 0 <= nc < COLS):
                    continue
                if MAP[nr][nc] == 1:
                    continue
                if (nr, nc, nt) in reservations:
                    continue
                if (nr, nc) in visited and visited[(nr, nc)] <= nt:
                    continue
                visited[(nr, nc)] = nt
                new_path = path + [((nr, nc), nt)]
                queue.append((nr, nc, nt, new_path))
        return None

    def plan_path(current_pos, target, current_time, cell_blocked, current_agv_id):
        reservations = build_reservation_table(current_time, cell_blocked, current_agv_id, margin=1)
        schedule = time_augmented_bfs_path(current_pos, target, current_time, reservations)
        return schedule

    # -----------------------------------------
    # 기존 BFS (참고용)
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

    def find_nearest_exit(pos):
        return min(exit_coords, key=lambda e: abs(pos[0]-e[0]) + abs(pos[1]-e[1]))

    # -----------------------------------------
    # AGV, Stats, 및 최종 결과 생성 함수
    # -----------------------------------------
    class AGV:
        def __init__(self, agv_id, start_pos):
            self.id = agv_id
            self.start_pos = (float(start_pos[0]), float(start_pos[1]))
            self.pos = (float(start_pos[0]), float(start_pos[1]))
            self.path = []      # 기존 경로 (미사용)
            self.schedule = []  # ((row, col), scheduled_arrival_time)
            self.cargo = 0
            self.pickup_time = None
            self.busy_until = None  # 작업 중 (픽업/드롭) 종료 예정 시간
            self.target = None

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

    def compute_simulation_result(stats, sim_duration):
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
    # AGV 작업 프로세스 (동적 대체 경로 선택 포함)
    # -----------------------------------------
    def do_pick(agv, env, stats, cell_blocked):
        now = env.now
        agv.busy_until = now + 10
        key = (int(round(agv.pos[0])), int(round(agv.pos[1])))
        cell_blocked[key] = now + 10
        yield env.timeout(10)
        agv.cargo = 1
        if now >= WARMUP_PERIOD:
            agv.pickup_time = now
        stats.agv_stats[agv.id]["count"] += 1
        agv.busy_until = None

    def do_drop(agv, env, stats, cell_blocked):
        start_drop = env.now
        agv.busy_until = start_drop + 10
        key = (int(round(agv.pos[0])), int(round(agv.pos[1])))
        cell_blocked[key] = start_drop + 10
        yield env.timeout(10)
        drop_finish = env.now
        if agv.pickup_time is not None:
            duration = drop_finish - agv.pickup_time
            stats.agv_stats[agv.id]["times"].append(duration)
            agv.pickup_time = None
        agv.cargo = 0
        stats.delivered_count += 1
        agv.busy_until = None

    def restart_simulation_with_current_state():
        global SIM_RUNNING, SIM_ENV, SIM_STATS, SIM_AGVS, SIM_DURATION, global_speed_factor
        if not SIM_RUNNING:
            return
        current_time = SIM_ENV.now
        current_positions = []
        current_cargos = []
        current_schedules = []
        for agv in SIM_AGVS:
            current_positions.append(agv.pos)
            current_cargos.append(agv.cargo)
            current_schedules.append(agv.schedule.copy() if agv.schedule else [])
        delivered_count = SIM_STATS.delivered_count
        SIM_RUNNING = False
        env = RealtimeEnvironment(factor=global_speed_factor, initial_time=current_time)
        stats = Stats()
        stats.delivered_count = delivered_count
        agvs = []
        cell_blocked = {}
        for i, (pos, cargo, schedule) in enumerate(zip(current_positions, current_cargos, current_schedules)):
            agv = AGV(i, pos)
            agv.cargo = cargo
            agv.schedule = schedule
            agvs.append(agv)
            env.process(agv_process(agv, env, stats, SIM_DURATION, cell_blocked))
        env.process(record_stats(env, SIM_DURATION, stats))
        env.process(record_interval_stats(env, SIM_DURATION, stats))
        SIM_ENV = env
        SIM_STATS = stats
        SIM_AGVS = agvs
        socketio.start_background_task(run_continued_simulation, env, SIM_DURATION)

    def run_continued_simulation(env, sim_duration):
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
            result = compute_simulation_result(SIM_STATS, sim_duration)
            socketio.emit('simulation_final', result)

    def agv_process(agv, env, stats, sim_duration, cell_blocked):
        """
        AGV의 동작 프로세스.
        cargo 상태에 따라 선반 또는 출구를 목표로 하며,
        시간 확장 BFS로 경로(스케줄)를 계산하여 이동합니다.
        만약 이동하려는 다음 셀이 이미 점유되어 있으면,
        예상 대기시간을 산출한 후 대체 경로(alternative_schedule)를 계산하고,
        대체 경로가 더 빠르면 해당 스케줄로 교체합니다.
        (대체 경로 계산에 실패하면 0.5초 대기 후 스케줄을 초기화하여 재계획합니다.)
        """
        while env.now < sim_duration:
            # 스케줄이 없거나 남은 스케줄이 1 이하이면 새 경로 계산
            if not agv.schedule or len(agv.schedule) <= 1:
                current_grid_pos = (int(round(agv.pos[0])), int(round(agv.pos[1])))
                if agv.cargo == 0:
                    target = select_shelf(agv.pos, agv)
                else:
                    target = find_nearest_exit(current_grid_pos)
                agv.target = target
                new_schedule = plan_path(current_grid_pos, target, env.now, cell_blocked, agv.id)
                if new_schedule is None:
                    yield env.timeout(0.5)
                    continue
                else:
                    agv.schedule = new_schedule

            # 이동: 스케줄의 다음 단계 진행
            if len(agv.schedule) > 1:
                current_entry = agv.schedule[0]  # (cell, scheduled_time)
                next_entry = agv.schedule[1]
                next_cell, scheduled_time = next_entry

                # 충돌 확인: 다음 셀이 다른 AGV에 의해 점유되어 있는 경우
                conflict = False
                blocking_waits = []
                for other in SIM_AGVS:
                    if other.id != agv.id:
                        other_grid = (int(round(other.pos[0])), int(round(other.pos[1])))
                        if other_grid == next_cell:
                            conflict = True
                            if other.busy_until is not None:
                                blocking_waits.append(max(other.busy_until - env.now, 0))
                            else:
                                blocking_waits.append(0.5)
                if conflict:
                    wait_time = min(blocking_waits) if blocking_waits else 0.5
                    modified_cell_blocked = cell_blocked.copy()
                    modified_cell_blocked[next_cell] = env.now + wait_time
                    alternative_schedule = plan_path(
                        (int(round(agv.pos[0])), int(round(agv.pos[1]))),
                        agv.target,
                        env.now,
                        modified_cell_blocked,
                        agv.id
                    )
                    if alternative_schedule is None:
                        yield env.timeout(wait_time)
                        agv.schedule = []
                        continue
                    alt_arrival = alternative_schedule[-1][1]
                    current_schedule_final = agv.schedule[-1][1] if agv.schedule else float('inf')
                    wait_option = current_schedule_final + wait_time
                    if alt_arrival < wait_option:
                        agv.schedule = alternative_schedule
                    else:
                        yield env.timeout(wait_time)
                        agv.schedule = []
                        continue

                if env.now < scheduled_time:
                    yield env.timeout(scheduled_time - env.now)
                duration = scheduled_time - current_entry[1]
                if duration <= 0:
                    duration = 0.001
                current_pos = agv.pos
                dx = next_cell[0] - current_pos[0]
                dy = next_cell[1] - current_pos[1]
                distance = math.sqrt(dx**2 + dy**2)
                num_steps = int(distance / STEP_SIZE)
                if num_steps > 0:
                    step_time = duration / num_steps
                    for _ in range(num_steps):
                        current_pos = (current_pos[0] + dx/num_steps, current_pos[1] + dy/num_steps)
                        yield env.timeout(step_time)
                        agv.pos = current_pos
                        rounded_pos = (round(current_pos[0], 1), round(current_pos[1], 1))
                        stats.agv_stats[agv.id]["location_log"].append((env.now, rounded_pos))
                else:
                    yield env.timeout(duration)
                    current_pos = (float(next_cell[0]), float(next_cell[1]))
                    agv.pos = current_pos
                agv.schedule.pop(0)
            else:
                yield env.timeout(0.1)

            # cargo 작업 처리
            current_grid_pos = (int(round(agv.pos[0])), int(round(agv.pos[1])))
            if agv.cargo == 0 and current_grid_pos in shelf_coords:
                conflict = False
                for other in SIM_AGVS:
                    if other.id != agv.id:
                        other_pos = (int(round(other.pos[0])), int(round(other.pos[1])))
                        if other_pos == current_grid_pos:
                            conflict = True
                            break
                if conflict:
                    yield env.timeout(0.5)
                    agv.schedule = []
                    continue
                yield env.process(do_pick(agv, env, stats, cell_blocked))
                agv.schedule = []
                yield env.timeout(random.uniform(0.5, 1.5))
            elif agv.cargo == 1 and current_grid_pos in exit_coords:
                conflict = False
                for other in SIM_AGVS:
                    if other.id != agv.id:
                        other_pos = (int(round(other.pos[0])), int(round(other.pos[1])))
                        if other_pos == current_grid_pos:
                            conflict = True
                            break
                if conflict:
                    yield env.timeout(0.5)
                    agv.schedule = []
                    continue
                yield env.process(do_drop(agv, env, stats, cell_blocked))
                agv.schedule = []
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

    # -----------------------------------------
    # 시뮬레이션 실행 (최종 결과)
    # -----------------------------------------
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

    # -----------------------------------------
    # (A안) 실시간 시뮬레이션 + 업데이트 루프
    # -----------------------------------------
    SIM_APP_RUNNING = False
    def run_simulation_task(agv_count, sim_duration):
        global SIM_RUNNING, SIM_ENV, SIM_STATS, SIM_AGVS, SIM_DURATION, SIM_FINISHED
        SIM_RUNNING = True
        SIM_FINISHED = False
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
        result = compute_simulation_result(stats, sim_duration)
        socketio.emit('simulation_final', result)

    # -----------------------------------------
    # Socket.IO 이벤트 핸들러 및 서버 관련 코드
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

    @socketio.on('message')
    def handle_message(message):
        global SIM_PAUSED, SIM_RUNNING, is_paused
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
            if 'speed' in data:
                try:
                    new_speed = float(data.get('speed'))
                    if new_speed <= 0:
                        socketio.emit('message', {'error': 'speed must be positive'})
                        return
                    global_speed_factor = 1.0 / new_speed
                    restart_simulation_with_current_state()
                except Exception as e:
                    socketio.emit('message', {'error': str(e)})
            if 'agv_count' in data:
                try:
                    new_count = int(data.get('agv_count') or 3)
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
            agv_count = int(data.get('agv_count') or 3)
            duration = int(data.get('duration') or 3000)
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
            agv_count = int(data.get('agv_count') or 3)
            duration = int(data.get('duration') or 3000)
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
            current_paths.append(agv.schedule.copy() if agv.schedule else [])
        delivered_count_paused = SIM_STATS.delivered_count
        SIM_RUNNING = False

    def resume_simulation():
        global SIM_RUNNING, SIM_ENV, SIM_STATS, SIM_AGVS, SIM_DURATION, global_speed_factor, delivered_count_paused, current_time_paused
        env = RealtimeEnvironment(factor=global_speed_factor, initial_time=current_time_paused)
        stats = Stats()
        stats.delivered_count = delivered_count_paused
        agvs = []
        cell_blocked = {}
        for i, (pos, cargo, schedule) in enumerate(zip(current_positions, current_cargos, current_paths)):
            agv = AGV(i, pos)
            agv.cargo = cargo
            agv.schedule = schedule
            agvs.append(agv)
            env.process(agv_process(agv, env, stats, SIM_DURATION, cell_blocked))
        env.process(record_stats(env, SIM_DURATION, stats))
        env.process(record_interval_stats(env, SIM_DURATION, stats))
        SIM_ENV = env
        SIM_STATS = stats
        SIM_AGVS = agvs
        socketio.start_background_task(run_continued_simulation, env, SIM_DURATION)

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
