from typing import List
from collections import deque, defaultdict


class Solution:
    def orangesRotting(self, grid: List[List[int]]) -> int:
        m = len(grid)
        n = len(grid[0])
        q = deque()

        for i in range(m):
            for j in range(n):
                if grid[i][j] == 2:
                    q.append((i, j))
        count = 0
        ne = len(q)
        dire = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        while q:
            ne = len(q)
            haveNew = False
            for _ in range(ne):
                x, y = q.popleft()
                for dx, dy in dire:
                    if (
                        0 <= x + dx < m
                        and 0 <= y + dy < n
                        and grid[x + dx][y + dy] == 1
                    ):
                        q.append((x + dx, y + dy))
                        grid[x + dx][y + dy] = 2
                        haveNew = True
            if haveNew:
                count += 1

        for i in range(m):
            for j in range(n):
                if grid[i][j] == 1:
                    return -1

        return count
