from functools import reduce
from typing import List
class Solution:
    def xorAfterQueries(self, nums: List[int], queries: List[List[int]]) -> int:
        n = len(nums)
        q = len(queries)
        MOD = 10**9 + 7
        dic = defaultdict(lambda: 1)
        for li, ri, ki, vi in queries:#优化一：li,ri,ki相同的一起处理
            dic[(li, ri, ki)] = dic[(li, ri, ki)] * vi % MOD
        for (li, ri, ki), vi in dic.items():
            if vi == 1:#优化二：乘1不用算
                continue
            nums[li:ri+1:ki] = [(val * vi) % MOD for val in nums[li:ri+1:ki]]


        return reduce(xor, nums)

solution = Solution()
solution.xorAfterQueries([2,3,1,5,4],[[1,4,2,3],[0,2,1,2]])