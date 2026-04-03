
from typing import List
from math import inf

class Solution:
    def maximumAmount(self, coins: List[List[int]]) -> int:
        m, n = len(coins), len(coins[0])
        # dp[i][j][k] 中的 k 表示“已经使用了几次机会”
        dp = [[[-inf for _ in range(3)] for _ in range(n + 1)] for _ in range(m + 1)]

        # 初始化：给出一个“虚空”入口
        for k in range(3):
            dp[0][1][k] = 0

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                x = coins[i-1][j-1]
                for k in range(3):
                    # 【核心修正 1】：不管 x 正负，都可以选择“不消耗机会硬扛”
                    res = max(dp[i-1][j][k], dp[i][j-1][k]) + x

                    # 【核心修正 2】：只有 x < 0 且此时有可用机会（k > 0）时，才尝试抵消
                    # 抵消意味着当前格子计为 0，且从“已使用 k-1 次”的状态转移过来
                    if x < 0 and k > 0:
                        res = max(res, dp[i-1][j][k-1], dp[i][j-1][k-1])

                    dp[i][j][k] = res

        # 最终结果是到达终点时，使用了 0, 1, 2 次机会中的最大值
        return dp[m][n][2]
