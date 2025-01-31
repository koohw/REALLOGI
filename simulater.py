import simpy
from collections import deque, defaultdict
import random

REPEAT_RUNS = 15          # 15회 반복 실험
WARMUP_PERIOD = 30        # 30초 이전 픽업은 통계(평균 소요시간) 제외
CHECK_INTERVAL = 3000     # 3000초 마다 delivered_count 기록

################################
# 맵 정의
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

# 선반 / 출구 위치
shelf_coords = [(2,2),(2,4),(2,6),(5,2),(5,4),(5,6)]
exit_coords  = [(0,c) for c in range(COLS) if MAP[0][c] == 2]


def bfs_path(start, goal, current_time, cell_blocked, congestion_count):
    """cell_blocked 칸(현재 시간보다 늦게까지 점유)을 회피하는 BFS"""
    if start == goal:
        return [start]
    visited = {start: None}
    queue = deque([start])

    while queue:
        r, c = queue.popleft()
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr, nc = r+dr, c+dc

            # 맵 범위 확인
            if not (0 <= nr < ROWS and 0 <= nc < COLS):
                continue

            # 벽 체크
            if MAP[nr][nc] == 1:
                continue

            # 작업 중 칸 체크
            if (nr, nc) in cell_blocked and cell_blocked[(nr, nc)] > current_time:
                congestion_count[(nr, nc)] += 1
                continue

            # 이미 방문
            if (nr, nc) in visited:
                continue

            visited[(nr,nc)] = (r,c)
            queue.append((nr,nc))

            if (nr, nc) == goal:
                # goal까지 도달 -> 경로 복원
                path = []
                cur = (nr,nc)
                while cur is not None:
                    path.append(cur)
                    cur = visited[cur]
                path.reverse()
                return path
    return None


################################
# AGV 클래스
################################
class AGV:
    """AGV 기본 속성/상태"""
    def __init__(self, agv_id, start_pos, env, priority):
        self.id = agv_id
        self.env = env
        self.start_pos = start_pos
        self.pos = start_pos
        self.path = []
        self.priority = priority
        self.running = True

        self.cargo = 0          # 0: 비적재, 1: 적재
        self.pickup_time = None # 워밍업 이후 픽업 시점

    def __repr__(self):
        return f"AGV(id={self.id}, pos={self.pos}, cargo={self.cargo})"


################################
# 코디네이터
################################
class Coordinator:
    def __init__(self, env, agvs, sim_duration):
        self.env = env
        self.agvs = agvs
        self.sim_duration = sim_duration
        self.end_time = None

        # 아래 속성은 run_one_sim(...)에서 주입
        #   - cell_blocked, congestion_count, agv_stats, delivered_count
        #   - shelf_coords, exit_coords
        #   - delivered_history (3000초 체크)
        #   - delivered_record (매초 delivered_count 기록)

        env.process(self.coordinator_run())

    def coordinator_run(self):
        """1초씩 시뮬레이션 진행하여 sim_duration까지 도달."""
        for _ in range(self.sim_duration):
            now = self.env.now

            # (1) 이동 요청
            move_requests = []
            for agv in self.agvs:
                if agv.running:
                    self.update_target(agv, now)
                    if len(agv.path) > 1:
                        next_cell = agv.path[1]
                        move_requests.append((agv, next_cell))

            # (2) 충돌 처리
            from collections import defaultdict
            cell_map = defaultdict(list)
            for agv, cell in move_requests:
                cell_map[cell].append(agv)

            losers = []
            for cell, arr in cell_map.items():
                if len(arr) > 1:
                    # 우선순위 높은 것부터
                    arr.sort(key=lambda x: x.priority, reverse=True)
                    for lose_agv in arr[1:]:
                        losers.append(lose_agv)

            for lose_agv in losers:
                self.recalc_path(lose_agv, now)

            # (3) 최종 이동
            final_moves = []
            for agv, cell in move_requests:
                if agv not in losers and len(agv.path) > 1 and agv.path[1] == cell:
                    final_moves.append((agv, cell))

            for agv, cell in final_moves:
                agv.path.pop(0)
                agv.pos = cell

            # (4) 픽업/하역
            yield self.handle_pick_drop()

            # (5) 1초 경과
            yield self.env.timeout(1)
            now = self.env.now

            # (6) 매초마다 delivered_count 기록
            self.delivered_record[now] = self.delivered_count

            # (7) 기존 CHECK_INTERVAL(3000초) 체크
            if now in self.delivered_history:
                self.delivered_history[now] = self.delivered_count

        self.end_time = self.env.now

    def handle_pick_drop(self):
        """픽업/하역 작업을 진행 (10초)"""
        events = []
        now = self.env.now
        for agv in self.agvs:
            if not agv.running:
                continue

            # 선반 픽업
            if agv.pos in self.shelf_coords and agv.cargo == 0:
                events.append(self.env.process(self.do_pick(agv)))

            # 출구 하역
            elif agv.pos in exit_coords and agv.cargo > 0:
                events.append(self.env.process(self.do_drop(agv)))

        if events:
            return simpy.events.AllOf(self.env, events)
        else:
            return self.env.timeout(0)

    def do_pick(self, agv):
        now = self.env.now
        # 10초간 점유
        self.cell_blocked[agv.pos] = now + 10
        yield self.env.timeout(10)

        # 픽업
        agv.cargo = 1
        if now >= WARMUP_PERIOD:
            agv.pickup_time = now
        self.agv_stats[agv.id]["count"] += 1

    def do_drop(self, agv):
        now = self.env.now
        # 10초간 점유
        self.cell_blocked[agv.pos] = now + 10
        yield self.env.timeout(10)

        # 하역
        if agv.pickup_time is not None:
            dur = now - agv.pickup_time
            self.agv_stats[agv.id]["times"].append(dur)
            agv.pickup_time = None

        agv.cargo = 0
        self.delivered_count += 1

    def update_target(self, agv, now):
        """목적지 경로가 없으면 새 경로 선택"""
        if len(agv.path) <= 1:
            if agv.cargo == 0:
                # 무한재고 → 아무 선반 임의
                shelf = random.choice(shelf_coords)
                p = bfs_path(agv.pos, shelf, now, self.cell_blocked, self.congestion_count)
                agv.path = p if p else []
            else:
                # 짐 있음 -> 최근접 출구
                ex = self.find_nearest_exit(agv.pos)
                p = bfs_path(agv.pos, ex, now, self.cell_blocked, self.congestion_count)
                agv.path = p if p else []

    def find_nearest_exit(self, pos):
        return min(exit_coords, key=lambda e: abs(pos[0]-e[0]) + abs(pos[1]-e[1]))

    def recalc_path(self, agv, now):
        if len(agv.path) > 1:
            goal = agv.path[-1]
            newp = bfs_path(agv.pos, goal, now, self.cell_blocked, self.congestion_count)
            agv.path = newp if newp else []


