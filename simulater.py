import simpy
from collections import deque
import random

#############################
# 맵/좌표 및 유틸 설정
#############################

# 지도 (0: 빈 칸, 1: 벽, 2: 출입구)
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

def is_walkable(r, c):
    """지도 범위 내이고, 1(벽)이 아니면 True."""
    return (0 <= r < ROWS) and (0 <= c < COLS) and (MAP[r][c] != 1)

def bfs_path(start, goal):
    """BFS로 start->goal 경로를 찾는다. 없으면 None."""
    if start == goal:
        return [start]
    visited = {start: None}
    queue = deque([start])
    while queue:
        r, c = queue.popleft()
        for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
            nr, nc = r+dr, c+dc
            if is_walkable(nr,nc) and (nr,nc) not in visited:
                visited[(nr,nc)] = (r,c)
                queue.append((nr,nc))
                if (nr,nc) == goal:
                    path = []
                    cur = (nr,nc)
                    while cur is not None:
                        path.append(cur)
                        cur = visited[cur]
                    path.reverse()
                    return path
    return None

########################
# 시뮬레이션 전역 변수
########################

# 선반 좌표 / 출구 좌표
shelf_coords = [(2,2),(2,4),(2,6),(5,2),(5,4),(5,6)]
exit_coords = [(0,c) for c in range(COLS) if MAP[0][c] == 2]

# 선반 Resource(단일점유) & 재고(Container)
shelf_resources = {}  # { shelf: simpy.Resource(capacity=1) }
shelf_stock = {}      # { shelf: simpy.Container(...) }

TIME_LIMIT = 50000    # 최장 시뮬레이션 시간

#############################
# AGV 클래스
#############################

class AGV:
    def __init__(self, agv_id, start_pos, env, priority=1):
        self.id = agv_id
        self.env = env
        self.pos = start_pos   # 현재 위치
        self.target_path = []  # 이동 경로
        self.priority = priority
        self.running = True
        self.cargo = None      # 화물 (None or 1)
        self.work_shelf = None # 현재 할당된 선반

    def __repr__(self):
        return f"AGV(id={self.id}, pos={self.pos}, prio={self.priority})"

#############################
# 중앙 코디네이터
#############################

