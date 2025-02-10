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

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit

import logging

logger = logging.getLogger(__name__)

# -----------------------------------------
# 전역 설정 & 전역 변수
# -----------------------------------------

# Global settings & variables
global_speed_factor = 1.0
SIM_RUNNING = False
SIM_DURATION = 0
SIM_ENV = None
SIM_STATS = None
SIM_AGVS = []
SIM_PAUSED = False  # Added missing global variable
PREVIOUS_SPEED = 1.0  # Added missing global variable

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

    # Import all the original simulation code and functions here
    # ... (original simulation code) ...



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


    def restart_simulation_with_current_state():
        """현재 AGV 상태로 새로운 시뮬레이션 시작"""
        global SIM_RUNNING, SIM_ENV, SIM_STATS, SIM_AGVS, SIM_DURATION, global_speed_factor

        if not SIM_RUNNING:
            return

        # 현재 상태 저장
        current_time = SIM_ENV.now
        current_positions = []
        current_cargos = []
        current_paths = []
        for agv in SIM_AGVS:
            current_positions.append(agv.pos)
            current_cargos.append(agv.cargo)
            current_paths.append(agv.path.copy() if agv.path else [])

        delivered_count = SIM_STATS.delivered_count

        # 이전 시뮬레이션 중단
        SIM_RUNNING = False

        # 새로운 환경 생성 (새로운 속도 적용)
        env = RealtimeEnvironment(factor=global_speed_factor, initial_time=current_time)
        stats = Stats()
        stats.delivered_count = delivered_count  # 이전 배송 수 유지
        agvs = []
        cell_blocked = {}

        # AGV 재생성 (이전 위치와 상태 유지)
        for i, (pos, cargo, path) in enumerate(zip(current_positions, current_cargos, current_paths)):
            agv = AGV(i, pos)  # 현재 위치로 초기화
            agv.cargo = cargo  # 화물 상태 유지
            agv.path = path  # 현재 경로 유지
            agvs.append(agv)
            env.process(agv_process(agv, env, stats, SIM_DURATION, cell_blocked))

        # 통계 기록 프로세스 재시작
        env.process(record_stats(env, SIM_DURATION, stats))
        env.process(record_interval_stats(env, SIM_DURATION, stats))

        # 전역 변수 업데이트
        SIM_ENV = env
        SIM_STATS = stats
        SIM_AGVS = agvs

        socketio.start_background_task(run_continued_simulation, env, SIM_DURATION)

    def run_continued_simulation(env, sim_duration):
        """재시작된 시뮬레이션을 실행"""
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
                    yield env.timeout(STEP_SIZE)
                    agv.pos = current_pos
                    rounded_pos = (round(current_pos[0],1), round(current_pos[1],1))
                    stats.agv_stats[agv.id]["location_log"].append((env.now, rounded_pos))

                remaining = distance - num_steps * STEP_SIZE
                if remaining > 0:
                    current_pos = (
                        current_pos[0] + remaining * dx / distance,
                        current_pos[1] + remaining * dy / distance
                    )
                    yield env.timeout(remaining)
                    agv.pos = current_pos
                    rounded_pos = (round(current_pos[0],1), round(current_pos[1],1))
                    stats.agv_stats[agv.id]["location_log"].append((env.now, rounded_pos))

                agv.pos = (float(next_cell[0]), float(next_cell[1]))
                agv.path.pop(0)
            else:
                yield env.timeout(0.1)

            if agv.pos in shelf_coords and agv.cargo == 0:
                yield env.process(do_pick(agv, env, stats, cell_blocked))
                agv.path = []
                yield env.timeout(random.uniform(0.5,1.5))
            elif agv.pos in exit_coords and agv.cargo == 1:
                yield env.process(do_drop(agv, env, stats, cell_blocked))
                agv.path = []
                yield env.timeout(random.uniform(0.5,1.5))

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
        env = RealtimeEnvironment(factor=1)
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


    @socketio.on('message')
    def handle_message(message):
        global SIM_PAUSED, SIM_RUNNING, is_paused  # Added missing global declarations
        try:
            data = json.loads(message) if isinstance(message, str) else message
            logger.info(f'Received message: {data}')

            # Command 처리
            if 'command' in data:
                command = data['command']
                if command == 'start':
                    if is_paused:
                        is_paused = False
                        resume_simulation()
                        return
                    # simulate_stream 함수의 로직 사용
                    global global_speed_factor  # Added missing global declaration
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



            # Speed 업데이트 처리
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

            # AGV count 업데이트 처리
            if 'agv_count' in data:
                try:
                    new_count = int(data['agv_count'])
                    if new_count <= 0:
                        socketio.emit('message', {'error': 'AGV count must be positive'})
                        return
                    # AGV 수 업데이트 로직 추가
                except ValueError as e:
                    socketio.emit('message', {'error': str(e)})

            # Ping 처리
            if data.get('type') == 'ping':
                socketio.emit('message', {
                    'type': 'pong',
                    'timestamp': time.time()
                })

        except Exception as e:
            logger.error(f'Error processing message: {str(e)}')
            socketio.emit('message', {'error': str(e)})

    # -- 실시간 시뮬레이션 시작 --
    # Update the handle_simulate_stream to initialize pause state
    @socketio.on('simulate_stream')
    def handle_simulate_stream(data):
        global global_speed_factor, SIM_RUNNING, SIM_PAUSED  # Added missing globals
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

            # Reset pause state when starting new simulation
            SIM_PAUSED = False
            socketio.start_background_task(run_simulation_task, agv_count, duration)
            emit('simulation_status', {'status': 'running'})

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


    # -- 배속 업데이트 --
    @socketio.on('update_speed')
    def handle_update_speed(data):
        global global_speed_factor
        try:
            new_speed = 1.0 / float(data.get('speed'))
            if new_speed <= 0:
                emit('error', {'message': 'speed must be positive'})
                return
            global_speed_factor = new_speed

            # 속도 변경 시 시뮬레이션 재시작
            restart_simulation_with_current_state()

            emit('status', {'message': f'Speed updated to {new_speed}'})
            print(f"[update_speed] Global speed factor updated to: {new_speed}")
        except Exception as e:
            emit('error', {'message': str(e)})

    @app.route('/health')
    def health_check():
        return jsonify({"status": "ok"})

    def pause_simulation():
        """현재 AGV 상태로 새로운 시뮬레이션 시작"""
        global SIM_RUNNING, SIM_ENV, SIM_STATS, SIM_AGVS, SIM_DURATION, global_speed_factor, delivered_count_paused, current_time_paused, current_positions, current_cargos, current_paths

        if not SIM_RUNNING:
            return

        # 현재 상태 저장
        current_time_paused = SIM_ENV.now
        current_positions = []
        current_cargos = []
        current_paths = []
        for agv in SIM_AGVS:
            current_positions.append(agv.pos)
            current_cargos.append(agv.cargo)
            current_paths.append(agv.path.copy() if agv.path else [])

        delivered_count_paused = SIM_STATS.delivered_count

        # 이전 시뮬레이션 중단
        SIM_RUNNING = False

    def resume_simulation():
        global SIM_RUNNING, SIM_ENV, SIM_STATS, SIM_AGVS, SIM_DURATION, global_speed_factor, delivered_count_paused, current_time_paused

        env = RealtimeEnvironment(factor=global_speed_factor, initial_time=current_time_paused)
        stats = Stats()
        stats.delivered_count = delivered_count_paused  # 이전 배송 수 유지
        agvs = []
        cell_blocked = {}

        # AGV 재생성 (이전 위치와 상태 유지)
        for i, (pos, cargo, path) in enumerate(zip(current_positions, current_cargos, current_paths)):
            agv = AGV(i, pos)  # 현재 위치로 초기화
            agv.cargo = cargo  # 화물 상태 유지
            agv.path = path  # 현재 경로 유지
            agvs.append(agv)
            env.process(agv_process(agv, env, stats, SIM_DURATION, cell_blocked))

        # 통계 기록 프로세스 재시작
        env.process(record_stats(env, SIM_DURATION, stats))
        env.process(record_interval_stats(env, SIM_DURATION, stats))

        # 전역 변수 업데이트
        SIM_ENV = env
        SIM_STATS = stats
        SIM_AGVS = agvs

        socketio.start_background_task(run_continued_simulation, env, SIM_DURATION)

    # Add these new Socket.IO event handlers
    @socketio.on('pause_simulation')
    def handle_pause():
        try:
            if pause_simulation():
                emit('simulation_status', {'status': 'paused'})
                emit('status', {'message': 'Simulation paused'})
            else:
                emit('error', {'message': 'Cannot pause - simulation not running or already paused'})
        except Exception as e:
            emit('error', {'message': str(e)})


    @socketio.on('resume_simulation')
    def handle_resume():
        try:
            if resume_simulation():
                emit('simulation_status', {'status': 'running'})
                emit('status', {'message': 'Simulation resumed'})
            else:
                emit('error', {'message': 'Cannot resume - simulation not paused or not running'})
        except Exception as e:
            emit('error', {'message': str(e)})


    # Modify the update_loop_task to include pause status
    def update_loop_task():
        """1초마다 현재 상태를 클라이언트에 전송하는 루프."""
        while True:
            if not SIM_RUNNING:
                eventlet.sleep(1.0)
                continue

            current_time = 0
            delivered_count = 0
            agv_positions = {}
            cnt=0
            state=[]
            if SIM_ENV is not None and SIM_STATS is not None and SIM_AGVS is not None:
                current_time = round(SIM_ENV.now, 2)
                delivered_count = SIM_STATS.delivered_count
                for agv in SIM_AGVS:
                    cnt+=1
                    state.append({'agv_id':agv.id, 'location_x':agv.pos[0], 'location_y':agv.pos[1]})
                    agv_positions[agv.id] = (round(agv.pos[0], 1), round(agv.pos[1], 1))

            positions = {
                'sim_time': current_time,
                'agv_positions': agv_positions,
                'delivered_count': delivered_count,
                'paused': SIM_PAUSED
            }
            socketio.emit('message', {'agv_count': cnt, 'agvs':state})
            eventlet.sleep(UPDATE_INTERVAL)




    # -----------------------------------------
    # 서버 시작 시 update_loop_task 실행
    # -----------------------------------------
    # def start_background_loops():
    #     """시작 시 update_loop_task를 백그라운드로 실행"""
    socketio.start_background_task(update_loop_task)

    return app, socketio



def run_server(port):
    """Start multiple server instances on different ports"""
    try:
        multiprocessing.set_start_method('spawn')
    except RuntimeError:
        # Method already set
        pass

    app, socketio = create_app(port)
    print(f"Starting server on port {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False)


def start_multi_server():
    """Start multiple server instances on different ports"""
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

        # Wait for all processes
        for process in processes:
            process.join()

    except KeyboardInterrupt:
        print("\nShutting down servers...")
        for process in processes:
            process.terminate()

        # Wait for processes to terminate
        for process in processes:
            process.join()

        print("All servers shut down successfully")
        sys.exit(0)


if __name__ == '__main__':
    # Set start method for multiprocessing
    multiprocessing.set_start_method('spawn')
    start_multi_server()