########################################
# 단일 시뮬레이션(1회) 수행 후 결과 반환
########################################
def run_one_sim(agv_count, sim_duration, run_id=1):
    print(f"\n=== [Run {run_id}] 시뮬레이션 시작 ===")

    env = simpy.Environment()

    cell_blocked = {}
    congestion_count = defaultdict(int)
    agv_stats = defaultdict(lambda: {"count": 0, "times": []})

    # AGV 생성
    agvs = []
    start_row = 8
    start_cols = [0,2,4,6,1,3,5]
    for i in range(agv_count):
        r, c = start_row, start_cols[i % len(start_cols)]
        prio = agv_count - i
        agv = AGV(i, (r,c), env, prio)
        agvs.append(agv)

    # 코디네이터
    coord = Coordinator(env, agvs, sim_duration)
    coord.cell_blocked = cell_blocked
    coord.congestion_count = congestion_count
    coord.agv_stats = agv_stats
    coord.delivered_count = 0

    coord.shelf_coords = shelf_coords
    coord.exit_coords = exit_coords

    # 3000초 간격(기존)
    delivered_history = {}
    for t in range(CHECK_INTERVAL, sim_duration+1, CHECK_INTERVAL):
        delivered_history[t] = 0
    coord.delivered_history = delivered_history

    # 매초 기록
    delivered_record = defaultdict(int)
    delivered_record[0] = 0
    coord.delivered_record = delivered_record

    # 시뮬레이션 실행
    env.run(until=sim_duration)

    end_time = coord.end_time if coord.end_time is not None else env.now
    delivered_count = coord.delivered_count

    # AGV별 통계
    final_agv_stats = {}
    for aid, data in agv_stats.items():
        cnt = data["count"]
        times = data["times"]
        avg_t = sum(times)/len(times) if times else 0
        final_agv_stats[aid] = {
            "count": cnt,
            "times": times,
            "avg_time": avg_t
        }

    print(f"=== [Run {run_id}] 종료 시간: {end_time} sec ===")
    print(f" 총 하역 건수: {delivered_count}")
    for aid, st in final_agv_stats.items():
        print(f"  AGV{aid}: 픽업={st['count']}회, 평균 소요={st['avg_time']:.2f}s")

    if congestion_count:
        max_blocked_cell = max(congestion_count, key=congestion_count.get)
        print(f" 가장 정체가 심했던 칸: {max_blocked_cell} (차단 횟수={congestion_count[max_blocked_cell]})")
    else:
        print(" 정체 기록 없음.")

    return {
        "end_time": end_time,
        "delivered_count": delivered_count,
        "delivered_history": dict(delivered_history),  # 3000초 요약
        "delivered_record": dict(delivered_record),    # 매초 기록
        "agv_stats": final_agv_stats,
        "congestion_count": dict(congestion_count)
    }

