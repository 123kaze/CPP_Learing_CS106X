from functools import lru_cache
from typing import List



class Solution:
    def rob(self, nums: List[int]) -> int:
        '''
        :param nums:
        :return: 偷盗的金额数目
        dfs(i) = max(dfs(i-1),dfs(i-2)+nums[i])
        '''
        n = len(nums)
        @lru_cache(None)
        def dfs(i):
            if i < 0:
                return 0
            return max(dfs(i-1),dfs(i-2)+nums[i])

        return dfs(n-1)