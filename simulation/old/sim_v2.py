import simpy
from collections import deque, defaultdict
import random
import statistics

################################
# 상수 정의
################################
REPEAT_RUNS = 15          # 15회 반복 실험
WARMUP_PERIOD = 30        # 30초 이전 픽업은 통계 제외
CHECK_INTERVAL = 3000     # 3000초마다 delivered_count 기록
MOVE_RATE = 1.0           # 이동 대기 시간의 exponential 분포 파라미터 (평균 1초)
STEP_SIZE = 0.01          # 연속 이동 시 0.01 단위로 이동

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
# BFS 경로 탐색 함수
################################
def bfs_path(start, goal, current_time, cell_blocked, congestion_count):
    """
    현재 시간보다 늦게까지 점유된 셀(cell_blocked)을 피하는 BFS.
    주로 정적 격자상에서 경로를 찾는 용도.
    """
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
    """현재 위치에서 맨해튼 거리가 가장 가까운 출구 반환"""
    return min(exit_coords, key=lambda e: abs(pos[0] - e[0]) + abs(pos[1] - e[1]))

################################
# AGV 클래스
################################
class AGV:
    def __init__(self, agv_id, start_pos):
        self.id = agv_id
        # 위치를 실수형 좌표로 저장 (예: (0.0, 8.0))
        self.start_pos = (float(start_pos[0]), float(start_pos[1]))
        self.pos = (float(start_pos[0]), float(start_pos[1]))
        self.path = []       # 경로 (목표지점까지의 셀 리스트; 각 셀은 정수 튜플)
        self.cargo = 0       # 0: 비적재, 1: 적재
        self.pickup_time = None  # 워밍업 이후 픽업 시점 기록
    def __repr__(self):
        return f"AGV(id={self.id}, pos={self.pos}, cargo={self.cargo})"

################################
# 전역 통계 클래스
################################
class Stats:
    def __init__(self):
        self.delivered_count = 0
        self.delivered_record = defaultdict(int)   # key: 시간(초), value: delivered_count
        self.delivered_history = {}                # CHECK_INTERVAL마다 기록
        # AGV별 통계: 픽업 횟수, 사이클 시간(픽업~하역), 대기 및 이동 시간, 위치 로그
        self.agv_stats = defaultdict(lambda: {"count": 0, "times": [], "wait_times": [], "travel_times": [],
                                               "location_log": []})

################################
# 픽업/하역 프로세스
################################
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

