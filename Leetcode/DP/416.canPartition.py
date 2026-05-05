from functools import cache
from typing import List
class Solution:
    def canPartition(self, nums: List[int]) -> bool:
        n = len(nums)
        s = sum(nums)
        if s % 2 != 0:
            return False
        s = s // 2
        @cache
        def dfs(i,j)->bool:
            '''
            边界：i==0,j==0
            :param i: 当前第i个
            :param j: target值
            :return:
            dfs(i,j) = dfs(i-1,j) or dfs(i-1,j-nums[i])
            '''
            if i <0 :
                return True if j == 0 else False
            if j < nums[i] :
                return dfs(i-1,j)
            return dfs(i-1,j) or dfs(i-1,j-nums[i])


        return dfs(n-1,s)
