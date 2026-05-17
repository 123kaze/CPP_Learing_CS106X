from typing import List


class Solution:
    def numIslands(self, grid: List[List[str]]) -> int:
        dirc = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        m = len(grid)
        n = len(grid[0])
        res = 0

        def dfs(i, j):
            num = grid[i][j]
            grid[i][j] = "0"
            if num == "0":
                return
            if num == "1":
                for dx, dy in dirc:
                    nx, ny = dx + i, dy + j
                    if 0 <= nx < m and 0 <= ny < n and grid[nx][ny] == "1":
                        dfs(nx, ny)

        for i in range(m):
            for j in range(n):
                if grid[i][j] == "1":
                    res += 1
                    dfs(i, j)

        return res


s = Solution()
print(
    s.numIslands(
        [
            ["1", "1", "0", "0", "0"],
            ["1", "1", "0", "0", "0"],
            ["0", "0", "1", "0", "0"],
            ["0", "0", "0", "1", "1"],
        ]
    )
)
