from typing import List

class Solution:
    def minPathSum(self, grid: List[List[int]]) -> int:
        m = len(grid)
        n = len(grid[0])
        directions = [(1,0),(0,1)]
        # 可以dfs，但是我希望用dp来做
        # dp[i][j] 为到这里的最小数字
        # dp[i][j] = min(dp[i-1][j],dp[i][j-1])+grid[i][j]
        dp = [[inf for _ in range(n+1)] for _ in range(m+1)]
        dp[0][1] = 0
        for i in range(1,m+1):
            for j in range(1,n+1):
                dp[i][j] = min(dp[i-1][j],dp[i][j-1]) + grid[i-1][j-1]

        return dp[m][n]
        1 3
        1 5