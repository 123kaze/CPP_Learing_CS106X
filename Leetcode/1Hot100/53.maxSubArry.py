from typing import List


class Solution:
    def maxSubArray(self, nums: List[int]) -> int:
        n = len(nums)
        res = nums[0]
        i = 0
        cur = 0
        for j in range(n):
            cur = cur + nums[j]
            res = max(res, cur)
            if cur < 0:
                cur = 0

        return res
