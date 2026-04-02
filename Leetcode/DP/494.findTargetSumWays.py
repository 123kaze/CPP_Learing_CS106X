from functools import cache
from typing import List

from pyparsing import nums


class Solution:
    def findTargetSumWays(self, nums: List[int], target: int) -> int:
        # p zhangsu
        # s 所有元素和，s-p为负数和
        # p-(s-p) = target
        # p = (s+t)/2
        '''
        dfs(i,c) = dfs(i-1,c)+dfs(i-1,c-wi)
        '''
        n = len(nums)
        target +=sum(nums)
        target//=2
        if target%2==1 or target <0:
            return 0
        f = [[0]*(target+1) for i in range(n+1)]
        f[0][0] = 1
        for i,x in enumerate(nums):
            for c in range(target+1):
                if c < x:
                    f[i+1][c] = f[i][c]
                else:
                    f[i+1][c] = f[i][c]+f[i][c-x]
        return f[n][target]


    def zeroOneKnapsack(self, capacity:int,w:List[int],v:List[int]) -> int:
        n = len(w)
        @cache
        def dfs(i,c):
            if i<0:
                return 0
            if c<w[i]:
                return dfs(i-1,c)
            return max(dfs(i-1,c),dfs(i-1,c-w[i])+v[i])

