from typing import List
from functools import cache
def zero_one_knapsack(capacity: int, w: List[int], v: List[int]) -> int:
    n = len(w)
    '''dfs(i,c) = max(dfs(i-1,c),dfs(i,c-w[i])+v[i])'''
    cache1 = [[0]*(capacity+1) for i in range(n+1)]


    def dfs(i,c):
        if i < 0:
            return 0
        if cache1[i][c] != 0 :
            return cache1[i][c]
        if c < w[i]:
            res = dfs(i-1,c)
        else:
            res = max(dfs(i-1,c),dfs(i-1,c-w[i])+v[i])
        cache1[i][c] = res
        return res

    @cache
    def dfs1(i,c):
        if i < 0:
            return 0
        if c < w[i]:
            return dfs1(i-1,c)
        return max(dfs1(i-1,c),dfs1(i-1,c-w[i])+v[i])


    return dfs(n-1,capacity)
class Solution:
    def findTargetSumWays(self, nums: List[int], target: int) -> int:
        '''
        p 正数和，s 全数和，那么有p-(s-p) = target
        s-p 负数和
        2p-s=target
        p = s+t //2
        :param nums:
        :param target:
        :return:  方案数目
        dfs(i,c) = dfs(i-1,c)+dfs(i,c-w[i]) 因为是方案数目不是max
        '''
        n = len(nums)
        s = sum(nums)
        t = s+target
        if t<0 or t%2:
            return 0
        t//=2
        @cache
        def dfs(i,c):
            '''
            :param i: 当前选哪个 n
            :param c: 当前空余容量 t
            :return:  方案数目
            '''
            if i<0:
                return 1 if c == 0 else 0
            if c<nums[i]:
                return dfs(i-1,c)
            return dfs(i-1,c)+dfs(i-1,c-nums[i])

        f = [[0]*(t+1) for i in range(n+1)]
        f[0][0] =1
        for i,x in enumerate(nums):
            for c in range(t+1):
                if c < x:
                    f[i+1][c] = f[i][c]
                    continue
                f[i+1][c] = f[i][c] + f[i][c-x]

        return f[n][t]