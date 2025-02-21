from flask import Flask, Response, request, jsonify
import simpy
from collections import deque, defaultdict
import random
import statistics
import time
import json

app = Flask(__name__)

################################
# 상수 정의
################################
REPEAT_RUNS = 15          # 반복실험 횟수 (최종 결과용)
WARMUP_PERIOD = 30        # 30초 이전 픽업은 통계에서 제외
CHECK_INTERVAL = 3000     # 3000초마다 delivered_count 기록
MOVE_RATE = 1.0           # 이동 대기 시간의 exponential 분포 파라미터 (평균 1초)
STEP_SIZE = 0.01          # 연속 이동 시 0.01 단위

################################
# 맵 정의 (격자)
################################
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

# 선반 및 출구 좌표 (정수 튜플)
shelf_coords = [(2, 2), (2, 4), (2, 6), (5, 2), (5, 4), (5, 6)]
exit_coords  = [(0, c) for c in range(COLS) if MAP[0][c] == 2]

################################
# controlled_timeout 함수
################################
def controlled_timeout(env, duration, speed):
    """SimPy timeout 후, speed가 'max'가 아니면 실제 time.sleep(duration/speed)를 실행"""
    yield env.timeout(duration)
    if speed != "max":
        time.sleep(duration / speed)

################################
# BFS 경로 탐색 함수
################################
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

################################
# AGV 클래스
################################
class AGV:
    def __init__(self, agv_id, start_pos):
        self.id = agv_id
        self.start_pos = (float(start_pos[0]), float(start_pos[1]))
        self.pos = (float(start_pos[0]), float(start_pos[1]))
        self.path = []  # 정수 좌표 리스트
        self.cargo = 0
        self.pickup_time = None
    def __repr__(self):
        return f"AGV(id={self.id}, pos={self.pos}, cargo={self.cargo})"

################################
# 전역 통계 클래스
################################
class Stats:
    def __init__(self):
        self.delivered_count = 0
        self.delivered_record = defaultdict(int)
        self.delivered_history = {}
        self.agv_stats = defaultdict(lambda: {"count": 0, "times": [], "wait_times": [], "travel_times": [],
                                               "location_log": []})

################################
# 픽업/하역 프로세스 (speed 인자 추가)
################################
def do_pick(agv, env, stats, cell_blocked, speed):
    now = env.now
    cell_blocked[agv.pos] = now + 10
    yield from controlled_timeout(env, 10, speed)
    agv.cargo = 1
    if now >= WARMUP_PERIOD:
        agv.pickup_time = now
    stats.agv_stats[agv.id]["count"] += 1

def do_drop(agv, env, stats, cell_blocked, speed):
    start_drop = env.now
    cell_blocked[agv.pos] = start_drop + 10
    yield from controlled_timeout(env, 10, speed)
    drop_finish = env.now
    if agv.pickup_time is not None:
        duration = drop_finish - agv.pickup_time
        stats.agv_stats[agv.id]["times"].append(duration)
        agv.pickup_time = None
    agv.cargo = 0
    stats.delivered_count += 1

################################
# AGV 비동기 프로세스 (연속 이동 및 작업, speed 인자 추가)
################################
def agv_process(agv, env, stats, sim_duration, cell_blocked, speed, print_positions=False):
    while env.now < sim_duration:
        if not agv.path or len(agv.path) <= 1:
            if agv.cargo == 0:
                preferred = shelf_coords[agv.id % len(shelf_coords)]
                target = preferred if random.random() < 0.5 else random.choice(shelf_coords)
                path = bfs_path((int(agv.pos[0]), int(agv.pos[1])), target, env.now, cell_blocked, defaultdict(int))
                agv.path = path if path is not None else []
            else:
                target = find_nearest_exit((int(agv.pos[0]), int(agv.pos[1])))
                path = bfs_path((int(agv.pos[0]), int(agv.pos[1])), target, env.now, cell_blocked, defaultdict(int))
                agv.path = path if path is not None else []
        if len(agv.path) > 1:
            next_cell = agv.path[1]
            current_pos = agv.pos
            dx = next_cell[0] - current_pos[0]
            dy = next_cell[1] - current_pos[1]
            distance = (dx**2 + dy**2)**0.5
            num_steps = int(distance / STEP_SIZE)
            for i in range(num_steps):
                current_pos = (current_pos[0] + STEP_SIZE * dx / distance,
                               current_pos[1] + STEP_SIZE * dy / distance)
                yield from controlled_timeout(env, STEP_SIZE, speed)
                rounded_pos = (round(current_pos[0],2), round(current_pos[1],2))
                stats.agv_stats[agv.id]["location_log"].append((env.now, rounded_pos))
                if print_positions:
                    print(f"[{env.now:.2f} sec] AGV{agv.id} 위치: {rounded_pos}")
            remaining = distance - num_steps * STEP_SIZE
            if remaining > 0:
                current_pos = (current_pos[0] + remaining * dx / distance,
                               current_pos[1] + remaining * dy / distance)
                yield from controlled_timeout(env, remaining, speed)
                rounded_pos = (round(current_pos[0],2), round(current_pos[1],2))
                stats.agv_stats[agv.id]["location_log"].append((env.now, rounded_pos))
                if print_positions:
                    print(f"[{env.now:.2f} sec] AGV{agv.id} 위치: {rounded_pos}")
            agv.pos = (float(current_pos[0]), float(current_pos[1]))
            agv.path.pop(0)
        else:
            yield from controlled_timeout(env, 0.1, speed)
        if agv.pos in shelf_coords and agv.cargo == 0:
            yield env.process(do_pick(agv, env, stats, cell_blocked, speed))
            agv.path = []
            yield from controlled_timeout(env, random.uniform(0.5,1.5), speed)
        elif agv.pos in exit_coords and agv.cargo == 1:
            yield env.process(do_drop(agv, env, stats, cell_blocked, speed))
            agv.path = []
            yield from controlled_timeout(env, random.uniform(0.5,1.5), speed)

