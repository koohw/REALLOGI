import heapq

class AStarPathFinder:
    def __init__(self, grid_map):
        self.grid_map = grid_map
        self.width = len(grid_map[0])
        self.height = len(grid_map)

    def _heuristic(self, a, b):
        """맨해튼 거리(Heuristic) 계산"""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def find_path(self, start, goal):
        """
        A* 알고리즘으로 최적 경로를 찾습니다.  화이팅팅 ㅎㅎ 최우수상 드가장~~
        :param start: 시작 위치 (x, y)
        :param goal: 목표 위치 (x, y)
        :return: 경로 리스트 [(x1, y1), (x2, y2), ...]
        """
        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {}
        g_score = {start: 0}
        f_score = {start: self._heuristic(start, goal)}

        while open_set:
            _, current = heapq.heappop(open_set)

            if current == goal:
                return self._reconstruct_path(came_from, current)

            neighbors = self._get_neighbors(current)
            for neighbor in neighbors:
                tentative_g_score = g_score[current] + 1  # 모든 이동 비용은 1로 설정
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + self._heuristic(neighbor, goal)
                    if neighbor not in [item[1] for item in open_set]:
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))

        return []  # 경로를 찾지 못한 경우

    def _reconstruct_path(self, came_from, current):
        """경로를 역추적합니다."""
        path = []
        while current in came_from:
            path.append(current)
            current = came_from[current]
        path.append(current)  # 시작점 추가
        return path[::-1]  # 경로를 뒤집어 반환

    def _get_neighbors(self, position):
        """현재 위치의 이웃을 반환합니다."""
        x, y = position
        neighbors = [
            (x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)
        ]
        valid_neighbors = [
            (nx, ny) for nx, ny in neighbors
            if 0 <= nx < self.width and 0 <= ny < self.height and self.grid_map[ny][nx] == 0
        ]
        return valid_neighbors


# 테스트
if __name__ == "__main__":
    grid = [
        [0, 0, 0, 0, 0],
        [0, 1, 0, 1, 1],
        [0, 1, 0, 1, 0],
        [0, 1, 0, 1, 0],
        [0, 0, 0, 0, 0],
    ]

    path_finder = AStarPathFinder(grid)
    start = (0, 0)
    goal = (4, 4)
    path = path_finder.find_path(start, goal)

    print("격자 지도:")
    for row in grid:
        print(" ".join(str(cell) for cell in row))

    print("\n최단 경로:")
    print(path)
