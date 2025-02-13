# common.py
from collections import deque

##############################################################################
# 지도 정보
##############################################################################
map_data = [
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
ROWS = len(map_data)
COLS = len(map_data[0])

shelf_coords = [(2,2),(2,4),(2,6),
                (5,2),(5,4),(5,6)]
exit_coords = [(0,c) for c in range(COLS) if map_data[0][c] == 2]

##############################################################################
# BFS 경로 탐색
##############################################################################
def bfs_path(grid, start, goal, obstacles=set()):
    """
    start부터 goal까지의 전체 경로(list)를 BFS로 탐색. obstacles는 점유 좌표(set).
    """
    if not start or not goal:
        return None
    queue = deque([(start, [start])])
    visited = set([start])
    directions = [(0,1),(0,-1),(1,0),(-1,0)]
    while queue:
        curr, path = queue.popleft()
        if curr == goal:
            return path
        r, c = curr
        for dr, dc in directions:
            nr, nc = r+dr, c+dc
            if 0<=nr<ROWS and 0<=nc<COLS:
                if grid[nr][nc] != 1 and ((nr,nc) == goal or (nr,nc) not in obstacles):
                    if (nr,nc) not in visited:
                        visited.add((nr,nc))
                        queue.append(((nr,nc), path+[(nr,nc)]))
    return None

##############################################################################
# 이동 방향 계산 함수
##############################################################################
def compute_direction(curr, nxt):
    """
    curr→nxt 이동 시 상하좌우(u, d, R, L)를 반환
    """
    dr = nxt[0] - curr[0]
    dc = nxt[1] - curr[1]
    if dr == -1 and dc == 0:
        return "u"
    elif dr == 1 and dc == 0:
        return "d"
    elif dr == 0 and dc == 1:
        return "R"
    elif dr == 0 and dc == -1:
        return "L"
    else:
        return ""

##############################################################################
# 인접 좌표 반환
##############################################################################
def available_moves(pos):
    """
    pos를 기준으로 상하좌우 유효 좌표를 리스트로 반환.
    """
    moves = []
    for (dr, dc) in [(0,1),(0,-1),(1,0),(-1,0)]:
        new_r, new_c = pos[0]+dr, pos[1]+dc
        if 0<=new_r<ROWS and 0<=new_c<COLS and map_data[new_r][new_c]!=1:
            moves.append((new_r, new_c))
    return moves

##############################################################################
# 데드락 여부 확인 함수
##############################################################################
def is_deadlocked(pos, occupied):
    """
    pos가 인접 좌표 모두 다른 AGV 등으로 막혀 있으면 True(데드락).
    occupied: 점유 좌표 집합
    """
    for m in available_moves(pos):
        if m not in occupied:
            return False
    return True