################################
# 통계 기록 프로세스
################################
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

################################
# 단일 시뮬레이션 실행 함수 (1회, speed 인자 및 output_mode 추가)
################################
def run_one_sim(agv_count, sim_duration, run_id=1, speed="max", output_mode="live"):
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
    if output_mode == "final":
        print_positions = False
    else:
        print_positions = True if agv_count >= 3 and speed != "max" else False
    for agv in agvs:
        env.process(agv_process(agv, env, stats, sim_duration, cell_blocked, speed, print_positions))
    env.process(record_stats(env, sim_duration, stats))
    env.process(record_interval_stats(env, sim_duration, stats))
    env.run(until=sim_duration)
    final_agv_stats = {}
    for agv_id, data in stats.agv_stats.items():
        count = data["count"]
        times = data["times"]
        avg_time = sum(times)/len(times) if times else 0
        final_agv_stats[agv_id] = {"count": count, "times": times, "avg_time": avg_time,
                                   "wait_times": data["wait_times"],
                                   "travel_times": data["travel_times"],
                                   "location_log": data["location_log"]}
    result = {
        "end_time": sim_duration,
        "delivered_count": stats.delivered_count,
        "delivered_history": stats.delivered_history,
        "delivered_record": dict(stats.delivered_record),
        "agv_stats": final_agv_stats
    }
    return result

################################
# 최적화 분석 함수 (simulate_for_agv_count)
################################
def simulate_for_agv_count(agv_count, sim_duration, speed):
    run_results = []
    for run_id in range(1, REPEAT_RUNS+1):
        res = run_one_sim(agv_count, sim_duration, run_id, speed, output_mode="final")
        run_results.append(res)
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

################################
# Flask 엔드포인트: 최종 결과 반환
################################
@app.route('/simulate', methods=['GET'])
def simulate_endpoint():
    try:
        agv_count = int(request.args.get('agv_count', 3))
        duration = int(request.args.get('duration', 3000))
        speed_str = request.args.get('speed', "1")
        output = request.args.get('output', "live")
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    if speed_str == "max":
        speed = "max"
    else:
        try:
            speed = float(speed_str)
            if speed <= 0:
                return jsonify({"error": "speed must be positive or 'max'"}), 400
        except:
            return jsonify({"error": "Invalid speed value"}), 400
    result = run_one_sim(agv_count, duration, run_id=1, speed=speed, output_mode=output)
    if output == "final":
        for agv in result["agv_stats"].values():
            agv["location_log"] = []  # 위치 로그 제거
    return jsonify(result)

################################
# Flask 엔드포인트: 스트리밍 시뮬레이션 (실시간 업데이트)
################################
@app.route('/stream', methods=['GET'])
def stream_endpoint():
    try:
        agv_count = int(request.args.get('agv_count', 3))
        duration = int(request.args.get('duration', 3000))
        speed_str = request.args.get('speed', "1")
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    if speed_str == "max":
        speed = "max"
    else:
        try:
            speed = float(speed_str)
            if speed <= 0:
                return jsonify({"error": "speed must be positive or 'max'"}), 400
        except:
            return jsonify({"error": "Invalid speed value"}), 400
    def event_stream():
        for state in simulation_stream(agv_count, duration, speed):
            yield f"data: {state}\n\n"
    return Response(event_stream(), mimetype="text/event-stream")

################################
# Flask 엔드포인트: 최적화 분석
################################
@app.route('/simulate_opt', methods=['GET'])
def simulate_opt_endpoint():
    try:
        min_agv = int(request.args.get('min_agv', 3))
        max_agv = int(request.args.get('max_agv', 6))
        duration = int(request.args.get('duration', 3000))
        speed_str = request.args.get('speed', "1")
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    if speed_str == "max":
        speed = "max"
    else:
        try:
            speed = float(speed_str)
            if speed <= 0:
                return jsonify({"error": "speed must be positive or 'max'"}), 400
        except:
            return jsonify({"error": "Invalid speed value"}), 400
    results = []
    for agv_count in range(min_agv, max_agv+1):
        res = simulate_for_agv_count(agv_count, duration, speed)
        results.append(res)
    return jsonify({"optimization_results": results})

################################
# 스트리밍 시뮬레이션 제너레이터
################################
def simulation_stream(agv_count, sim_duration, speed):
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
        env.process(agv_process(agv, env, stats, sim_duration, cell_blocked, speed, print_positions=True))
    env.process(record_stats(env, sim_duration, stats))
    env.process(record_interval_stats(env, sim_duration, stats))
    
    update_interval = 0.1
    last_update_real = time.time()
    while env.now < sim_duration:
        env.run(until=env.now + update_interval)
        state = {
            "sim_time": round(env.now, 2),
            "agv_positions": {agv.id: (round(agv.pos[0],2), round(agv.pos[1],2)) for agv in agvs},
            "delivered_count": stats.delivered_count
        }
        yield json.dumps(state) + "\n"
        if speed != "max":
            elapsed = time.time() - last_update_real
            sleep_time = max(0, update_interval/speed - elapsed)
            time.sleep(sleep_time)
            last_update_real = time.time()

################################
# Flask 메인 실행
################################
if __name__ == "__main__":
    app.run(debug=True)
