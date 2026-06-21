from typing import List
class Solution:
    def maxAreaOfIsland(self, grid: List[List[int]]) -> int:
        m = len(grid)
        n = len(grid[0])
        res = 0
        curmax = 0
        directions = [[0,1],[1,0],[0,-1],[-1,0]]
        def dfs(i, j):
            nonlocal curmax
            x, y = i, j
            if grid[x][y] == 1:
                curmax+=1
                grid[x][y] = 0

                for dx, dy in directions:
                    nx, ny = x+dx, y+dy
                    if 0<=nx<m and 0<=ny<n and grid[nx][ny]==1:
                        dfs(nx, ny)


        for i in range(m):
            for j in range(n):
                curmax = 0
                dfs(i, j)
                res = max(res, curmax)
        return res