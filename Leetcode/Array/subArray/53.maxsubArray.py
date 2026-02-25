from typing import List


class Solution:
    def maxSubArray(self, nums: List[int]) -> int:
        current = maxs = nums[0]
        for num in nums[1:]:
            current = max(current + num, num)
            maxs = max(maxs, current)

        return maxs
