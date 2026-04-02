from typing import List
class Solution:
    def mincostTickets(self, days: List[int], costs: List[int]) -> int:
        # n =len(days)
        # m = len(costs)
        # f = [[[0]*(day+1) for _ in range(n)] for day in days]
        # for x in days:
        #     f[x][0][0] = 0
        # for d in range(n+1):
        #     for i,x in enumerate(days):
        #         for c in costs:
        #             if c < x:
        #                 f[d][i+1][c] = f[d][i][c]
        #             else:
        #                 f[d][i+1][c] = min(f[d][i][c], f[d][i+1][c-x])
        last = days[-1]
        dp = [0]*(last+1)
        travel = set(days)
        for i in range(1,last+1):
            if i not in travel:
                dp[i] = dp[i-1]
            else:
                dp[i] = min(dp[i-1]+costs[0],dp[max(i-7,0)]+costs[1],dp[max(i-30,0)]+costs[2])

        return dp[last]