################################
# AGV 비동기 프로세스 (연속 이동 및 작업)
################################
def agv_process(agv, env, stats, sim_duration, cell_blocked, print_positions=False):
    """
    AGV는 다음을 반복:
      1. 경로가 없으면 cargo 상태에 따라 목표(선반 또는 출구)를 선택하고 bfs_path로 경로 생성.
      2. 경로가 있으면, 목표 셀까지 연속적으로 STEP_SIZE 단위로 이동.
      3. 이동 후 선반이면 픽업, 출구이면 하역 작업 수행.
      4. 작업 후 경로 초기화하고 짧은 딜레이(cooldown)를 둠.
      5. 각 이동 시 (env.now, 위치)를 기록하고, print_positions True이면 출력.
    """
    while env.now < sim_duration:
        # 경로 생성
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
        
        # 연속 이동: 다음 셀 중심까지 0.01 단위로 이동
        if len(agv.path) > 1:
            next_cell = agv.path[1]  # 정수 튜플 (예: (x, y))
            current_pos = agv.pos
            dx = next_cell[0] - current_pos[0]
            dy = next_cell[1] - current_pos[1]
            distance = (dx**2 + dy**2)**0.5  # 보통 1
            num_steps = int(distance / STEP_SIZE)
            for i in range(num_steps):
                # 현재 위치 업데이트
                current_pos = (current_pos[0] + STEP_SIZE * dx / distance,
                               current_pos[1] + STEP_SIZE * dy / distance)
                yield env.timeout(STEP_SIZE)  # 0.01초마다 이동
                stats.agv_stats[agv.id]["location_log"].append((env.now, current_pos))
                if print_positions:
                    print(f"[{env.now:.2f} sec] AGV{agv.id} 위치: {current_pos}")
            # 나머지 거리 처리
            remaining = distance - num_steps * STEP_SIZE
            if remaining > 0:
                current_pos = (current_pos[0] + remaining * dx / distance,
                               current_pos[1] + remaining * dy / distance)
                yield env.timeout(remaining)
                stats.agv_stats[agv.id]["location_log"].append((env.now, current_pos))
                if print_positions:
                    print(f"[{env.now:.2f} sec] AGV{agv.id} 위치: {current_pos}")
            # 도착 후 정확한 위치 설정 (정수 셀 중심)
            agv.pos = (float(next_cell[0]), float(next_cell[1]))
            agv.path.pop(0)
        else:
            yield env.timeout(0.1)
        
        # 작업 수행
        if agv.pos in shelf_coords and agv.cargo == 0:
            yield env.process(do_pick(agv, env, stats, cell_blocked))
            agv.path = []
            yield env.timeout(random.uniform(0.5, 1.5))
        elif agv.pos in exit_coords and agv.cargo == 1:
            yield env.process(do_drop(agv, env, stats, cell_blocked))
            agv.path = []
            yield env.timeout(random.uniform(0.5, 1.5))

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
# 단일 시뮬레이션 실행 함수 (1회)
################################
def run_one_sim(agv_count, sim_duration, run_id=1):
    env = simpy.Environment()
    cell_blocked = {}   # 픽업/하역 중 셀 점유 관리
    stats = Stats()
    
    agvs = []
    start_row = 8
    start_cols = [0, 2, 4, 6, 1, 3, 5]
    for i in range(agv_count):
        pos = (start_row, start_cols[i % len(start_cols)])
        # 시작 위치를 float로 변환
        agv = AGV(i, pos)
        agvs.append(agv)
    
    # AGV 대수가 3 이상이면 실시간 위치 출력 활성화
    print_positions = True if agv_count >= 3 else False
    
    for agv in agvs:
        env.process(agv_process(agv, env, stats, sim_duration, cell_blocked, print_positions))
    
    env.process(record_stats(env, sim_duration, stats))
    env.process(record_interval_stats(env, sim_duration, stats))
    
    env.run(until=sim_duration)
    
    final_agv_stats = {}
    for agv_id, data in stats.agv_stats.items():
        count = data["count"]
        times = data["times"]
        avg_time = sum(times) / len(times) if times else 0
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
# 최적화 분석을 위한 다중 시뮬레이션 함수
################################
def simulate_for_agv_count(agv_count, sim_duration):
    run_results = []
    for run_id in range(1, REPEAT_RUNS + 1):
        res = run_one_sim(agv_count, sim_duration, run_id)
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
# 메인 함수
################################
def main():
    mode = input("단일 시뮬레이션 모드로 실행하시겠습니까? (y/n, n이면 AGV 최적화 분석 모드): ").strip().lower()
    sim_duration = int(input("시뮬레이션 종료 시간 (초, 예: 28800): "))
    
    if mode == "y":
        agv_count = int(input("AGV 대수: "))
        all_runs_end_time = []
        all_runs_final_delivered = []
        all_runs_delivered_record = []
        all_runs_agv_stats = []
        for run_i in range(1, REPEAT_RUNS + 1):
            result = run_one_sim(agv_count, sim_duration, run_i)
            all_runs_end_time.append(result["end_time"])
            all_runs_final_delivered.append(result["delivered_count"])
            all_runs_delivered_record.append(result["delivered_record"])
            all_runs_agv_stats.append(result["agv_stats"])
        avg_final_delivered = statistics.mean(all_runs_final_delivered)
        std_final_delivered = statistics.stdev(all_runs_final_delivered) if len(all_runs_final_delivered) > 1 else 0
        print("\n===========================")
        print("Summary of 15 Simulation Runs")
        print("===========================")
        print(f" - Simulation End Time: {sim_duration:.2f} sec")
        print(f" - Average Delivered Count: {avg_final_delivered:.2f} (std: {std_final_delivered:.2f})")
        agv_counts = defaultdict(list)
        agv_avg_durations = defaultdict(list)
        for agv_stats in all_runs_agv_stats:
            for aid, st in agv_stats.items():
                agv_counts[aid].append(st["count"])
                agv_avg_durations[aid].append(st["avg_time"])
        print("\n=== Average AGV Statistics over 15 Runs ===")
        for aid in sorted(agv_counts.keys()):
            avg_count = statistics.mean(agv_counts[aid])
            std_count = statistics.stdev(agv_counts[aid]) if len(agv_counts[aid]) > 1 else 0
            avg_duration = statistics.mean(agv_avg_durations[aid])
            std_duration = statistics.stdev(agv_avg_durations[aid]) if len(agv_avg_durations[aid]) > 1 else 0
            print(f" AGV{aid}: Average Pickups = {avg_count:.2f} (std: {std_count:.2f}), "
                  f"Average Cycle Time = {avg_duration:.2f} s (std: {std_duration:.2f} s)")
    else:
        min_agv = int(input("최소 AGV 대수: "))
        max_agv = int(input("최대 AGV 대수: "))
        results = []
        print("\n최적화 분석 진행 중...")
        for agv_count in range(min_agv, max_agv + 1):
            res = simulate_for_agv_count(agv_count, sim_duration)
            results.append(res)
            print(f"AGV {agv_count:>2d}: Delivered = {res['avg_delivered']:.2f} (std: {res['std_delivered']:.2f}), " +
                  f"Throughput = {res['throughput_per_hour']:.2f} per hour, " +
                  f"Per AGV = {res['delivered_per_agv']:.2f}, " +
                  f"Cycle = {res['avg_cycle']:.2f} s, Wait = {res['avg_wait']:.2f} s, Travel = {res['avg_travel']:.2f} s")
        print("\n===============================")
        print("최적화 분석 결과 (AGV 수에 따른 성능 지표)")
        print("===============================")
        print(f"{'AGV Count':>10s} | {'Avg Delivered':>14s} | {'Std':>7s} | {'Throughput/hr':>14s} | {'Per AGV':>8s} | {'Cycle (s)':>10s} | {'Wait (s)':>9s} | {'Travel (s)':>11s}")
        print("-" * 95)
        for res in results:
            print(f"{res['agv_count']:>10d} | {res['avg_delivered']:>14.2f} | {res['std_delivered']:>7.2f} | " +
                  f"{res['throughput_per_hour']:>14.2f} | {res['delivered_per_agv']:>8.2f} | " +
                  f"{res['avg_cycle']:>10.2f} | {res['avg_wait']:>9.2f} | {res['avg_travel']:>11.2f}")
            
if __name__ == "__main__":
    main()
