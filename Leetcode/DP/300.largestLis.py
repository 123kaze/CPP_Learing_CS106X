from functools import lru_cache,cache
from typing import List
class Solution:
    def lengthOfLIS(self, nums: List[int]) -> int:
        n = len(nums)
        @cache
        def dfs(i):
            '''
            :param i:  子序列最后一个数字下标
            :return: 以i为最后一个下表，返回的数字是多少
            '''
            res = 0
            for j in range(i):
                if nums[j] < nums[i]:
                    res = max(res,dfs(j))

            return res+1

        return max(dfs(i)for i in range(n))