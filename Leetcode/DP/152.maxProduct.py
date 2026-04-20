from typing import List
from functools import cache
class Solution:
    def maxProduct(self, nums: List[int]) -> int:
        n = len(nums)

        @cache
        def dfs(i):
            '''
            1.我们用选或者不选来做
            2.我们用选了之后选哪个来做
            :param i:当前数字下表
            :return: 当前为i下标时候，之前返回的数字最大值
            dfs(i) =
            '''
            if i == 0:
                return nums[0],nums[0]
            prevmax , prevmin = dfs(i - 1)
            maxs = max(prevmax*nums[i], prevmin*nums[i],nums[i])
            mins = min(prevmax*nums[i], prevmin*nums[i],nums[i])
            return maxs, mins
        ans = -inf
        for i in range(n):
            ans = max(dfs(i)[0], ans)

        return ans