class Coordinator:
    """
    - 매 틱(1초)마다 AGV '다음 칸' 이동 예약을 모으고, 충돌 시 우선순위로 결정
    - 선반에서는 Resource(capacity=1)로 단일점유 보장 + Container로 재고 관리
    - TIME_LIMIT 넘으면 중단
    """
    def __init__(self, env, agvs):
        self.env = env
        self.agvs = agvs
        self.t = 0
        self.action = env.process(self.run())

    def run(self):
        while True:
            if self.t > TIME_LIMIT:
                print(f"[t={self.t}] 시간 {TIME_LIMIT} 초과 -> Deadlock 등으로 중단.")
                break

            # 모든 선반이 0이고, 모든 AGV가 종료 상태면 끝
            if self.all_shelves_empty() and all(not agv.running for agv in self.agvs):
                break

            # 1) 각 AGV '다음 칸' 이동 예약 수집
            move_requests = []
            for agv in self.agvs:
                if not agv.running:
                    continue
                self.update_agv_target(agv)
                next_cell = None
                if len(agv.target_path) > 1:
                    next_cell = agv.target_path[1]
                if next_cell is not None:
                    move_requests.append((agv, next_cell))

            # 2) 충돌(동일칸) -> 우선순위 조정
            cell_map = {}
            for (agv, cell) in move_requests:
                cell_map.setdefault(cell, []).append(agv)

            losers = []
            for cell, same_req in cell_map.items():
                if len(same_req) > 1:
                    # priority 큰 값이 높은 우선순위
                    same_req.sort(key=lambda a: a.priority, reverse=True)
                    winner = same_req[0]
                    for lz in same_req[1:]:
                        losers.append(lz)

            # losers -> 경로 재탐색
            for lz in losers:
                if len(lz.target_path) > 1:
                    goal = lz.target_path[-1]
                    new_path = bfs_path(lz.pos, goal)
                    if new_path and len(new_path) > 1:
                        lz.target_path = new_path
                    else:
                        pass  # 대기

            # 3) 최종 이동
            final_moves = []
            for (agv, cell) in move_requests:
                if agv not in losers:
                    if len(agv.target_path) > 1 and agv.target_path[1] == cell:
                        final_moves.append((agv, cell))

            # 실제 이동
            for (agv, cell) in final_moves:
                agv.target_path.pop(0)
                agv.pos = cell

            # 4) 선반/출구 작업
            yield self.handle_pickup_and_dropoff()

            # 1초 대기
            yield self.env.timeout(1)
            self.t += 1

            if self.t % 100 == 0:
                active_count = sum(a.running for a in self.agvs)
                st = {s: shelf_stock[s].level for s in shelf_coords}
                print(f"[시각 {self.t}] 남은AGV={active_count}, 재고={st}")

        print("=== 시뮬레이션 종료 ===")

    def handle_pickup_and_dropoff(self):
        """선반 도착 -> Resource request -> 10초 작업 -> 재고 확인 후 get(1)
           출구 도착 -> 10초 하역"""
        events = []
        for agv in self.agvs:
            if not agv.running:
                continue
            # 선반 도착 & 화물없음
            if agv.pos in shelf_coords and agv.cargo is None:
                shelf = agv.pos
                req = shelf_resources[shelf].request()
                ev = self.env.process(self.do_shelf_pickup(agv, shelf, req))
                events.append(ev)
            # 출구 도착 & 화물있음
            elif agv.pos in exit_coords and agv.cargo == 1:
                ev = self.env.process(self.do_dropoff(agv))
                events.append(ev)

        if events:
            return simpy.events.AllOf(self.env, events)
        else:
            return self.env.timeout(0)

    def do_shelf_pickup(self, agv, shelf, req):
        """
        1. 선반 Resource 요청
        2. 10초 작업
        3. 재고가 1 이상 있으면 yield get(1)
        4. 없으면 픽업 실패
        """
        try:
            yield req
            yield self.env.timeout(10)  # 10초간 픽업 시도

            # 재고가 남아있는지 확인
            if shelf_stock[shelf].level > 0:
                yield shelf_stock[shelf].get(1)
                agv.cargo = 1
                print(f"[t={self.env.now}] AGV{agv.id} 선반{shelf} 픽업 성공(남은={shelf_stock[shelf].level})")
            else:
                print(f"[t={self.env.now}] AGV{agv.id} 선반{shelf} 재고없음 -> 실패")
                self.assign_new_shelf(agv)

        finally:
            shelf_resources[shelf].release(req)

    def do_dropoff(self, agv):
        """출구에서 10초 하역"""
        yield self.env.timeout(10)
        agv.cargo = None
        print(f"[t={self.env.now}] AGV{agv.id} 출구{agv.pos} 하역 완료")
        # 새 선반 할당
        self.assign_new_shelf(agv)

    def update_agv_target(self, agv):
        """경로 없으면 선반 or 출구로 목적지 설정."""
        if not agv.running:
            return
        if len(agv.target_path) <= 1:
            # 경로가 없음
            if agv.cargo is None:
                # 화물 없으면 선반
                if agv.work_shelf is None or shelf_stock[agv.work_shelf].level == 0:
                    self.assign_new_shelf(agv)
                if agv.work_shelf:
                    path = bfs_path(agv.pos, agv.work_shelf)
                    if path:
                        agv.target_path = path
                    else:
                        print(f"AGV{agv.id} 선반{agv.work_shelf} 경로X -> 중단")
                        agv.running = False
            else:
                # 화물 있으면 출구
                ex = self.find_nearest_exit(agv.pos)
                p = bfs_path(agv.pos, ex)
                if p:
                    agv.target_path = p
                else:
                    print(f"AGV{agv.id} 출구경로X -> 중단")
                    agv.running = False

    def assign_new_shelf(self, agv):
        """재고>0인 임의의 선반 할당"""
        cand = [s for s in shelf_coords if shelf_stock[s].level > 0]
        if not cand:
            # 재고있는 선반 없음 -> 종료
            agv.running = False
            return
        agv.work_shelf = random.choice(cand)

    def find_nearest_exit(self, pos):
        """맨해튼 거리 최소인 출구"""
        best = None
        best_dist = 999999
        for e in exit_coords:
            d = abs(pos[0]-e[0]) + abs(pos[1]-e[1])
            if d < best_dist:
                best_dist = d
                best = e
        return best

    def all_shelves_empty(self):
        """모든 선반 재고가 0인지?"""
        return all(shelf_stock[s].level == 0 for s in shelf_coords)

##########################
# 시뮬레이션 루틴
##########################

def simulation(env, agv_count, total_items):
    """
    1) 선반 Resource+Container 초기화
    2) AGV 생성
    3) Coordinator 실행
    """
    global shelf_resources, shelf_stock
    per_shelf = total_items // len(shelf_coords)

    # 선반 초기화
    for s in shelf_coords:
        shelf_resources[s] = simpy.Resource(env, capacity=1)
        shelf_stock[s] = simpy.Container(env, capacity=999999, init=per_shelf)

    # AGV 생성
    start_positions = [(8,2),(8,3),(8,4),(8,5)]
    agvs = []
    for i in range(agv_count):
        sp = start_positions[i % len(start_positions)]
        priority = agv_count - i
        agv = AGV(i, sp, env, priority)
        agvs.append(agv)

    coordinator = Coordinator(env, agvs)
    yield env.process(coordinator.run())

def main():
    try:
        agv_count = int(input("Enter the number of AGVs: ").strip())
        total_items = int(input("Enter the total number of items (multiple of 6): ").strip())
        if total_items % 6 != 0:
            raise ValueError("Total items must be a multiple of 6.")

        env = simpy.Environment()
        env.process(simulation(env, agv_count, total_items))
        env.run()

        print("\n=== Simulation Results ===")
        final_stocks = {s: shelf_stock[s].level for s in shelf_coords}
        print("선반별 최종 재고:", final_stocks)

    except Exception as e:
        print("오류 발생:", e)

if __name__ == "__main__":
    main()
