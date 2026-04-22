from functools import cache
from typing import List
class Solution:
    def canPartition(self, nums: List[int]) -> bool:
        n = len(nums)

        @cache
        def dfs(i):
            '''
            :param i:
            :return:
            '''
            if i == 0:
                return False