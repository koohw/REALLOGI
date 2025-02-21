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

# 선반 및 출구 좌표
shelf_coords = [(2, 2), (2, 4), (2, 6), (5, 2), (5, 4), (5, 6)]
exit_coords  = [(0, c) for c in range(COLS) if MAP[0][c] == 2]

################################
# BFS 경로 탐색 함수
################################
def bfs_path(start, goal, current_time, cell_blocked, congestion_count):
    """
    현재 시간보다 늦게까지 점유된 셀(cell_blocked)을 피하는 BFS.
    여기서는 cell_blocked와 congestion_count를 고려하긴 하지만,
    주로 정적 격자상에서 경로를 찾는 용도로 사용합니다.
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
        self.start_pos = start_pos
        self.pos = start_pos
        self.path = []       # 경로(목표지점까지의 셀 리스트)
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
        # AGV별 통계: 픽업 횟수, 사이클 시간 (픽업~하역 사이), 추가로 대기 및 이동 시간 합산은 개별 run 후 별도로 산출
        self.agv_stats = defaultdict(lambda: {"count": 0, "times": [], "wait_times": [], "travel_times": []})

################################
# 픽업/하역 프로세스
################################
def do_pick(agv, env, stats, cell_blocked):
    now = env.now
    # 픽업 작업 동안 해당 셀은 10초간 점유됨
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
# AGV 비동기 프로세스 (이동 및 작업)
################################
def agv_process(agv, env, stats, sim_duration, cell_blocked):
    """
    AGV는 다음을 반복:
      1. 경로가 없으면 cargo 상태에 따라 목표(선반 또는 출구)를 선택하고 bfs_path로 경로 생성.
      2. 경로가 있으면, expovariate(MOVE_RATE)에 따른 지연 후 경로의 다음 셀로 이동.
      3. 이동 후 선반이면 픽업, 출구이면 하역 작업 수행.
      4. 작업 후 경로 초기화하고, 사이클 후 짧은 딜레이(cooldown)를 둠.
    """
    while env.now < sim_duration:
        if not agv.path or len(agv.path) <= 1:
            if agv.cargo == 0:
                # 선호 선반: AGV의 ID에 따른 기본 선반 (절반 확률로)
                preferred = shelf_coords[agv.id % len(shelf_coords)]
                target = preferred if random.random() < 0.5 else random.choice(shelf_coords)
                path = bfs_path(agv.pos, target, env.now, cell_blocked, defaultdict(int))
                agv.path = path if path is not None else []
            else:
                target = find_nearest_exit(agv.pos)
                path = bfs_path(agv.pos, target, env.now, cell_blocked, defaultdict(int))
                agv.path = path if path is not None else []
        
        if len(agv.path) > 1:
            yield env.timeout(random.expovariate(MOVE_RATE))
            agv.path.pop(0)
            agv.pos = agv.path[0]
        else:
            yield env.timeout(0.1)
        
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
    # 단일 run에 대해 시뮬레이션을 실행하고 run별 결과를 반환합니다.
    env = simpy.Environment()
    cell_blocked = {}   # 픽업/하역 중 셀 점유 관리
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
    
    # run별 AGV 통계: 각 AGV의 픽업 횟수와 평균 사이클 시간 (픽업~하역)
    final_agv_stats = {}
    for agv_id, data in stats.agv_stats.items():
        count = data["count"]
        times = data["times"]
        avg_time = sum(times) / len(times) if times else 0
        final_agv_stats[agv_id] = {"count": count, "times": times, "avg_time": avg_time,
                                   "wait_times": data["wait_times"],
                                   "travel_times": data["travel_times"]}
    
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
    # 주어진 AGV 대수에 대해 REPEAT_RUNS 번 시뮬레이션한 후,
    # 각 run의 결과를 집계하여 평균 및 표준편차 등 주요 지표를 산출합니다.
    run_results = []
    for run_id in range(1, REPEAT_RUNS + 1):
        res = run_one_sim(agv_count, sim_duration, run_id)
        run_results.append(res)
    # 각 run의 총 배송량
    delivered_counts = [res["delivered_count"] for res in run_results]
    avg_delivered = statistics.mean(delivered_counts)
    std_delivered = statistics.stdev(delivered_counts) if len(delivered_counts) > 1 else 0
    # 시간당 처리량 (deliveries per hour)
    throughput = avg_delivered / sim_duration * 3600
    # AGV당 평균 배송량
    delivered_per_agv = avg_delivered / agv_count
    # 평균 사이클 시간 (모든 AGV에서 발생한 사이클 시간의 평균)
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
        # 단일 모드: 특정 AGV 대수로 시뮬레이션 실행
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
        # (추가) 구간별 delivered_count 등은 기존과 같이 출력할 수 있음...
        # AGV별 통계도 출력
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
        # 최적화 모드: 최소 ~ 최대 AGV 대수에 대해 시뮬레이션 수행하고 성능 지표 비교
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
