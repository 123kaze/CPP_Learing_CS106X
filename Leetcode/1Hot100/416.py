from typing import List
from functools import lru_cache

class Solution:
    def canPartition(self, nums: List[int]) -> bool:
        n = len(nums)
        if n<=1:
            return True
        s = sum(nums)
        if s%2:
            return False
        t = s//2
        @lru_cache(None)
        def dfs(i,j):
            '''
            从0到i,能不能选出和为j的组合
            1.dfs(i,j) = dfs(i-1,j),j<nums[i]
            2.dfs(i,j) = dfs(i-1,j)||dfs(i-1,j-nums[i]) , j>=nums[i]
            '''
            if i<0:
                return j==0
            if j<nums[i]:
                return dfs(i-1,j)
            return dfs(i-1,j) or dfs(i-1,j-nums[i])
        
        return dfs(n-1,t)