########################################
# 헬퍼 함수: t 이하 가장 큰 key의 value 가져오기
########################################
def get_delivered_up_to(record, t):
    """
    record: {time: delivered_count} 매초 누적 기록
    t 이하인 가장 큰 time에 대한 delivered_count를 반환
    """
    # t 이하인 키들 중 최대값 찾기
    valid_keys = [k for k in record.keys() if k <= t]
    if not valid_keys:
        return 0
    return record[max(valid_keys)]

########################################
# 메인 (15회 반복)
########################################
def main():
    agv_count = int(input("AGV 대수: "))
    sim_duration = int(input("시뮬레이션 종료 시간(초, 예: 28800): "))

    # 추가) 사용자에게 '몇 초 간격으로 하역량을 볼건지' 입력받기
    chunk_size = int(input("하역량을 확인할 시간 간격(초) 입력 (예: 600): "))

    all_runs_end_time = []
    all_runs_final_delivered = []
    all_runs_delivered_record = []  # 매초 delivered_count 기록
    all_runs_agv_stats = []         # 각 run의 AGV stats

    for run_i in range(1, REPEAT_RUNS+1):
        result = run_one_sim(agv_count, sim_duration, run_i)
        all_runs_end_time.append(result["end_time"])
        all_runs_final_delivered.append(result["delivered_count"])
        all_runs_delivered_record.append(result["delivered_record"])
        all_runs_agv_stats.append(result["agv_stats"])

    # ====== 15회 결과 요약 ======
    avg_end_time = sum(all_runs_end_time) / REPEAT_RUNS
    avg_final_delivered = sum(all_runs_final_delivered) / REPEAT_RUNS

    print("\n===========================")
    print("15회 반복 실험 결과 요약")
    print("===========================")
    print(f" - 평균 종료 시각: {avg_end_time:.2f} 초")
    print(f" - 평균 최종 하역 건수: {avg_final_delivered:.2f}")

    # 1) 구간별(사용자가 지정한 chunk_size) 하역량
    #    각 run별 delivered_record[t] = t초까지 누적 하역
    #    0~chunk_size 구간 = get_delivered_up_to(chunk_size) - get_delivered_up_to(0)
    #    chunk_size~2*chunk_size = get_delivered_up_to(2*chunk_size) - get_delivered_up_to(chunk_size)
    #    ...
    print(f"\n=== {chunk_size}초 간격 구간별 하역 건수 (평균) ===")

    chunk_results_list = []  # run별 { "구간이름": 그 구간 배달량 }

    for run_idx in range(REPEAT_RUNS):
        record = all_runs_delivered_record[run_idx]
        run_chunk_dict = {}

        prev_t = 0
        prev_val = get_delivered_up_to(record, 0)
        t = chunk_size

        # chunk 단위로 반복
        while t <= sim_duration:
            cur_val = get_delivered_up_to(record, t)
            delta = cur_val - prev_val
            chunk_name = f"{prev_t}~{t}"
            run_chunk_dict[chunk_name] = delta

            prev_t = t
            prev_val = cur_val
            t += chunk_size

        chunk_results_list.append(run_chunk_dict)

    # 구간 목록
    # (모든 run에서 동일 구간이 생길 것이라 가정: 0~chunk_size, chunk_size~2chunk_size, ...)
    if chunk_size > 0:
        max_chunks = sim_duration // chunk_size  # 정수 나눗셈
        chunk_keys = [f"{i*chunk_size}~{(i+1)*chunk_size}" for i in range(max_chunks)]
    else:
        chunk_keys = []

    # 각 구간별 15회 평균
    for ck in chunk_keys:
        s = 0
        for rcd in chunk_results_list:
            s += rcd.get(ck, 0)
        avg_chunk = s / REPEAT_RUNS
        print(f" - 구간 {ck} : 평균 {avg_chunk:.2f} 개")

    # 2) AGV별 15회 통계
    from collections import defaultdict
    agv_aggregator = defaultdict(lambda: {"count_sum": 0, "times_all": []})

    for run_idx in range(REPEAT_RUNS):
        agv_stats_map = all_runs_agv_stats[run_idx]
        for aid, st in agv_stats_map.items():
            agv_aggregator[aid]["count_sum"] += st["count"]
            agv_aggregator[aid]["times_all"].extend(st["times"])

    print("\n=== AGV별 평균 통계 (15회 결과) ===")
    for aid in sorted(agv_aggregator.keys()):
        total_count = agv_aggregator[aid]["count_sum"]
        times_list = agv_aggregator[aid]["times_all"]
        avg_count = total_count / REPEAT_RUNS
        avg_time = (sum(times_list)/len(times_list)) if times_list else 0
        print(f" AGV{aid}: "
              f"(평균 픽업 횟수) {avg_count:.2f}, "
              f"(소요시간 평균) {avg_time:.2f}s")


if __name__ == "__main__":
    main()
